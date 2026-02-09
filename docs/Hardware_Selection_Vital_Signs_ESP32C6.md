# WiFi CSI Vital Signs Detection: Lựa Chọn Hardware và Antenna

## 1. Executive Summary

Đề tài này nhằm xây dựng hệ thống **phát hiện các chỉ số sống (Vital Signs)** như nhịp tim (Heart Rate) và nhịp thở (Respiratory Rate) sử dụng WiFi CSI (Channel State Information). Để đạt được mục tiêu này, chúng ta chọn:

- **Thiết bị chính**: **ESP32-C6 Microcontroller**
- **Thiết bị phát**: ESP32-C6 với **Omnidirectional Antenna**
- **Thiết bị thu**: ESP32-C6 với **8dBi Panel Antenna**

Lựa chọn này được dựa trên các yêu cầu kỹ thuật cụ thể của ứng dụng vital signs detection, khả năng CSI, hiệu suất RF, và chi phí.

---

## 2. Tại Sao Chọn ESP32-C6?

### 2.1 Hỗ Trợ WiFi 6 (802.11ax) và WiFi 6E

| Tiêu Chí | ESP32-C6 | ESP32-S3 | Intel 5300 | Atheros |
|----------|----------|----------|-----------|---------|
| **WiFi Standard** | 802.11ax (WiFi 6) | 802.11n (WiFi 4) | 802.11n (WiFi 4) | 802.11n (WiFi 4) |
| **Frequency Bands** | 2.4 GHz, 5 GHz, 6 GHz | 2.4 GHz, 5 GHz | 5 GHz | 2.4/5 GHz |
| **Bandwidth Support** | Up to 160 MHz | 40 MHz max | 40 MHz max | 40 MHz max |
| **Subcarriers (80MHz)** | 234 subcarriers | ~56 subcarriers | ~56 subcarriers | ~56 subcarriers |

**Ưu điểm của WiFi 6**:
- **Nhiều subcarriers hơn** → Độ phân giải cao hơn cho chi tiết chuyển động nhỏ (breathing, heartbeat)
- **OFDMA technology** → Tín hiệu sạch hơn, ít nhiễu
- **Dải tần số rộng hơn** → Tính linh hoạt cao

Đối với **vital signs detection**, việc có nhiều subcarriers là yếu tố **quan trọng cực kỳ**, vì:
- Nhịp thở (~0.2-0.33 Hz) và nhịp tim (~1-1.7 Hz) tạo ra biến đổi CSI rất nhỏ
- Nhiều subcarriers cho phép phát hiện những biến thiên tinh tế này trên toàn bộ spectrum
- Phùng hợp với các paper nghiên cứu gần đây (Wang et al. 2017, Liu et al. 2015)[1][2]

### 2.2 Quá Trình Đo CSI trên ESP32-C6

ESP32-C6 sử dụng **Least Square (LS) channel estimation** tương tự như Intel 5300, nhưng với:
- Subcarriers được lấy mẫu từ mỗi gói tin WiFi (~100-200 packets/second)
- CSI được extract từ training fields trong WiFi preamble
- Dữ liệu có thể accessed qua **ESP-IDF WiFi CSI callback API**

**Code Example - CSI Callback trên ESP32-C6**:
```c
void wifi_csi_rx_cb(const wifi_csi_info_t *info) {
    // info->rx_ctrl.sig_len: độ dài CSI data (bytes)
    // info->csi_data: pointer tới CSI complex values
    // info->rx_ctrl: RSSI, antenna selection, bandwidth info
    
    // Tính amplitude từ CSI
    for (int i = 0; i < info->rx_ctrl.sig_len; i += 2) {
        int16_t real = (int16_t)((info->csi_data[i+1] << 8) | info->csi_data[i]);
        int16_t imag = (int16_t)((info->csi_data[i+3] << 8) | info->csi_data[i+2]);
        float amplitude = sqrt(real*real + imag*imag);
        
        // Log amplitude để xử lý
        printf("%f\n", amplitude);
    }
}

// Setup CSI receiving
wifi_csi_config_t csi_config = {
    .lltf_en = true,           // Receive LTF field
    .htltf_en = true,          // Receive HT-LTF
    .stbc_htltf2_en = true,
    .ltf_merge_en = true,
    .channel_filter_en = false,
    .manu_scale = false,
    .shift = false,
};

esp_wifi_set_csi_config(&csi_config);
esp_wifi_set_csi_rx_cb(wifi_csi_rx_cb, NULL);
```

