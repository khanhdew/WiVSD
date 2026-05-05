# Real-time CSI Person Detection

Công cụ detect realtime người sử dụng CSI từ ESP32 và trained Random Forest model.

## ✅ Chuẩn bị hoàn tất

Tất cả dependencies đã được fix:
- ✓ Python imports fixed (relative imports in csi_preprocessing)
- ✓ Model files ready (357KB main model + 649KB retrained)
- ✓ CLI and GUI fully functional
- ✓ Offline test passed

### 🧪 Test trước khi sử dụng:
```bash
python3 test_detector.py
```
Output sẽ hiển thị model predictions với sample data và xác nhận setup đã sẵn sàng.

## Hai cách sử dụng:

### 1. CLI Version (Command Line)
**File:** `realtime_detector.py`

#### Cách sử dụng:
```bash
python3 realtime_detector.py --port /dev/ttyUSB0 --baudrate 2000000 --window 200 --model models/rf_person_detector.joblib
```

#### Tham số:
- `--port`: Serial port (required) - e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, `COM3`
- `--baudrate`: Serial baudrate (default: 2000000)
- `--window`: Số packet để accumulate trước khi predict (default: 200)
- `--model`: Path đến trained model (default: `models/rf_person_detector.joblib`)

#### Ví dụ:
```bash
# Detect realtime trên port /dev/ttyUSB0
python3 realtime_detector.py --port /dev/ttyUSB0

# Custom window size
python3 realtime_detector.py --port /dev/ttyUSB0 --window 100

# Use retrained model
python3 realtime_detector.py --port /dev/ttyUSB0 --model models/rf_person_detector_retrained.joblib
```

#### Output:
```
================================================================================
REAL-TIME CSI PERSON DETECTION
================================================================================
Model: models/rf_person_detector.joblib
Window Size: 200 packets
================================================================================

[2026-04-30T15:30:45.123456] PERSON | Confidence: 85.32% | Packets: 200 | Amp: μ=1.23e+02 σ=4.56e+01 CV=0.3715
[2026-04-30T15:30:50.654321] NO PERSON | Confidence: 92.15% | Packets: 200 | Amp: μ=5.43e+01 σ=2.34e+01 CV=0.4301
```

---

### 2. GUI Version (Graphical User Interface)
**File:** `realtime_detector_gui.py`

#### Cách sử dụng:
```bash
python3 realtime_detector_gui.py
```

Giao diện sẽ hiện lên cho phép:
- Chọn serial port và baudrate
- Cấu hình detection window size
- Chọn model
- Start/Stop detection
- Xem realtime results, confidence, statistics

#### Tính năng:
- **Live Status**: Hiển thị kết quả detection realtime (PERSON/NO PERSON)
- **Confidence Bar**: Progress bar hiển thị độ tin tưởng
- **Statistics**: Đếm packets và predictions
- **Log**: Lịch sử detections gần đây

---

## Cách hoạt động

Cả hai script đều:

1. **Kết nối ESP32**: Đọc CSI data từ serial port
2. **Buffer packets**: Gom CSI packets vào buffer theo window size
3. **Extract features**: Tính 3 features từ CSI amplitude:
   - `amp_mean`: Trung bình amplitude
   - `amp_std`: Độ lệch chuẩn amplitude
   - `amp_cv`: Hệ số biến đổi (std/mean)
4. **Predict**: Đưa features vào trained RF model để classify
5. **Display results**: Hiển thị kết quả + confidence

---

## Output Interpretation

### Prediction:
- `PERSON`: Có người detected (probability > 0.5)
- `NO PERSON`: Không có người detected

### Confidence:
- **High (>80%)**: Kết quả tin tưởng
- **Medium (50-80%)**: Cần xem xét thêm
- **Low (<50%)**: Kết quả không chắc chắn

### Features:
- **amp_mean**: Amplitude trung bình - indicator của signal strength
- **amp_std**: Độ lệch chuẩn - indicator của signal variation
- **amp_cv**: Hệ số biến đổi - normalized variation

---

## Chuẩn bị

### Yêu cầu:
- Python 3.12+
- Packages: pandas, numpy, scipy, pyserial, joblib
- Trained model file: `models/rf_person_detector.joblib`

### Cài đặt dependencies:
```bash
pip install pandas numpy scipy pyserial scikit-learn joblib hampel
```

### Kiểm tra connection ESP32:
```bash
# List available ports
python3 -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"

# Quick test serial connection
python3 -c "
import serial
port = '/dev/ttyUSB0'  # Change as needed
ser = serial.Serial(port, 2000000, timeout=1)
print(f'Connected to {port}')
for i in range(5):
    line = ser.readline()
    print(line[:100])  # First 100 chars
ser.close()
"
```

---

## Troubleshooting

### Port không tìm thấy:
```bash
# List all ports
ls /dev/ttyUSB* /dev/ttyACM*

# hoặc
python3 -c "import serial.tools.list_ports; [print(p) for p in serial.tools.list_ports.comports()]"
```

### Permission denied:
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and log in again
```

### Model not found:
```bash
# Verify model exists
ls -lh models/rf_person_detector.joblib

# Use full path if needed
python3 realtime_detector.py --port /dev/ttyUSB0 --model /full/path/to/model.joblib
```

### Low confidence predictions:
- Tăng `--window` size (e.g., 300, 500) để lấy nhiều data hơn
- Kiểm tra CSI signal quality từ ESP32
- Calibrate model lại nếu cần

## Advanced Usage

### Tạo custom detection script:
```python
from realtime_detector import RealtimeDetector

detector = RealtimeDetector(
    port='/dev/ttyUSB0',
    baudrate=2000000,
    window_size=200,
    model_path='models/rf_person_detector.joblib'
)
detector.run()
```

### Integrate vào ứng dụng khác:
```python
from realtime_detector_gui import RealtimeDetectorGUI
from src.csi_preprocessing.classifier import predict_with_model_features

# Predict manually
features = [100.5, 45.2, 0.45]  # [mean, std, cv]
pred, details = predict_with_model_features(features)
print(f"Prediction: {pred}, Confidence: {details.get('proba')}")
```

## Performance Notes

- **Accuracy**: Phụ thuộc vào training data và model quality
- **Latency**: ~1-2s cho một window size 200 packets (phụ thuộc vào sample rate)
- **CPU Usage**: ~5-15% (realtime processing)
- **Memory**: ~50-100MB

## References

- CSI Data Format: `docs/Understanding_CSI.md`
- Model Training: `scripts/train_ml_classifier.py`
- Feature Extraction: `src/csi_preprocessing/processing.py`
