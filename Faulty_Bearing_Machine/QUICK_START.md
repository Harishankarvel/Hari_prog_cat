# 🚀 Bearing Fault Detection System - Quick Start

## Your System is Ready to Use!

### ✅ What You Have:

1. **Trained Model** (`model.pkl`)
   - 89% accuracy
   - Trained on 324 samples
   - Detects 3 bearing conditions

2. **Web Interface** (Flask App)
   - Beautiful drag-and-drop interface
   - Real-time predictions
   - Confidence scores

3. **Training Data**
   - 45 generated CSV files
   - 15 files per bearing condition
   - 2000 samples each

---

## 🎯 How to TEST Your Model

### Method 1: Using Web Interface (Recommended)

**Step 1: Start the Server**
```bash
python h:\HARI\app.py
```

**Step 2: Open Browser**
```
http://localhost:5000
```

**Step 3: Upload Test File**
- Drag and drop a CSV file from `h:\HARI\data\*\` folders
- Or use one of these pre-generated test files:
  - `h:\HARI\data\normal\normal_1.csv` → Predicts "Normal Bearing"
  - `h:\HARI\data\inner\inner_1.csv` → Predicts "Inner Race Fault"
  - `h:\HARI\data\outer\outer_1.csv` → Predicts "Outer Race Fault"

**Step 4: View Results**
- See bearing condition (Normal/Inner/Outer)
- View confidence percentage
- Check number of samples analyzed

---

### Method 2: Using Python Script

```python
import joblib
import pandas as pd
import numpy as np
from scipy.fft import fft

# Load model
model = joblib.load('h:\\HARI\\model.pkl')

# Load your CSV file
df = pd.read_csv('h:\\HARI\\data\\normal\\normal_1.csv', sep=';', decimal=',')
signal = df.iloc[:, 1].values  # Get Measurements column

# Extract features
segment = signal[:512]
features = [
    np.mean(segment),
    np.std(segment),
    np.max(segment),
    np.min(segment),
    np.sqrt(np.mean(segment**2)),
    np.mean(np.abs(fft(segment))),
    np.max(np.abs(fft(segment)))
]

# Predict
prediction = model.predict([features])[0]
classes = {0: 'Normal', 1: 'Inner Fault', 2: 'Outer Fault'}
print(f"Predicted: {classes[prediction]}")
```

---

## 📊 Test Data Locations

Your pre-generated test files (ready to use):

```
h:\HARI\data\
├── normal\
│   ├── normal_1.csv
│   ├── normal_2.csv
│   └── ... (15 files total)
├── inner\
│   ├── inner_1.csv
│   ├── inner_2.csv
│   └── ... (15 files total)
└── outer\
    ├── outer_1.csv
    ├── outer_2.csv
    └── ... (15 files total)
```

---

## 📝 CSV File Format

Your test files should follow this format:

```csv
Case_No;Measurements
1;0,254
2;0,187
3;-0,314
...
2000;0,412
```

**Important:**
- Separator: **Semicolon (;)**
- Decimal: **Comma (,)**
- Minimum samples: **512**
- Recommended: **2000+**

---

## 🎨 Web Interface Features

### Upload Box
- Drag & drop CSV files
- Click to browse
- Shows filename and size

### Analysis Button
- Disabled until file selected
- Shows loading spinner
- Processes securely on server

### Results Display
- **Bearing Condition** (colored by type)
- **Confidence Level** (0-100%)
- **Signal Samples** (total preprocessed)
- **Status** indicator

### Clear Button
- Resets interface
- Ready for new file

---

## ⚙️ Model Information

| Property | Value |
|----------|-------|
| Type | Random Forest Classifier |
| Classes | 3 (Normal, Inner, Outer) |
| Training Accuracy | 89% |
| Features Extracted | 7 |
| Segment Size | 512 samples |
| Total Training Samples | 324 segments |

---

## 🔧 Customizing Test Data

### Create Your Own Test File

**Python Script:**

```python
import csv
import random

# Generate test file
with open('my_test.csv', 'w', newline='') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(['Case_No', 'Measurements'])
    for i in range(1, 2001):
        value = random.gauss(0, 0.2)  # Normal bearing
        writer.writerow([i, str(value).replace('.', ',')])
```

**Upload this file to the web interface for testing!**

---

## 📱 Files You Have

| File | Purpose |
|------|---------|
| `app.py` | Flask web server |
| `Pandom_processors.py` | Model training script |
| `model.pkl` | Trained model |
| `templates/index.html` | Web interface |
| `TESTING_GUIDE.md` | Detailed guide |
| `requirements.txt` | Dependencies |

---

## 🚀 Quick Commands

```bash
# Start web server
python h:\HARI\app.py

# Install dependencies
pip install -r h:\HARI\requirements.txt

# Run training (optional)
python h:\HARI\Pandom_processors.py

# Generate new data (optional)
python h:\HARI\generate_enhanced_data.py
```

---

## ✨ Next Steps

1. ✅ **Start the server** → `python app.py`
2. ✅ **Open browser** → `http://localhost:5000`
3. ✅ **Upload test file** → From `data\` folders
4. ✅ **View prediction** → See bearing condition & confidence
5. ✅ **Try more files** → Test all conditions

---

## 💡 Pro Tips

- Use files from `normal_1.csv`, `inner_1.csv`, `outer_1.csv` for quick tests
- More samples (2000+) = better accuracy
- Confidence > 80% = Reliable prediction
- If results vary, upload multiple files to confirm

---

**🎉 Your bearing fault detection system is ready!**

Any questions? Check `TESTING_GUIDE.md` for detailed information.
