import numpy as np
from scipy.fft import fft
from scipy.stats import kurtosis, skew

def extract_vibration_features(signal, sampling_rate=10000):
    """
    Extract 3 simplified features for bearing fault detection
    
    1. RMS - Root Mean Square (Energy)
    2. Kurtosis - Signal impulsiveness (>3 = fault)
    3. Mean_Freq - Center frequency of energy
    """
    
    features = []
    
    # 1. RMS (Root Mean Square)
    rms = np.sqrt(np.mean(signal**2))
    features.append(rms)
    
    # 2. Kurtosis - Signal impulsiveness
    kurt = kurtosis(signal, fisher=False)
    features.append(kurt)
    
    # 3. Mean Frequency
    fft_vals = np.abs(fft(signal))
    frequencies = np.fft.fftfreq(len(signal), 1/sampling_rate)[:len(signal)//2]
    power_spectrum = fft_vals[:len(signal)//2]
    
    mean_freq = np.sum(frequencies * power_spectrum) / (np.sum(power_spectrum) + 1e-10)
    features.append(mean_freq)
    
    return np.array(features)


def get_feature_names():
    """Return names of 3 features"""
    return ['RMS', 'Kurtosis', 'Mean_Freq']
