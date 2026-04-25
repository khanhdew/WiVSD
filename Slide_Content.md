# NỘI DUNG SLIDE THUYẾT TRÌNH ĐỒ ÁN
*(Tài liệu này cung cấp cấu trúc, các gạch đầu dòng đưa lên slide và lời thoại gợi ý (Speaker Notes) cho từng slide)*

---

## SLIDE 1: TIÊU ĐỀ (TITLE SLIDE)
**Nội dung hiển thị trên slide:**
*   **Tên đồ án:** Applying WiFi Sensing Technology for Detecting Vital Signs in Rescue Operations
*   *(Ứng dụng công nghệ cảm biến WiFi trong việc phát hiện dấu hiệu sinh tồn phục vụ cứu hộ cứu nạn)*
*   **Sinh viên thực hiện:** [Tên của bạn]
*   **Giảng viên hướng dẫn:** [Tên GVHD]
*   **Ngày bảo vệ:** [Ngày tháng]

🎤 **Speaker Notes (Lời thoại gợi ý):**
> Kính chào hội đồng bảo vệ và các quý vị đại biểu. Hôm nay em xin phép được trình bày đề tài đồ án tốt nghiệp với tiêu đề "Ứng dụng công nghệ cảm biến WiFi trong việc phát hiện dấu hiệu sinh tồn phục vụ công tác cứu hộ". Đây là một hướng nghiên cứu kết hợp giữa mạng viễn thông không dây và xử lý tín hiệu số để giải quyết một bài toán mang ý nghĩa nhân đạo sâu sắc.

---

## SLIDE 2: ĐẶT VẤN ĐỀ & TÍNH CẤP THIẾT
**Nội dung hiển thị trên slide:**
*   **Thách thức trong Cứu hộ (SAR):**
    *   Tầm nhìn bị hạn chế (môi trường đục: bê tông, gạch vỡ).
    *   Yêu cầu phát hiện sự sống nhanh chóng ("Khung giờ vàng").
*   **Hạn chế của phương pháp truyền thống:**
    *   Y tế (ECG, đai hô hấp): Yêu cầu tiếp xúc vật lý trực tiếp $\rightarrow$ Bất khả thi.
    *   Radar / UWB chuyên dụng: Chi phí đắt đỏ, cồng kềnh, tiêu thụ năng lượng lớn.
*   **Giải pháp:** Công nghệ WiFi Sensing không tiếp xúc (Contactless Sensing).
    *   Khả năng đâm xuyên vật cản (Non-Line-Of-Sight - NLOS).
    *   Sử dụng sóng WiFi phân bố rộng khắp (Ubiquitous).

*(Hình ảnh gợi ý: Cảnh cứu hộ trong đống đổ nát, so sánh giữa thiết bị ECG tiếp xúc và Radar)*

🎤 **Speaker Notes:**
> Trong các thảm họa sập đổ, rào cản lớn nhất của đội cứu hộ là không thể quan sát qua các bức tường hay đống đổ nát. Việc dùng thiết bị y tế tiếp xúc trực tiếp là bất khả thi, còn radar chuyên dụng thì lại quá đắt tiền để trang bị đại trà. Do đó, nhóm em đã tiếp cận một giải pháp thay thế đột phá: sử dụng chính sóng WiFi để xuyên tường và quét các dấu hiệu của sự sống.

---

## SLIDE 3: MỤC TIÊU ĐỀ TÀI
**Nội dung hiển thị trên slide:**
*   **Mục tiêu cốt lõi:**
    *   Thiết kế hệ thống phát hiện nhịp thở không tiếp xúc qua tường/vật cản.
    *   Tối ưu hóa hệ thống phần cứng siêu rẻ (Ultra-low cost) cho cứu hộ.
    *   Triển khai quy trình xử lý tín hiệu số (DSP) mạnh mẽ để lọc nhiễu môi trường.
    *   Ứng dụng Học máy (Machine Learning) để tự động hóa việc phân loại trạng thái có/không có người.

🎤 **Speaker Notes:**
> Đề tài đặt ra 4 mục tiêu chính: Xây dựng được hệ thống phát hiện nhịp thở không tiếp xúc; sử dụng phần cứng cực kỳ rẻ để có thể nhân rộng; xây dựng bộ lọc nhiễu phức tạp; và cuối cùng là áp dụng AI để máy tính tự động đưa ra cảnh báo có người sống hay không.

---

