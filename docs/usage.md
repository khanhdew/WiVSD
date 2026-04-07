# Hướng dẫn sử dụng — CSI preprocessing & person-detection

## Tổng quan
Bộ mã này tiền xử lý dữ liệu CSI (CSV) thành dataset nén (`dataset.npz`) và metadata (`dataset_quality.json`), đồng thời cung cấp hai cách để phát hiện "có người"/"không có người": một heuristic nhanh và một mô hình ML (RandomForest) đã huấn luyện.

## Yêu cầu
- Python >= 3.12
- Thư viện: `numpy`, `pandas`, `scipy`, `scikit-learn`, `joblib`, `hampel` (có thể cài qua `pip`).
- Cài đặt (ví dụ):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # nếu có
# hoặc cài tay
pip install numpy pandas scipy scikit-learn joblib hampel
```

## CLI — Preprocess và (tùy chọn) predict bằng model
- Tiền xử lý 1 file CSV và lưu dataset:

```bash
PYTHONPATH=src python -m csi_preprocessing.cli --input path/to/file.csv --output outdir
```

- Tiền xử lý + dùng model đã huấn luyện để dự đoán:

```bash
PYTHONPATH=src python -m csi_preprocessing.cli --input path/to/file.csv --output outdir --model models/rf_person_detector.joblib
```

Kết quả trong `outdir/`:
- `dataset.npz` — dữ liệu CNN input (nếu có)
- `dataset_quality.json` — báo cáo chất lượng (SNR, entropy, outlier_rate, v.v.)
- `model_prediction.json` — (nếu `--model` được cung cấp) kết quả dự đoán và chi tiết

## Python API (ví dụ nhanh)
- Tiền xử lý chương trình (trả lại dict với `output` và `quality`):

```python
from pathlib import Path
from csi_preprocessing.dataset import preprocess_csv_pipeline
res = preprocess_csv_pipeline(Path('router no person/csi_data_20260305_143420.csv'), Path('outdir'))
print(res['quality'])
```

- Dự đoán bằng model từ CSV (feature extraction + pipeline):

```python
from csi_preprocessing.classifier import predict_with_model_from_csv
pred, details = predict_with_model_from_csv(Path('router no person/csi_data_20260305_143420.csv'), model_path='models/rf_person_detector.joblib')
print(pred, details)
```

- Dự đoán từ feature vector (amp_mean, amp_std, amp_cv):

```python
from csi_preprocessing.classifier import predict_with_model_features
features = [50.0, 10.0, 0.2]
pred, details = predict_with_model_features(features, model_path='models/rf_person_detector.joblib')
```

- Heuristic nhanh (chỉ tính từ CSV):

```python
from csi_preprocessing.classifier import predict_from_csv_fast
pred, details = predict_from_csv_fast('router no person/csi_data_20260305_143420.csv')
```

## Huấn luyện model (nếu muốn tự train lại)
Sử dụng script training đã cung cấp. Ví dụ mặc định (giả sử có thư mục `Router` và `router no person`):

```bash
PYTHONPATH=src python scripts/train_ml_classifier.py --root . --limit 200 --model models/rf_person_detector.joblib --out reports/model_train_eval.json
```

- Kết quả: mô hình lưu tại `models/rf_person_detector.joblib`, báo cáo tại `reports/model_train_eval.json`.
- Kiến trúc hiện tại: `Pipeline(StandardScaler(), RandomForestClassifier(n_estimators=200))`, input là vector 3 chiều: `[amp_mean, amp_std, amp_cv]`.

Tùy chọn mới (hữu ích để tránh data leakage / chỉ định holdout):

- `--pos-train DIR [DIR ...]` : danh sách thư mục chứa mẫu dương (positive) để train (relative đến `--root` hoặc absolute).
- `--neg-train DIR [DIR ...]` : danh sách thư mục chứa mẫu âm (negative) để train.
- `--pos-test DIR [DIR ...]`  : (tuỳ chọn) danh sách thư mục chứa mẫu dương cho test (nếu cung cấp, script sẽ không chia random).
- `--neg-test DIR [DIR ...]`  : (tuỳ chọn) danh sách thư mục chứa mẫu âm cho test.

Ví dụ sử dụng explicit train/test (sử dụng thư mục `holdout` làm tập test):

```bash
PYTHONPATH=src python scripts/train_ml_classifier.py \
	--root . \
	--model models/rf_person_detector.joblib \
	--out reports/model_train_retrained.json \
	--pos-train Router \
	--neg-train "router no person" \
	--pos-test holdout/Router \
	--neg-test "holdout/router no person"
