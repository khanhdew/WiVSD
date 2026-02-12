# Nhận diện Dấu hiệu Sinh tồn sử dụng Cảm biến WiFi (WiFi Sensing)

Tài liệu này cung cấp cơ sở lý thuyết, giới thiệu đề tài và tổng quan các nghiên cứu liên quan về việc sử dụng tín hiệu WiFi (CSI) để phát hiện nhịp thở và nhịp tim. Nội dung được biên soạn dựa trên các công trình nghiên cứu uy tín từ IEEE và ACM.

## 1. Giới thiệu (Introduction)

Trong những năm gần đây, việc giám sát sức khỏe không tiếp xúc (contactless health monitoring) đã trở thành một chủ đề nghiên cứu nóng hổi, đặc biệt trong bối cảnh dân số già hóa và nhu cầu theo dõi sức khỏe tại nhà ngày càng tăng. Các phương pháp truyền thống thường yêu cầu người dùng đeo các thiết bị chuyên dụng (wearable devices) như đồng hồ thông minh hoặc đai ngực, gây ra sự bất tiện và khó chịu khi sử dụng lâu dài, đặc biệt là trong lúc ngủ.

**Cảm biến WiFi (WiFi Sensing)** nổi lên như một giải pháp thay thế đầy tiềm năng. Tận dụng hạ tầng WiFi có sẵn ở khắp mọi nơi, phương pháp này cho phép theo dõi các dấu hiệu sinh tồn (vital signs) như nhịp thở và nhịp tim mà không cần bất kỳ thiết bị đeo nào trên cơ thể, đảm bảo sự thoải mái và riêng tư cho người dùng. Công nghệ này hoạt động dựa trên nguyên lý: các chuyển động nhỏ của cơ thể (như lồng ngực phập phồng khi thở) sẽ gây ra những biến đổi tinh tế trong tín hiệu vô tuyến truyền giữa bộ phát và bộ thu WiFi.

## 2. Cơ sở Nghiên cứu (Research Basis)

### 2.1. Thông tin Trạng thái Kênh (Channel State Information - CSI)

Trong các chuẩn WiFi hiện đại (như 802.11n/ac/ax) sử dụng công nghệ OFDM (Orthogonal Frequency Division Multiplexing), tín hiệu được truyền trên nhiều sóng mang phụ (subcarriers) ở các tần số khác nhau. Thay vì chỉ sử dụng chỉ số cường độ tín hiệu (RSS) thô sơ và không ổn định, các nghiên cứu hiện đại tập trung vào **Channel State Information (CSI)**.

CSI mô tả cách tín hiệu lan truyền từ bộ phát đến bộ thu, bao gồm các hiện tượng như tán xạ (scattering), fading và suy hao công suất theo khoảng cách. Về mặt toán học, với một gói tin WiFi được truyền đi, CSI tại sóng mang phụ thứ $k$ có thể được biểu diễn dưới dạng số phức:

$$H(f_k, t) = |H(f_k, t)| e^{j \angle H(f_k, t)}$$

Trong đó:
*   $|H(f_k, t)|$: Là biên độ (amplitude) của kênh truyền.
*   $\angle H(f_k, t)$: Là pha (phase) của kênh truyền.

CSI cung cấp độ phân giải chi tiết hơn RSS rất nhiều ("fine-grained information"), cho phép phát hiện các biến đổi nhỏ trong môi trường.

### 2.2. Mô hình Vùng Fresnel (Fresnel Zone Model)

Để giải thích tại sao tín hiệu WiFi có thể phát hiện được cử động hô hấp, các nhà nghiên cứu (tiêu biểu là *Daqing Zhang et al.*) đã áp dụng **Mô hình Vùng Fresnel**.

Không gian giữa bộ phát (Tx) và bộ thu (Rx) được chia thành các vùng hình elip đồng tâm gọi là vùng Fresnel. Khi một vật thể (hoặc con người) chuyển động trong các vùng này, sóng phản xạ từ vật thể sẽ giao thoa với sóng đi thẳng (Line-of-Sight - LoS).
*   Nếu vật thể ở ranh giới vùng Fresnel lẻ, tín hiệu phản xạ sẽ tăng cường tín hiệu tại Rx (constructive interference).
*   Nếu vật thể ở ranh giới vùng Fresnel chẵn, tín hiệu phản xạ sẽ làm suy yếu tín hiệu tại Rx (destructive interference).

