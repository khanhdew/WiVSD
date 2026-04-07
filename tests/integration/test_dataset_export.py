import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from csi_preprocessing.dataset import preprocess_csv_pipeline


def test_dataset_export_files_and_schema():
    data0 = [0.0, 1.0, 1.0, 0.0, 0.5, 0.5, -0.5, 0.5]
    data1 = [0.1, 0.9, 0.9, 0.1, 0.4, 0.6, -0.4, 0.6]

    df = pd.DataFrame({'data': [str(data0), str(data1)]})
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / 'sample.csv'
        df.to_csv(src_path, index=False)
        out_dir = Path(tmpdir) / 'out'

        result = preprocess_csv_pipeline(src_path, out_dir, fs=100.0)
        assert 'quality' in result

        npz_path = out_dir / 'dataset.npz'
        json_path = out_dir / 'dataset_quality.json'
        assert npz_path.exists()
        assert json_path.exists()

        loaded = np.load(npz_path)
        assert 'cnn_input' in loaded
        assert 'freq' in loaded
        assert 'times' in loaded

        quality = result['quality']
        assert 'entropy_amp' in quality and 'entropy_phase' in quality
        assert 0.0 <= quality['entropy_amp'] <= 1.0
        assert 0.0 <= quality['entropy_phase'] <= 1.0
