# BÁO CÁO TỔNG KẾT ĐỒ ÁN
**Đề tài:** Applying WiFi Sensing Technology for Detecting Vital Signs in Rescue Operations
*(Ứng dụng công nghệ cảm biến WiFi trong việc phát hiện dấu hiệu sinh tồn phục vụ công tác cứu hộ)*

---

## MỞ ĐẦU
### 1. Đặt vấn đề và Tính cấp thiết của đề tài
Trong các thảm họa tự nhiên như động đất, sạt lở đất, hoặc các tai nạn sập đổ công trình, công tác tìm kiếm và cứu nạn (Search and Rescue - SAR) đòi hỏi các phương pháp có khả năng phát hiện sự sống một cách nhanh chóng, chính xác và an toàn. Các phương pháp đo lường dấu hiệu sinh tồn truyền thống (như điện tâm đồ ECG, đai đo nhịp thở) yêu cầu phải có sự tiếp xúc vật lý trực tiếp với cơ thể người bệnh. Điều này là hoàn toàn bất khả thi trong những kịch bản cứu hộ mà nạn nhân bị kẹt dưới các đống đổ nát hoặc trong khu vực nguy hiểm.

Bên cạnh đó, các hệ thống camera hồng ngoại hay radar chuyên dụng tuy có khả năng quét không tiếp xúc nhưng lại gặp phải các trở ngại về chi phí cực kỳ đắt đỏ, tiêu thụ năng lượng lớn, và bị hạn chế tầm nhìn (Line-Of-Sight - LOS) do các chướng ngại vật đục (tường, gạch ngói, gỗ).

Gần đây, công nghệ cảm biến vô tuyến dựa trên tín hiệu WiFi (WiFi Sensing) nổi lên như một giải pháp đột phá, mang tính khả thi cao. Với đặc tính sóng điện từ phân bố rộng khắp, tín hiệu WiFi có khả năng đâm xuyên qua các vật cản phi kim loại, đồng thời phản xạ lại khi tương tác với cơ thể con người. Sự dịch chuyển vi mô của lồng ngực (khi hô hấp) sẽ gây ra những biến đổi tinh tế trong tín hiệu phản xạ. Bằng cách khai thác Thông tin Trạng thái Kênh truyền (Channel State Information - CSI) ở lớp Vật lý (Physical Layer) của mạng WiFi, chúng ta có thể trích xuất những biến đổi siêu nhỏ này để ước lượng nhịp thở của nạn nhân, từ đó xác định vị trí của sự sống đằng sau vật cản.

### 2. Mục tiêu nghiên cứu
Mục tiêu cốt lõi của đồ án này là thiết kế, xây dựng và đánh giá một hệ thống phát hiện dấu hiệu sinh tồn (nhịp thở) không tiếp xúc (Contactless Vital Signs Detection) dựa trên tín hiệu WiFi CSI. Hệ thống được tinh chỉnh để phục vụ trong bối cảnh cứu hộ với tiêu chí: độ nhạy cao, giá thành thấp, dễ triển khai, và có khả năng hoạt động trong môi trường có nhiễu loạn đa đường (multipath fading).

---

## CHƯƠNG 1: CƠ SỞ LÝ THUYẾT VỀ CHANNEL STATE INFORMATION (CSI)

### 1.1. Channel State Information (CSI) là gì?
Trong hệ thống truyền thông không dây ứng dụng kỹ thuật Đa phân chia theo tần số trực giao (Orthogonal Frequency Division Multiplexing - OFDM), tín hiệu dải nền được chia thành nhiều sóng mang con (subcarriers) trực giao với nhau. Khác với Chỉ số cường độ tín hiệu nhận (RSSI) chỉ cung cấp một giá trị năng lượng tổng hợp thô cho toàn bộ kênh truyền, CSI mang lại độ phân giải hạt mịn (fine-grained) bằng cách miêu tả trạng thái kênh truyền độc lập trên từng sóng mang con.

Mô hình toán học của kênh truyền trong miền tần số được biểu diễn bởi:
$$Y = H \times X + N$$
Trong đó:
*   $Y$ là véc-tơ tín hiệu nhận được.
*   $X$ là véc-tơ tín hiệu truyền đi.
*   $N$ là nhiễu trắng Gaussian (AWGN).
*   $H$ chính là Ma trận Thông tin trạng thái kênh truyền (CSI).

