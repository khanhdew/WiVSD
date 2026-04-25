# BÁO CÁO TỔNG KẾT ĐỒ ÁN TỐT NGHIỆP
**Đề tài:** Applying WiFi Sensing Technology for Detecting Vital Signs in Rescue Operations
*(Ứng dụng công nghệ cảm biến WiFi trong việc phát hiện dấu hiệu sinh tồn phục vụ công tác tìm kiếm và cứu nạn)*

---

## LỜI MỞ ĐẦU

### 1. Đặt vấn đề và bối cảnh nghiên cứu
Trong bối cảnh biến đổi khí hậu toàn cầu đang diễn biến phức tạp, các thảm họa tự nhiên như động đất, sạt lở đất hay các tai nạn sập đổ công trình xây dựng ngày càng trở nên khó lường và để lại hậu quả nặng nề về nhân mạng. Trọng tâm của công tác tìm kiếm và cứu nạn (Search and Rescue - SAR) trong những khung giờ vàng (Golden Hours) đầu tiên sau khi thảm họa xảy ra là khả năng định vị và phát hiện sự sống một cách nhanh chóng, chính xác. Tuy nhiên, trong môi trường đổ nát, việc tiếp cận nạn nhân bị cản trở nghiêm trọng bởi các vật liệu đục (bê tông, gạch ngói, ván gỗ), khiến các phương pháp quan sát quang học thông thường như camera hoàn toàn bị vô hiệu hóa.

Các phương pháp y tế truyền thống để đo lường các dấu hiệu sinh tồn (Vital Signs) chủ đạo như nhịp tim và nhịp thở thường đòi hỏi phải có sự tiếp xúc vật lý trực tiếp với cơ thể người bệnh, ví dụ như sử dụng máy điện tâm đồ (ECG), máy đo nồng độ oxy trong máu (SpO2) kẹp ngón tay, hay các đai cảm biến biến dạng lồng ngực. Rõ ràng, những phương thức tiếp xúc trực tiếp (contact-based) này là hoàn toàn bất khả thi trong kịch bản mà nạn nhân bị vùi lấp.

Để giải quyết bài toán phát hiện sự sống xuyên tường (Through-wall life detection), các công nghệ cảm biến không tiếp xúc (Contactless Sensing) đã được nghiên cứu. Radar dải siêu rộng (Ultra-Wideband - UWB) hoặc radar sóng milimet (mmWave) cho thấy hiệu quả đâm xuyên và độ phân giải xuất sắc. Tuy nhiên, các hệ thống radar chuyên dụng này vấp phải rào cản chí mạng về chi phí triển khai cực kỳ đắt đỏ, cấu trúc phần cứng cồng kềnh, tiêu thụ năng lượng khổng lồ và đòi hỏi chuyên môn vận hành phức tạp. Điều này hạn chế khả năng trang bị đại trà cho lực lượng cứu hộ tiền phương.

Gần đây, với sự bùng nổ của mạng cục bộ không dây (WLAN), công nghệ cảm biến dựa trên sóng WiFi (WiFi Sensing) nổi lên như một giải pháp đột phá và mang tính cách mạng. Dựa trên bản chất sóng vô tuyến phân bố rộng khắp (Ubiquitous) ở các băng tần 2.4 GHz và 5 GHz, tín hiệu WiFi có khả năng đâm xuyên qua các vật cản phi kim loại. Khi tương tác với cơ thể con người, tín hiệu sẽ bị tán xạ, nhiễu xạ và phản xạ. Chuyển động cơ học vi mô (Micro-movements) của lồng ngực và bụng trong quá trình hô hấp (co giãn khoảng 5-12 mm) sẽ gây ra sự điều biến pha và biên độ lên sóng vô tuyến phản xạ. Bằng cách khai thác Thông tin Trạng thái Kênh truyền (Channel State Information - CSI) ở lớp Vật lý (Physical Layer) của mạng WiFi – vốn dĩ mang lại độ phân giải hạt mịn (fine-grained resolution) cho từng sóng mang con (subcarrier) – chúng ta hoàn toàn có thể trích xuất những biến đổi siêu nhỏ này, từ đó ước lượng chu kỳ hô hấp của nạn nhân mà không cần bất kỳ tiếp xúc vật lý nào.

### 2. Mục tiêu nghiên cứu
Mục tiêu cốt lõi của đồ án này là nghiên cứu cơ sở lý thuyết, thiết kế kiến trúc phần cứng, và xây dựng một quy trình xử lý tín hiệu số (Digital Signal Processing - DSP) kết hợp học máy (Machine Learning) nhằm phát triển hệ thống phát hiện dấu hiệu sinh tồn (nhịp thở) không tiếp xúc dựa trên tín hiệu WiFi CSI.
Hệ thống được tối ưu hóa đặc biệt cho bối cảnh tìm kiếm cứu nạn với các tiêu chí khắt khe:
1.  **Giá thành siêu thấp (Ultra-low cost):** Sử dụng phần cứng thương mại (COTS - Commercial Off-The-Shelf) thay vì thiết bị chuyên dụng đắt tiền.
2.  **Khả năng đâm xuyên (Penetration capability):** Đảm bảo hoạt động ổn định trong điều kiện không có tầm nhìn thẳng (NLOS - Non-Line-Of-Sight).
3.  **Kháng nhiễu đa đường (Multipath mitigation):** Triển khai các thuật toán loại bỏ nhiễu động do môi trường gây ra.
4.  **Tự động hóa phát hiện:** Ứng dụng trí tuệ nhân tạo để phân loại trạng thái có người/không có người một cách tự động với độ chính xác cao.

