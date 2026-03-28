import joblib
import numpy as np
import pandas as pd
from scipy.fft import fft
import os

# Load model and scaler
model = joblib.load('h:\\HARI\\model.pkl')
scaler = joblib.load('h:\\HARI\\scaler.pkl')

class_names = {0: 'Normal Bearing', 1: 'Inner Race Fault', 2: 'Outer Race Fault'}

def load_csv_file(file_path):
    try:
        df = pd.read_csv(file_path, header=0, sep=';', decimal=',')
        signal = df.iloc[:, 1].values
        if signal.size > 0:
            return signal
        else:
            df = pd.read_csv(file_path, header=None)
            signal = df.values.flatten()
        return signal
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def extract_features(signal):
    features = []
    features.append(np.mean(signal))
    features.append(np.std(signal))
    features.append(np.max(signal))
    features.append(np.min(signal))
    features.append(np.sqrt(np.mean(signal**2)))  # RMS
    fft_vals = np.abs(fft(signal))
    features.append(np.mean(fft_vals))
    features.append(np.max(fft_vals))
    return features

# Test with one file from each category
test_files = {
    'normal': 'h:\\HARI\\data\\normal\\normal_1.csv',
    'inner': 'h:\\HARI\\data\\inner\\inner_1.csv',
    'outer': 'h:\\HARI\\data\\outer\\outer_1.csv'
}

print("Testing model predictions:\n")
print("-" * 60)

for category, file_path in test_files.items():
    if os.path.exists(file_path):
        signal = load_csv_file(file_path)
        
        if signal is not None:
            segment_size = 512
            predictions = []
            probabilities = []
            
            # Test first segment
            if len(signal) >= segment_size:
                segment = signal[:segment_size]
                features = extract_features(segment)
                
                # Scale and predict
                features_scaled = scaler.transform([features])[0]
                pred = model.predict([features_scaled])[0]
                prob = model.predict_proba([features_scaled])[0]
                
                print(f"Category: {category.upper()}")
                print(f"  Prediction: {class_names[pred]} (Class {pred})")
                print(f"  Probabilities:")
                for class_id, class_name in class_names.items():
                    print(f"    - {class_name}: {prob[class_id]*100:.2f}%")
                print("-" * 60)
    else:
        print(f"File not found: {file_path}")