Mỗi phần tử $H(f)$ của lưới CSI là một số phức, bao hàm thông tin về suy hao biên độ (Amplitude attenuation) và dịch chuyển pha (Phase shift) của sóng điện từ khi lan truyền qua không gian:
$$H(f) = |H(f)| e^{j\angle H(f)}$$

Sự co giãn của lồng ngực khi hít thở (khoảng 5-12mm đối với người trưởng thành) sẽ làm thay đổi độ dài đường truyền của sóng phản xạ từ cơ thể, dẫn đến sự điều biên và điều pha lên tín hiệu CSI nhận được.

### 1.2. Hiệu ứng đa đường (Multipath Effect)
Trong không gian kín (indoor), sóng vô tuyến không chỉ đi trực tiếp từ bộ phát (Tx) đến bộ thu (Rx), mà còn phản xạ qua các bức tường, trần nhà, đồ đạc và cơ thể người. Tín hiệu thu được là sự tổng hợp (xếp chồng) của nhiều tia sóng có biên độ và trễ pha khác nhau. Sự dịch chuyển lồng ngực làm thay đổi độ dài của một trong các tia phản xạ (dynamic path), gây ra sự biến thiên tuần hoàn trong tổng vector tín hiệu nhận được. Nhiệm vụ của hệ thống là bóc tách thành phần biến thiên tuần hoàn (chu kỳ hô hấp) ra khỏi các nhiễu tĩnh (static path) và nhiễu môi trường.

---

## CHƯƠNG 2: THIẾT KẾ HỆ THỐNG VÀ LỰA CHỌN THIẾT BỊ PHẦN CỨNG

### 2.1. Lựa chọn thiết bị: ESP32 Microcontroller
Trong số các nền tảng hỗ trợ trích xuất CSI hiện nay (như Intel 5300, Atheros, Broadcom Raspberry Pi), đồ án đã quyết định sử dụng vi điều khiển **ESP32**.

Lý do lựa chọn dựa trên sự cân nhắc toàn diện về tính ứng dụng trong môi trường cứu hộ:
1.  **Giá thành và Kích thước:** ESP32 là vi điều khiển giá cực rẻ, kích thước siêu nhỏ, cho phép triển khai hệ thống dưới dạng các node cảm biến di động, dễ dàng thả vào các khe hở của đống đổ nát trong các thảm họa.
2.  **Khả năng hỗ trợ CSI:** Framework ESP-IDF tích hợp sẵn hàm callback cho phép trích xuất trực tiếp dữ liệu CSI (gồm 64 subcarriers ở băng thông 20MHz) tại lớp MAC một cách dễ dàng mà không cần phải can thiệp sâu vào firmware như các dòng card mạng Intel hay Broadcom.
3.  **Tiết kiệm năng lượng:** Trong kịch bản cứu hộ, năng lượng là yếu tố sống còn. ESP32 tiêu thụ điện năng cực thấp, cho phép hệ thống hoạt động liên tục bằng nguồn pin dự phòng trong nhiều ngày.

Tuy ESP32 chỉ hỗ trợ kiến trúc 1x1 SISO (Single-Input Single-Output) và cung cấp dữ liệu CSI với độ phân giải 8-bit, nhưng thông qua các kỹ thuật xử lý tín hiệu tiên tiến ở các bước sau, hệ thống vẫn đảm bảo khả năng khôi phục tín hiệu hô hấp với độ chính xác cao.

### 2.2. Lựa chọn Antenna: Panel Antenna (Ăng-ten định hướng)
Thay vì sử dụng ăng-ten đẳng hướng (Omni-directional antenna) mặc định phát sóng đều ra mọi hướng, hệ thống được nâng cấp sử dụng **Panel Antenna** (Ăng-ten mảng pha định hướng).

