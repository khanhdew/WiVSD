### 1. Transmitter (TX - Thiết bị Phát)
- Chế độ hoạt động (Mode): Station (STA) + ESP-NOW
- Băng tần (Band): 2.4 GHz Only
- Giao thức WiFi (Protocol): 802.11ax (WiFi 6) - Bắt buộc
- Độ rộng kênh (Bandwidth): 20 MHz (HT20)
- Kênh (Channel): Cố định (ví dụ: 13), tránh kênh bị nhiễu.
- Tốc độ gửi gói tin (ESP-NOW Rate): 100
- PHY Mode: HE20 (High Efficiency 20MHz)
- Rate + Guard Interval: MCS0 + LGI (Long Guard Interval ~1600ns) -> Giúp chống nhiễu phản xạ cực tốt.
### 2. Receiver (RX - Thiết bị Thu)
- Chế độ hoạt động (Mode): Station (STA) + CSI Promiscuous
- Băng tần (Band): 2.4 GHz Only
- Giao thức WiFi (Protocol): 802.11ax (WiFi 6) - Phải giống TX để hiểu gói tin
- Độ rộng kênh (Bandwidth): 20 MHz (HT20)
- Kênh (Channel): Phải trùng khớp hoàn toàn với TX (ví dụ: Kênh 13).
- Cấu hình CSI (CSI Config):
    - Enable: Bật
    - Type: LLTF (Legacy LTF) + HT-LTF + STBC-HTLTF2 (Quan trọng để lấy đủ thông tin kênh truyền).

CSI Config RX
```C++
#elif CONFIG_IDF_TARGET_ESP32C6
    wifi_csi_config_t csi_config = {
        .enable                 = true,  // Bật tính năng thu thập CSI
        .acquire_csi_legacy     = false, // Tắt Legacy: Không quan tâm gói tin chuẩn cũ (ít subcarrier)
        .acquire_csi_ht20       = false, // Tắt HT20: Không dùng chuẩn 11n
        .acquire_csi_ht40       = false, // Tắt HT40: Không dùng chuẩn 11n
        .acquire_csi_su         = true,  // [QUAN TRỌNG] Bắt gói tin HE Single User (ESP-NOW gửi ở dạng này)
        .acquire_csi_mu         = true,  // Bắt gói tin HE Multi User (nếu có)
        .acquire_csi_dcm        = true,  // Bắt gói tin dùng Dual Carrier Modulation (đặc trưng 11ax)
        .acquire_csi_beamformed = true,  // Lấy cả CSI từ gói có Beamforming (thông tin không gian tốt hơn)
        .acquire_csi_he_stbc    = 2,     // Space-Time Block Coding: 2 = Lấy mẫu cả STBC-HELTF2 (Tăng độ tin cậy)
        .val_scale_cfg          = false, // Giữ nguyên biên độ gốc (Raw scale), không tự động scale
        .dump_ack_en            = false, // Không lấy CSI của gói ACK (chỉ quan tâm gói Data chính)
        .reserved               = false
    };
```

Tóm tắt chiến thuật:

Hệ thống chạy hoàn toàn trên nền tảng WiFi 6 (11ax) ở băng thông 20MHz. Tuy băng thông hẹp (20MHz) nhưng nhờ mật độ subcarrier dày đặc (234 điểm) và Long Guard Interval, đây là cấu hình "sạch" và chi tiết nhất để phát hiện nhịp tim/thở trên chip ESP32-C6.