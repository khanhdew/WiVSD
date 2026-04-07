"""Simple heuristic classifier for CSI dataset outputs.

Provides:
- predict_from_quality(quality) -> int
- predict_from_npz(npz_path) -> (prediction:int, details:dict)

Heuristics are intentionally simple and explainable for quick evaluation.
"""
from pathlib import Path
import json
from typing import Tuple, Dict, Any

import numpy as np
from csi_preprocessing.parse import parse_csi_row


def predict_from_quality(quality: Dict[str, Any]) -> int:
    """Return 1 if heuristic predicts presence of person, else 0.

    Heuristic rules (ordered):
    - High SNR strongly indicates person (snr_amp >= -5 dB)
    - Moderate SNR + low entropy + low outlier rate indicates person
    - Otherwise predict no person
    """
    snr = float(quality.get('snr_amp', 0.0))
    entropy = float(quality.get('entropy_amp', 1.0))
    outlier = float(quality.get('outlier_rate_amp', 1.0))

    if snr >= -5.0:
        return 1
    if snr >= -20.0 and entropy < 0.6 and outlier < 0.25:
        return 1
    return 0


def predict_from_npz(npz_path: Path) -> Tuple[int, Dict[str, Any]]:
    """Predict label from a `dataset.npz` file (or quality JSON beside it).

    Returns (prediction, details) where details contains any features used.
    """
    npz_path = Path(npz_path)
    parent = npz_path.parent
    quality_path = parent / 'dataset_quality.json'

    # Prefer quality JSON if present
    if quality_path.exists():
        try:
            q = json.loads(quality_path.read_text(encoding='utf-8'))
            pred = predict_from_quality(q)
            return int(pred), {'source': 'quality', 'quality': q}
        except Exception as e:
            # fall back to NPZ-based heuristics
            pass

    # Fallback: use NPZ contents
    try:
        data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        return 0, {'error': 'cannot_load_npz', 'exc': str(e)}

    # If frequency axis exists, check respiration band energy
    if 'cnn_input' in data:
        cnn = data['cnn_input']
        freq = data['freq'] if 'freq' in data else np.array([])
        details: Dict[str, Any] = {'source': 'npz'}

        if freq.size and cnn.size:
            try:
                mask = (freq >= 0.1) & (freq <= 0.6)
                if mask.any():
                    # cnn assumed to be dB values (10*log10)
                    if cnn.ndim == 3:
                        spec = cnn[:, mask, :]
                        power_lin = float(np.mean(10 ** (spec / 10.0)))
                    elif cnn.ndim == 2:
                        spec = cnn[mask, :]
                        power_lin = float(np.mean(10 ** (spec / 10.0)))
                    else:
                        power_lin = float(np.mean(10 ** (cnn / 10.0)))
                    details['power_lin'] = power_lin
                    # threshold chosen empirically for small-sample heuristic
                    return (1 if power_lin > 1e-9 else 0), details
            except Exception:
                pass

        # fallback to average dB threshold
        try:
            avg_db = float(np.mean(cnn))
            details['avg_db'] = avg_db
            return (1 if avg_db > -80.0 else 0), details
        except Exception:
            return 0, {'error': 'no_usable_features'}

    return 0, {'error': 'no_cnn_input'}


