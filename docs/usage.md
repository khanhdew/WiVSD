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
Sử dụng script training đã cung cấp:

```bash
PYTHONPATH=src python scripts/train_ml_classifier.py --root . --limit 200 --model models/rf_person_detector.joblib --out reports/model_train_eval.json
```

- Kết quả: mô hình lưu tại `models/rf_person_detector.joblib`, báo cáo tại `reports/model_train_eval.json`.
- Kiến trúc hiện tại: `Pipeline(StandardScaler(), RandomForestClassifier(n_estimators=200))`, input là vector 3 chiều: `[amp_mean, amp_std, amp_cv]`.

## Đánh giá / Tuning
- Chạy evaluator toàn bộ dataset (module):

```bash
PYTHONPATH=src python -m csi_preprocessing.evaluate --root . --out reports/eval_summary.json
```

- Chạy quick-eval trên CSVs:

```bash
PYTHONPATH=src python scripts/eval_fast.py --root . --limit 20 --out reports/eval_fast_summary.json
```

- Tuning thresholds (dùng kết quả `eval_fast_summary.json`):

```bash
python3 scripts/tune_threshold.py --in reports/eval_fast_summary.json --out reports/threshold_tuning.json
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