---

## CHƯƠNG 1: TỔNG QUAN TÀI LIỆU VÀ CƠ SỞ LÝ THUYẾT VỀ CHANNEL STATE INFORMATION (CSI)

### 1.1. Lịch sử phát triển của WiFi Sensing
Trong giai đoạn sơ khai, các nghiên cứu về cảm biến vô tuyến thường tận dụng Chỉ số cường độ tín hiệu nhận (Received Signal Strength Indicator - RSSI). RSSI đo lường tổng công suất tín hiệu vô tuyến thu được tại thiết bị nhận (Receiver) và được cung cấp sẵn trên mọi thiết bị WiFi thông qua lớp Điều khiển Truy cập Môi trường (MAC). Mặc dù dễ dàng truy xuất, RSSI lại bộc lộ những khiêm khuyết chí mạng: nó chỉ là một giá trị vô hướng (scalar) biểu diễn năng lượng tổng hợp, cực kỳ nhạy cảm với nhiễu môi trường, dao động mạnh và không có khả năng mô tả tính chất đa đường (multipath) phức tạp của không gian truyền sóng. Do đó, RSSI chỉ phù hợp cho các bài toán định vị thô (coarse-grained localization) hoặc phát hiện sự hiện diện ở quy mô lớn, hoàn toàn bất lực trước những chuyển động vĩ mô như nhịp thở.

Bước ngoặt lớn xảy ra vào đầu thập kỷ 2010 khi công nghệ Đa phân chia theo tần số trực giao (Orthogonal Frequency Division Multiplexing - OFDM) kết hợp Đa ngõ vào Đa ngõ ra (Multiple-Input Multiple-Output - MIMO) trở thành tiêu chuẩn trong chuẩn IEEE 802.11n. Thay vì một giá trị đơn lẻ, OFDM chia dải băng thông rộng thành nhiều dải băng hẹp trực giao gọi là sóng mang con (subcarriers). Để giải điều chế tín hiệu một cách chính xác tại bộ thu, hệ thống bắt buộc phải ước lượng đặc tính của kênh truyền cho từng sóng mang con. Tập hợp các ước lượng này chính là Thông tin Trạng thái Kênh truyền (CSI). Bằng cách khai thác các công cụ như Intel 5300 CSI Tool hay Atheros CSI Tool, các nhà nghiên cứu đã bắt đầu truy xuất được CSI ở mức lớp Vật lý, mở ra kỷ nguyên mới cho WiFi Sensing với độ phân giải hạt mịn (fine-grained).

### 1.2. Mô hình toán học của Kênh truyền vô tuyến và CSI
Trong một hệ thống truyền thông OFDM với dải băng thông hẹp (narrowband), tín hiệu nhận được tại bộ thu trên miền tần số có thể được biểu diễn qua phương trình toán học kinh điển:

$$Y(f, t) = H(f, t) \times X(f, t) + N(f, t)$$

Trong đó:
*   $X(f, t)$ là véc-tơ tín hiệu dải nền (baseband) được truyền đi từ bộ phát tại sóng mang con có tần số $f$ vào thời điểm $t$.
*   $Y(f, t)$ là véc-tơ tín hiệu nhận được tại bộ thu.
*   $N(f, t)$ là nhiễu trắng cộng theo phân bố Gauss (Additive White Gaussian Noise - AWGN) và các nhiễu nền khác.
*   $H(f, t)$ là Đáp ứng Tần số Kênh truyền (Channel Frequency Response - CFR), chính là dữ liệu CSI mà hệ thống trích xuất.

Đại lượng $H(f, t)$ là một số phức (complex number), biểu diễn sự biến đổi mà tín hiệu vô tuyến phải chịu khi đi qua không gian truyền dẫn. Nó có thể được biểu diễn dưới dạng tọa độ cực:

$$H(f, t) = |H(f, t)| e^{j\angle H(f, t)}$$

Trong đó:
*   $|H(f, t)|$ là Biên độ (Amplitude), đại diện cho sự suy hao (Attenuation) năng lượng của tín hiệu do khoảng cách truyền, sự hấp thụ của vật liệu và suy hao phân cực.
*   $\angle H(f, t)$ là Góc Pha (Phase), phản ánh sự dịch chuyển pha (Phase shift) do thời gian trễ truyền dẫn (Time of Flight - ToF) trong không gian dội lại.

### 1.3. Hiệu ứng đa đường (Multipath Fading) và Vùng Fresnel
Trong môi trường thực tế (đặc biệt là không gian trong nhà hoặc môi trường đổ nát phức tạp), sóng vô tuyến bức xạ từ ăng-ten phát không bao giờ di chuyển theo một đường thẳng lý tưởng duy nhất đến ăng-ten thu. Thay vào đó, tín hiệu sẽ chịu tác động của các hiện tượng phản xạ (reflection), khúc xạ (refraction), và tán xạ (scattering) khi tương tác với tường, trần nhà, mặt đất, đồ đạc và chính cơ thể con người.