Việc ứng dụng Panel Antenna được biện luận bởi các cơ sở khoa học sau:
1.  **Tăng Tỷ số Tín hiệu trên Nhiễu (SNR):** Bằng cách tập trung năng lượng bức xạ vào một góc mở (beamwidth) hẹp, Panel Antenna tăng đáng kể độ lợi (Gain) về hướng của mục tiêu. Điều này bù đắp cho sự suy hao cực lớn khi tín hiệu 2.4GHz phải đâm xuyên qua các vật thể đục (tường gạch, bê tông) trong môi trường cứu hộ.
2.  **Giảm thiểu Nhiễu Đa đường (Multipath Mitigation):** Trong các đống đổ nát, tín hiệu dội lại từ vô số các mảnh vỡ tĩnh sẽ che lấp đi biến thiên nhỏ nhoi từ nhịp thở. Panel Antenna đóng vai trò như một bộ lọc không gian (Spatial Filter), hạn chế thu các tia sóng dội từ các hướng không mong muốn, giúp tín hiệu CSI sạch hơn và phản ánh đúng chuyển động tại khu vực mục tiêu đang hướng tới.

### 2.3. Cấu hình mạng và Thu thập dữ liệu
Dữ liệu được thu thập trong một môi trường có kích thước $8m \times 4m$. Cấu hình hệ thống cụ thể như sau:
*   **Băng tần:** 2.4 GHz. Sóng 2.4GHz có bước sóng xấp xỉ 12.5cm, có tính chất nhiễu xạ và đâm xuyên vật cản tốt hơn so với băng tần 5GHz, đáp ứng yêu cầu kịch bản cứu hộ (Non-Line-Of-Sight - NLOS).
*   **Băng thông (Bandwidth):** 20 MHz (tương ứng với 64 sóng mang con trên kiến trúc ESP32).
*   **Cấu hình gói tin (Packet Type):** Gói tin HE SU (High Efficiency Single User) được sử dụng để tối ưu hóa việc trích xuất Channel Estimation ở chuẩn Wi-Fi hiện đại.
*   **Tốc độ lấy mẫu (Sampling Rate):** 100 packets per second (100 Hz). Tần số hô hấp của người bình thường dao động từ 0.2 Hz đến 0.5 Hz. Theo định lý lấy mẫu Nyquist-Shannon ($f_s \ge 2f_{max}$), tốc độ 100 Hz là dư sức để tái tạo tín hiệu hô hấp, đồng thời cung cấp đủ điểm dữ liệu để thực hiện các bộ lọc trung bình trượt và loại bỏ nhiễu gai ở miền thời gian.

*[LƯU Ý CHO TÁC GIẢ: Bổ sung sơ đồ khối phần cứng, hình ảnh thực tế thiết bị ESP32 gắn Panel Antenna và ảnh chụp môi trường phòng 8x4m tại đây để tăng tính trực quan cho báo cáo]*

---

## CHƯƠNG 3: QUY TRÌNH TIỀN XỬ LÝ TÍN HIỆU CSI (DATA PREPROCESSING)

Dữ liệu CSI thô (Raw CSI) trích xuất từ ESP32 chứa đựng rất nhiều nhiễu do sai số phần cứng (Clock offset, Thermal noise) và dao động môi trường. Do đó, một Pipeline Tiền xử lý dữ liệu phức tạp mang tính học thuật cao đã được xây dựng và mã hóa.

### 3.1. Giải mã Biên độ và Pha từ Số phức (Amplitude & Phase Extraction)
Dữ liệu CSI từ ESP32 trả về dưới dạng chuỗi các giá trị thực (Real) và ảo (Imaginary) xen kẽ (Ví dụ: Định dạng C5/C6 chứa mảng số nguyên biểu diễn các thành phần I/Q).
Đối với mỗi sóng mang con $k$, biên độ $A_k$ và góc pha $\phi_k$ được tính toán như sau:
$$A_k = \sqrt{Re(H_k)^2 + Im(H_k)^2}$$
$$\phi_k = \arctan\left(\frac{Im(H_k)}{Re(H_k)}\right)$$

### 3.2. Chỉnh lý Pha (Phase Unwrapping & Phase Sanitization)
Góc pha tính bằng hàm arctan bị giới hạn trong khoảng $[-\pi, \pi]$. Khi pha vượt qua giới hạn này, nó bị cuộn lại (wrapped), tạo ra các bước nhảy đột ngột. Để khôi phục tính liên tục của dữ liệu, hàm `unwrap_phase` được áp dụng, cộng hoặc trừ $2\pi$ tại các điểm có sự sai phân lớn hơn $\pi$.

