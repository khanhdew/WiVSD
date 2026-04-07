import argparse
from pathlib import Path
import json

import numpy as np
import pandas as pd

from .dataset import preprocess_csv_pipeline
from .classifier import predict_with_model_from_csv


def main():
    parser = argparse.ArgumentParser(description='CSI preprocessing pipeline')
    parser.add_argument('--input', required=True, type=Path, help='Path to CSI CSV file')
    parser.add_argument('--output', required=True, type=Path, help='Output directory')
    parser.add_argument('--model', type=Path, default=None, help='Path to trained joblib model to use for prediction')
    args = parser.parse_args()
    # Run full preprocessing pipeline which saves dataset and quality JSON
    result = preprocess_csv_pipeline(args.input, args.output)

    # If a model path is provided, run model prediction and save prediction JSON
    if args.model:
        try:
            pred, details = predict_with_model_from_csv(args.input, model_path=args.model)
            out_dir = Path(result.get('output', args.output))
            out_dir.mkdir(parents=True, exist_ok=True)
            # write separate prediction file
            (out_dir / 'model_prediction.json').write_text(json.dumps({'prediction': int(pred), 'details': details}, indent=2), encoding='utf-8')
            # also append to dataset_quality.json when possible
            try:
                qpath = out_dir / 'dataset_quality.json'
                q = json.loads(qpath.read_text(encoding='utf-8')) if qpath.exists() else {}
                q['model_prediction'] = int(pred)
                q['model_details'] = details
                qpath.write_text(json.dumps(q, indent=2, ensure_ascii=False), encoding='utf-8')
            except Exception:
                pass
            print('Model prediction:', pred)
        except Exception as e:
            print('Model prediction failed:', e)
    else:
        print('Saved dataset to', result.get('output', args.output))


if __name__ == '__main__':
    main()