## SLIDE 4: CƠ SỞ LÝ THUYẾT VỀ WiFi CSI
**Nội dung hiển thị trên slide:**
*   **CSI (Channel State Information) là gì?**
    *   Cung cấp thông tin kênh truyền ở độ phân giải hạt mịn (Fine-grained).
    *   Mô tả Biên độ (Amplitude) và Pha (Phase) trên từng Sóng mang con (Subcarrier) của hệ thống OFDM.
    *   Công thức: $H(f) = |H(f)| e^{j\angle H(f)}$
*   **Nguyên lý hoạt động:**
    *   Lồng ngực co giãn khi hít thở ($\sim$ 5-12mm).
    *   Gây ra sự biến đổi siêu nhỏ về chiều dài đường truyền sóng phản xạ (Dynamic path).
    *   Tạo ra sự dịch chuyển pha tuần hoàn trong tín hiệu thu được $\rightarrow$ Phác họa lại nhịp thở.

*(Hình ảnh gợi ý: Biểu đồ mô tả sóng WiFi truyền từ Tx đập vào lồng ngực người phản xạ về Rx, so sánh RSSI thô và CSI chi tiết)*

🎤 **Speaker Notes:**
> Thay vì dùng RSSI vốn dĩ rất thô và nhiễu, hệ thống dùng CSI. CSI chia sóng WiFi thành nhiều sóng mang nhỏ. Khi lồng ngực người phập phồng khoảng 5-12mm, sóng WiFi phản xạ lại sẽ bị lệch pha đôi chút. Thu thập các độ lệch pha này theo thời gian, chúng ta sẽ vẽ lại được nguyên xi dạng sóng của nhịp thở con người.

---

## SLIDE 5: THIẾT KẾ PHẦN CỨNG & THU THẬP DỮ LIỆU
**Nội dung hiển thị trên slide:**
*   **Phần cứng:** Vi điều khiển **ESP32**
    *   Siêu nhỏ, giá rẻ (phù hợp chèn vào khe đổ nát).
    *   Hỗ trợ trích xuất CSI nguyên bản từ lớp MAC.
    *   Tiêu thụ điện cực thấp.
*   **Ăng-ten:** **Panel Antenna** (Ăng-ten định hướng)
    *   Tập trung năng lượng, tăng khả năng đâm xuyên vật cản.
    *   Giảm thiểu nhiễu Đa đường (Multipath) từ các vật thể xung quanh.
*   **Cấu hình Thực nghiệm:**
    *   Băng tần: **2.4 GHz** (Băng thông 20 MHz, 64 subcarriers).
    *   Tốc độ lấy mẫu: **100 Hz** (Gói tin HE SU).
    *   Môi trường: Phòng mô phỏng $8m \times 4m$.

*(Hình ảnh gợi ý: Hình ESP32 cắm Panel Antenna, sơ đồ mặt bằng phòng lab)*

🎤 **Speaker Notes:**
> Điểm đặc biệt của đồ án là việc sử dụng vi mạch ESP32 giá chỉ vài chục ngàn thay vì máy tính đắt tiền. Mặc dù yếu, nhưng khi em trang bị cho nó ăng-ten định hướng Panel Antenna, năng lượng sóng được dồn thẳng về phía mục tiêu, triệt tiêu được rất nhiều nhiễu dội lại từ các bức tường xung quanh. Dữ liệu được lấy liên tục ở mức 100 gói tin trên giây ở băng tần 2.4GHz để đảm bảo khả năng xuyên tường tốt nhất.

---

## SLIDE 6: KIẾN TRÚC XỬ LÝ TÍN HIỆU SỐ (PIPELINE)
**Nội dung hiển thị trên slide:**
*   **Sơ đồ luồng dữ liệu (Data Pipeline):**
    1.  *Raw I/Q Data* $\rightarrow$ Tính Biên độ & Pha.
    2.  *Phase Unwrap & SFO/CFO Sanitization* $\rightarrow$ Khử lỗi phần cứng.
    3.  *Hampel Filter* $\rightarrow$ Lọc nhiễu gai (Outliers).
    4.  *Savitzky-Golay Filter* $\rightarrow$ Làm mịn, bảo toàn đỉnh sóng.
    5.  *Elliptic Bandpass Filter* $\rightarrow$ Lọc tần số hô hấp.
    6.  *PCA (Phân tích thành phần chính)* $\rightarrow$ Trích xuất tín hiệu.

*(Hình ảnh gợi ý: Vẽ một Block Diagram nằm ngang mũi tên nối tiếp các khối xử lý này)*

