import numpy as np
from csi_preprocessing.filters import apply_savgol, sanitize_phase_robust, unwrap_phase_list


def test_unwrap_phase_list():
    phases = [np.array([0, np.pi, -np.pi/2]), np.array([])]
    unwrapped = unwrap_phase_list(phases)
    assert len(unwrapped) == 2
    assert np.allclose(unwrapped[0][0], 0)


def test_sanitize_phase_robust_identity():
    phase = np.linspace(0, 1, 10)
    out = sanitize_phase_robust(phase)
    assert out.shape == phase.shape


def test_apply_savgol_no_change():
    data = np.array([1.0, 2.0, 3.0])
    out = apply_savgol(data, window_length=3, polyorder=1)
    assert out.shape == data.shape