Kết quả là bộ thu nhận được vô số bản sao (copies) của tín hiệu gốc, mỗi bản sao di chuyển theo một con đường (path) có chiều dài khác nhau, chịu mức suy hao khác nhau và đến bộ thu ở các thời điểm trễ (delay) khác nhau. Hiện tượng này được gọi là Hiệu ứng đa đường (Multipath Fading). CSI chính là sự tổng hợp hình học (vector superposition) của toàn bộ các tia sóng đa đường này:

$$H(f, t) = \sum_{k=1}^{L} \alpha_k(t) e^{-j 2\pi f \tau_k(t)}$$

Trong đó:
*   $L$ là tổng số đường truyền (multipath rays).
*   $\alpha_k(t)$ là biên độ suy hao của tia thứ $k$.
*   $\tau_k(t)$ là thời gian trễ của tia thứ $k$, tương quan mật thiết với chiều dài đường đi $d_k(t)$ thông qua phương trình $\tau_k(t) = d_k(t) / c$ (với $c$ là tốc độ ánh sáng).

**Nguyên lý phát hiện nhịp thở:**
Giả sử có một môi trường với các vật thể tĩnh và một mục tiêu (cơ thể người) đang hô hấp. Quần thể các đường truyền $L$ có thể được chia thành hai nhóm: nhóm các đường truyền tĩnh (Static paths - phản xạ từ tường, nền nhà) và đường truyền động (Dynamic path - phản xạ từ lồng ngực người).
Khi con người hít thở, lồng ngực mở rộng và co lại tạo ra một độ dời $\Delta d(t)$ có tính tuần hoàn. Mặc dù $\Delta d(t)$ rất nhỏ (cỡ milimet), nhưng do bước sóng của WiFi (ví dụ: $\lambda \approx 12.5 \text{ cm}$ ở băng tần 2.4 GHz) cũng tương đối ngắn, sự dịch chuyển này đủ để tạo ra một sự thay đổi pha đáng kể:

$$\Delta \phi(t) = \frac{2\pi \Delta d(t)}{\lambda}$$

Sự biến thiên pha $\Delta \phi(t)$ của tia động (Dynamic path) sẽ làm thay đổi vector tổng hợp của tín hiệu nhận được tại bộ thu. Quỹ tích của vector CSI trong mặt phẳng phức sẽ vẽ ra một cung tròn khi lồng ngực dịch chuyển. Bằng cách chiếu sự dịch chuyển này lên trục biên độ hoặc trục pha, chúng ta sẽ thu được một tín hiệu hàm sin biến thiên tuần hoàn tương ứng với chính nhịp thở của đối tượng. Khái niệm này còn được giải thích sâu hơn thông qua lý thuyết Vùng Fresnel (Fresnel Zones), nơi sự thay đổi tín hiệu mạnh hay yếu phụ thuộc vào việc đường truyền động cắt qua các ranh giới của các vùng Fresnel đồng tâm.

---

## CHƯƠNG 2: THIẾT KẾ PHẦN CỨNG VÀ MÔ HÌNH THU THẬP DỮ LIỆU

### 2.1. Phân tích và lựa chọn vi điều khiển ESP32
Việc lựa chọn thiết bị phần cứng đóng vai trò tiên quyết quyết định tính khả thi của hệ thống trong kịch bản cứu hộ SAR. Historcally, các nghiên cứu WiFi Sensing học thuật thường phụ thuộc vào các dòng card mạng Intel WiFi Link 5300 (Intel 5300 CSI Tool) hay chip Atheros. Dù cung cấp chất lượng CSI tốt nhờ số lượng anten MIMO lớn (3x3), các nền tảng này đã trở nên lỗi thời, ngưng sản xuất, và buộc phải chạy trên các máy tính xách tay cồng kềnh, tiêu thụ nhiều điện năng.

Trong đồ án này, vi điều khiển **ESP32** (của Espressif Systems) được lựa chọn làm nền tảng nòng cốt (Core processing unit) vì những lý luận khoa học và thực tiễn sau:
1.  **Định tuyến biên (Edge Deployment) và Kích thước (Form Factor):** ESP32 là một hệ thống trên chip (SoC) cực kỳ nhỏ gọn gọn gọn, cho phép nhúng vào các thiết bị IoT siêu nhỏ. Trong kịch bản sập công trình, các thiết bị này có thể được triển khai thành một mảng mạng cảm biến không dây (Wireless Sensor Networks) thả qua các khe hở của cấu trúc đổ nát, việc mà các laptop dùng chip Intel không thể làm được.
2.  **Hỗ trợ CSI nguyên bản (Native CSI Support):** Khác với sự phức tạp của việc biên dịch (compile) custom kernel như trên Linux để lấy dữ liệu từ Intel/Broadcom, framework ESP-IDF hỗ trợ API `esp_wifi_set_csi_rx_cb` cho phép trích xuất trực tiếp raw CSI từ lớp MAC/PHY. Dữ liệu CSI thu được bao gồm 64 giá trị số phức (I/Q) tương ứng với 64 sóng mang con trên băng thông 20 MHz.
3.  **Tối ưu năng lượng (Ultra-Low Power):** ESP32 tiêu thụ dòng điện rất thấp. Hệ thống có thể hoạt động bền bỉ trong vòng 48-72 giờ chỉ với một viên pin dự phòng tiêu chuẩn, đảm bảo thời gian hoạt động trọn vẹn trong "Khung giờ vàng" của công tác cứu hộ.