Sự thay đổi liên tục vị trí của lồng ngực khi hít vào/thở ra sẽ cắt qua các vùng Fresnel này, tạo ra các dao động hình sin đặc trưng trong biên độ và pha của tín hiệu CSI thu được.

## 3. Ảnh hưởng của Dấu hiệu Sinh tồn tới WiFi CSI

Chuyển động của lồng ngực do hô hấp (khoảng 5mm - 12mm) và nhịp tim (khoảng 0.5mm) tuy rất nhỏ nhưng vẫn đủ để làm thay đổi đường đi của sóng phản xạ.

Sự thay đổi chiều dài đường đi $\Delta d(t)$ do chuyển động của lồng ngực sẽ gây ra độ dịch pha $\Delta \phi(t)$ trong tín hiệu CSI thu tại máy thu, theo công thức:

$$\Delta \phi(t) = 2\pi \frac{\Delta d(t)}{\lambda}$$

Trong đó $\lambda$ là bước sóng của tín hiệu WiFi (khoảng 12.5 cm với sóng 2.4GHz và 6 cm với sóng 5GHz).
Vì biên độ chuyển động của nhịp tim rất nhỏ so với bước sóng, việc phát hiện nhịp tim khó khăn hơn nhiều so với nhịp thở và thường đòi hỏi các kỹ thuật xử lý tín hiệu nâng cao hoặc thuật toán học sâu (Deep Learning) để tách nhiễu.

## 4. Quy trình Xử lý Tín hiệu và Công nghệ Chi tiết (Technical Deep Dive)

Để trích xuất thành công dấu hiệu sinh tồn từ tín hiệu CSI đầy nhiễu, các hệ thống thường tuân theo một quy trình xử lý (pipeline) nghiêm ngặt gồm các bước sau:

### 4.1. Tiền xử lý dữ liệu và Làm sạch (Sanitization)

Tín hiệu CSI thô thu được từ các dòng chip WiFi thương mại (như ESP32, Intel 5300, Atheros) thường chứa nhiều nhiễu do phần cứng giá rẻ, bao gồm:
*   **Lỗi lệch tần số tàu sân bay (Carrier Frequency Offset - CFO)**: Gây ra sự quay pha ngẫu nhiên theo thời gian.
*   **Lỗi lệch tần số lấy mẫu (Sampling Frequency Offset - SFO)**: Gây ra sự trôi thời gian (time drift).
*   **Nhiễu môi trường**: Do các vật thể khác chuyển động hoặc nhiễu điện từ.

**Các kỹ thuật làm sạch phổ biến:**
1.  **Hampel Filter & Outlier Removal**: Loại bỏ các điểm dữ liệu bất thường (outliers) do nhiễu xung đột ngột.
2.  **Linear Phase Calibration (LPC)**: Hiệu chỉnh tuyến tính pha để loại bỏ độ trễ thời gian ngẫu nhiên. Công thức hiệu chỉnh thường dùng:
    $$\angle \hat{H}_k = \angle H_k - \frac{2\pi k}{N} \delta$$
    Trong đó $\delta$ là độ trễ ước tính.
3.  **Conjugate Multiplication (CM)**: Nhân liên hợp CSI giữa hai ăng-ten khác nhau để triệt tiêu các lỗi pha chung (common phase errors) do phần cứng, chỉ giữ lại sự khác biệt pha do môi trường.
4.  **PCA (Principal Component Analysis)**: Giảm chiều dữ liệu và trích xuất các thành phần chính chứa thông tin biến thiên mạnh nhất (thường là do hô hấp), loại bỏ các thành phần nhiễu nền (noise floor).

### 4.2. Trích xuất Dấu hiệu Sinh tồn (Vital Sign Extraction)

Sau khi làm sạch, tín hiệu cần được tách thành thành phần hô hấp (0.1 - 0.5 Hz) và nhịp tim (0.8 - 2.0 Hz).
*   **Bộ lọc thông dải (Band-pass Filtering)**: Sử dụng bộ lọc Butterworth hoặc Chebychev để tách riêng dải tần số mong muốn.
*   **Phân tích phổ (Spectral Analysis)**: Sử dụng FFT (Fast Fourier Transform) hoặc Short-Time Fourier Transform (STFT) để chuyển sang miền tần số, tìm đỉnh phổ năng lượng cao nhất tương ứng với nhịp thở/tim.
*   **Biến đổi Wavelet (Discrete Wavelet Transform - DWT)**: Hiệu quả hơn FFT trong việc xử lý tín hiệu không dừng (non-stationary signals), giúp tách nhịp tim yếu ớt khỏi nhiễu hô hấp mạnh hơn.