def predict_from_csv_fast(csv_path: Path, n_packets_max: int = 200) -> Tuple[int, Dict[str, Any]]:
    """Lightweight CSV-based heuristic predictor.

    Parses up to `n_packets_max` packets, computes per-packet mean amplitude,
    and uses coefficient-of-variation as a proxy for activity.
    Returns (prediction, details).
    """
    try:
        import pandas as pd
    except Exception:
        return 0, {'error': 'pandas_missing'}

    csv_path = Path(csv_path)
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return 0, {'error': 'cannot_load_csv', 'exc': str(e)}

    # locate data column
    if 'data' in df.columns:
        col = df['data']
    else:
        col = df.iloc[:, 0]

    amp_means = []
    for i, v in enumerate(col):
        if i >= n_packets_max:
            break
        try:
            arr = parse_csi_row(v)
        except Exception:
            continue
        if arr.size < 2:
            continue
        imag = arr[0::2]
        real = arr[1::2]
        l = min(len(real), len(imag))
        if l == 0:
            continue
        amp = np.hypot(real[:l], imag[:l])
        amp_means.append(float(np.mean(amp)))

    if not amp_means:
        return 0, {'error': 'no_valid_packets'}

    amps = np.asarray(amp_means)
    amp_mean = float(np.mean(amps))
    amp_std = float(np.std(amps))
    amp_cv = amp_std / amp_mean if amp_mean != 0 else 0.0

    # Simple heuristic thresholds (tunable):
    # - coefficient-of-variation > 0.02 suggests motion/presence
    # - or absolute std > 0.05
    pred = 1 if (amp_cv > 0.02 or amp_std > 0.05) else 0
    details = {'amp_mean': amp_mean, 'amp_std': amp_std, 'amp_cv': amp_cv, 'n_packets': len(amp_means)}
    return int(pred), details


# Model-based prediction helpers
_LOADED_MODEL = None
_LOADED_MODEL_PATH = None

def _load_trained_model(model_path: Path | str = 'models/rf_person_detector.joblib'):
    """Load and cache a trained joblib model pipeline."""
    global _LOADED_MODEL, _LOADED_MODEL_PATH
    try:
        from joblib import load as _joblib_load
    except Exception:
        _joblib_load = None

    if _joblib_load is None:
        raise ImportError('joblib is required to load trained models')

    model_path = Path(model_path)
    if _LOADED_MODEL is not None and _LOADED_MODEL_PATH == str(model_path):
        return _LOADED_MODEL

    if not model_path.exists():
        raise FileNotFoundError(f'model not found: {model_path}')

    _LOADED_MODEL = _joblib_load(model_path)
    _LOADED_MODEL_PATH = str(model_path)
    return _LOADED_MODEL


def predict_with_model_features(features: Any, model_path: Path | str = 'models/rf_person_detector.joblib'):
    """Predict using a trained pipeline from a raw feature vector.

    `features` should be an iterable of shape (n_features,) or (1, n_features).
    Returns (prediction:int, details:dict).
    """
    import numpy as _np

    try:
        model = _load_trained_model(model_path)
    except Exception as e:
        return 0, {'error': 'model_load_failed', 'exc': str(e)}

    arr = _np.asarray(features)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    try:
        pred = model.predict(arr)
        details = {'model_path': str(model_path), 'features': arr.tolist()}
        # include probability when available
        if hasattr(model, 'predict_proba'):
            try:
                proba = model.predict_proba(arr).tolist()
                details['proba'] = proba
            except Exception:
                pass
        return int(pred[0]), details
    except Exception as e:
        return 0, {'error': 'model_predict_failed', 'exc': str(e)}


def predict_with_model_from_csv(csv_path: Path, model_path: Path | str = 'models/rf_person_detector.joblib', n_packets_max: int = 200):
    """Compute CSV features and predict with trained model.

    Returns (prediction:int, details:dict) or error details.
    """
    pred_h, details = predict_from_csv_fast(csv_path, n_packets_max=n_packets_max)
    if isinstance(details, dict) and details.get('error'):
        return 0, {'error': 'feature_extract_failed', 'details': details}

    amp_mean = details.get('amp_mean')
    amp_std = details.get('amp_std')
    amp_cv = details.get('amp_cv')
    if amp_mean is None or amp_std is None or amp_cv is None:
        return 0, {'error': 'missing_features', 'details': details}

    features = [float(amp_mean), float(amp_std), float(amp_cv)]
    return predict_with_model_features(features, model_path=model_path)
