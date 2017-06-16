import mne
import numpy as np
import os
import fnmatch
from anlffr.helper import biosemi2mne as bs
from anlffr.preproc import find_blinks
from mne.preprocessing.ssp import compute_proj_epochs
from mne.time_frequency import tfr_multitaper

# Adding Files and locations
froot = 'D:/DATA/BindingEEG/'
# froot = '/autofs/cluster/transcend/hari/ObjectFormation/'

subjlist = ['SubjMS', ]
para = 'Binding'
epochs = []
doTFR = False
saveEpochs = False
saveAve = False
for subj in subjlist:

    fpath = froot + subj + '/'

    # These are so that the generated files are organized better
    respath = fpath + 'RES/'

    bdfs = fnmatch.filter(os.listdir(fpath), subj + '_' + para + '*.bdf')
    print 'Viola!', len(bdfs),  'files found!'


    # Load data and read event channel
    rawlist = []
    evelist = []
    for k, rawname in enumerate(bdfs):
        rawtemp, evestemp = bs.importbdf(fpath + rawname, verbose='DEBUG')
        rawlist += [rawtemp, ]
        evelist += [evestemp, ]
    raw, eves = mne.concatenate_raws(rawlist, events_list=evelist)
    
    # raw.info['bads'] += []
    # Filter the data for ERPs
    raw.filter(l_freq=2.0, h_freq=40, l_trans_bandwidth=0.15)

    # raw.apply_proj()
    fs = raw.info['sfreq']
    removeblinks = True

    if removeblinks:
        # SSP for blinks
        blinks = find_blinks(raw, ch_name=['A1', ])
        blinkname = (fpath + subj + '_' + para + '_blinks_erp' + '-eve.fif')
        mne.write_events(blinkname, blinks)
        epochs_blinks = mne.Epochs(raw, blinks, 998, tmin=-0.25,
                                   tmax=0.25, proj=True,
                                   baseline=(-0.25, 0),
                                   reject=dict(eeg=500e-6))
        blink_projs = compute_proj_epochs(epochs_blinks, n_grad=0,
                                          n_mag=0, n_eeg=4,
                                          verbose='DEBUG')
        raw.add_proj(blink_projs)

    evokeds = []
    condnames = ['coh03', 'coh06', 'coh09', 'coh12']
    condlists = [1, 2, 3, 4]
    eves2 = np.zeros((eves.shape[0]*2, 3), dtype=np.int)
    fs_int = int(raw.info['sfreq'])
    for k, row in enumerate(eves):
        eves2[2*k, :] = row + np.asarray([fs_int, 0, 0])
        eves2[2*k + 1, :] = row + np.asarray([2*fs_int, 0, 0])

    for k, condstem in enumerate(condnames):
        condlist = condlists[k]
        print 'Running Subject', subj, 'Condition', condstem

        # Epoching events of type
        epochs = mne.Epochs(raw, eves2, condlist, tmin=-0.4, proj=True,
                            tmax=1.0, baseline=(-0.2, 0.0), name=condstem,
                            reject=dict(eeg=100e-6))
        evokeds += [epochs.average(), ]
        fstem = subj + '_' + para
        if doTFR:
            freqs = np.arange(5., 70., 1.)
            n_cycles = freqs * 0.2
            power, itc = tfr_multitaper(epochs, freqs, n_cycles,
                                        time_bandwidth=2.0, n_jobs=-1)
            fname_pow = fstem + '_pow_' + condstem + '-tfr.h5'
            fname_itc = fstem + '_itc_' + condstem + '-tfr.h5'
            power.save(fpath + fname_pow)
            itc.save(fpath + fname_itc)

        if saveEpochs:
            fname_epochs = fstem + '_' + condstem + '-epo.fif'
            epochs.save(fpath + fname_epochs)

    # Now save overall onset N100
    epochs = mne.Epochs(raw, eves, condlists, tmin=-0.4, proj=True,
                        tmax=1.0, baseline=(-0.2, 0.0), name='onset',
                        reject=dict(eeg=100e-6))
    evokeds += [epochs.average(), ]
    if saveEpochs:
            fname_epochs = fstem + '_onset-epo.fif'
            epochs.save(fpath + fname_epochs)

    if saveAve:
        avename = subj + '_' + para + '_collapse-ave.fif'
        mne.write_evokeds(fpath + avename, evokeds)