*Hạn chế thiết kế:* Do kiến trúc phần cứng, ESP32 giới hạn ở chuẩn 802.11n, sử dụng anten SISO (Single-Input Single-Output) và độ phân giải dữ liệu 8-bit. Việc thiếu đi sự đa dạng không gian (Spatial Diversity) của hệ thống MIMO đặt ra thách thức cực lớn cho khâu xử lý tín hiệu ở các bước sau.

### 2.2. Kỹ thuật bức xạ và Lựa chọn Panel Antenna
Nhằm khắc phục nhược điểm SISO của ESP32 và tối ưu hóa hệ thống cho môi trường cứu hộ (nhiều vật cản, nhiễu mạnh), đồ án đã thực hiện một nâng cấp mang tính đột phá về thiết kế: thay thế ăng-ten đẳng hướng (Omni-directional antenna) đi kèm board mạch bằng **Panel Antenna (Ăng-ten định hướng mảng pha)**.

Phân tích điện từ trường lý giải sự ưu việt của thiết kế này:
1.  **Tập trung Năng lượng (Beamforming effect):** Panel Antenna có búp sóng (beamwidth) hẹp (thường từ 30° đến 60°), giúp tập trung Công suất bức xạ đẳng hướng tương đương (EIRP) vào một hướng cụ thể. Điều này làm tăng độ lợi ăng-ten (Antenna Gain) lên mức 12-14 dBi (so với 2-3 dBi của ăng-ten đẳng hướng). Năng lượng tập trung này đóng vai trò sống còn giúp tín hiệu 2.4GHz có đủ khả năng đâm xuyên qua các vách tường gạch đục, bê tông cốt thép để tiếp cận nạn nhân (NLOS Penetration).
2.  **Lọc Không gian (Spatial Filtering) giảm Đa đường:** Nhiễu đa đường (Multipath) từ các mảng vỡ ở các hướng không mong muốn là kẻ thù số một che lấp tín hiệu hô hấp. Panel antenna hoạt động như một bộ lọc thụ động trong miền không gian (spatial filter), triệt tiêu các tia sóng (rays) dội lại từ các góc nằm ngoài búp sóng chính. Tỷ số Tín hiệu trên Nhiễu (SNR) của "tia động" (dynamic path) phản xạ từ nạn nhân được nâng lên đáng kể.

### 2.3. Thông số môi trường và Cấu hình thu thập
Quá trình thiết lập thực nghiệm (Empirical Setup) được thiết kế khắt khe nhằm thu thập tập dữ liệu (dataset) chất lượng cao:
*   **Không gian thực nghiệm:** Môi trường mô phỏng không gian trong nhà (Indoor environment) có kích thước tiêu chuẩn $8m \times 4m$, chứa các vật dụng gây tán xạ sóng.
*   **Băng tần hoạt động (Operating Frequency):** Lựa chọn băng tần 2.4 GHz. Sóng điện từ ở 2.4 GHz có bước sóng $\lambda \approx 12.5 \text{ cm}$. Theo lý thuyết truyền sóng, bước sóng càng dài, tính chất nhiễu xạ (Diffraction) quanh vật cản và khả năng đâm xuyên vật liệu (Penetration) càng tốt hơn so với băng tần 5 GHz (bước sóng ngắn dễ bị hấp thụ bởi môi trường).
*   **Cấu trúc dữ liệu:** Gói tin được thiết lập chuẩn HE SU (High Efficiency Single User) nhằm tối ưu hóa việc định tuyến frame và cấp phát OFDM. Băng thông kênh truyền được khóa cứng ở 20 MHz (tạo ra 64 subcarriers).
*   **Tần số lấy mẫu (Sampling Rate):** Để đáp ứng khắt khe định lý lấy mẫu Nyquist-Shannon ($f_{sample} \ge 2 \cdot f_{max}$), đồng thời chống lại hiện tượng chồng phổ (Aliasing), tốc độ phát gói tin (Packet Injection Rate) được ép ở mức 100 packets/second (100 Hz). Với tần số hô hấp thông thường của con người nằm trong khoảng 0.2 - 0.5 Hz (12-30 nhịp/phút), việc lấy mẫu ở 100 Hz cung cấp một độ phân giải thời gian (temporal resolution) cực kỳ dày đặc (oversampling). Sự lấy mẫu dư thừa này cung cấp không gian dữ liệu khổng lồ để các bộ lọc FIR/IIR hoạt động trơn tru và phát huy hiệu quả tối đa.
*   **Lưu trữ dữ liệu:** Dữ liệu chuỗi thời gian (time-series) của I/Q data được xuất liên tục qua cổng Serial và đóng gói thành file `.csv` chứa trong thư mục `Router` với tổng số 4000 packets/file (tương đương 40 giây quan sát liên tục cho mỗi mẫu).

*[LƯU Ý CHO TÁC GIẢ: Bổ sung hình vẽ (Block Diagram) mô tả luồng giao tiếp giữa bộ phát (Tx) và bộ thu (Rx) trang bị ESP32, hình ảnh minh họa búp sóng của Panel Antenna, và sơ đồ bố trí thiết bị (Floor Plan) trong phòng thí nghiệm]*

---

## CHƯƠNG 3: KIẾN TRÚC TIỀN XỬ LÝ TÍN HIỆU SỐ TIÊN TIẾN (ADVANCED DIGITAL SIGNAL PREPROCESSING PIPELINE)