Tuy nhiên, pha còn chịu ảnh hưởng nặng nề bởi **Lỗi tần số sóng mang (Carrier Frequency Offset - CFO)** và **Lỗi tần số lấy mẫu (Sampling Frequency Offset - SFO)** do phần cứng của Tx và Rx không đồng bộ hoàn hảo. Các lỗi này tạo ra một độ lệch pha tuyến tính dọc theo các index của sóng mang con.
Giải pháp xử lý (Phase Sanitization) được triển khai thông qua phép Hồi quy tuyến tính (Linear Regression). Thuật toán tìm một đường thẳng $y = ax + b$ khớp nhất với sự phân bố của pha trên các sóng mang con (chỉ xét các sóng mang hợp lệ, bỏ qua null/guard subcarriers), sau đó trừ đi thành phần tuyến tính này để triệt tiêu hoàn toàn SFO và CFO, giữ lại phần dư (residual) chứa thông tin chuyển động thực sự.

### 3.3. Lọc nhiễu gai bằng Bộ lọc Hampel (Hampel Filter)
Sự rơi rớt gói tin hoặc nhiễu điện từ đột ngột tạo ra các xung nhiễu gai (outliers) có biên độ lớn. Bộ lọc Hampel được thiết kế để phát hiện và thay thế các outlier này một cách mạnh mẽ (robust).
Với cửa sổ trượt có kích thước $k$ (trong thuật toán sử dụng $k_{amp} = 50$, $k_{phs} = 30$), Hampel filter tính toán trung vị (Median) và Độ lệch tuyệt đối so với trung vị (Median Absolute Deviation - MAD):
$$MAD = median(|x_i - median(X)|)$$
Nếu một điểm dữ liệu lệch khỏi trung vị một lượng vượt quá $n \times \sigma$ (với $\sigma \approx 1.4826 \times MAD$, $n = 3.0$ cho biên độ), điểm đó bị kết luận là nhiễu và được thay thế bằng giá trị trung vị của cửa sổ. Phương pháp này ưu việt hơn bộ lọc trung bình (Moving Average) vì nó không bị làm méo bởi các giá trị ngoại lai cực đại.

### 3.4. Làm mịn tín hiệu bằng Bộ lọc Savitzky-Golay
Sau Hampel, tín hiệu vẫn chứa các nhiễu tần số cao cục bộ. Bộ lọc Savitzky-Golay (S-G filter) được áp dụng. S-G filter là một phương pháp làm mịn dựa trên Hồi quy đa thức cục bộ (Local Polynomial Regression) sử dụng bình phương tối thiểu (Least Squares).
Ưu điểm tuyệt đối của bộ lọc S-G (với cấu hình cửa sổ $= 31$, bậc đa thức $= 3$ cho biên độ) là khả năng làm mịn dữ liệu nhưng vẫn **bảo toàn được hình dạng, chiều cao và độ rộng của các cực đại/cực tiểu (peaks/valleys)**, điều rất quan trọng để giữ lại biên độ của nhịp thở.

### 3.5. Trích xuất dải tần hô hấp bằng Bộ lọc Elliptic (Elliptic Bandpass Filter)
Nhịp thở con người rơi vào khoảng 10 - 36 nhịp/phút, tương đương với dải tần số $0.15 \text{ Hz} - 0.6 \text{ Hz}$.
Để cô lập dải tần này, hệ thống thiết kế một bộ lọc Thông dải (Bandpass Filter). Thay vì dùng Butterworth thông thường, **Bộ lọc Elliptic (Cauer filter)** bậc 4 được sử dụng.
Lý do mang tính kỹ thuật: Bộ lọc Elliptic cho phép độ dốc cắt (roll-off) cực kỳ dốc, chuyển đổi đột ngột giữa dải thông (passband) và dải triệt (stopband). Nhờ thiết lập dải gợn sóng (ripple) cho phép ở dải thông (rp = 0.1 dB) và độ suy hao lớn ở dải triệt (rs = 40 dB), bộ lọc Elliptic triệt tiêu hoàn toàn các can nhiễu từ cử động cơ thể (tần số > 1Hz) hoặc nhiễu thay đổi chậm của môi trường (tần số < 0.1Hz), giúp tín hiệu hô hấp lộ diện dưới dạng sóng hình sin mượt mà.

