from anlffr.helper import biosemi2mne as bs
import mne
import numpy as np
import os
import fnmatch
from scipy.signal import savgol_filter as sg
from scipy.io import savemat


# Setup bayesian-weighted averaging
def bayesave(x, trialdim=0, timedim=1, method='mean', smoothtrials=19):
    ntrials = x.shape[trialdim]
    if method == 'mean':
        summary = x.mean(axis=trialdim) * (ntrials) ** 0.5
    else:
        summary = np.median(x, axis=trialdim) * (ntrials) ** 0.5

    ntime = x.shape[timedim]
    wts = 1 / np.var(x - summary, axis=timedim, keepdims=True)
    wts = sg(wts, smoothtrials, 3, axis=trialdim)  # Smooth the variance
    normFactor = wts.sum()
    wts = wts.repeat(ntime, axis=timedim)
    ave = (x * wts).sum(axis=trialdim) / normFactor
    return ave


# Adding Files and locations
froot = 'D:/DATA/ABR/'

subjlist = ['S050', ]

earlist = ['L', 'R']


for ear in earlist:
    if ear == 'L':
        conds = [[3, 9], [5, 10], [6, 12]]
        names = ['_L_soft', '_L_moderate', '_L_loud']
    else:
        conds = [[48, 144], [80, 160], [96, 192]]
        names = ['_R_soft', '_R_moderate', '_R_loud']

    for subj in subjlist:
        print 'Running Subject', subj
        for ind, cond in enumerate(conds):
            name = names[ind]
            print 'Doing condition ', cond
            fpath = froot + '/' + subj + '/'
            bdfs = fnmatch.filter(os.listdir(fpath), subj + '_ABR*.bdf')

            if len(bdfs) >= 1:
                for k, bdf in enumerate(bdfs):
                    edfname = fpath + bdf
                    # Load data and read event channel
                    extrachans = [u'GSR1', u'GSR2', u'Erg1', u'Erg2', u'Resp',
                                  u'Plet', u'Temp']
                    raw, eves = bs.importbdf(edfname, nchans=36,
                                             extrachans=extrachans)
                    raw.set_channel_types({'EXG3': 'eeg', 'EXG4': 'eeg'})

                    # Pick channels to not include in epoch rejection
                    raw.info['bads'] += ['EXG3', 'EXG4', 'A1', 'A2', 'A30',
                                         'A7', 'A6', 'A24', 'A28', 'A29',
                                         'A3', 'A11', 'A15', 'A16', 'A17',
                                         'A10', 'A21', 'A20', 'A25']
                    # Filter the data
                    raw.filter(l_freq=130., h_freq=3000, picks=np.arange(36))

                    # Epoch the data
                    tmin, tmax = -0.002, 0.015
                    bmin, bmax = -0.001, 0.001
                    epochs = mne.Epochs(raw, eves, cond, tmin=tmin, proj=False,
                                        tmax=tmax, baseline=(bmin, bmax),
                                        picks=np.arange(36),
                                        reject=dict(eeg=200e-6),
                                        verbose='WARNING')
                    xtemp = epochs.get_data()
                    t = epochs.times * 1e3 - 1.6  # Adjust for delay and use ms
                    # Reshaping so that channels is first
                    if(xtemp.shape[0] > 0):
                        xtemp = xtemp.transpose((1, 0, 2))
                        if(k == 0):
                            x = xtemp
                        else:
                            x = np.concatenate((x, xtemp), axis=1)
                    else:
                        continue
            else:
                RuntimeError('No BDF files found!!')

            # Average data
            goods = [28, 3, 30, 26, 4, 25, 7, 31, 22, 9, 8, 21, 11, 12, 18]
            if ear == 'L':
                refchan = 34
            else:
                refchan = 35

            y = y = x[goods, :, :].mean(axis=0) - x[refchan, :, :]
            z = bayesave(y) * 1e6  # microV

            # Make dictionary and save
            mdict = dict(t=t, x=z)
            savepath = froot + '/ABRresults/'
            savename = subj + name + '_ABR.mat'
            savemat(savepath + savename, mdict)
