# Hướng Dẫn Sử Dụng Serial to CSV

## Cài đặt

Cài đặt thư viện `pyserial`:

```bash
pip install pyserial
```

## Cách sử dụng

### 1. Chế độ Simple (Ghi toàn bộ dòng)

Đọc tất cả dữ liệu từ serial và ghi từng dòng vào CSV:

```bash
python serial_to_csv.py --port /dev/ttyUSB0 --baudrate 115200
```

**Output CSV:**
```
timestamp,data
2026-02-23 10:30:15.123,CSI: [1.2, 3.4, 5.6]
2026-02-23 10:30:15.234,CSI: [1.3, 3.5, 5.7]
```

### 2. Chế độ Parse (Tự động parse dữ liệu)

Nếu ESP32 gửi dữ liệu đã được format (VD: `value1,value2,value3`):

```bash
python serial_to_csv.py --port /dev/ttyUSB0 --mode parse --delimiter ","
```

**Ví dụ dữ liệu từ ESP32:**
```
rssi,csi_len,amplitude
-45,128,234.5
-46,128,235.1
```

**Output CSV:**
```
timestamp,rssi,csi_len,amplitude
2026-02-23 10:30:15.123,-45,128,234.5
2026-02-23 10:30:15.234,-46,128,235.1
```

### 3. Các tùy chọn khác

```bash
# Chỉ định file output
python serial_to_csv.py --port /dev/ttyUSB0 --output my_data.csv

# Thay đổi baud rate
python serial_to_csv.py --port /dev/ttyUSB0 --baudrate 921600

# Sử dụng delimiter khác (VD: tab)
python serial_to_csv.py --port /dev/ttyUSB0 --mode parse --delimiter $'\t'

# Windows
python serial_to_csv.py --port COM3 --baudrate 115200
```

## Tìm Serial Port

### Linux/Mac:
```bash
ls /dev/tty*
# Thường là: /dev/ttyUSB0, /dev/ttyACM0
```

### Windows:
Mở Device Manager → Ports (COM & LPT) → Tìm COM port (VD: COM3, COM4)

## Cấp quyền (Linux)

Nếu gặp lỗi "Permission denied":

```bash
sudo chmod 666 /dev/ttyUSB0
# Hoặc thêm user vào group dialout
sudo usermod -a -G dialout $USER
# Sau đó logout/login lại
```

## Dừng chương trình

Nhấn `Ctrl+C` để dừng và đóng file CSV.

## Ví dụ code ESP32 (Arduino)

```cpp
void setup() {
  Serial.begin(115200);
}

void loop() {
  // Chế độ simple - gửi chuỗi
  Serial.println("CSI Data: amplitude=123.4, phase=56.7");
  
  // Hoặc chế độ parse - gửi CSV format
  Serial.print(rssi);
  Serial.print(",");
  Serial.print(csi_len);
  Serial.print(",");
  Serial.println(amplitude);
  
  delay(100);
}
```

## Xem trước dữ liệu

Trước khi chạy script, có thể xem dữ liệu thô từ serial:

```bash
# Linux/Mac
cat /dev/ttyUSB0

# Hoặc dùng screen
screen /dev/ttyUSB0 115200

# Windows - dùng PuTTY hoặc Arduino Serial Monitor
```
