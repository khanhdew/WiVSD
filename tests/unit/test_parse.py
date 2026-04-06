import numpy as np
from csi_preprocessing.parse import compute_amplitude_phase, parse_csi_row


def test_parse_csi_row_json():
    data = '[1, 2, 3, 4]'
    arr = parse_csi_row(data)
    assert np.allclose(arr, np.array([1, 2, 3, 4]))


def test_compute_amplitude_phase_simple():
    csi = np.array([1.0, 0.0, 0.0, 1.0])
    amp, ph = compute_amplitude_phase(csi)
    assert amp.shape == (2,)
    assert np.allclose(amp, np.array([1.0, 1.0]))
    assert np.allclose(ph, np.array([np.pi/2, 0.0]))
