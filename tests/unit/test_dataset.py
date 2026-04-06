import numpy as np
from csi_preprocessing.dataset import build_cnn_input, construct_matrix


def test_construct_matrix_empty():
    M = construct_matrix({}, 'amp')
    assert M.shape == (0, 0)


def test_build_cnn_input_empty():
    X = np.zeros((0, 0))
    cnn_input, freqs, times = build_cnn_input(X)
    assert cnn_input.size == 0
    assert freqs.size == 0
    assert times.size == 0
