import os
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import threading
import time
try:
    import serial
except Exception:
    serial = None

# --- Configuration ---
DATA_DIR = r'H:\SIGNALS MODEL\casting_data\casting_data\train'
IMG_SIZE = (64, 64)  # Resize images to standard size
# Use absolute path for model file in script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(SCRIPT_DIR, 'ml_defect_model.pkl')

class DefectDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Defect Detection System")
        self.root.geometry("600x550")
        self.root.configure(bg="#f0f0f0")

        # UI Styling
        self.header_font = ("Helvetica", 16, "bold")
        self.label_font = ("Helvetica", 12)
        self.result_font = ("Helvetica", 14, "bold")
        self.btn_font = ("Helvetica", 10, "bold")

        # Arduino / LED / LCD state (must be before _setup_ui)
        self.arduino = None
        self.arduino_enabled = False
        self.led_threads = {}
        self.led_stop_events = {}
        self.led_widgets = {}
        self.lcd_label = None
        self.model = None

        self._setup_ui()
        self._load_model_if_exists()
        # Auto-train on startup if model doesn't exist
        self._auto_train_on_startup()

    def _setup_ui(self):
        # Header
        header = tk.Label(self.root, text="Defect Detection System", font=self.header_font, bg="#f0f0f0")
        header.pack(pady=20)

        # --- SECTION: Image Selection & Prediction ---
        pred_frame = tk.Frame(self.root, bg="white", bd=1, relief="solid")
        pred_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        tk.Label(pred_frame, text="Defect Detection", font=("Helvetica", 11, "bold"), bg="white").pack(pady=5)
        
        # Button to select image
        tk.Button(pred_frame, text="Select Image", command=self.upload_image, font=self.btn_font, bg="#4CAF50", fg="white").pack(pady=10)
        
        # Image Display Area
        self.img_panel = tk.Label(pred_frame, bg="#e0e0e0", text="[No Image Selected]")
        self.img_panel.pack(pady=10, ipady=30, ipadx=30)
        
        # Labels for Defect Status and Confidence Score
        self.result_lbl = tk.Label(pred_frame, text="Result: -", font=self.result_font, bg="white")
        self.result_lbl.pack(pady=10)
        
        self.score_lbl = tk.Label(pred_frame, text="Confidence Score: -", font=("Helvetica", 11), bg="white", fg="#666")
        self.score_lbl.pack(pady=5)

        # --- SECTION: Simulated LCD and LEDs ---
        hw_frame = tk.Frame(pred_frame, bg="white")
        hw_frame.pack(pady=10)

        # Simulated I2C LCD (two-line)
        self.lcd_label = tk.Label(hw_frame, text="\n", font=("Courier", 12), bg="#003300", fg="#00FF00", width=24, height=2, bd=2, relief="sunken")
        self.lcd_label.grid(row=0, column=0, columnspan=3, pady=5)

        # LED indicators (simulated)
        led_lbl = tk.Label(hw_frame, text="LEDs:", bg="white")
        led_lbl.grid(row=1, column=0, sticky="w", padx=(0,10))

        red_led = tk.Label(hw_frame, text=" ", bg="grey", width=3, height=1, bd=1, relief="ridge")
        red_led.grid(row=1, column=1, padx=5)
        blue_led = tk.Label(hw_frame, text=" ", bg="grey", width=3, height=1, bd=1, relief="ridge")
        blue_led.grid(row=1, column=2, padx=5)

        self.led_widgets['red'] = red_led
        self.led_widgets['blue'] = blue_led

        # ESP32 connection controls
        conn_frame = tk.Frame(pred_frame, bg="white")
        conn_frame.pack(pady=5)

        tk.Label(conn_frame, text="ESP32 COM:", bg="white").grid(row=0, column=0)
        self.com_entry = tk.Entry(conn_frame, width=10)
        self.com_entry.insert(0, "COM8")
        self.com_entry.grid(row=0, column=1, padx=5)
        self.connect_btn = tk.Button(conn_frame, text="Connect ESP32", command=self.connect_arduino, font=self.btn_font)
        self.connect_btn.grid(row=0, column=2, padx=5)

        # Ensure clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _load_model_if_exists(self):
        if os.path.exists(MODEL_FILE):
            try:
                self.model = joblib.load(MODEL_FILE)
                print(f"✓ Model loaded successfully from {MODEL_FILE}")
                # Try to compute overall accuracy on the full dataset (if available)
                try:
                    X, y = self.load_data()
                    if X.size and y.size:
                        y_pred_all = self.model.predict(X)
                        overall_acc = accuracy_score(y, y_pred_all)
                        print(f"[MODEL] Overall model accuracy on full dataset: {overall_acc:.2%}")
                    else:
                        print("[MODEL] No data available to compute overall accuracy.")
                except Exception as e:
                    print(f"[MODEL] Could not compute overall accuracy: {e}")

                return True
            except (FileNotFoundError, EOFError, Exception) as e:
                print(f"✗ Model loading error: {e}")
                print(f"  Model file will be retrained.")
                return False
        else:
            print(f"ℹ Model file not found at: {MODEL_FILE}")
            print(f"  Auto-training will begin on startup...")
            return False

    def _auto_train_on_startup(self):
        """Auto-train the model on startup if it doesn't exist"""
        if not os.path.exists(MODEL_FILE):
            thread = threading.Thread(target=self.train_model_logic, daemon=True)
            thread.start()

    def train_model_logic(self):
        # Logic to train the model on background thread
        try:
            print("[TRAINING] Loading data...")
            X, y = self.load_data()
            
            if len(X) == 0 or len(y) == 0:
                error_msg = "Error: Train folder empty or missing."
                print(error_msg)
                messagebox.showerror("Training Error", error_msg)
                return
            
            print(f"[TRAINING] Loaded {len(X)} images")
            unique_classes = np.unique(y)
            print(f"[TRAINING] Found classes: {unique_classes}")
            
            if len(unique_classes) < 2:
                error_msg = f"Error: Found only {len(unique_classes)} class(es): {unique_classes}. Need 2 classes."
                print(error_msg)
                messagebox.showerror("Training Error", error_msg)
                return

            # Split Data
            print("[TRAINING] Splitting data (80/20)...")
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train Random Forest
            print("[TRAINING] Training Random Forest (100 estimators)...")
            clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            clf.fit(X_train, y_train)
            
            # Evaluate Model
            y_pred = clf.predict(X_test)
            test_acc = accuracy_score(y_test, y_pred)
            print(f"[TRAINING] Model accuracy on test set: {test_acc:.2%}")
            
            # Calculate Overall Accuracy (on entire dataset)
            y_pred_all = clf.predict(X)
            overall_acc = accuracy_score(y, y_pred_all)
            print(f"[TRAINING] Overall model accuracy on full dataset: {overall_acc:.2%}")
            
            # Save Model
            print(f"[TRAINING] Saving model to {MODEL_FILE}...")
            joblib.dump(clf, MODEL_FILE)
            self.model = clf
            
            success_msg = f"✓ Training completed!\nTest Accuracy: {test_acc:.2%}\nOverall Accuracy: {overall_acc:.2%}"
            print(success_msg)
            messagebox.showinfo("Training Success", success_msg)
            
        except ValueError as e:
            error_msg = f"Value error during training: {e}"
            print(error_msg)
            messagebox.showerror("Training Error", error_msg)
        except Exception as e:
            error_msg = f"Unexpected training error: {e}"
            print(error_msg)
            messagebox.showerror("Training Error", error_msg)

    def update_train_status(self, text, color):
        self.root.after(0, lambda: self._update_ui_post_train(text, color))

    def _update_ui_post_train(self, text, color):
        self.train_status_lbl.config(text=text, fg=color)

    def load_data(self):
        # Reads images from data/ok and data/defective
        features = []
        labels = []
        # Mapping: ok -> 0, defective -> 1
        classes = {'ok': 0, 'defective': 1}
        
        if not os.path.exists(DATA_DIR):
            error_msg = f"Data directory '{DATA_DIR}' not found."
            print(error_msg)
            messagebox.showerror("Data Error", error_msg)
            return np.array([]), np.array([])
            
        for category, label_id in classes.items():
            dir_path = os.path.join(DATA_DIR, category)
            if not os.path.exists(dir_path):
                print(f"Warning: '{dir_path}' folder not found. Skipping {category} category.")
                continue
            
            images_loaded = 0
            for file_name in os.listdir(dir_path):
                # Basic check for image extensions
                if not file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    continue
                try:
                    p = os.path.join(dir_path, file_name)
                    img = Image.open(p).convert('RGB')
                    img = img.resize(IMG_SIZE)
                    # Flatten image (Naive approach suitable for simple demo)
                    img_arr = np.array(img).flatten()
                    features.append(img_arr)
                    labels.append(label_id)
                    images_loaded += 1
                except Exception as e:
                    print(f"Skipping file: {file_name} - {e}")
            
            print(f"[DATA] Loaded {images_loaded} images from '{category}' category")
                
        return np.array(features), np.array(labels)

    def upload_image(self):
        # [REQ 1] This opens the File Explorer
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg *.bmp")])
        if not file_path:
            return
            
        # Display the image on GUI
        try:
            load = Image.open(file_path)
            load.thumbnail((200, 200)) # Resize for display only
            render = ImageTk.PhotoImage(load)
            self.img_panel.configure(image=render, text="")
            self.img_panel.image = render 
            
            # Trigger Prediction
            self.predict(file_path)
        except FileNotFoundError as e:
            print(f"File error: {e}")
            messagebox.showerror("Error", "Image file not found.")
        except Exception as e:
            print(f"Image loading error: {e}")
            messagebox.showerror("Error", f"Could not open image file: {str(e)}")

    def predict(self, file_path):
        if not self.model:
            messagebox.showwarning("Warning", "Please train the model first!")
            self.result_lbl.config(text="Prediction: Model Missing")
            return

        try:
            # Preprocess the single image exactly like training data
            img = Image.open(file_path).convert('RGB')
            img = img.resize(IMG_SIZE)
            img_vector = np.array(img).flatten().reshape(1, -1)
            
            # [REQ 2] Predict Class (0 or 1)
            pred_cls = self.model.predict(img_vector)[0]
            
            # [REQ 3] Get Confidence Score (Probability)
            probs = self.model.predict_proba(img_vector)[0]
            score = probs[pred_cls] # The probability of the chosen class
            
            # Update GUI based on result
            if pred_cls == 1:
                status = "DEFECTIVE"
                color = "red"
            else:
                status = "OK"
                color = "green"
            
            print(f"[PREDICT] Prediction: {status}, Score: {score:.2%}, Color: {color}")
            
            self.result_lbl.config(text=f"Prediction: {status}", fg=color)
            self.score_lbl.config(text=f"Confidence Score: {score:.2%}") # Format as percentage
            # Update simulated LCD
            try:
                self.update_lcd(status, score)
                print(f"[LCD] Updated with: {status}, {score:.2%}")
            except Exception as e:
                print(f"[LCD] Error: {e}")

            # Start blinking appropriate LED and notify ESP32 if connected
            try:
                if pred_cls == 1:
                    self.start_led_blink('red')
                    self.send_arduino('DEFECTIVE')
                else:
                    self.start_led_blink('blue')
                    self.send_arduino('OK')
            except Exception as e:
                print(f"[LED/ESP32] Control error: {e}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Prediction failed: {e}")
            print(f"[PREDICT] Error: {e}")

    # ---------------- Arduino / LED / LCD Helper Methods ----------------
    def connect_arduino(self):
        port = self.com_entry.get().strip()
        if not port:
            messagebox.showinfo("ESP32", "Please enter COM port.")
            return
        if serial is None:
            messagebox.showerror("ESP32", "pyserial not installed. Install with: pip install pyserial")
            return
        try:
            # If already connected, close first
            if self.arduino and getattr(self.arduino, 'is_open', False):
                self.arduino.close()
            self.arduino = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            self.arduino_enabled = True
            self.connect_btn.config(text="Disconnect ESP32", command=self.disconnect_arduino)
            messagebox.showinfo("ESP32", f"Connected to {port}")
        except Exception as e:
            messagebox.showerror("ESP32", f"Could not open {port}: {e}")

    def disconnect_arduino(self):
        try:
            if self.arduino and getattr(self.arduino, 'is_open', False):
                self.arduino.close()
        except Exception:
            pass
        self.arduino = None
        self.arduino_enabled = False
        self.connect_btn.config(text="Connect ESP32", command=self.connect_arduino)
        messagebox.showinfo("ESP32", "Disconnected")

    def send_arduino(self, cmd: str):
        # Send a short command string to ESP32 (ending with newline)
        try:
            if self.arduino_enabled and self.arduino and getattr(self.arduino, 'is_open', False):
                self.arduino.write((cmd + "\n").encode())
                print(f"[ESP32] Sent command: {cmd}")
            else:
                print(f"[ESP32] Not connected. Would send: {cmd}")
        except Exception as e:
            print(f"[ESP32] Send error: {e}")

    def start_led_blink(self, color: str):
        # color must be 'red' or 'blue'
        # Stop any existing blinking
        self.stop_all_leds()
        stop_event = threading.Event()
        self.led_stop_events[color] = stop_event
        lbl = self.led_widgets.get(color)
        if lbl is None:
            print(f"[LED] Error: {color} LED widget not found")
            return

        print(f"[LED] Starting {color} LED blink")

        def worker():
            on_color = 'red' if color == 'red' else 'blue'
            blink_count = 0
            while not stop_event.is_set() and blink_count < 10:  # Blink 10 times
                try:
                    self.root.after(0, lambda c=on_color, l=lbl: l.config(bg=c))
                    time.sleep(0.5)
                    self.root.after(0, lambda c='grey', l=lbl: l.config(bg=c))
                    time.sleep(0.5)
                    blink_count += 1
                except Exception as e:
                    print(f"[LED] Error in blink loop: {e}")
                    break
            self.root.after(0, lambda l=lbl: l.config(bg='grey'))
            print(f"[LED] {color} LED blink completed ({blink_count} cycles)")

        t = threading.Thread(target=worker, daemon=True)
        self.led_threads[color] = t
        t.start()

    def stop_all_leds(self):
        for ev in list(self.led_stop_events.values()):
            ev.set()
        self.led_stop_events.clear()
        self.led_threads.clear()
        for lbl in self.led_widgets.values():
            try:
                lbl.config(bg='grey')
            except Exception:
                pass

    def update_lcd(self, status: str, score: float):
        # Simple two-line LCD simulation
        try:
            line1 = f"Status: {status}"
            line2 = f"Conf: {score:.2%}"
            text = f"{line1}\n{line2}"
            self.lcd_label.config(text=text)
            print(f"[LCD GUI] Updated: {text}")
        except Exception as e:
            print(f"[LCD GUI] Error: {e}")

    def on_closing(self):
        # Cleanup threads and serial on exit
        try:
            self.stop_all_leds()
            if self.arduino and getattr(self.arduino, 'is_open', False):
                self.arduino.close()
        except Exception:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DefectDetectionApp(root)
    root.mainloop()

    