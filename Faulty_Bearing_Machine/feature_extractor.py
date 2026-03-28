import numpy as np
from scipy.fft import fft
from scipy import signal as sp_signal
from scipy.stats import kurtosis, skew

def extract_comprehensive_features(signal, sampling_rate=10000):
    """
    Extract 14 comprehensive features for bearing fault detection
    
    Time Domain (7 features):
    1. RMS - Root Mean Square (Energy)
    2. Peak Value - Maximum absolute value (Severity)
    3. Peak-to-Peak - max(x) - min(x) (Range)
    4. Kurtosis - E[x⁴]/σ⁴ (Impulsiveness, >3 indicates fault)
    5. Skewness - E[(x-μ)³]/σ³ (Asymmetry)
    6. Crest Factor - Peak/RMS (Spikiness)
    7. Impulse Factor - Peak/Mean|x| (Impact strength)
    
    Frequency Domain (7 features):
    8. Mean Frequency - ∑(f⋅P(f))/∑P(f) (Energy center)
    9. RMS Frequency - √(∑(f²⋅P(f))/∑P(f)) (Spread)
    10. Centroid Frequency - weighted mean (Balance point)
    11. Spectral Kurtosis - Kurtosis of frequency domain
    12. BPFO Energy Ratio - Outer race bearing fault indicator
    13. BPFI Energy Ratio - Inner race bearing fault indicator
    14. Harmonic Ratio - Multiples of shaft speed
    """
    
    features = []
    
    # ========== TIME DOMAIN FEATURES ==========
    
    # 1. RMS (Root Mean Square) - √(1/N ∑x²)
    rms = np.sqrt(np.mean(signal**2))
    features.append(rms)
    
    # 2. Peak Value - max|x|
    peak_value = np.max(np.abs(signal))
    features.append(peak_value)
    
    # 3. Peak-to-Peak - max(x) - min(x)
    peak_to_peak = np.max(signal) - np.min(signal)
    features.append(peak_to_peak)
    
    # 4. Kurtosis - E[x⁴]/σ⁴ (Fisher=True means subtract 3 for normal distribution)
    kurt = kurtosis(signal, fisher=False)  # Pearson's definition
    features.append(kurt)
    
    # 5. Skewness - E[(x-μ)³]/σ³
    skewness = skew(signal)
    features.append(skewness)
    
    # 6. Crest Factor - Peak/RMS
    crest_factor = peak_value / (rms + 1e-10)
    features.append(crest_factor)
    
    # 7. Impulse Factor - Peak/Mean|x|
    mean_abs = np.mean(np.abs(signal))
    impulse_factor = peak_value / (mean_abs + 1e-10)
    features.append(impulse_factor)
    
    # ========== FREQUENCY DOMAIN FEATURES ==========
    
    # Compute FFT
    fft_vals = np.abs(fft(signal))
    frequencies = np.fft.fftfreq(len(signal), 1/sampling_rate)[:len(signal)//2]
    power_spectrum = fft_vals[:len(signal)//2]
    
    # 8. Mean Frequency - ∑(f⋅P(f))/∑P(f)
    mean_freq = np.sum(frequencies * power_spectrum) / (np.sum(power_spectrum) + 1e-10)
    features.append(mean_freq)
    
    # 9. RMS Frequency - √(∑(f²⋅P(f))/∑P(f))
    rms_freq = np.sqrt(np.sum((frequencies**2) * power_spectrum) / (np.sum(power_spectrum) + 1e-10))
    features.append(rms_freq)
    
    # 10. Centroid Frequency - weighted mean frequency
    centroid_freq = np.sum(frequencies * (power_spectrum**2)) / (np.sum(power_spectrum**2) + 1e-10)
    features.append(centroid_freq)
    
    # 11. Spectral Kurtosis - Kurtosis of frequency domain
    spectral_kurt = kurtosis(power_spectrum, fisher=False)
    features.append(spectral_kurt)
    
    # ===== BEARING FAULT FREQUENCIES (assuming standard bearing) =====
    # These are proportions of shaft speed (fs)
    # For bearing fault detection, we look for energy concentration at specific frequencies
    
    shaft_speed = mean_freq / 100 if mean_freq > 0 else 1  # Estimate shaft speed
    
    # Ball Pass Frequency Outer race (BPFO) ≈ 3.57 * fs for typical bearings
    # Ball Pass Frequency Inner race (BPFI) ≈ 5.43 * fs for typical bearings
    
    bpfo_freq = 3.57 * shaft_speed
    bpfi_freq = 5.43 * shaft_speed
    
    # 12. BPFO Energy Ratio - Energy concentration at outer race frequency
    freq_band_width = 500  # Hz bandwidth around BPFO
    bpfo_band = np.abs(frequencies - bpfo_freq) < freq_band_width
    bpfo_energy = np.sum(power_spectrum[bpfo_band]) / (np.sum(power_spectrum) + 1e-10)
    features.append(bpfo_energy)
    
    # 13. BPFI Energy Ratio - Energy concentration at inner race frequency
    bpfi_band = np.abs(frequencies - bpfi_freq) < freq_band_width
    bpfi_energy = np.sum(power_spectrum[bpfi_band]) / (np.sum(power_spectrum) + 1e-10)
    features.append(bpfi_energy)
    
    # 14. Harmonic Ratio - Measure of harmonic content (multiples of fundamental)
    # Find fundamental frequency (1st significant peak)
    if len(power_spectrum) > 0:
        peaks, _ = sp_signal.find_peaks(power_spectrum, height=np.max(power_spectrum)*0.1)
        if len(peaks) > 0:
            fundamental_peak = peaks[0]
            fundamental_freq = frequencies[fundamental_peak]
            
            # Find energy in harmonics (multiples of fundamental frequency)
            harmonic_energy = 0
            for harmonic in range(2, 6):  # Check 2nd to 5th harmonics
                harmonic_band = np.abs(frequencies - harmonic * fundamental_freq) < 500
                harmonic_energy += np.sum(power_spectrum[harmonic_band])
            
            fundamental_energy = np.sum(power_spectrum[np.abs(frequencies - fundamental_freq) < 500])
            harmonic_ratio = harmonic_energy / (fundamental_energy + 1e-10)
        else:
            harmonic_ratio = 0
    else:
        harmonic_ratio = 0
    
    features.append(harmonic_ratio)
    
    return np.array(features)


def get_feature_names():
    """Return names of all 14 features"""
    return [
        # Time Domain
        "RMS",
        "Peak Value",
        "Peak-to-Peak",
        "Kurtosis",
        "Skewness",
        "Crest Factor",
        "Impulse Factor",
        # Frequency Domain
        "Mean Frequency",
        "RMS Frequency",
        "Centroid Frequency",
        "Spectral Kurtosis",
        "BPFO Energy Ratio",
        "BPFI Energy Ratio",
        "Harmonic Ratio"
    ]
