import numpy as np
from sklearn.decomposition import PCA


def pca_reduce(matrix: np.ndarray, n_components: int = 5):
    if matrix.size == 0:
        return np.zeros((0, 0)), None

    n_components = min(n_components, min(matrix.shape))
    pca = PCA(n_components=n_components)
    transformed = pca.fit_transform(matrix)
    return transformed, pca


def select_pca_components(pca: PCA, min_cumulative_variance: float = 0.8, max_components: int = 5):
    if pca is None:
        return []
    ratios = np.asarray(pca.explained_variance_ratio_)
    if ratios.size == 0:
        return []

    cumulative = np.cumsum(ratios)
    selected = np.searchsorted(cumulative, min_cumulative_variance, side='right') + 1
    selected = min(selected, max_components, ratios.size)
    if selected <= 0:
        selected = min(max_components, ratios.size)
    return list(range(selected))


def pca_component_ranking(pca: PCA):
    if pca is None:
        return []
    return list(enumerate(pca.explained_variance_ratio_))
