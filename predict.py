"""HackSphere inference contract and CSV CLI. QuickML is required by default."""
import argparse
import csv
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request

from energy.local_model import load_model, predict_local
from energy.quickml import QuickMLError, configured, extract_predictions, predict_quickml, _read_json
from energy.telemetry import clean_rows, parse_csv


DEFAULT_LIVE_URL = 'https://gridlens-50047133296.development.catalystappsail.in/api/predict'
PUBLISHED_QUICKML_ENDPOINT_URL = 'https://api.catalyst.zoho.in/quickml/v1/project/92358000000016001/endpoints/predict'


def predict_hosted(rows):
    endpoint = os.getenv('GRIDLENS_PREDICT_URL', DEFAULT_LIVE_URL)
    parsed = urlparse(endpoint)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise QuickMLError('Configure a valid HTTPS GRIDLENS_PREDICT_URL or direct QuickML OAuth credentials.')
    predictions = []
    # Bounded chunks fit the hosting request timeout while preserving arbitrary row order.
    for offset in range(0, len(rows), 100):
        batch = rows[offset:offset + 100]
        request = Request(endpoint, data=json.dumps({'rows':batch}, allow_nan=False).encode(),
                          headers={'Content-Type':'application/json'}, method='POST')
        response = _read_json(request, timeout=180)
        if not isinstance(response, dict) or response.get('provider') != 'quickml':
            raise QuickMLError('The hosted prediction service did not return a verified QuickML response.')
        predictions.extend(extract_predictions(response, len(batch)))
    return predictions


def predict(input_df):
    """Return one numeric prediction per input row, preserving input order.

    Accepts the evaluator's pandas DataFrame or a list of telemetry dictionaries.
    Explicit PREDICT_ALLOW_LOCAL=1 is for local testing only; never submit it on.
    """
    rows = input_df.to_dict(orient='records') if hasattr(input_df, 'to_dict') else input_df
    rows, warnings = clean_rows(rows, load_model()['medians'])
    for warning in warnings:
        print(warning, file=sys.stderr)
    if os.getenv('PREDICT_ALLOW_LOCAL') == '1':
        print('LOCAL PREVIEW: these predictions are not from QuickML.', file=sys.stderr)
        return predict_local(rows)
    if configured() and os.getenv('QUICKML_AUTH_MODE', 'oauth') == 'oauth':
        return predict_quickml(rows)
    return predict_hosted(rows)


def main():
    parser = argparse.ArgumentParser(description='Forecast energy demand using the published QuickML model.')
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--local-preview', action='store_true', help='Use the local development model instead of QuickML.')
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('Input and output paths must be different.')
    if args.local_preview:
        os.environ['PREDICT_ALLOW_LOCAL'] = '1'
    try:
        rows = parse_csv(args.input.read_text(encoding='utf-8-sig'))
        values = predict(rows)
        with args.output.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['timestamp', 'target_demand_kw'])
            writer.writerows((r['timestamp'], round(v, 4)) for r, v in zip(rows, values))
        print(f'Wrote {len(values)} predictions to {args.output}')
    except (ValueError, RuntimeError, OSError) as error:
        print(f'Prediction failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
