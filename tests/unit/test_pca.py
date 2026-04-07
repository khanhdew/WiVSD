import numpy as np
from csi_preprocessing.pca import pca_reduce, pca_component_ranking, select_pca_components


def test_pca_reduce_identity():
    X = np.eye(5)
    transformed, pca = pca_reduce(X, n_components=3)
    assert transformed.shape == (5, 3)
    assert pca.explained_variance_ratio_.shape == (3,)


def test_pca_component_ranking_and_selection():
    X = np.vstack([np.arange(10), np.arange(10) * 2, np.arange(10) * 3]).T
    transformed, pca = pca_reduce(X, n_components=3)
    ranking = pca_component_ranking(pca)
    assert len(ranking) == 3
    selected = select_pca_components(pca, min_cumulative_variance=0.7, max_components=3)
    assert 1 <= len(selected) <= 3