### 2.3 Hiệu Suất CPU và Processing Realtime

| Thông Số | ESP32-C6 | ESP32-S3 | Intel 5300 |
|----------|----------|----------|-----------|
| **CPU Frequency** | 160 MHz (dual-core) | 240 MHz (dual-core) | N/A (NIC standalone) |
| **AI Accelerator** | None, nhưng có **extension instructions** | **AI Accelerator built-in** | N/A |
| **RAM** | 320 KB SRAM + 16 MB Flash | 512 KB SRAM + 8 MB PSRAM | N/A |
| **TensorFlow Lite Support** | Yes (basic) | Yes (optimized) | No |

**Cho vital signs detection**, ta chỉ cần:
- **Real-time signal processing** (Butterworth filter, FFT)
- **Đơn giản ML models** (không cần inference phức tạp)
- → ESP32-C6 đủ mạnh để chạy xử lý tín hiệu biên (edge processing)

### 2.4 OTA Update và Ecosystem

ESP32-C6 tích hợp sâu với **Espressif IoT ecosystem**:
- Hỗ trợ OTA firmware update
- HTTPS/TLS built-in
- RainMaker cloud platform (optional)
- Fully open-source toolchain (ESP-IDF)
- Cộng đồng research sử dụng rộng rãi (esp-csi project)

### 2.5 Chi Phí

| Thiết Bị | Giá (USD) | Ghi Chú |
|----------|-----------|--------|
| ESP32-C6 DevKit | $8-15 | Rẻ nhất, module built-in |
| Omni Antenna (5 dBi) | $3-5 | Cho transmitter |
| Panel Antenna (8 dBi) | $5-10 | Cho receiver (directional) |
| **Tổng** | **$20-35** | Chi phí rất thấp so với Intel 5300 ($50-100) |

---

## 3. Antenna Specifications và Lựa Chọn

### 3.1 Khái Niệm Antenna Gain (Độ Lợi Antenna)

**Antenna Gain** là thước đo khả năng tập trung sức mạnh RF theo một hướng nhất định, so với một **isotropic radiator** (phát đều theo mọi hướng).

**Công thức**:
$$
G_{\text{dBi}} = 10 \log_{10}(G_{\text{linear}})
$$

Ví dụ:
- **0 dBi**: Isotropic antenna (tham chiếu)
- **2.15 dBi**: Half-wave dipole (so sánh chuẩn)
- **5 dBi**: Omni antenna (vừa)
- **8 dBi**: Panel antenna (directional, đủ mạnh cho vital signs)
- **15+ dBi**: Highly directional (Yagi, parabolic)

**Gain vs. Directivity**:
```
Omni Antenna (6 dBi)      Panel Antenna (8 dBi)
    ↑↑↑↑↑                      ↑↑↑
   ↑ O ↑      (phát đều)      ↑ P ↑    (phát tập trung)
    ↑↑↑↑↑                      ↑↑↑
```

### 3.2 Lựa Chọn Antenna cho Transmitter (Omni)

**Specification**:
- **Loại**: PCB Omni antenna hoặc IPEX external antenna
- **Gain**: 5-6 dBi hoặc 0 dBi (built-in PCB antenna)
- **Bandwidth**: 2.4-5.8 GHz
- **Impedance**: 50 Ω
- **Polarization**: Linear (vertical)

**Tại sao Omni cho Transmitter?**
- **Mục đích**: Phát tín hiệu training packets đến receiver ở **tất cả hướng**
- Trong vital signs application, người đứng ở **bất kỳ vị trí nào** trong phòng đều cần được phát hiện
- Omni antenna đảm bảo coverage toàn diện (360° horizontal, ~90° vertical)
- Gain 6 dBi là **đủ tốt** để tín hiệu đạt receiver với SNR cao

**Ứng dụng cụ thể**:
```
Transmitter (Omni 6 dBi)
         ↓ phát mạnh đều
    
      ┌────────┐
      │ Phòng  │  Người ở bất kỳ vị trí
      │(5m x 5m)│  đều nhận được tín hiệu
      └────────┘
         ↑
     Receiver (Panel 8 dBi)
     tập trung nghe 1 hướng
```

### 3.3 Lựa Chọn Antenna cho Receiver (Panel 8 dBi)

