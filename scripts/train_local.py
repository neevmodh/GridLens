"""Reproduce the original baseline without replacing the selected model."""
import csv
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from energy.config import ROOT
from energy.features import engineer
from energy.local_model import predict_local
from energy.telemetry import WEATHER


def solve(matrix, vector):
    augmented = [row[:] + [target] for row, target in zip(matrix, vector)]
    size = len(vector)
    for column in range(size):
        pivot = max(range(column, size), key=lambda r: abs(augmented[r][column]))
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        if abs(divisor) < 1e-12:
            raise ValueError('Singular training matrix.')
        augmented[column] = [v / divisor for v in augmented[column]]
        for row in range(size):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    return [row[-1] for row in augmented]


def fit(rows):
    names = list(engineer(rows[0]))
    features = [list(engineer(row).values()) for row in rows]
    means = [statistics.mean(col) for col in zip(*features)]
    scales = [statistics.pstdev(col) or 1 for col in zip(*features)]
    x = [[1] + [(v - mean) / scale for v, mean, scale in zip(row, means, scales)] for row in features]
    y = [float(r['target_demand_kw']) for r in rows]
    size = len(names) + 1
    matrix = [[sum(row[i] * row[j] for row in x) + (0.1 if i == j and i > 0 else 0)
               for j in range(size)] for i in range(size)]
    vector = [sum(row[i] * target for row, target in zip(x, y)) for i in range(size)]
    return {'features': names, 'means': means, 'scales': scales,
            'weights': solve(matrix, vector),
            'medians': {key: statistics.median(float(r[key]) for r in rows) for key in WEATHER}}


def main():
    with (ROOT / 'data/train_telemetry.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    rows.sort(key=lambda row: row['timestamp'])
    split = int(len(rows) * 0.8)
    validation_model = fit(rows[:split])
    predictions = predict_local(rows[split:], validation_model)
    actual = [float(r['target_demand_kw']) for r in rows[split:]]
    rmse = math.sqrt(statistics.mean((p - y) ** 2 for p, y in zip(predictions, actual)))
    mae = statistics.mean(abs(p - y) for p, y in zip(predictions, actual))
    mean_target = statistics.mean(float(r['target_demand_kw']) for r in rows[:split])
    baseline = math.sqrt(statistics.mean((mean_target - y) ** 2 for y in actual))
    model = fit(rows)
    model['metadata'] = {'name': 'Local ridge regression', 'training_rows': len(rows),
                         'training_start': rows[0]['timestamp'], 'training_end': rows[-1]['timestamp'],
                         'validation': {'strategy': 'chronological final 20% of labeled training data',
                                        'fit_rows': split, 'validation_rows': len(actual),
                                        'rmse_kw': round(rmse, 4), 'mae_kw': round(mae, 4),
                                        'mean_baseline_rmse_kw': round(baseline, 4)},
                         'notice': 'Local preview only. Not QuickML or a hidden-test score.'}
    (ROOT / 'models/legacy-preview.json').write_text(json.dumps(model, indent=2) + '\n')
    print(json.dumps(model['metadata'], indent=2))
    print('Saved the original baseline to models/legacy-preview.json. The selected model is unchanged.')
    return rows


if __name__ == '__main__':
    main()
