from anlffr.helper import biosemi2mne as bs
import mne
import numpy as np
from anlffr import spectral
from scipy import io
import os
import fnmatch
import pylab as pl

# Adding Files and locations
froot = 'D:/DATA/EFRlevel/'

subjlist = ['S168', 'S170', 'S171', 'S186']

condlist = [[1, 5], [2, 6], [3, 7], [4, 8], 1, 2, 3, 4]
condnames = ['55dB', '65dB', '75dB', '85dB', '55dBpos', '65dBpos',
             '75dBpos', '85dBpos']
overwriteOld = True
for subj in subjlist:
    for k, cond in enumerate(condlist):
        fpath = froot + subj + '/'

        # These are so that the generated files are organized better
        respath = fpath + 'RES/'
        condname = condnames[k]

        print 'Running Subject', subj, 'Condition', condname

        save_raw_name = subj + '_' + condname + '_alltrial.mat'

        if os.path.isfile(respath + save_raw_name) and not overwriteOld:
            print 'Epoched data is already available on disk!'
            print 'Loading data from:', respath + save_raw_name
            x = io.loadmat(respath + save_raw_name)['x']
            fs = 4096.0
        else:
            bdfs = fnmatch.filter(os.listdir(fpath), subj +
                                  '_EFRlevel*.bdf')
            print 'No pre-epoched data found, looking for BDF files'
            print 'Viola!', len(bdfs),  'files found!'

            for k, edfname in enumerate(bdfs):
                # Load data and read event channel
                (raw, eves) = bs.importbdf(fpath + edfname, nchans=34,
                                           refchans=['EXG1', 'EXG2'])

                # raw.set_channel_types({'EXG3': 'eeg', 'EXG4': 'eeg'})
                raw.info['bads'] += ['A1', 'A2', 'A30', 'A7', 'A6', 'A24',
                                     'A28', 'A29', 'A3', 'A11', 'A15', 'A16',
                                     'A17', 'A10', 'A21', 'A20', 'A25']
                raw.drop_channels(raw.info['bads'])
                # Filter the data
                raw.filter(l_freq=2, h_freq=100)
                # MAYBE use w/ filtering picks=np.arange(0, 17, 1))

                # raw.apply_proj()
                fs = raw.info['sfreq']

                # Epoching events of type
                epochs = mne.Epochs(
                    raw, eves, cond, tmin=-0.025, proj=False,
                    tmax=1.025, baseline=(-0.025, 0.0),
                    reject=dict(eeg=200e-6))  # 200 regular, 50 strict

                xtemp = epochs.get_data()

                # Reshaping to the format needed by spectral.mtcpca() and
                # calling it
                if(xtemp.shape[0] > 0):
                    xtemp = xtemp.transpose((1, 0, 2))
                    xtemp = xtemp[:15, :, :]
                    if(k == 0):
                        x = xtemp
                    else:
                        x = np.concatenate((x, xtemp), axis=1)
                else:
                    continue

        nPerDraw = 400
        nDraws = 100
        params = dict(Fs=fs, fpass=[5, 1000], tapers=[1, 1], Npairs=2000,
                      itc=1, nfft=32768)

        Ntrials = x.shape[1]

        print 'Running Mean Spectrum Estimation'
        (S, N, f) = spectral.mtspec(x, params, verbose=True)

        print 'Running CPCA PLV Estimation'
        (cplv, f) = spectral.mtcpca(x, params, verbose=True)

        print 'Running channel by channel PLV Estimation'
        (plv, f) = spectral.mtplv(x, params, verbose=True)

        print 'Running CPCA Power Estimation'
        (cpow, f) = spectral.mtcspec(x, params, verbose=True)

        print 'Running raw spectrum estimation'
        (Sraw, f) = spectral.mtspecraw(x, params, verbose=True)

        # Saving Results
        res = dict(cpow=cpow, plv=plv, cplv=cplv, Sraw=Sraw,
                   f=f, S=S, N=N, Ntrials=Ntrials)

        save_name = subj + '_' + condname + '_EFRlevel_results.mat'

        if (not os.path.isdir(respath)):
            os.mkdir(respath)
        io.savemat(respath + save_name, res)

        if not os.path.isfile(respath + save_raw_name):
            io.savemat(respath + save_raw_name, dict(x=x, subj=subj))

        plotStuff = False
        if plotStuff:
            pl.figure()
            pl.plot(f, plv.T, linewidth=2)
            pl.xlabel('Frequency (Hz)', fontsize=16)
            pl.ylabel('Phase Locking', fontsize=16)
            ax = pl.gca()
            ax.set_xlim([5, 100])
            ax.tick_params(labelsize=16)
            pl.show()