**Specification**:
- **Loại**: Panel antenna (planar array)
- **Gain**: 8 dBi
- **Bandwidth**: 2.4-5.8 GHz (hoặc 5-6 GHz riêng)
- **Impedance**: 50 Ω
- **Beamwidth**: ~60-90° horizontal, ~30-40° vertical
- **Directivity**: Medium (không quá narrow, nhưng tập trung hơn omni)

**Tại sao 8 dBi cho Receiver?**

**Đối với Vital Signs Detection**, đây là lựa chọn **tối ưu** vì:

1. **Độ nhạy cao cho biến thiên nhỏ**:
   - Nhịp thở (0.2-0.33 Hz) gây biến thiên CSI rất nhỏ (~0.1-0.5 dB)
   - Nhịp tim (1-1.7 Hz) gây biến thiên ~1-2 dB
   - Gain 8 dBi giúp **tăng SNR**, làm cho những biến thiên này rõ hơn
   
   **So sánh tín hiệu**:
   ```
   Không antenna:          Với 8 dBi panel:
   [==========]    vs     [================]
   SNR: 15 dB                SNR: 23 dB
   Tín hiệu nhỏ → Có thể detect
   ```

2. **Directivity trung bình - tốt cho phòng**:
   - Beamwidth ~60-90° không quá narrow (không bỏ lỡ người di chuyển)
   - Nhưng **tập trung được tín hiệu** từ vùng quan tâm
   - Giảm noise từ các hướng khác

3. **Cân bằng hiệu suất - chi phí**:
   - 8 dBi là điểm gấp khúc tối ưu: mạnh nhưng vẫn rẻ (~$5-10)
   - 15+ dBi sẽ quá hẹp (Yagi antenna), khó setup trong phòng

### 3.4 Tính Toán Gain Cụ Thể

**Friis Transmission Equation**:
$$
P_r = P_t + G_t + G_r - PL - 20\log_{10}f - 20\log_{10}d - 32.45
$$

Trong đó:
- $P_t$: Transmit power (ESP32 max ~+20 dBm)
- $G_t$: Transmitter antenna gain (Omni ~5 dBi)
- $G_r$: Receiver antenna gain (Panel ~8 dBi)
- $PL$: Path loss in open space
- $f$: Frequency (2.4 GHz or 5 GHz)
- $d$: Distance (ví dụ 5 meters)

**Example tại 2.4 GHz, 5 meters**:
```
P_r = 20 (dBm) + 5 (dBi) + 8 (dBi) - path_loss
    = 20 + 5 + 8 - 40.7 dB (free space 2.4 GHz, 5 m)
    ≈ -7.7 dBm
    
SNR ≈ -7.7 - Noise_floor(-95 dBm) = 87.3 dB
→ Excellent signal quality cho CSI extraction
```

---

## 4. Phù Hợp với Vital Signs Detection

### 4.1 Nguyên Lý Phân Tích Vital Signs qua WiFi CSI

**Nhịp thở (Breathing Rate)**:
- **Tần số**: 12-20 lần/phút = **0.2-0.33 Hz**
- **Biên độ chuyển động**: ~2-3 cm (chest expansion)
- **CSI signature**: Biến thiên **amplitude** trên subcarriers khoảng **0.1-0.5 dB**
- **Phương pháp detection**:
  1. Tính amplitude từ CSI: $A = \sqrt{I^2 + Q^2}$
  2. Lấy mean amplitude trên tất cả subcarriers
  3. Áp dụng Butterworth filter (0.1-0.5 Hz)
  4. FFT để tìm peak frequency
  5. Đọc breathing rate từ peak

**Nhịp tim (Heart Rate)**:
- **Tần số**: 60-100 lần/phút = **1-1.67 Hz**
- **Biên độ chuyển động**: ~0.1-0.5 mm (vessel wall oscillation)
- **CSI signature**: Biến thiên **phase** trên subcarriers (tốt hơn amplitude)
- **Phương pháp detection**:
  1. Tính phase từ CSI: $\phi = \arctan2(Q, I)$
  2. Unwrap phase để loại bỏ discontinuities
  3. Calibrate phase trend
  4. Áp dụng Butterworth filter (0.8-2.5 Hz)
  5. FFT để detect heart rate