🎤 **Speaker Notes:**
> Nhược điểm của thiết bị giá rẻ là dữ liệu nguyên thủy chứa cực kỳ nhiều nhiễu rác. Vì vậy, linh hồn của đồ án nằm ở 파peline tiền xử lý tín hiệu gồm 6 bước khắt khe này. Tín hiệu thô sẽ được bóc tách phần thực phần ảo, giải cuộn pha, lọc các gai nhiễu điện từ, làm mịn và cuối cùng nén lại để ra được tần số hô hấp cốt lõi.

---

## SLIDE 7: XỬ LÝ LỖI PHẦN CỨNG & LỌC NHIỄU
**Nội dung hiển thị trên slide:**
*   **Phase Sanitization (Khử lỗi đồng bộ):**
    *   Lỗi lệch xung nhịp SFO/CFO làm pha bị xoay tuyến tính.
    *   Giải pháp: Áp dụng Hồi quy tuyến tính (Linear Regression) để tìm và triệt tiêu đường thẳng nhiễu.
*   **Lọc ngoại lai (Hampel Filter):**
    *   Sử dụng Trung vị (Median) và Độ lệch MAD.
    *   Loại bỏ nhiễu Impulsive mạnh hơn thuật toán trung bình cộng.
*   **Bộ lọc Elliptic Bandpass:**
    *   Dải thông: **0.15 Hz - 0.5 Hz** (tương ứng nhịp thở).
    *   Ưu điểm: Độ dốc cắt (roll-off) cực cao, chặn đứng nhiễu cơ thể và tĩnh học.

*(Hình ảnh gợi ý: Biểu đồ so sánh sóng trước và sau khi đi qua bộ lọc Hampel / Elliptic lấy từ code)*

🎤 **Speaker Notes:**
> Để đi sâu hơn, em xin giới thiệu 3 chốt chặn quan trọng. Đầu tiên là thuật toán Hồi quy tuyến tính để sửa lỗi phần cứng giữa bộ thu và phát. Thứ hai là bộ lọc Hampel loại bỏ các gai tín hiệu do rớt mạng bằng phương pháp thống kê trung vị. Thứ ba là bộ lọc Elliptic cắt gọt sắc lẹm chỉ giữ lại đúng dải tần số từ 0.15 đến 0.5 Hz – chính là tần số hít thở tự nhiên của con người.

---

## SLIDE 8: TRÍCH XUẤT ĐẶC TRƯNG VỚI PCA VÀ STFT
**Nội dung hiển thị trên slide:**
*   **Phân tích Thành phần Chính (PCA):**
    *   Chuyển đổi 64 sóng mang con thành các thành phần trực giao.
    *   Chọn PC1/PC2: Bắt giữ phương sai lớn nhất $\rightarrow$ tín hiệu thở thuần khiết nhất.
*   **Biến đổi Fourier và Entropy Phổ (Spectral Entropy - SE):**
    *   Chuyển tín hiệu từ miền thời gian sang tần số (Spectrogram).
    *   $SE$: Đại lượng đo sự phân tán năng lượng.
        *   $SE$ cao: Nhiễu môi trường, không có nhịp thở (White noise).
        *   $SE$ thấp: Năng lượng tập trung tại 1 đỉnh $\rightarrow$ Có người đang hô hấp.

*(Hình ảnh gợi ý: Đồ thị Spectrogram minh họa dải năng lượng hô hấp rõ nét trên nền tối)*

🎤 **Speaker Notes:**
> Do hiện tượng deep fade, không phải 64 sóng mang đều bắt được nhịp thở. Áp dụng toán học PCA, chúng ta ép 64 chiều dữ liệu này lại thành 1 dòng tín hiệu duy nhất mang phương sai lớn nhất. Sau đó, tín hiệu được chuyển sang miền tần số. Bằng cách đo chỉ số Entropy Phổ, nếu năng lượng hội tụ thành một vệt sáng duy nhất, thuật toán nhận biết ngay đó là nhịp thở ổn định của nạn nhân.

---

## SLIDE 9: PHÂN LOẠI TRẠNG THÁI BẰNG MACHINE LEARNING
**Nội dung hiển thị trên slide:**
*   **Thuật toán: Random Forest Classifier**
    *   Tập hợp (Ensemble) nhiều Cây quyết định (Decision Trees).
    *   Chống Overfitting bằng cơ chế Bagging và chọn đặc trưng ngẫu nhiên.
