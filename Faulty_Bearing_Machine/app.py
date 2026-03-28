from flask import Flask, render_template, request, jsonify
import joblib
import numpy as np
import pandas as pd
import os
from vibration_features import extract_vibration_features, get_feature_names
from feature_extractor import extract_comprehensive_features, get_feature_names as get_14_feature_names

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates'))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Load the trained model, scaler, and class names
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model = joblib.load(os.path.join(BASE_DIR, 'model.pkl'))
scaler = joblib.load(os.path.join(BASE_DIR, 'scaler.pkl'))
class_names = joblib.load(os.path.join(BASE_DIR, 'class_names.pkl'))  # {0: Normal, 1: Inner, 2: Outer, 3: Ball}

def load_csv_signal(file_path):
    """Load signal from CSV file with flexible parsing"""
    try:
        # First, try to read with semicolon separator (European format)
        try:
            df = pd.read_csv(file_path, sep=';', decimal=',')
            # If we got data, use the second column (Measurements) if it exists
            if len(df.columns) > 1:
                signal = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().values.astype(np.float64)
                if len(signal) > 0:
                    return signal
            # Otherwise use first column
            signal = pd.to_numeric(df.iloc[:, 0], errors='coerce').dropna().values.astype(np.float64)
            if len(signal) > 0:
                return signal
        except:
            pass
        
        # Try comma separator
        try:
            df = pd.read_csv(file_path, sep=',')
            if len(df.columns) > 1:
                signal = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().values.astype(np.float64)
                if len(signal) > 0:
                    return signal
            signal = pd.to_numeric(df.iloc[:, 0], errors='coerce').dropna().values.astype(np.float64)
            if len(signal) > 0:
                return signal
        except:
            pass
        
        # Try simpler parsing on raw file  
        with open(file_path, 'r') as f:
            lines = f.readlines()
            measurements = []
            # Skip header line if present
            start_idx = 1 if (lines and ('Case_No' in lines[0] or 'Signal' in lines[0] or 'Measurement' in lines[0])) else 0
            for line in lines[start_idx:]:
                parts = line.strip().split(';')
                if len(parts) > 1:
                    try:
                        val = float(parts[1].replace(',', '.'))
                        measurements.append(val)
                    except:
                        try:
                            val = float(parts[0].replace(',', '.'))
                            measurements.append(val)
                        except:
                            pass
            
            if len(measurements) > 0:
                return np.array(measurements, dtype=np.float64)
    
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None
    return None

def predict_bearing_condition(signal):
    """Predict bearing condition from signal and compute all 14 features"""
    segment_size = 512
    predictions = []
    confidences = []
    features_3_list = []       # 3 features for prediction
    features_14_list = []      # 14 comprehensive features for display
    
    if len(signal) < segment_size:
        return None, None, None, None, "Signal too short. Minimum 512 samples required."
    
    # Extract features from segments
    for i in range(0, len(signal) - segment_size, segment_size):
        segment = signal[i:i+segment_size]
        
        # 3 features for model prediction
        features_3 = extract_vibration_features(segment)
        features_3_list.append(features_3)
        
        # 14 comprehensive features for display
        features_14 = extract_comprehensive_features(segment)
        features_14_list.append(features_14)
        
        # Scale 3 features and predict
        features_scaled = scaler.transform([features_3])[0]
        pred = model.predict([features_scaled])[0]
        prob = model.predict_proba([features_scaled])[0]
        
        predictions.append(int(pred))
        confidences.append(float(max(prob)) * 100)
    
    # Get most common prediction
    final_prediction = max(set(predictions), key=predictions.count)
    avg_confidence = np.mean(confidences)
    
    # Average features from all segments
    avg_features_3 = np.mean(features_3_list, axis=0) if features_3_list else None
    avg_features_14 = np.mean(features_14_list, axis=0) if features_14_list else None
    
    return int(final_prediction), float(avg_confidence), avg_features_3, avg_features_14, None

@app.route('/')
def index():
    return render_template('index.html')

def is_feature_dataset(file_path):
    """Check if the CSV contains pre-extracted features (RMS, Kurtosis, Mean_Freq columns)"""
    try:
        df = pd.read_csv(file_path, nrows=2)
        required_cols = {'RMS', 'Kurtosis', 'Mean_Freq'}
        return required_cols.issubset(set(df.columns))
    except:
        return False