Thách thức khó khăn nhất trong WiFi Sensing là sự tồn tại của các nguồn nhiễu loạn (noises) có công suất mạnh hơn gấp hàng nghìn lần so với tín hiệu thay đổi nhỏ nhoi do lồng ngực người thở gây ra. Nguồn nhiễu này đến từ nhiễu nhiệt (thermal noise), không đồng bộ xung nhịp phần cứng (hardware clock desynchronization), dao động điện áp, và nhiễu từ môi trường (quạt gió, các thiết bị điện tử khác).

Để giải quyết bài toán hóc búa này, một luồng tiền xử lý dữ liệu phức hợp (Pipeline) bao gồm nhiều tầng lọc toán học tiên tiến đã được triển khai trong file module `processing.py` và `filters.py`.

### 3.1. Giải điều chế Không gian Phức (Complex Demodulation)
Dữ liệu I/Q nguyên thủy đọc từ ESP32 được lưu trữ dạng chuỗi xen kẽ phần thực và ảo (real, imag). Bước đầu tiên là phục hồi cấu trúc số phức $H_k(t) = I_k(t) + jQ_k(t)$ cho sóng mang thứ $k$.

Trích xuất Biên độ (Amplitude - $A_k$) và Pha (Phase - $\phi_k$) bằng phép chuyển đổi hệ tọa độ Euclid sang hệ tọa độ cực:
$$A_k(t) = \sqrt{I_k(t)^2 + Q_k(t)^2}$$
$$\phi_k(t) = \arctan2(Q_k(t), I_k(t))$$
Việc thực hiện các phép toán trên cấu trúc mảng đa chiều (Tensor) được tối ưu hóa bằng thư viện `NumPy` để đạt hiệu năng xử lý song đa luồng.

### 3.2. Giải nén Pha và Thanh lọc Pha (Phase Unwrapping and Sanitization)
**Vấn đề cuộn pha (Phase Wrapping):** Do hàm arctan chỉ có tập giá trị từ $-\pi$ đến $\pi$, khi độ trễ truyền dẫn làm góc pha vượt qua giới hạn này, giá trị pha bị cắt xén (wrap) và cuộn lại, tạo ra những điểm đứt gãy không liên tục cực lớn (nhảy vọt $2\pi$).
Giải pháp: Áp dụng thuật toán Phase Unwrapping (sử dụng `np.unwrap`). Thuật toán quét tuần tự qua trục thời gian/tần số, phát hiện các đạo hàm bậc nhất vượt ngưỡng $\pi$, và tiến hành bù đắp lượng $2\pi$ để khôi phục tính liên tục của dòng pha.

**Lỗi đồng bộ phần cứng (CFO & SFO):** Mặc dù đã unwrap, góc pha thực tế thu nhận được $\hat{\phi}_k(t)$ khác xa góc pha lý thuyết $\phi_k(t)$ do thiết bị phát và thu không dùng chung một bộ dao động thạch anh (Oscillator). Điều này dẫn đến sự sai lệch Carrier Frequency Offset (CFO - gây nhiễu hằng số) và Sampling Frequency Offset (SFO - gây nhiễu tuyến tính theo tần số sóng mang):
$$\hat{\phi}_k(t) = \phi_k(t) + 2\pi \left( \frac{k}{N} \Delta t \right) + \beta + Z$$
Để triệt tiêu SFO và CFO, thuật toán **Phase Sanitization** được áp dụng dựa trên giả định rằng các thành phần lỗi SFO làm pha lệch tuyến tính dọc theo các sóng mang con $k$. Bằng cách áp dụng **Hồi quy Tuyến tính (Linear Regression) sử dụng bình phương tối thiểu (Least Squares)** trên phân bố pha của các subcarrier hợp lệ (bỏ qua guard null subcarriers), ta tìm được độ dốc $a$ (tương ứng SFO) và hằng số $b$ (tương ứng CFO). Tín hiệu pha tinh khiết (Sanitized Phase) thu được bằng cách lấy pha ban đầu trừ đi thành phần tuyến tính này.

### 3.3. Thuật toán Lọc nhiễu ngoại lai Hampel (Hampel Outlier Removal)
Tín hiệu CSI sau trích xuất thường dính các xung nhiễu gai (Impulsive noise / Outliers) sinh ra bởi sự mất mát gói tin (packet drop), sự thay đổi trạng thái nội bộ của vi mạch (AGC gain shift). Các bộ lọc tuyến tính như Moving Average sẽ bị phá vỡ hoàn toàn (distorted) khi gặp các gai nhiễu có biên độ lớn.

**Bộ lọc Hampel** là một bộ lọc phi tuyến (Non-linear filter) mang tính chống chịu cao (Robust statistics). Đối với một cửa sổ trượt độ rộng $K$ tâm tại $i$, thuật toán không tính trung bình (mean) mà tính **Trung vị (Median - $m_i$)**.
Tiếp đó, tính toán **Độ lệch tuyệt đối so với trung vị (Median Absolute Deviation - MAD)**:
$$MAD_i = median(|x_j - m_i|) \quad \text{với } j \in [i - K/2, i + K/2]$$
Độ lệch chuẩn ước lượng được định nghĩa là $\sigma \approx 1.4826 \times MAD_i$.
Bất kỳ điểm dữ liệu nào thỏa mãn $|x_i - m_i| > 3\sigma$ (ngưỡng 3-sigma) sẽ bị gắn cờ là nhiễu ngoại lai và bị thay thế cưỡng bức bằng giá trị trung vị $m_i$. Trong thực nghiệm, cửa sổ $K=50$ cho biên độ và $K=30$ cho pha đã triệt tiêu hoàn toàn các gai nhiễu mà không làm suy giảm tần số nhịp thở.