### 3.6. Giảm chiều dữ liệu bằng Phân tích thành phần chính (PCA)
Tín hiệu CSI từ ESP32 cung cấp hàng chục chuỗi thời gian (time-series) cho mỗi subcarrier. Tuy nhiên, mức độ tương quan với nhịp thở của mỗi subcarrier là khác nhau (do đặc tính multipath fading làm một số subcarrier bị suy hao nghiêm trọng - deep fades).
Thuật toán Phân tích Thành phần Chính (Principal Component Analysis - PCA) được áp dụng trên ma trận dữ liệu đã lọc. Bằng cách tính toán ma trận hiệp phương sai và phân rã giá trị đặc dị (SVD), PCA chuyển đổi dữ liệu đa chiều sang không gian các thành phần chính (Principal Components - PCs) trực giao.
Thành phần chính đầu tiên (PC1) hoặc PC2 là véc-tơ bắt giữ phương sai lớn nhất của tập dữ liệu, do đó nó tổng hợp và trích xuất thành công nhất tín hiệu dao động tuần hoàn của lồng ngực từ tất cả các sóng mang con.

*[LƯU Ý CHO TÁC GIẢ: Chèn các biểu đồ đồ thị so sánh tín hiệu CSI trước và sau khi đi qua từng bộ lọc (Hampel, Savitzky-Golay, Elliptic) lấy từ Notebook csi_processing.ipynb để báo cáo thêm phần thuyết phục]*

---

## CHƯƠNG 4: TRÍCH XUẤT ĐẶC TRƯNG, PHÂN TÍCH PHỔ VÀ MÔ HÌNH HỌC MÁY (MACHINE LEARNING)

### 4.1. Phân tích phổ và Trích xuất đặc trưng (Spectrogram & Spectral Entropy)
Sau khi có được thành phần chính (PC) từ thuật toán PCA, tín hiệu được chuyển từ miền thời gian sang miền tần số bằng Biến đổi Fourier Thời gian ngắn (Short-Time Fourier Transform - STFT), tạo ra biểu diễn phổ (Spectrogram) với cửa sổ Hanning.

Để phân loại xem dữ liệu thu được là tín hiệu hô hấp thực sự hay là nhiễu động ngẫu nhiên (chuyển động của người, môi trường), một chỉ số quan trọng được tính toán là **Entropy Phổ (Spectral Entropy - SE)**:
$$H = - \sum (P(f) \log_2 P(f))$$
Trong đó $P(f)$ là phân bố xác suất công suất trong miền tần số.
*   Nếu môi trường tĩnh và có nhịp thở đều: Năng lượng phổ sẽ tập trung cao độ tại một đỉnh tần số duy nhất (tần số hô hấp), dẫn đến Entropy Phổ thấp.
*   Nếu có chuyển động lớn hoặc nhiễu loạn: Năng lượng phổ phân tán đều (White-noise-like), dẫn đến Entropy Phổ cao (gần tới 1.0).
Dựa vào ngưỡng SE (ví dụ 0.5), hệ thống có thể phán đoán sơ bộ tình trạng có chuyển động hay không (no movement / movement).

Bên cạnh Spectrogram, các đặc trưng thống kê ở miền thời gian cũng được trích xuất (Trung bình biên độ `amp_mean`, Độ lệch chuẩn biên độ `amp_std`, và Hệ số biến thiên `amp_cv = amp_std / amp_mean`) để tạo thành véc-tơ đặc trưng (Feature Vector) đầu vào cho mô hình học máy.

### 4.2. Xây dựng mô hình phân loại với Random Forest
Để giải quyết bài toán phát hiện sự sống/hành động từ véc-tơ đặc trưng đã trích xuất, mô hình **Random Forest (Rừng ngẫu nhiên)** được lựa chọn.