**Paper tham khảo**:
- Wang et al. (2017) "PhaseBeat" - Sử dụng phase difference của CSI[1]
- Liu et al. (2015) "Tracking vital signs during sleep" - Multi-person sensing[2]
- Gu et al. (2019) "WiFi-based real-time breathing and heart rate monitoring" - Real-time system[3]

### 4.2 Tại Sao 8 dBi Panel Là Lựa Chọn Tốt Nhất

| Yêu Cầu | 8 dBi Panel | 0 dBi PCB | 15 dBi Yagi |
|---------|------------|-----------|------------|
| **SNR cao** | ✓✓✓ Tốt | ✗ Yếu | ✓✓✓ Tốt |
| **Detectable breathing** | ✓✓✓ Dễ | ✗ Khó | ✓✓✓ Dễ |
| **Detectable heartbeat** | ✓✓✓ Dễ | ✗ Rất khó | ✓✓✓ Dễ |
| **Coverage rộng** | ✓✓ Bình thường | ✓✓✓ Toàn diện | ✗ Hẹp |
| **Setup dễ** | ✓✓✓ Dễ | ✓✓✓ Dễ | ✗ Khó (cần định hướng) |
| **Chi phí** | ✓✓ Rẻ ($5-10) | ✓✓✓ Rẻ nhất | ✗ Đắt ($20+) |
| **Kích thước** | ✓✓ Nhỏ (10x6cm) | ✓✓✓ Nhỏ nhất | ✗ Lớn (20-30cm) |

**Kết luận**: **8 dBi panel antenna cân bằng hoàn hảo** giữa hiệu suất (detect vital signs) và tính thực tiễn (setup dễ, chi phí rẻ, kích thước vừa).

### 4.3 Cấu Hình Antenna cụ thể

**Transmitter Setup** (Phát):
```
ESP32-C6 Module
    ↓
Omni Antenna (6 dBi external IPEX)
    ↓
Phát mạnh và đều qua tất cả hướng
```

**Receiver Setup** (Thu):
```
ESP32-C6 Module
    ↓
Panel Antenna (8 dBi, SMA connector)
    ↓
Định hướng về phía người (tập trung nhận)
↓
Tính CSI từ tín hiệu nhận được
```

**Layout trong phòng** (ví dụ 5m x 5m):
```
┌─────────────────────────────┐
│                             │
│   TX (Omni)      RX (Panel) │
│      [O]    ────────>  [P]  │
│                        ││   │
│                        ││ Hướng sang người
│                             │
│      ~~~ Người ở vị trí bất kỳ ~~~
│                             │
└─────────────────────────────┘

Khoảng cách TX-RX: 2-5 meters
Người đứng: Giữa hoặc cạnh RX, trong vùng coverage của Panel
```

---

## 5. Khả Năng Kỹ Thuật của ESP32-C6

### 5.1 WiFi CSI Extraction

| Thông Số | Chi Tiết |
|----------|----------|
| **Sampling rate** | 100-200 CSI packets/second (phụ thuộc frame rate) |
| **Subcarriers** | 234 subcarriers @ 80 MHz bandwidth |
| **Complex values/packet** | ~234 (1 TX antenna) × 3 (RX antennas) = 702 values/packet |
| **Data size/packet** | ~1.4 KB (uncompressed) |
| **Data rate** | 140-280 KB/second (raw CSI) |
| **Real-time processing** | ✓ Khả thi (filtering + FFT < 10ms) |

### 5.2 Power Consumption

| Mode | Power Consumption |
|------|-------------------|
| WiFi RX CSI Active | ~80-100 mA @ 3.3V |
| Processing (FFT, Filter) | +20-30 mA |
| **Tổng** | **~100-130 mA** |
| **Với pin 5000 mAh** | ~40 giờ continuous operation |

**Ứng dụng thực tế**: Thích hợp cho monitoring 24/7 hoặc thử nghiệm lab dài hạn.

### 5.3 Tích Hợp với Machine Learning

Ngoài signal processing, ta có thể integrate ML model cho classification:
- **TensorFlow Lite for Microcontrollers** có thể chạy trên ESP32-C6
- Model nhỏ gọn (~50-200 KB) để phân loại: sitting vs standing, active vs resting

**Ví dụ**:
```python
# Sau khi extract vital signs amplitude
# Input: breathing_signal, heart_rate
# Output: người đang hoạt động? 

model.predict([breathing_amp, heart_rate]) 
# → [0.9, 0.1] → Active người
```

---