### 3.4. Căng chỉnh đường cong bằng Bộ lọc Savitzky-Golay (S-G Filter)
Để tiếp tục làm mịn tín hiệu (Smoothing) nhưng không gây méo dạng sóng (Waveform distortion), bộ lọc **Savitzky-Golay (Local Polynomial Regression)** được khai thác.
Khác với các bộ lọc thông thấp IIR/FIR làm trễ pha và suy hao đỉnh (peak attenuation), bộ lọc S-G thực hiện khớp một hàm đa thức bậc $p$ (ở đây chọn bậc 3) vào một cửa sổ dữ liệu trượt kích thước $W$ (ở đây chọn $W=31$) bằng phương pháp bình phương tối thiểu.
Về mặt toán học, Savitzky-Golay bảo toàn tối đa các moment bậc cao của tín hiệu, giúp các đỉnh (peaks) và đáy (valleys) của sóng hô hấp giữ nguyên độ sắc nét và biên độ, là cơ sở sống còn để thuật toán trích xuất đặc trưng đo đếm chính xác nhịp độ.

### 3.5. Cô lập dải thông bằng Bộ lọc Thông dải Elliptic (Elliptic Bandpass Filter)
Tín hiệu thu được hiện tại vẫn là sự chồng chập của nhịp thở (0.15 - 0.5 Hz), nhịp tim (1.0 - 2.0 Hz), cử động cơ thể chậm (<0.1 Hz) và các rung động tĩnh học.
Sứ mệnh cô lập riêng tần số hô hấp được giao cho **Bộ lọc IIR Elliptic (Cauer Filter)** bậc 4. Trong lý thuyết xử lý tín hiệu số (DSP), bộ lọc Butterworth cung cấp dải thông phẳng tuyệt đối nhưng độ dốc cắt (roll-off) quá thoải. Ngược lại, bộ lọc Elliptic chấp nhận một lượng gợn sóng nhỏ (Ripple) ở cả dải thông (Passband) và dải triệt (Stopband) để đổi lấy một **khu vực chuyển tiếp (Transition band) cực kỳ dốc và hẹp**.
Với cấu hình tham số:
*   Tần số cắt dưới (Lowcut) = 0.15 Hz
*   Tần số cắt trên (Highcut) = 0.5 Hz (Tương ứng 9 - 30 nhịp thở/phút)
*   Ripple dải thông (rp) = 0.1 dB
*   Suy hao dải triệt (rs) = 40 dB

Bộ lọc Elliptic đã tàn nhẫn cắt bỏ toàn bộ thành phần ngoài băng tần (out-of-band noises). Đầu ra của khối này là một tín hiệu hình sin hoàn mỹ, dao động tuần hoàn, phản ánh nguyên bản chuyển động giãn nở lồng ngực của đối tượng quan sát.

### 3.6. Tối ưu Không gian với Phân tích Thành phần Chính (PCA)
Tín hiệu thở phản xạ trên 64 sóng mang con mang tính đồng pha nhưng khác biệt về biên độ (do Fading). Một số subcarrier rơi vào vùng rãnh sâu (Deep Fade) mang tỷ số SNR cực thấp, mang toàn nhiễu. Việc tính trung bình cộng toàn bộ 64 subcarriers sẽ làm loãng và phá hủy tín hiệu thở.

Thuật toán **Phân tích Thành phần Chính (Principal Component Analysis - PCA)** được áp dụng để giải quyết bài toán này. PCA thực hiện chuẩn hóa ma trận $X$ (Packet x Subcarriers), tính toán ma trận Hiệp phương sai (Covariance Matrix) và phân rã Giá trị Đặc dị (Singular Value Decomposition - SVD).
Kết quả thu được là một phép biến đổi tuyến tính, nén 64 chiều dữ liệu xuống còn một số lượng nhỏ các thành phần chính trực giao (Principal Components - PCs).
PC thứ nhất (PC1) là hình chiếu của dữ liệu lên hướng có phương sai lớn nhất. Do biến thiên lồng ngực mang năng lượng tương quan lớn nhất trên toàn bộ các sóng mang, PC1 (hoặc PC2) sẽ tự động thâu tóm và "vắt" kiệt thông tin hô hấp, bỏ lại các nhiễu vô hướng ở các PC thấp hơn.

*[LƯU Ý CHO TÁC GIẢ: Cung cấp loạt đồ thị biểu diễn tín hiệu Time-Series dạng sóng trước và sau khi đi qua từng bộ lọc (Raw -> Hampel -> Savitzky-Golay -> Bandpass -> PCA) để chứng minh tính hiệu quả ưu việt của Pipeline.]*

---

## CHƯƠNG 4: PHÂN TÍCH PHỔ, TRÍCH XUẤT ĐẶC TRƯNG VÀ MÔ HÌNH HỌC MÁY (MACHINE LEARNING)

Quy trình tiền xử lý đã xuất ra tín hiệu PC1 dạng sóng tinh khiết. Tuy nhiên, để hệ thống tự động đưa ra kết luận "Có người sống/hô hấp" hay "Môi trường trống rỗng" đòi hỏi khả năng tư duy phân loại của Trí tuệ Nhân tạo (AI).

