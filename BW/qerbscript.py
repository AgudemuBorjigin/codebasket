# -*- coding: utf-8 -*-
"""
Created on Mon Nov  4 22:17:31 2013

Script to analyze BW data and get Qerb
@author: Hari Bharadwaj
"""
from scipy import io
from glob import glob
import pylab as pl
import numpy as np
from scipy import integrate
from scipy.optimize import minimize

rootdir = '/home/hari/Documents/MATLAB/BW/'
subj = 'I25'

flist = glob(rootdir + subj + '/*.mat')
bwlist = []
threshlist = []
asymmlist = []

# Convert from SPL RMS to spectral level SPL
fc = 4000
noisebw = (0.25 + 0.25)*fc
spectralLevel_correction = 10*np.log10(noisebw)


for k, fname in enumerate(flist):
    dat = io.loadmat(fname)   
    if(dat.has_key('bw')):
        bw = dat['bw'].ravel()[0]
        asymm = dat['asymm'].ravel()[0]
        thresh = dat['thresh'].ravel()[0] - spectralLevel_correction
        Ps = dat['soundLevel'].ravel()[0]
        bwlist = bwlist + [bw,]
        asymmlist = asymmlist + [asymm,]
        threshlist = threshlist + [thresh,] 
        if(asymm == 0):
            pl.plot(bw,thresh,'ok',linewidth = 3, ms = 10)
            pl.hold(True)
        elif(asymm == 1):
            pl.plot(bw,thresh,'<b',linewidth = 3, ms = 10)
            pl.hold(True)
        elif(asymm == 2):
            pl.plot(bw,thresh, '>r',linewidth = 3, ms = 10)
            pl.hold(True)
        else:
            print 'Unknown notch shape!'
            
bwlist = np.asarray(bwlist)
threshlist = np.asarray(threshlist)
asymmlist = np.asarray(asymmlist)    

pl.xlabel('Relative Notch Width',fontsize = 20)
pl.ylabel('Masker Spectrum Level at Threshold (dB SPL)',fontsize = 20)
pl.xlim((-0.02, 0.22))
ax = pl.gca()
for tick in ax.xaxis.get_major_ticks():
    tick.label1.set_fontsize(20)
for tick in ax.yaxis.get_major_ticks():
    tick.label1.set_fontsize(20)
pl.show()

def roex(g,p,w,t):
    """roex filter as described in Oxenham and Shera (2003) equation (3)
    
    Oxenham, A. J., & Shera, C. A. (2003). Estimates of human cochlear tuning
    at low levels using forward and simultaneous masking. JARO, 4(4), 541-554.
    
    Parameters
    ----------
    g - Deviation from center frequency (relative)
    p - slope parameter (different for upper and lower sides)
    t - Factor by which second slope is shallower than first
    w - relative weigths slopes (determines where 2nd starts to dominate)
    
    Returns
    -------
    W - filter weighting
    
    Note
    ----
    
    To fit only a slope parameter, set w = 0 (t is immaterial then)
    To fit a roex(p,r), set t = numpy.inf 
    
    """
    W = (1 - w)*(1 + p*g)*np.exp(-1*p*g) + w*(1 + p*g/t)*np.exp(-1*p*g/t)
    return W
    
def intRoexp(g1,g2,p,r):
    """Calculates the integral of the roex(p,r) function from g1 to g2
    
    See Patterson et al., (1982)
    
    Parameters
    ----------
    g1, g2 - Limits of the integral in normalized terms (eg.: g1=0.1,g2=0.35)
    p - SLope parameter
    r - parameter determining transition point
    
    Returns
    --------
    I - Integral under the curve
    
    Patterson, R. D., Nimmo-Smith, I., Weber, D. L., and Milroy, R. (1982)
    “The deterioration of hearing with age: Frequency selectivity, the critical
    ratio, the audiogram, and speech threshold,” J. Acoust. Soc. Am. 72,
    1788–1803.
    
    """
    uplimit = -(1 - r)*np.exp(-p*g2)*(2 + p*g2)/p + r
    lowlimit = -(1 - r)*np.exp(-p*g1)*(2 + p*g1)/p + r
    
    I = uplimit - lowlimit
    return I
    
    
    