*   **Bộ đặc trưng đầu vào (Features Input):**
    *   Trung bình biên độ (Mean).
    *   Độ lệch chuẩn (Std Dev).
    *   Hệ số biến thiên (Coefficient of Variation).
    *   Entropy Phổ (Spectral Entropy).
*   **Tập dữ liệu:** Huấn luyện và kiểm thử chéo, chốt kiểm tra trên tập Holdout 200 mẫu.

*(Hình ảnh gợi ý: Biểu tượng Rừng ngẫu nhiên (các cây quyết định) bầu chọn ra kết quả)*

🎤 **Speaker Notes:**
> Các đặc trưng tín hiệu sau đó được nạp vào mạng Trí tuệ Nhân tạo. Nhóm sử dụng Rừng ngẫu nhiên (Random Forest). Lý do là vì nó xử lý dữ liệu phi tuyến tính rất tốt và chống lại hiện tượng học vẹt (overfitting) hoàn hảo so với mạng nơ-ron truyền thống, đặc biệt phù hợp với dữ liệu phòng kính.

---

## SLIDE 10: KẾT QUẢ ĐÁNH GIÁ (EVALUATION RESULTS)
**Nội dung hiển thị trên slide:**
*   **Độ chính xác (Accuracy) đạt: 94.0%** trên 200 mẫu nghiệm thu.
*   **Ưu điểm hệ thống:**
    *   Phân loại xuất sắc trạng thái Tĩnh (Không người) và Hô hấp (Có người).
    *   Tỷ lệ báo động giả (False Positive) và bỏ lọt (False Negative) cực thấp (< 6%).
    *   Thời gian suy luận (Inference latency) cỡ mili-giây $\rightarrow$ Đáp ứng cảnh báo Real-time.

*(Hình ảnh gợi ý: Chèn Confusion Matrix (Ma trận nhầm lẫn) chứng minh các chỉ số TP, FP, TN, FN)*

🎤 **Speaker Notes:**
> Sau quá trình kiểm tra nghiêm ngặt với 200 mẫu mới hoàn toàn, hệ thống đạt độ chính xác lên tới 94%. Tỷ lệ cảnh báo sai rất thấp, và độ trễ đưa ra dự đoán chỉ tính bằng mili-giây. Điều này chứng minh rằng việc kết hợp ESP32 giá rẻ và bộ giải thuật xử lý tín hiệu tinh vi của nhóm là một hướng đi hoàn toàn thành công và khả thi.

---

## SLIDE 11: KẾT LUẬN & HƯỚNG MỞ RỘNG
**Nội dung hiển thị trên slide:**
*   **Kết luận:**
    *   Hoàn thiện hệ thống SAR không tiếp xúc giá rẻ, chính xác, tính tự động cao.
    *   Minh chứng sức mạnh của sự kết hợp: COTS Hardware (ESP32) + Advanced DSP + Machine Learning.
*   **Hướng phát triển tương lai:**
    *   **Phần cứng:** Nâng cấp MIMO (WiFi 6 / 5GHz) để xác định định hướng 3D (AoA) của nạn nhân.
    *   **Phần mềm:** Ứng dụng Deep Learning (CNN/LSTM) lên trực tiếp Spectrogram tensor để bóc tách cả nhịp tim.
    *   **Môi trường:** Đưa vào thực nghiệm trong điều kiện sập đổ thật (xuyên tường đa lớp bê tông).

🎤 **Speaker Notes:**
> Tóm lại, đồ án đã giải quyết được bài toán khó: phát hiện sự sống bằng thiết bị rẻ tiền qua tường. Trong tương lai, hệ thống có thể được nâng cấp lên các module WiFi 6 hỗ trợ MIMO để không chỉ phát hiện sự sống mà còn định vị chính xác tọa độ 3D của nạn nhân, và trích xuất thêm nhịp tim thông qua các mạng Deep Learning.

---

## SLIDE 12: Q&A (HỎI ĐÁP)
**Nội dung hiển thị trên slide:**
*   **Cảm ơn Hội đồng và các Thầy/Cô đã lắng nghe!**
*   *Mời Hội đồng đặt câu hỏi.*

🎤 **Speaker Notes:**
> Bài trình bày của em đến đây là kết thúc. Em xin chân thành cảm ơn sự lắng nghe của quý thầy cô trong hội đồng. Em rất mong nhận được những góp ý, phản biện để đề tài được hoàn thiện hơn ạ. Em xin mời hội đồng đặt câu hỏi.