## 6. Tổng Kết Lựa Chọn Hardware

### 6.1 Lý Do Chính

| Yếu Tố | Lý Do |
|--------|-------|
| **ESP32-C6 (not S3, not Intel)** | WiFi 6, 234 subcarriers, rẻ, phù hợp vital signs |
| **Omni Antenna cho TX** | Coverage toàn diện, phát đều, phù hợp sensing application |
| **8 dBi Panel cho RX** | Cân bằng SNR cao + coverage vừa + rẻ + dễ setup |

### 6.2 Bill of Materials (BOM)

| Thành phần | Số lượng | Giá (USD) | Ghi Chú |
|-----------|---------|-----------|--------|
| ESP32-C6 DevKit M1 | 2 | $12 × 2 | Transmitter + Receiver |
| Omni IPEX Antenna (2.4-5GHz, 5dBi) | 1 | $4 | TX antenna |
| Panel Antenna (2.4-5GHz, 8dBi, SMA) | 1 | $8 | RX antenna |
| SMA to IPEX Adapter | 1 | $2 | Connect panel antenna to RX |
| USB Power Bank (5000mAh) | 2 | $10 × 2 | Power supply |
| USB cables + connectors | 1 | $3 | Serial debug, programming |
| **TỔNG** | - | **~$65** | Chi phí cho prototype |

### 6.3 So Sánh với Phương Án Khác

| Phương Án | Ưu Điểm | Nhược Điểm | Chi Phí |
|-----------|---------|-----------|--------|
| **ESP32-C6 + Panel 8dBi** ✓ | WiFi 6, CSI sạch, rẻ | Cần phát triển software | $60-70 |
| Intel 5300 + external antenna | Tool support tốt, ổn định | Cũ, khó mua, đắt, không WiFi 6 | $80-120 |
| Atheros AR9003 | Hỗ trợ Linux tốt | WiFi 4, subcarriers ít | $70-100 |
| TP-Link router + monitor | Thiết bị thương mại | Khó access CSI API, proprietary | $100-200 |

**Kết luận**: **ESP32-C6 với panel antenna 8dBi là phương án tối ưu** cho đề tài vital signs detection.

---

## 7. Hướng Dẫn Lắp Ráp và Sử Dụng

### 7.1 Hardware Assembly

**Bước 1: Chuẩn Bị Thiết Bị**
```bash
# Kiểm tra danh sách:
- ESP32-C6 DevKit (x2)
- Omni antenna IPEX (x1)
- Panel antenna SMA (x1)
- IPEX-to-SMA adapter (nếu cần)
- USB cables cho programming
```

**Bước 2: Kết Nối Antenna**
```
Transmitter (TX - ESP32-C6 #1):
├── IPEX connector (mặc định trên module)
└── Cắm Omni antenna vào IPEX slot

Receiver (RX - ESP32-C6 #2):
├── IPEX connector (mặc định)
├── IPEX-to-SMA adapter
└── Cắm Panel antenna vào SMA connector
    (Hoặc nếu module hỗ trợ SMA trực tiếp)
```

**Bước 3: Power Supply**
```
Cách 1 (Development):
- USB-to-Serial cable cấp power + cho debug
- TX: Cổng USB-C trên DevKit
- RX: Cổng USB-C trên DevKit

Cách 2 (Standalone):
- Power bank 5V vào GPIO pins
- VDD → +5V (qua LDO)
- GND → GND
```

### 7.2 Software Setup

**1. Clone ESP-CSI repo**:
```bash
git clone https://github.com/espressif/esp-csi.git
cd esp-csi/examples/get-started/csi_send
```

**2. Configure cho Transmitter**:
```bash
idf.py set-target esp32c6
idf.py menuconfig
# Tìm: Component config → WiFi → CSI Rx callback
# Enable CSI function
```

**3. Flash Transmitter**:
```bash
idf.py build
idf.py -p /dev/ttyUSB0 flash
```

**4. Tương tự cho Receiver (csi_recv)**:
```bash
cd ../csi_recv
idf.py set-target esp32c6
idf.py build
idf.py -p /dev/ttyUSB1 flash
```

### 7.3 Verification

**Kiểm tra CSI data được xuất hiện**:
```bash
# Serial monitor RX device
idf.py monitor -p /dev/ttyUSB1

# Output expected:
# CSI data: Real=123, Imag=45, ...
# CSI len: 702 bytes
# RSSI: -50 dBm
```

