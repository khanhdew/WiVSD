import pytest
from pathlib import Path

from csi_preprocessing.classifier import predict_with_model_features, predict_with_model_from_csv


def test_model_file_exists():
    p = Path('models/rf_person_detector.joblib')
    assert p.exists(), f"Model file not found at {p}"


def test_model_predicts_on_sample_features():
    p = Path('models/rf_person_detector.joblib')
    features = [50.0, 10.0, 0.2]
    pred, details = predict_with_model_features(features, model_path=p)
    assert isinstance(pred, int)
    assert isinstance(details, dict)
    assert 'model_path' in details


def test_model_predicts_from_csv():
    p = Path('models/rf_person_detector.joblib')
    sample_csv = Path('router no person/csi_data_20260305_143420.csv')
    if not sample_csv.exists():
        pytest.skip("sample CSV not present")
    pred, details = predict_with_model_from_csv(sample_csv, model_path=p)
    assert isinstance(pred, int)
    assert isinstance(details, dict)