### 4.3. Các Kiến trúc Deep Learning Tiên tiến (2020-2024)

Thay vì thiết kế thủ công các bộ lọc (hand-crafted features), xu hướng hiện đại (2023-2024) sử dụng các mô hình học sâu end-to-end:

*   **CNN-LSTM / CNN-GRU**:
    *   **CNN (Convolutional Neural Network)**: Dùng để trích xuất đặc trưng không gian (spatial features) từ các sóng mang phụ (subcarriers) và các ăng-ten khác nhau.
    *   **LSTM/GRU (Recurrent Neural Network)**: Dùng để học sự phụ thuộc theo thời gian (temporal dependencies) của chuỗi tín hiệu, rất phù hợp với tính chất tuần hoàn của nhịp thở và tim.
    *   *Ví dụ*: Mô hình **SenseFi** hoặc các biến thể sử dụng cơ chế Attention (Attention Mechanism) để tập trung vào các đoạn tín hiệu quan trọng.

*   **Transformers**:
    *   Gần đây (2024), kiến trúc Transformer (với cơ chế Self-Attention) bắt đầu được áp dụng để xử lý chuỗi CSI dài, cho phép nắm bắt các mối quan hệ xa hơn và phức tạp hơn so với RNN truyền thống.
    *   Mô hình như **ViT (Vision Transformer)** có thể được áp dụng bằng cách coi phổ CSI (Spectrogram) như một hình ảnh đầu vào.

*   **Học Tương phản (Contrastive Learning)**:
    *   Giải quyết vấn đề thiếu dữ liệu gán nhãn (labeled data). Mô hình học cách phân biệt giữa các đoạn tín hiệu "tương tự" (cùng một trạng thái hô hấp) và "khác biệt" mà không cần nhãn cụ thể, sau đó tinh chỉnh (fine-tune) với một lượng nhỏ dữ liệu có nhãn.

## 5. Tổng quan các nghiên cứu liên quan (Literature Review)

Các nghiên cứu tiêu biểu được cập nhật với độ sâu kỹ thuật cao hơn:

### 5.1. PhaseBeat (IEEE ICDCS 2017)
*   **Đóng góp chính**: Sử dụng dữ liệu Pha (Phase) thay vì Biên độ (Amplitude).
*   **Kỹ thuật lõi**: Đề xuất phương pháp hiệu chỉnh pha bằng cách lấy hiệu giữa hai ăng-ten nhận (CSI Phase Difference) để loại bỏ lỗi CFO/SFO. Sử dụng DWT để tái tạo tín hiệu.

### 5.2. TensorBeat (ACM TIST 2017)
*   **Đóng góp chính**: Đa người dùng (Multi-person monitoring).
*   **Kỹ thuật lõi**: Sử dụng Phân rã Tensor CP (Canonical Polyadic Decomposition). Dữ liệu CSI được mô hình hóa dưới dạng Tensor 3 chiều (Thời gian $\times$ Sóng mang $\times$ Ăng-ten). Phân rã Tensor giúp tách các thành phần tín hiệu độc lập tương ứng với các người dùng khác nhau ở các vị trí khác nhau.

### 5.3. Các nghiên cứu mới nhất (2023-2024)
*   **BreatheSmart (2023)**: Sử dụng Deep Learning để phân loại các kiểu thở bất thường (như ngưng thở khi ngủ - apnea) với độ chính xác >98%.
*   **VitalCrypt (2024)**: Kết hợp mã hóa đồng hình (Homomorphic Encryption) với Deep Learning nhẹ (Lightweight DL) để đảm bảo quyền riêng tư người dùng ngay từ khâu thu thập dữ liệu, giải quyết lo ngại về bảo mật dữ liệu sinh trắc học.

## Kết luận
Lĩnh vực WiFi Sensing đã chuyển dịch từ các mô hình vật lý đơn giản (Fresnel Zone) sang các hệ thống phức tạp kết hợp Xử lý tín hiệu số nâng cao (Tensor Decomposition, Wavelet) và Trí tuệ nhân tạo (Deep Learning, Transformers). Sự kết hợp này cho phép đạt độ chính xác cao (>95% cho nhịp tim) và khả năng ứng dụng thực tế trong môi trường đa dạng, mở ra kỷ nguyên mới cho y tế số không xâm lấn.