Random Forest là một thuật toán học máy kết hợp (Ensemble Learning), hoạt động bằng cách xây dựng một quần thể bao gồm nhiều Cây quyết định (Decision Trees) trong thời gian huấn luyện.
Lý do học thuật để lựa chọn Random Forest:
1.  **Chống Overfitting (Quá khớp):** Nhờ cơ chế Bagging (Bootstrap Aggregating) - mỗi cây được huấn luyện trên một tập mẫu con ngẫu nhiên - và tính ngẫu nhiên trong việc chọn đặc trưng tại mỗi node, thuật toán này giải quyết hoàn hảo bài toán overfitting so với cây quyết định đơn lẻ.
2.  **Khả năng xử lý dữ liệu phi tuyến tính:** Đặc trưng của sóng WiFi phản xạ từ cơ thể người có tính phi tuyến tính cao tùy thuộc vào vị trí và khoảng cách. Random Forest phân chia không gian đặc trưng bằng các mặt cắt siêu phẳng phức tạp, mang lại hiệu suất phân loại xuất sắc mà không đòi hỏi tinh chỉnh (tuning) hyper-parameter quá phức tạp như các mạng Neural Networks học sâu (Deep Learning).

### 4.3. Kết quả thử nghiệm và Đánh giá
Hệ thống đã được thử nghiệm nghiêm ngặt trong điều kiện phòng với cấu hình 200 mẫu test, bao gồm các kịch bản có người (thở bình thường) và không có người (tĩnh).
Kết quả cực kỳ khả quan: **Mô hình Random Forest đạt độ chính xác (Accuracy) lên tới 94%.**
Sự thành công này khẳng định vai trò cốt lõi của chuỗi Pipeline Tiền xử lý tín hiệu (từ Unwrap Phase, lọc Elliptic đến PCA) đã làm sạch và làm nổi bật tín hiệu sinh tồn một cách xuất sắc từ phần cứng ESP32 có giá thành rẻ.

*[LƯU Ý CHO TÁC GIẢ: Bổ sung hình ảnh Confusion Matrix (Ma trận nhầm lẫn) của mô hình Random Forest, và biểu đồ ROC Curve (nếu có) để chứng minh độ tin cậy của con số 94%]*

---

## KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

### 1. Kết luận
Đồ án đã chứng minh một cách thực nghiệm và toán học khả năng ứng dụng công nghệ WiFi Sensing thông qua phân tích Channel State Information (CSI) để phát hiện nhịp thở không tiếp xúc. Điểm nhấn hàn lâm và kỹ thuật của hệ thống nằm ở việc tích hợp thành công phần cứng giá rẻ ESP32 với cấu trúc Panel Antenna định hướng, kết hợp với một luồng xử lý tín hiệu số (Digital Signal Processing - DSP) tinh vi (Phase Sanitization, Hampel, Savitzky-Golay, Elliptic bandpass, PCA). Mô hình học máy Random Forest cuối cùng đã mang lại độ chính xác 94%, khẳng định tiềm năng to lớn của hệ thống trong việc triển khai như một thiết bị SAR (Search and Rescue) trong tương lai.

### 2. Hạn chế và Hướng phát triển
Dù đạt kết quả tốt, hệ thống vẫn tồn tại các giới hạn lý thuyết:
*   Phần cứng ESP32 chỉ hoạt động ở kiến trúc 1x1 SISO và băng tần 2.4GHz, làm giảm khả năng phân giải không gian (Spatial resolution) so với các hệ thống MIMO (như 4x4 trên Router Broadcom).
*   Góc mở của Panel Antenna cần phải được tinh chỉnh cơ học thủ công để hướng về vị trí nạn nhân giả định.

**Hướng phát triển trong tương lai:**
*   Nâng cấp lên nền tảng phần cứng hỗ trợ MIMO (Multiple-Input Multiple-Output) ở băng tần 5GHz hoặc WiFi 6 (802.11ax) để thu được ma trận CSI đa chiều, ứng dụng Beamforming để định vị chính xác vị trí lồng ngực nạn nhân trong không gian 3D.
*   Ứng dụng các mạng học sâu tiên tiến hơn như LSTM (Long Short-Term Memory) hoặc Transformer để phân tích đặc trưng chuỗi thời gian (time-series) của CSI, nhằm phát hiện đồng thời cả nhịp thở và nhịp tim vi mô.
*   Tiến hành thực nghiệm trên các kịch bản NLOS khắt khe hơn (đâm xuyên nhiều lớp bê tông cốt thép) để mô phỏng chính xác môi trường cứu hộ thực tế.