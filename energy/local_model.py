import json
from struct import pack, unpack
from functools import lru_cache

from .config import ROOT
from .features import engineer, advanced_features


@lru_cache(maxsize=1)
def load_model():
    path = ROOT / 'models' / 'local-preview.json'
    if not path.exists():
        raise RuntimeError('Local model is missing. Restore models/local-preview.json or run scripts/benchmark.py with the training dependencies.')
    return json.loads(path.read_text())


def predict_local(rows, model=None):
    model = model or load_model()
    predictions = []
    for row in rows:
        features = advanced_features(row) if model.get('feature_version') == 2 else engineer(row)
        value = model['weights'][0]
        for i, key in enumerate(model['features']):
            value += model['weights'][i + 1] * (features[key] - model['means'][i]) / model['scales'][i]
        vector = [features[key] for key in model['features']]
        for tree in model.get('trees', []):
            node = 0
            while tree['left'][node] != -1:
                # sklearn evaluates tree features as float32. Matching that
                # conversion keeps the portable JSON evaluator deterministic.
                feature = unpack('f', pack('f', vector[tree['feature'][node]]))[0]
                node = tree['left'][node] if feature <= tree['threshold'][node] else tree['right'][node]
            value += model['learning_rate'] * tree['value'][node]
        predictions.append(round(max(0, value), 4))
    return predictions