### 4.1. Chuyển đổi Miền Tần số và Entropy Phổ (Spectral Entropy)
Mô hình AI cần các đặc trưng (Features) tĩnh và ổn định. Dữ liệu PC1 từ miền thời gian được chuyển sang miền tần số bằng phép **Biến đổi Fourier Thời gian ngắn (Short-Time Fourier Transform - STFT)** với hàm cửa sổ Hanning (nhằm giảm thiểu rò rỉ phổ - spectral leakage). Kết quả sinh ra một ma trận Phổ đồ (Spectrogram) chứa năng lượng theo thời gian và tần số.

Chỉ báo quan trọng nhất để phân biệt sự tồn tại của nhịp thở là **Entropy Phổ (Spectral Entropy - $SE$)**:
$$SE = \frac{-\sum_{f} P(f) \log_2 P(f)}{\log_2(N_f)}$$
*   Khi **không có đối tượng** hoặc đối tượng di chuyển hỗn loạn, năng lượng phân bổ đều trên mọi dải tần như nhiễu trắng (White Noise), xác suất $P(f)$ tiệm cận phân bố đồng đều, làm cho giá trị Entropy Phổ đạt mức cao (Gần 1.0).
*   Khi **có người đang thở đều**, toàn bộ năng lượng phổ bị cô đặc thành một đỉnh (peak) chói lọi duy nhất tại tần số hô hấp. Phân bố $P(f)$ trở nên nhọn (Spiky), khiến giá trị Entropy Phổ lao dốc mạnh.
Hệ thống tính toán SE kết hợp cùng các đặc trưng không gian thời gian (Spatial-temporal features) như: Trung bình (Mean), Độ lệch chuẩn (Standard Deviation), Phương sai (Variance), và Hệ số Biến thiên (Coefficient of Variation) để tạo ra tập véc-tơ đặc trưng nạp vào mô hình.

### 4.2. Kiến trúc Mô hình Học máy: Rừng ngẫu nhiên (Random Forest Classifier)
Trong hằng hà sa số các thuật toán học máy từ Máy Vector Hỗ trợ (SVM), K-Láng giềng gần nhất (KNN) đến Mạng Nơ-ron (Deep Learning), **Random Forest (RF)** được lựa chọn làm cơ quan nội tạng ra quyết định của hệ thống.

Random Forest là một thuật toán Học kết hợp (Ensemble Learning) mạnh mẽ, kiến tạo từ hàng trăm, hàng nghìn cây quyết định (Decision Trees) trong giai đoạn huấn luyện (Training phase) và đưa ra quyết định bằng cách lấy biểu quyết đa số (Majority Voting).
Cơ sở khoa học của sức mạnh RF:
1.  **Bootstrap Aggregating (Bagging):** Thay vì train trên toàn bộ dữ liệu dễ dẫn đến thiên lệch, RF tạo ra nhiều tập dữ liệu con bằng cách bốc thăm có hoàn lại (sampling with replacement). Mỗi cây Decision Tree lớn lên trên một tập dữ liệu khác biệt, làm giảm mạnh phương sai (Variance) của mô hình.
2.  **Độ đo tinh khiết Gini (Gini Impurity) và Information Gain:** Tại mỗi nút rẽ nhánh (Node split) của cây, thuật toán không rà soát toàn bộ đặc trưng mà chỉ lấy một tập con ngẫu nhiên. Thuật toán chọn đặc trưng phân nhánh tối ưu bằng cách tối thiểu hóa độ lẫn lộn Gini:
    $$Gini = 1 - \sum_{i=1}^{C} (p_i)^2$$
    Điều này ép buộc hệ thống phải tìm ra ngưỡng cắt chính xác nhất cho Entropy phổ hay Hệ số biến thiên để chia tách hai lớp "Có hô hấp" và "Không hô hấp".
3.  **Kháng nhiễu đa luồng (Overfitting resistance):** Nhờ sự đa dạng và ngẫu nhiên nội tại, Random Forest cực kỳ miễn nhiễm với Overfitting (tình trạng mô hình học vẹt dữ liệu train mà thất bại trên dữ liệu thực tế) – một điểm yếu tử huyệt của Mạng Neural khi làm việc với lượng dataset cỡ nhỏ/trung bình trong nghiên cứu không gian kín.

### 4.3. Kết quả đánh giá Mô hình (Evaluation Results)
Để đánh giá hệ thống, quy trình kiểm chứng chéo (Cross-validation) và tập Holdout test set đã được sử dụng. Cấu trúc thử nghiệm bao gồm 200 mẫu thử độc lập, hoàn toàn chưa từng được hệ thống quan sát trong quá trình huấn luyện, chứa cả các kịch bản môi trường không người và các kịch bản có nạn nhân với góc độ nằm, khoảng cách khác nhau.

Thành tích đạt được cực kỳ ấn tượng:
*   **Độ chính xác tổng thể (Overall Accuracy):** **94.0%**.
*   Khả năng phát hiện sai (False Positives - Nhận diện sai nhiễu môi trường thành người) và Bỏ lọt (False Negatives - Có người nhưng báo không) bị ép xuống mức tối thiểu (dưới 6%).
*   Độ trễ xử lý (Inference latency) của mô hình Random Forest chỉ rơi vào cỡ mili-giây, hoàn toàn đáp ứng kỳ vọng chạy Real-time trên hệ thống nhúng (Embedded devices) cho cứu hộ trực tiếp.