def predict_batch_from_features(file_path):
    """Classify each row of a pre-extracted feature dataset and return per-class counts and details"""
    df = pd.read_csv(file_path)
    
    feature_cols = ['RMS', 'Kurtosis', 'Mean_Freq']
    X = df[feature_cols].values
    
    # Scale features
    X_scaled = scaler.transform(X)
    
    # Predict each row
    predictions = model.predict(X_scaled)
    probabilities = model.predict_proba(X_scaled)
    
    # Count per class
    counts = {}
    for class_id, class_label in class_names.items():
        counts[class_label] = int(np.sum(predictions == class_id))
    
    # Build per-sample results
    sample_results = []
    for i in range(len(predictions)):
        pred_class = int(predictions[i])
        sample_results.append({
            'sample_index': i + 1,
            'predicted_class': class_names[pred_class],
            'confidence': round(float(max(probabilities[i])) * 100, 2),
            'RMS': round(float(X[i][0]), 6),
            'Kurtosis': round(float(X[i][1]), 6),
            'Mean_Freq': round(float(X[i][2]), 6),
        })
    
    avg_confidence = round(float(np.mean(np.max(probabilities, axis=1)) * 100), 2)
    
    # Compute per-class feature statistics
    class_features = {}
    for class_id, class_label in class_names.items():
        mask = predictions == class_id
        if np.sum(mask) == 0:
            continue
        class_X = X[mask]
        class_stats = {}
        for j, feat_name in enumerate(feature_cols):
            vals = class_X[:, j]
            class_stats[feat_name] = {
                'avg': round(float(np.mean(vals)), 6),
                'min': round(float(np.min(vals)), 6),
                'max': round(float(np.max(vals)), 6),
                'std': round(float(np.std(vals)), 6),
            }
        class_features[class_label] = {
            'count': int(np.sum(mask)),
            'avg_confidence': round(float(np.mean(np.max(probabilities[mask], axis=1)) * 100), 2),
            'features': class_stats,
        }
    
    return {
        'mode': 'batch',
        'total_samples': len(predictions),
        'class_counts': counts,
        'average_confidence': avg_confidence,
        'class_features': class_features,
        'sample_results': sample_results,
        'status': 'success'
    }

@app.route('/predict', methods=['POST'])
def predict():
    """Handle file upload and prediction - auto-detects batch feature dataset vs raw signal"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are supported'}), 400
        
        # Save file temporarily
        temp_path = 'temp_upload.csv'
        file.save(temp_path)
        
        # Check if it's a feature dataset (has RMS, Kurtosis, Mean_Freq columns)
        if is_feature_dataset(temp_path):
            result = predict_batch_from_features(temp_path)
            os.remove(temp_path)
            return jsonify(result), 200
        
        # Otherwise treat as raw vibration signal
        signal = load_csv_signal(temp_path)
        
        if signal is None:
            os.remove(temp_path)
            return jsonify({'error': 'Failed to read CSV file. Ensure it has numeric data.'}), 400
        
        # Make prediction
        prediction, confidence, features_3, features_14, error = predict_bearing_condition(signal)
        
        if error:
            os.remove(temp_path)
            return jsonify({'error': error}), 400
        
        # Clean up
        os.remove(temp_path)
        
        # Build 3-feature dict (used for prediction)
        feature_names_3 = get_feature_names()
        features_dict = {}
        if features_3 is not None:
            for name, value in zip(feature_names_3, features_3):
                features_dict[name] = round(float(value), 4)
        
        # Build 14-feature dict (comprehensive analysis)
        feature_names_14 = get_14_feature_names()
        comprehensive_features = {}
        if features_14 is not None:
            for name, value in zip(feature_names_14, features_14):
                comprehensive_features[name] = round(float(value), 6)
        
        result = {
            'mode': 'single',
            'bearing_condition': class_names[prediction],
            'prediction_class': int(prediction),
            'confidence': round(float(confidence), 2),
            'signal_samples': int(len(signal)),
            'features': features_dict,
            'comprehensive_features': comprehensive_features,
            'status': 'success'
        }
        
        return jsonify(result), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/info')
def info():
    """Return model information"""
    feature_names = get_feature_names()
    return jsonify({
        'model_type': 'Random Forest Classifier (Vibration Dataset)',
        'classes': class_names,
        'num_features': 3,
        'features': feature_names,
        'feature_descriptions': {
            'RMS': 'Root Mean Square - Signal energy level',
            'Kurtosis': 'Signal impulsiveness (>3 indicates fault)',
            'Mean_Freq': 'Center frequency of energy'
        },
        'segment_size': 512,
        'accuracy': 1.0,
        'training_samples': 224,
        'test_samples': 56,
        'status': 'ready'
    })

@app.route('/features')
def features_page():
    """Render the features explanation page"""
    return render_template('features.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
