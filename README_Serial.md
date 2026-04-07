# Hướng Dẫn Sử Dụng Serial to CSV - ESP32-C5/C6 CSI Data Logger

## Giới thiệu

Script đọc và parse dữ liệu CSI từ ESP32-C5/C6 qua Serial Port và ghi vào CSV file.

**Đặc điểm:**
- Dành riêng cho ESP32-C5/C6 (15 cột dữ liệu)
- Baudrate cố định: **921600**
- Tự động validate và parse CSI_DATA
- Tự động tạo tên file theo timestamp
- Log file không bắt buộc (tiết kiệm I/O)

## Cài đặt

Cài đặt thư viện cần thiết:

```bash
pip install pyserial
```

## Cách sử dụng

### 1. Sử dụng cơ bản (Khuyến nghị)

Tự động tạo file CSV với timestamp, không ghi log:

```bash
python serial_to_csv.py -p /dev/ttyACM0
```

**Output:** `csi_data_20260302_153024.csv`

### 2. Chỉ định tên file cụ thể

```bash
python serial_to_csv.py -p /dev/ttyACM0 -s my_csi_data.csv
```

### 3. Bật log file (debug)

Ghi các dòng không hợp lệ vào file log:

```bash
python serial_to_csv.py -p /dev/ttyACM0 -l errors.log
```

### 4. Tùy chọn đầy đủ

```bash
python serial_to_csv.py -p /dev/ttyACM0 -s data.csv -l debug.log
```

**Windows:**
```bash
python serial_to_csv.py -p COM3 -s csi_data.csv
```

## Tham số dòng lệnh

```
-p, --port      Serial port (bắt buộc)
                VD: /dev/ttyACM0, /dev/ttyUSB0, COM3

-s, --store     File CSV output (tùy chọn)
                Mặc định: csi_data_YYYYMMDD_HHMMSS.csv

-l, --log       File log cho dữ liệu không hợp lệ (tùy chọn)
                Mặc định: không ghi log
```

## CSV Output Format

File CSV gồm 15 cột (định dạng ESP32-C5/C6):

```csv
type,id,mac,rssi,rate,noise_floor,fft_gain,agc_gain,channel,local_timestamp,sig_len,rx_state,len,first_word,data
CSI_DATA,0,1a:2b:3c:4d:5e:6f,-45,11,0,30,15,1,12345678,128,0,256,1,[1,2,3,4,...]
```

**Giải thích các cột quan trọng:**
- `rssi`: Received Signal Strength Indicator
- `fft_gain`, `agc_gain`: Gain values từ receiver
- `channel`: WiFi channel
- `len`: Độ dài CSI data (số phần tử)
- `data`: JSON array chứa CSI raw data (I/Q values)

## Tìm Serial Port

### Linux/Mac:
```bash
# List tất cả các serial port
ls /dev/tty*

# Tìm ESP32 (thường là ACM hoặc USB)
ls /dev/ttyACM* /dev/ttyUSB*

# Hoặc dùng dmesg khi cắm thiết bị
dmesg | grep tty
```

Thường là:
- `/dev/ttyACM0` - ESP32-C6 qua USB
- `/dev/ttyUSB0` - ESP32 với USB-to-Serial adapter

### Windows:
1. Mở **Device Manager** (Win+X → Device Manager)
2. Tìm **Ports (COM & LPT)**
3. Tìm COM port của ESP32 (VD: COM3, COM4)

## Cấp quyền truy cập Serial (Linux)

Nếu gặp lỗi `Permission denied`:

```bash
# Cách 1: Cấp quyền cho port cụ thể (tạm thời)
sudo chmod 666 /dev/ttyACM0

# Cách 2: Thêm user vào group dialout (vĩnh viễn - khuyến nghị)
sudo usermod -a -G dialout $USER

# Sau đó logout và login lại
```

Kiểm tra quyền:
```bash
groups  # Kiểm tra xem có 'dialout' không
```

## Validation và Error Handling

Script tự động kiểm tra và chỉ ghi dữ liệu hợp lệ:

✅ **Dữ liệu hợp lệ:**
- Có chứa chuỗi `CSI_DATA`
- Đúng 15 cột (ESP32-C5/C6 format)
- JSON data parse thành công
- Độ dài CSI data khớp với giá trị `len`