def noiseEnergy(noiselevel,bw,asymm,pu,pd,w,t,onehighslope = True):
    """Calculates the noise energey leaking into the roex filter
    
    Parameters
    ----------
    
    bw - Notch width
    asymm - Asymmetry - 0 (symmetric), 1 (farther on lowside) or 2 (high-side)
    pu - Upside slope parameter
    pd - lowside slope parameter
    w - relative weigths of slopes
    t - factor of slopes
    noiselevel - spectral level in SPL of the masker (i.e per Hz)
    onehighslope - if True, then for the HF side, only the p-parameter is used
    
    Returns
    -------
    N - Noise energy filtered through roex filter
    
    Note
    ----
    Notched noise is of bandwidth 0.25*fc
    
    """
    
    if(asymm == 0):
        if(onehighslope):
            (Nu, err1)  = integrate.quad(roex, bw, bw+0.25, args=(pu,0,1))
        else:
            (Nu, err1)  = integrate.quad(roex, bw, bw+0.25, args=(pu,w,t))
            
        (Nl, err2) = integrate.quad(roex, bw, bw+0.25, args=(pd,w,t))        
    elif(asymm == 1):
        if(onehighslope):
            (Nu, err1)  = integrate.quad(roex, bw, bw+0.25, args=(pu,0,1))
        else:
            (Nu, err1)  = integrate.quad(roex, bw, bw+0.25, args=(pu,w,t))
            
        (Nl, err2) = integrate.quad(roex, bw + 0.2, bw+0.45, args=(pd,w,t))
    elif(asymm == 2):
        if(onehighslope):
            (Nu, err1)  = integrate.quad(roex, bw+0.2, bw+0.45, args=(pu,0,1))
        else:
            (Nu, err1)  = integrate.quad(roex, bw+0.2, bw+0.45, args=(pu,w,t))
            
        (Nl, err2) = integrate.quad(roex, bw, bw+0.25, args=(pd,w,t))
    else:
        print 'Unknown filter type!'
    
    fc = 4000
    N = (Nu + Nl)*(10**(noiselevel/20))*fc
    return N
    
    
        
def fitRoex(params,Ps,bwlist,threshlist,asymmlist):
    """Calculates the squared error between the roex function fit and data
    
    Parameters
    ----------
    params[0]: pu - High frequency side slope parameter
    params[1]: pd - Low frequency side slope parameter
    params[2]: w - relative weigths of slopes
    params[3]: t - factor of slopes
    params[4]: K - Detector efficiency
    threshlist - list of noise levels at threshold
    bwlist - list of relative notchwidths (of the nearer edge)
    asymmlist - List of asymmetries (see noiseEnergy)
    
    Returns
    -------
    sqerr - Sum of squared errors between fit and data
    
    """
    pu = params[0]
    pd = params[1]
    w = params[2]
    t = params[3]
    K = params[4]
    if((bwlist.shape[0] != threshlist.shape[0])
    or (bwlist.shape[0] != asymmlist.shape[0])):
        print 'Invalid Inputs! bwlist, threshlist and asymmlist sizes dont match!'
        return
    else:
        Npoints = bwlist.shape[0]
        
    
    Nlist = np.zeros(Npoints)    
    for k in np.arange(0,Npoints):
        bw = bwlist[k]
        asymm = asymmlist[k]
        thresh = threshlist[k]
        Nlist[k] = noiseEnergy(thresh,bw,asymm,K,pu,pd,w,t)
        
    Ps_estim = 20*np.log10(Nlist) + K
    Ps_true = Ps
    sqerr = ((Ps_estim - Ps_true)**2).sum()
    return sqerr
        
        
