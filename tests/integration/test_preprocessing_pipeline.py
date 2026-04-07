import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from csi_preprocessing.dataset import preprocess_csv_pipeline


def test_preprocessing_pipeline_end_to_end():
    # 2 traces with four complex points each (imag,real,...)
    data0 = [0.0, 1.0, 1.0, 0.0, 0.5, 0.5, -0.5, 0.5]
    data1 = [0.1, 0.9, 0.9, 0.1, 0.4, 0.6, -0.4, 0.6]

    df = pd.DataFrame({'data': [str(data0), str(data1)]})
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / 'sample.csv'
        df.to_csv(path, index=False)
        out_dir = Path(tmpdir) / 'out'
        result = preprocess_csv_pipeline(path, out_dir, fs=100.0)

        assert 'quality' in result
        # quality should report finite values
        q = result['quality']
        assert q['outlier_rate_amp'] >= 0.0
        assert q['outlier_rate_phase'] >= 0.0
        assert q['snr_amp'] >= -120.0
        assert q['snr_phase'] >= -120.0
        assert isinstance(q['pca_amp_selected'], int)
        assert isinstance(q['pca_phase_selected'], int)
        assert q['pca_amp_selected'] >= 0
        assert q['pca_phase_selected'] >= 0
        assert (out_dir / 'dataset.npz').exists()
        assert (out_dir / 'dataset_quality.json').exists()