❌ **Dữ liệu không hợp lệ (bị reject):**
- Không chứa `CSI_DATA`
- Số cột không đúng
- JSON parse lỗi
- Độ dài data không khớp

**Output trong quá trình chạy:**
```
[100] Valid CSI packets received (Invalid: 5)
[200] Valid CSI packets received (Invalid: 12)
[WARNING] Column count mismatch: got 25, expected 15 (C5/C6 format)
[WARNING] JSON decode error - data is incomplete
```

## Xem dữ liệu thô từ Serial

Trước khi chạy script, kiểm tra xem ESP32 có gửi dữ liệu không:

```bash
# Linux/Mac - xem dữ liệu thô
cat /dev/ttyACM0

# Hoặc dùng screen (Ctrl+A, K để thoát)
screen /dev/ttyACM0 921600

# Hoặc dùng minicom
minicom -D /dev/ttyACM0 -b 921600
```

**Windows:**
- Arduino Serial Monitor (Tools → Serial Monitor)
- PuTTY: Connection type = Serial, Speed = 921600

## Dừng chương trình

Nhấn `Ctrl+C` để dừng. Script sẽ:
1. Hiển thị tổng số packet hợp lệ/không hợp lệ
2. Đóng serial port
3. Đóng file CSV (dữ liệu đã được flush)

## Xử lý sự cố

### Lỗi: "Serial port not found"
```
[ERROR] Serial error: [Errno 2] No such file or directory: '/dev/ttyACM0'
```
**Giải pháp:**
- Kiểm tra ESP32 đã kết nối chưa
- List tất cả port: `ls /dev/tty*`
- Thử port khác: `-p /dev/ttyUSB0`

### Lỗi: "Permission denied"
```
[ERROR] Serial error: [Errno 13] Permission denied: '/dev/ttyACM0'
```
**Giải pháp:**
```bash
sudo chmod 666 /dev/ttyACM0
# Hoặc thêm vào group dialout (vĩnh viễn)
sudo usermod -a -G dialout $USER
```

### Không nhận được dữ liệu CSI
```
[INFO] Press Ctrl+C to stop...
(không có output gì)
```
**Giải pháp:**
- Kiểm tra ESP32 đã chạy firmware CSI chưa
- Xem dữ liệu thô: `cat /dev/ttyACM0`
- Kiểm tra baudrate (phải là 921600)
- Kiểm tra ESP32 đã flash code đúng chưa

### Tất cả packet đều invalid
```
[WARNING] Column count mismatch: got 25, expected 15 (C5/C6 format)
```
**Giải pháp:**
- ESP32 của bạn có thể không phải C5/C6
- Firmware có thể đang gửi format khác
- Kiểm tra dữ liệu thô để xác định số cột

## Ví dụ dữ liệu CSI từ ESP32-C5/C6

**Dữ liệu thô từ serial:**
```
CSI_DATA,0,1a:2b:3c:4d:5e:6f,-45,11,0,30,15,1,12345678,128,0,256,1,[1,2,3,4,5,6,...]
```

**Sau khi ghi vào CSV:**
| type | id | mac | rssi | rate | noise_floor | fft_gain | agc_gain | channel | ... | data |
|------|----|----|------|------|-------------|----------|----------|---------|-----|------|
| CSI_DATA | 0 | 1a:2b:3c:4d:5e:6f | -45 | 11 | 0 | 30 | 15 | 1 | ... | [1,2,3,...] |

## Tips

1. **Tự động tạo tên file** giúp tránh ghi đè dữ liệu cũ
2. **Không cần log file** khi chạy production (nhanh hơn)
3. **Bật log file** khi debug để xem dữ liệu bị reject
4. File CSV tự động flush sau mỗi dòng → an toàn khi Ctrl+C
5. Sử dụng `screen` hoặc `tmux` để chạy background trên server

## Xem thêm

- [ESP-CSI Documentation](../esp-csi/README.md)
- [CSI Data Format](../esp-csi/examples/get-started/README.md)
- Python script gốc: [csi_data_read_parse.py](../esp-csi/examples/get-started/tools/csi_data_read_parse.py)