```

Ghi chú: nếu không truyền `--pos-test`/`--neg-test`, script sẽ dùng `train_test_split(..., test_size=0.2, stratify=y)` để tách dữ liệu.

## Đánh giá / Tuning

- Chạy evaluator (duyệt dataset để sinh báo cáo):

```bash
PYTHONPATH=src python -m csi_preprocessing.evaluate --root . --out reports/eval_summary.json
```

Các tuỳ chọn hữu dụng:

- `--model`, `--model-path`, `--model_path MODEL`: đường dẫn tới joblib model được ưu tiên dùng để dự đoán. Nếu không truyền, evaluator sẽ cố tự động tìm `models/rf_person_detector.joblib` trong repo.
- `--dirs`, `-d DIR [DIR ...]`: danh sách thư mục rõ ràng để đánh giá (bỏ qua tìm kiếm toàn cục). Khi dùng `--dirs`, chỉ tìm các CSV xuất (khớp `csi_data_*.csv` hoặc `csi_output.csv`) để tránh lấy file ví dụ/rác.
- `--jobs`, `-j N`: số process worker (mặc định: auto).
- `--no-realtime`: tắt logging tiến độ realtime.
 - `--threshold T`: ngưỡng quyết định cho xác suất của mô hình để gán nhãn "có người" (mặc định `0.25`). Dùng khi bạn muốn áp một cutoff cố định cho `predict_proba(model)[:,1]`.

Ví dụ:

```bash
# dùng model đã huấn luyện và 4 worker
PYTHONPATH=src python -m csi_preprocessing.evaluate --root . --out reports/eval_summary.json --model models/rf_person_detector.joblib --jobs 4

# đánh giá chỉ trên thư mục holdout (với ngưỡng 0.25)
PYTHONPATH=src python -m csi_preprocessing.evaluate --root . --out reports/eval_holdout.json --model_path models/rf_person_detector_retrained.joblib --dirs holdout/Router "holdout/router no person" --jobs 4 --threshold 0.25
```

- Chạy quick-eval (nhanh) trên CSVs:

```bash
PYTHONPATH=src python scripts/eval_fast.py --root . --limit 20 --out reports/eval_fast_summary.json
```

- Tuning thresholds (tìm ngưỡng tốt nhất trên tập holdout):

```bash
# Dùng threshold_sweep để quét ngưỡng (precision/recall/F1) trên holdout
python3 scripts/threshold_sweep.py --model models/rf_person_detector_retrained.joblib --pos-dir holdout/Router --neg-dir "holdout/router no person" --out reports/threshold_sweep_holdout.json --plot reports/threshold_sweep_holdout.png
```

## Kiểm thử
- Chạy test suite (pytest):

```bash
PYTHONPATH=src pytest -q
```

## Lưu ý và khắc phục lỗi thường gặp
- Nếu `models/rf_person_detector.joblib` không tồn tại: chạy `scripts/train_ml_classifier.py` để tạo.
- Nếu CSV có cấu trúc khác (cột `data` không tồn tại): `predict_from_csv_fast` sẽ cố đọc cột đầu tiên; đảm bảo CSV có cột `data` hoặc định dạng nguyên bản từ bộ ghi.

## Bước tiếp theo
- Thêm unit test cho flag `--model` (chưa có).
- Mở rộng feature để cải thiện độ chính xác mô hình.

---
Tệp tài liệu này nằm tại [docs/usage.md](docs/usage.md).
