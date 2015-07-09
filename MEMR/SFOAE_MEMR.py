# -*- coding: utf-8 -*-
"""
Script to analyze MEMR OAE data with pure tone probes

"""
import numpy as np
from os import listdir
import fnmatch
import pylab as pl
from scipy.io import loadmat
from anlffr.tfr import tfr_multitaper, rescale
from statsmodels.robust.scale import stand_mad as mad


def rejecttrials(x, thresh=1.5, bipolar=True):
    """Simple function to reject trials from numpy array data

    Parameters
    ----------
    x : ndarray, shape (n_trials, n_time)
        Data as numpy array
    thresh : float, optional, default 1.5
        Threshold in number of median absolute deviations
    bipolar : boolean, optional, default True
        If odd (even) epoch is bad, also remove next even (previous odd) trial

    Returns
    -------
    list, length n_good_trials
        original array with bad epochs removed

    """

    n_trials, n_times = x.shape
    x_max = mad(x, axis=1)
    x_med = np.median(x_max)
    x_mad = mad(x_max)
    bads = []
    for k in range(n_trials):
        if np.abs(x_max[k] - x_med) > thresh * x_mad:
            bads += [k, ]
            if bipolar is True:
                if np.mod(k, 2) == 0:
                    bads += [k + 1, ]
                else:
                    bads += [k - 1, ]
        else:
            pass
    goods = np.setdiff1d(range(n_trials), np.unique(bads))
    print '%d Good trials Found' % len(goods)
    return goods


# Adding Files and locations
froot = '/Users/Hari/Documents/Data/MEMR/'

subjlist = ['I50']
fs = 48828.125  # Hz
ear = 'right'
freqs = range(650, 751, 25) + range(1000, 1101, 25)

for subj in subjlist:

    subj += ('_' + ear)
    fpath = froot + '/OAE/' + subj + '/'
    # These are so that the generated files are organized better
    respath = fpath + 'RES/'

    print 'Running Subject', subj
    pl.figure(1)
    for kfreq, freq in enumerate(freqs):
        matnames = fnmatch.filter(listdir(fpath), subj + '_' +
                                  str(freq) + 'Hz_SFOAE_MEMR.mat')

        if len(matnames) > 1:
            raise RuntimeError("Multiple files found for same probe"
                               "frequency! Check filenames, organization.")

        dat = loadmat(fpath + matnames[0])

        freq = float(freq)
        if freq != dat['f0'][0][0]:
            raise RuntimeError("File contains data from the wrong probe"
                               "frequency! Cannot continue!")

        P = dat['Pcanal']
        goods = rejecttrials(P, thresh=1.0)
        P_ave = np.mean(P[goods, :], axis=0)

        # Wavelet analysis
        P_env, itc, t = tfr_multitaper(P_ave[None, None, :], fs,
                                       frequencies=[freq, ],
                                       time_bandwidth=2.0, n_cycles=40.)
        P_env = rescale(P_env, t, baseline=(0.3, 0.5), mode='logratio',
                        copy=False)
        pl.figure(1)
        pl.plot(t, P_env.squeeze(), label=(str(freq) + ' Hz'))
        pl.hold(True)
        pl.show()
    pl.figure(1)
    pl.xlabel('Time (s)', fontsize=16)
    pl.ylabel('Ear canal pressure change (dB)', fontsize=16)
    pl.title('Wavelet analysis of MEMR effect', fontsize=16)
    pl.xlim((0.1, 1.2))
    pl.ylim((-0.015, 0.015))
    pl.legend(freqs, loc='best')