Con số 94% không chỉ khẳng định tính ưu việt của thuật toán Random Forest, mà bản chất nó là lời minh chứng đanh thép cho cả một triết lý thiết kế hệ thống từ đầu: Việc sử dụng ESP32 giá rẻ kết hợp Panel Antenna định hướng, cùng với chuỗi xử lý tín hiệu DSP khắt khe (Phase Sanitization, Elliptic Bandpass, PCA) đã trích xuất thành công và cung cấp một tín hiệu cực kỳ "sạch" và dồi dào thông tin lượng tử (Information Entropy) cho trí tuệ nhân tạo.

*[LƯU Ý CHO TÁC GIẢ: Tại đây, cung cấp Ma trận Nhầm lẫn (Confusion Matrix), Báo cáo Phân loại (Classification Report bao gồm Precision, Recall, F1-Score) và Biểu đồ mức độ quan trọng của đặc trưng (Feature Importance Plot) sinh ra từ mô hình Random Forest để luận giải thêm tính học thuật]*

---

## KẾT LUẬN VÀ KIẾN NGHỊ HƯỚNG MỞ RỘNG

### 1. Tổng kết những đóng góp của đề tài
Công trình đồ án tốt nghiệp này đã trình bày một hệ sinh thái nghiên cứu khép kín từ tầng vật lý đến tầng trí tuệ nhân tạo để giải quyết bài toán phát hiện dấu hiệu sinh tồn không tiếp xúc phục vụ cứu hộ cứu nạn.
Bằng sự kết hợp mang tính sáng tạo giữa nền tảng vi điều khiển IoT giá rẻ (ESP32), kỹ thuật hội tụ năng lượng bằng ăng-ten định hướng (Panel Antenna), và một quy trình xử lý tín hiệu phức hợp chuẩn mực học thuật (unwrap pha, hồi quy tuyến tính khử lỗi xung nhịp, lọc ngoại lai Hampel, lọc đa thức Savitzky-Golay, bộ lọc dốc đứng Elliptic và phép nén đa chiều PCA), hệ thống đã thành công giải mã được sự dịch chuyển vi mô ở quy mô bước sóng của lồng ngực người. Việc mô hình Random Forest đạt được ngưỡng chính xác 94% trên các dữ liệu nghiệm thu độc lập đã chứng minh tính khả thi, tính tin cậy và sự sẵn sàng của công nghệ WiFi Sensing trong các ứng dụng SAR thực tế.

### 2. Các điểm hạn chế (Limitations)
Bất chấp những kết quả tích cực, với tinh thần khoa học khách quan, hệ thống vẫn bộc lộ những rào cản lý thuyết chưa thể vượt qua:
*   **Giới hạn SISO:** ESP32 là hệ thống 1 ăng-ten thu và 1 ăng-ten phát. Việc thiếu vắng đa dạng không gian (Spatial diversity) như các hệ thống MIMO (Nhiều ngõ vào - Nhiều ngõ ra) cản trở hệ thống thực hiện định vị góc tới (Angle of Arrival - AoA), khiến chúng ta chỉ biết có người chứ chưa định vị được chính xác tọa độ 3D của nạn nhân.
*   **Giới hạn tần số:** Mặc dù 2.4 GHz đâm xuyên tốt, nhưng do bước sóng dài (12.5 cm), sự thay đổi góc pha $\Delta \phi$ sinh ra bởi dịch chuyển lồng ngực ($\approx 1$ cm) là rất nhỏ, yêu cầu SNR cực kỳ khắt khe. Các thiết bị phát sóng dân dụng lân cận (Lò vi sóng, Bluetooth) hoạt động cùng dải tần có thể gây nhiễu đồng kênh nghiêm trọng (Co-channel interference).

### 3. Kiến nghị hướng nghiên cứu tương lai
Dựa trên nền tảng của nghiên cứu này, các công trình tiếp theo có thể mở rộng ranh giới công nghệ theo các hướng sau:
1.  **Dịch chuyển sang phần cứng WiFi 6 / 802.11ax:** Ứng dụng các kiến trúc đa anten MIMO như Broadcom BCM4366 (4x4) hay Intel AX210 trên băng tần 5GHz / 6GHz (bước sóng cực ngắn) để phóng to sự nhạy cảm của góc pha. Ứng dụng kỹ thuật Beamforming định hướng số.
2.  **Ứng dụng Mạng Học Sâu (Deep Learning):** Thay vì trích xuất đặc trưng thủ công cho Random Forest, có thể đẩy trực tiếp Ma trận Phổ (Spectrogram Tensor) vào các mạng Neural Tích chập (Convolutional Neural Networks - CNNs) hoặc Mạng bộ nhớ dài-ngắn (Long Short-Term Memory - LSTM) để hệ thống tự động bóc tách các feature phức tạp ẩn sâu trong miền thời gian-tần số.
3.  **Tách nhịp tim (Heartbeat detection):** Biên độ dịch chuyển của nhịp tim chỉ rơi vào khoảng 0.1 - 0.5 mm (nhỏ hơn 10 lần so với nhịp thở). Nếu áp dụng các bộ lọc có độ phân giải siêu cao hoặc radar FMCW lai, việc trích xuất đồng thời nhịp thở và nhịp tim sẽ mang lại ý nghĩa y tế chuyên sâu cho đội ngũ cấp cứu tại hiện trường.