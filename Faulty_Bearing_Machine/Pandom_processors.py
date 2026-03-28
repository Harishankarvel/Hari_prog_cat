import numpy as np
import pandas as pd
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import joblib
from feature_extractor import extract_comprehensive_features, get_feature_names

# Load CSV file
def load_csv_file(file_path):
    try:
        # Try semicolon separator first (European format), then comma
        df = pd.read_csv(file_path, header=0, sep=';', decimal=',')
        # Extract signal from the second column (index 1, 'Measurements')
        signal = df.iloc[:, 1].values
        if signal.size > 0:
            return signal
        else:
            # Fallback: try comma separator
            df = pd.read_csv(file_path, header=None)
            signal = df.values.flatten()
        return signal
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

# Feature extraction
def extract_features(signal):
    """Use comprehensive feature extractor with 14 features"""
    return extract_comprehensive_features(signal)

# Create dataset
def create_dataset(folder_path, label):
    X, y = [], []
    segment_size = 512  # Reduced from 2048 to accommodate smaller datasets
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"Warning: Folder '{folder_path}' does not exist. Skipping.")
        return X, y
    
    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            signal = load_csv_file(os.path.join(folder_path, file))
            
            if signal is None:
                continue
            
            # Only segment if signal is long enough
            if len(signal) >= segment_size:
                for i in range(0, len(signal) - segment_size, segment_size):
                    segment = signal[i:i+segment_size]
                    features = extract_features(segment)
                    X.append(features)
                    y.append(label)
                
    return X, y

# Candidate paths per class (first existing folder will be used)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
class_path_candidates = {
    "normal": [os.path.join(DATA_DIR, "normal")],
    "inner_fault": [os.path.join(DATA_DIR, "inner_fault"), os.path.join(DATA_DIR, "inner")],
    "outer_fault": [os.path.join(DATA_DIR, "outer_fault"), os.path.join(DATA_DIR, "outer")],
    "ball_fault": [os.path.join(DATA_DIR, "ball_fault"), os.path.join(DATA_DIR, "ball")],
}


def resolve_class_paths(path_candidates):
    resolved = {}
    for class_name, candidates in path_candidates.items():
        existing = next((p for p in candidates if os.path.exists(p)), None)
        resolved[class_name] = existing if existing else candidates[0]
    return resolved


# Paths - resolved from candidates
classes = resolve_class_paths(class_path_candidates)

label_map = {name: i for i, name in enumerate(classes)}
inverse_label_map = {i: name for name, i in label_map.items()}

X, y = [], []

print("Loading datasets...")
for name, path in classes.items():
    print(f"  Loading {name} bearing data from {path}...")
    label = label_map[name]
    
    # Check if folder exists
    if not os.path.exists(path):
        print(f"    Warning: Folder '{path}' does not exist. Skipping.")
        continue
    
    file_count = 0
    segment_count = 0
    
    # Process all CSV files in the folder
    for file in sorted(os.listdir(path)):
        if file.endswith(".csv"):
            file_path = os.path.join(path, file)
            signal = load_csv_file(file_path)
            
            if signal is None:
                continue
            
            file_count += 1
            
            # Use overlapping segments (stride of 256 instead of segment_size)
            segment_size = 512
            stride = 256  # 50% overlap
            
            for i in range(0, len(signal) - segment_size + 1, stride):
                segment = signal[i:i+segment_size]
                if len(segment) == segment_size:
                    features = extract_features(segment)
                    X.append(features)
                    y.append(label)
                    segment_count += 1
    
    print(f"    Loaded {file_count} files, created {segment_count} segments")

X = np.array(X)
y = np.array(y)

# Validate dataset
if len(X) == 0 or len(y) == 0:
    print("Error: No data loaded. Please check if data directories exist and contain .csv files.")
    print(f"Current resolved paths: {list(classes.values())}")
    exit()

# Ensure all classes are present before training
present_labels = set(y.tolist())
missing_classes = [cls for cls, lbl in label_map.items() if lbl not in present_labels]
if missing_classes:
    print("Error: Missing samples for classes:", ", ".join(missing_classes))
    print("Please add data for all required classes: inner_fault, outer_fault, normal, ball_fault")
    exit()

print(f"Dataset loaded: {len(X)} samples with {X.shape[1]} features")
for cls_name, lbl in label_map.items():
    print(f"  {cls_name}: {(y == lbl).sum()} samples")

# Train model
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scale features (not required for RF, but kept for consistency if reused elsewhere)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

model = RandomForestClassifier(
    n_estimators=200,          # Number of trees
    max_depth=15,              # Maximum tree depth
    min_samples_split=5,       # Minimum samples to split
    min_samples_leaf=2,        # Minimum samples in leaf
    class_weight='balanced',   # Handle imbalanced data
    random_state=42,
    n_jobs=-1                  # Use all CPU cores
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
target_names = [inverse_label_map[i] for i in sorted(inverse_label_map)]
print(classification_report(y_test, y_pred, target_names=target_names, digits=4))

# Save model, scaler and label map
joblib.dump(model, "model.pkl")
joblib.dump(scaler, "scaler.pkl")
joblib.dump(label_map, "label_map.pkl")
print("Model saved as model.pkl")
print("Scaler saved as scaler.pkl")
print("Label map saved as label_map.pkl")