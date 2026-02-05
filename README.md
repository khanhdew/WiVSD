# WiVSD — WiFi Sensing for Vital Signs Detection

WiVSD là dự án nghiên cứu/trải nghiệm kỹ thuật về **ứng dụng WiFi sensing để phát hiện dấu hiệu sinh tồn (nhịp thở, nhịp tim)**. Repository cung cấp tài liệu tham khảo về thiết bị, hướng dẫn thiết lập, cũng như tổng hợp các công cụ trích xuất CSI (Channel State Information) từ nhiều nền tảng phần cứng.

## Nội dung chính
- Tổng quan mục tiêu và phạm vi của dự án WiVSD
- So sánh các dòng thiết bị hỗ trợ trích xuất CSI (Intel 5300, Broadcom/Nexmon, Atheros, ESP32, Intel AX series, USRP…)
- Liên kết đến các bài báo và công cụ mã nguồn mở phục vụ nghiên cứu WiFi sensing
- Định hướng thiết lập hệ thống và bước khởi đầu cho thử nghiệm vital sign detection

## Kiến trúc & phạm vi
- **Mục tiêu:** xây dựng pipeline sensing bằng WiFi để đo/ước lượng nhịp thở, nhịp tim trong môi trường indoor.
- **Dữ liệu cảm biến:** sử dụng CSI từ card WiFi/SoC hỗ trợ (20–160 MHz, 2.4/5/6 GHz, MIMO 1×1 đến 4×4).
- **Phạm vi repo:** tài liệu hướng dẫn và nghiên cứu; chưa kèm mã nguồn huấn luyện/triển khai mô hình.

## Bắt đầu nhanh
1. **Chọn thiết bị phần cứng** phù hợp nhu cầu:
   - **Thực hành nhanh/giá mềm:** Raspberry Pi 4B + Broadcom BCM43455C0 (Nexmon CSI) hoặc ESP32 (esp-csi).
   - **Độ chính xác cao:** Broadcom BCM4366C0 (ASUS RT-AC86U, 4×4 MIMO) hoặc Intel AX200/AX210 (WiFi 6, FeitCSI).
   - **Nghiên cứu kinh điển:** Intel 5300 hoặc Atheros CSI Tool (802.11n).
2. **Thiết lập công cụ trích xuất CSI** theo từng thiết bị (tham khảo file `CSI_Devices_Research.md`).
3. **Thu thập dữ liệu**: cấu hình điểm phát/thu, lưu CSI (PCAP/binary) ở tốc độ ≥25–100 Hz.
4. **Tiền xử lý**: hiệu chỉnh pha/biên độ, lọc nhiễu (Butterworth/Hampel), chuẩn hóa kênh.
5. **Phân tích/ML**: áp dụng thuật toán FFT, peak detection, hoặc mô hình học sâu (LSTM/Transformer) để suy ra nhịp thở/nhịp tim.

## Tài liệu & tham khảo
- Chi tiết về thông số thiết bị, ưu/nhược điểm, và danh sách bài báo: xem [`CSI_Devices_Research.md`](./CSI_Devices_Research.md).
- Các công cụ mã nguồn mở tiêu biểu:
  - Intel 5300 CSI Tool, Nexmon CSI, Atheros CSI Tool
  - esp-csi (ESP32), FeitCSI (Intel AX200/AX210), CSIKit (phân tích/parse dữ liệu)
- Tài liệu về CSI: [Understanding CSI from Tsinghua University](https://tns.thss.tsinghua.edu.cn/wst/docs/pre)

## Trạng thái & đóng góp
- Repo đang ở giai đoạn tài liệu hóa/khảo sát. Rất hoan nghênh các PR bổ sung:
  - Hướng dẫn cài đặt cụ thể cho từng thiết bị (script, ảnh chụp màn hình)
  - Notebook ví dụ tiền xử lý/ước lượng nhịp thở
  - Kết quả benchmark hoặc bộ dữ liệu mẫu

## Giấy phép
Phát hành dưới giấy phép [MIT](./LICENSE).
