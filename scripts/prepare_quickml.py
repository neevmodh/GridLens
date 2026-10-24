"""Export target-free engineered training features for an optional QuickML pipeline."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from energy.config import ROOT
from energy.features import advanced_features as engineer


def main():
    with (ROOT / 'data/train_telemetry.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    output = ROOT / 'data/quickml_training.csv'
    with output.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=[*engineer(rows[0]), 'target_demand_kw'])
        writer.writeheader()
        writer.writerows({**engineer(row), 'target_demand_kw': row['target_demand_kw']} for row in rows)
    print(f'Prepared {len(rows)} rows: {output}')
    print('For this dataset set QUICKML_FEATURE_SCHEMA=engineered on the server.')


if __name__ == '__main__':
    main()