---

## 8. Hướng Phát Triển Tiếp Theo

### 8.1 Vital Signs Detection Pipeline

```
CSI Raw Data → Amplitude Extraction → Butterworth Filter 
→ FFT → Peak Detection → Heart Rate + Breathing Rate
```

### 8.2 Expected Performance

**Breathing Detection**:
- Accuracy: ~95% (literature)
- Latency: <2 second (real-time)
- Distance: 1-5 meters
- Through-wall: Possible but degraded

**Heart Rate Detection**:
- Accuracy: ~90% (±3-5 bpm)
- Latency: <5 seconds (cần đủ dữ liệu)
- Distance: 1-3 meters (tốn SNR cao)
- Through-wall: Khó hơn breathing

### 8.3 Optimization

1. **Phase Calibration**: Loại bỏ hardware offset (quantization effect)
2. **Multi-antenna Combining**: Sử dụng 3 RX antenna nếu available
3. **Adaptive Filtering**: Thích ứng với thay đổi environment
4. **ML Classification**: Phân biệt multiple users (multi-user sensing)

---

## 9. Tài Liệu Tham Khảo

### Paper Nghiên Cứu Chính

[1] **Wang, X., Yang, C., & Mao, S. (2017). "PhaseBeat: Exploiting CSI phase data for vital sign monitoring with commodity WiFi devices"**
- IEEE 37th International Conference on Distributed Computing Systems
- Chứng minh phase CSI có thể detect heart rate
- Citations: 445+ (highly cited)
- Link: https://ieeexplore.ieee.org/abstract/document/7980063/

[2] **Liu, J., Wang, Y., Chen, Y., Yang, J., Chen, X., & Cheng, J. (2015). "Tracking vital signs during sleep leveraging off-the-shelf wifi"**
- Proceedings of the 16th International Workshop on Mobile Computing Systems and Applications
- Multi-person vital signs tracking
- Citations: 623+ (very influential)
- Link: https://dl.acm.org/doi/abs/10.1145/2746285.2746303

[3] **Gu, Y., Zhang, X., Liu, Z., & Ren, F. (2019). "WiFi-based real-time breathing and heart rate monitoring during sleep"**
- 2019 IEEE Global Communications Conference (GLOBECOM)
- Real-time implementation on commodity WiFi
- Demonstrates sleep monitoring
- Link: https://ieeexplore.ieee.org/abstract/document/9014297/

[4] **Espressif Systems. "ESP-CSI Project"**
- Open-source WiFi CSI framework
- GitHub: https://github.com/espressif/esp-csi
- Full documentation and examples
- Support cho tất cả ESP32 variants

[5] **Espressif Systems. "ESP32-C6 Datasheet"**
- Technical specifications
- WiFi 6E capability documentation
- CSI API reference
- Link: https://docs.espressif.com/projects/esp-idf/en/latest/esp32c6/

### Antenna References

[6] **IEEE Std 145-2013. "IEEE Standard for Definitions of Terms for Antennas"**
- Định nghĩa gain, directivity, beamwidth
- Standard reference cho antenna engineering

[7] **Balanis, C. A. (2016). "Antenna Theory: Analysis and Design" (4th Edition)**
- Comprehensive antenna theory textbook
- Panel antenna analysis
- RF propagation fundamentals

---

## 10. Kết Luận

**ESP32-C6 với panel antenna 8dBi là lựa chọn tối ưu** cho đề tài WiFi CSI Vital Signs Detection vì:

1. ✓ **Kỹ thuật**: WiFi 6, 234 subcarriers, SNR cao
2. ✓ **Chi phí**: Rẻ (~$60-70 cho prototype)
3. ✓ **Thực tiễn**: Dễ setup, ecosystem hỗ trợ tốt
4. ✓ **Hiệu suất**: Đủ để detect breathing (~0.2 Hz) và heartbeat (~1.5 Hz)
5. ✓ **Scalability**: Có thể mở rộng để multi-user sensing, ML integration

Hệ thống này có đủ khả năng để implement vital signs monitoring độc lập, và là nền tảng tốt cho research tiếp theo về WiFi CSI sensing applications.

---

**Ngày chuẩn bị**: 9 Tháng 2, 2026  
**Cho**: Đề tài Vital Signs Detection sử dụng WiFi CSI  
**Tác giả**: Khảnh Development Team, VienHLKH
