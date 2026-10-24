"""GridLens WSGI app. Run locally with python3 app.py; production uses Gunicorn."""
import csv
import io
import json
import logging
import mimetypes
import os
import re
import secrets
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIServer, make_server

from energy.config import ROOT
from energy.controller import build_dispatch, battery_settings, control_signals
from energy.analytics import capacity_advice, diagnostics
from energy.local_model import load_model, predict_local
from energy.quickml import QuickMLError, configured, predict_quickml
from energy.telemetry import ValidationError, clean_rows, parse_csv
from energy.history import CloudHistory, HistoryError, SUMMARY_KEYS

logger = logging.getLogger('gridlens')
MAX_BODY = 1_000_000
STATIC = ROOT / 'static'
DATA_DIR = Path(os.getenv('GRIDLENS_DATA_DIR', str(ROOT / '.runtime')))
_db_lock = threading.Lock()


@contextmanager
def database():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATA_DIR / 'runs.sqlite3', timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            connection.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, session TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)')
            yield connection
    finally:
        connection.close()


def session_id(environ):
    cookie = SimpleCookie()
    try:
        cookie.load(environ.get('HTTP_COOKIE', ''))
    except Exception:
        pass
    value = cookie.get('gridlens_session')
    if value and re.fullmatch(r'[A-Za-z0-9_-]{43}', value.value):
        return value.value
    return secrets.token_urlsafe(32)


def save_run(run,session,environ):
    if os.getenv('GRIDLENS_HISTORY_TABLE'):
        CloudHistory(environ).save(run,session)
        return
    with _db_lock,database() as connection:
        connection.execute('INSERT INTO runs VALUES (?, ?, ?, ?)',(run['id'],session,run['created_at'],json.dumps(run,allow_nan=False)))
        connection.execute('DELETE FROM runs WHERE id NOT IN (SELECT id FROM runs ORDER BY created_at DESC LIMIT 200)')


def get_run(run_id,session,environ):
    if os.getenv('GRIDLENS_HISTORY_TABLE'):
        return CloudHistory(environ).get(run_id,session)
    with _db_lock,database() as connection:
        record=connection.execute('SELECT payload FROM runs WHERE id = ? AND session = ?',(run_id,session)).fetchone()
    return json.loads(record['payload']) if record else None


def list_runs(session,environ):
    if os.getenv('GRIDLENS_HISTORY_TABLE'):
        return CloudHistory(environ).list(session)
    with _db_lock,database() as connection:
        records=connection.execute('SELECT payload FROM runs WHERE session = ? ORDER BY created_at DESC LIMIT 20',(session,)).fetchall()
    return [{key:run[key] for key in SUMMARY_KEYS} for run in (json.loads(record['payload']) for record in records)]


def model_status():
    return {'quickml_configured': configured(), 'local_model': load_model()['metadata'],
            'quickml_model':json.loads((ROOT/'models/quickml-evaluation.json').read_text()) if (ROOT/'models/quickml-evaluation.json').exists() else None,
            'history_storage':'catalyst_datastore' if os.getenv('GRIDLENS_HISTORY_TABLE') else 'local_sqlite',
            'feature_schema': os.getenv('QUICKML_FEATURE_SCHEMA', 'raw'),
            'environment': os.getenv('QUICKML_ENVIRONMENT', os.getenv('CATALYST_ENVIRONMENT', 'Development')),
            'live_verified': False,
            'notice': 'Configured means credentials are present; a successful live forecast verifies the connection.'}


def forecast(payload, environ=None):
    if not isinstance(payload, dict):
        raise ValidationError('Request body must be a JSON object.')
    rows = parse_csv(payload['csv']) if isinstance(payload.get('csv'), str) else payload.get('rows')
    rows, warnings = clean_rows(rows, load_model()['medians'], require_window=True)
    # Reject malformed battery settings before making a paid live API request.
    battery = battery_settings(payload.get('battery'))
    provider = payload.get('provider', 'local_preview')
    if provider == 'quickml':
        predictions = predict_quickml(rows, environ=environ)
    elif provider == 'local_preview':
        predictions = predict_local(rows)
    else:
        raise ValidationError('Provider must be local_preview or quickml.')
    points, summary, events, battery = build_dispatch(rows, predictions, battery)
    quality = diagnostics(points, load_model(), provider, len(warnings))
    advice = capacity_advice(rows, predictions, battery)
    return {'id': str(uuid.uuid4()), 'created_at': datetime.now(timezone.utc).isoformat(),
            'provider': provider, 'rows': points, 'summary': summary, 'events': events,
            'battery': battery, 'warnings': warnings,
            'diagnostics':quality, 'capacity_advice':advice,
            'model_name':load_model()['metadata']['name'] if provider=='local_preview' else 'Published QuickML endpoint',
            'input_source':'official_sample' if payload.get('input_source')=='official_sample' else 'user_input',
            'notice': 'Battery state is a simulation. Dispatch signals do not operate physical equipment.',
            'window_start': rows[0]['timestamp'], 'window_end': rows[-1]['timestamp']}


def export_csv(run):
    stream = io.StringIO(newline='')
    fields = ['timestamp', 'target_demand_kw', 'lower_demand_kw', 'upper_demand_kw', 'grid_mode', 'reason', 'critical_overload',
              'battery_soc_pct', 'battery_discharge_kw', 'battery_charge_kw', 'storage_shortfall_kwh']
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(run['rows'])
    return stream.getvalue().encode()


def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    session = session_id(environ)
    secure = '; Secure' if (environ.get('wsgi.url_scheme') == 'https' or environ.get('HTTP_X_FORWARDED_PROTO') == 'https'
                            or os.getenv('GRIDLENS_PUBLIC_ORIGIN','').startswith('https://')) else ''
    common = [('X-Content-Type-Options', 'nosniff'), ('Referrer-Policy', 'same-origin'),
              ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'"),
              ('Set-Cookie', f'gridlens_session={session}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800{secure}')]

    def respond(body, status='200 OK', content_type='application/json; charset=utf-8', headers=None):
        if content_type.startswith('application/json'):
            body = json.dumps(body, allow_nan=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        start_response(status, common + [('Content-Type', content_type), ('Content-Length', str(len(body))),
                                         ('Cache-Control', 'no-store' if path.startswith('/api') else 'no-cache')] + (headers or []))
        return [body]

    try:
        if method == 'GET' and path == '/api/health':
            return respond({'status': 'ok', **model_status()})
        if method == 'GET' and path == '/api/sample':
            query = parse_qs(environ.get('QUERY_STRING', ''))
            try:
                offset = int(query.get('offset', ['9'])[0])
            except ValueError:
                raise ValidationError('Sample offset must be a whole number.') from None
            with (ROOT / 'sample_test_input.csv').open() as stream:
                sample = list(csv.DictReader(stream))
            if not 0 <= offset <= len(sample) - 24:
                raise ValidationError('Sample offset is outside the available dataset.')
            return respond({'rows': sample[offset:offset + 24], 'source': 'Official sample_test_input.csv',
                            'historical': True, 'total_rows': len(sample)})
        if method == 'GET' and path == '/api/history':
            return respond({'runs':list_runs(session,environ)})
        if method == 'GET' and re.fullmatch(r'/api/runs/[a-f0-9-]{36}(?:/(?:export|signals))?', path):
            run_id = path.split('/')[3]
            run=get_run(run_id,session,environ)
            if not run:
                return respond({'error': 'Forecast run was not found for this browser session.'}, '404 Not Found')
            if path.endswith('/signals'):
                return respond(control_signals(run),headers=[('Content-Disposition','attachment; filename="gridlens-control-signals.json"')])
            if path.endswith('/export'):
                return respond(export_csv(run), content_type='text/csv; charset=utf-8',
                               headers=[('Content-Disposition', 'attachment; filename="gridlens-forecast.csv"')])
            return respond(run)
        if method == 'POST' and path in ('/api/forecast', '/api/scenario', '/api/predict'):
            if not environ.get('CONTENT_TYPE', '').split(';')[0].strip() == 'application/json':
                return respond({'error': 'Use application/json for forecast requests.'}, '415 Unsupported Media Type')
            origin = environ.get('HTTP_ORIGIN')
            if origin:
                host = environ.get('HTTP_HOST', '')
                allowed_origins = {'http://' + host, 'https://' + host}
                public_origin = os.getenv('GRIDLENS_PUBLIC_ORIGIN', '').rstrip('/')
                if public_origin:
                    allowed_origins.add(public_origin)
                if origin not in allowed_origins:
                    return respond({'error': 'Cross-origin requests are not accepted.'}, '403 Forbidden')
            try:
                length = environ.get('CONTENT_LENGTH')
                size = int(length) if length else None
            except ValueError:
                raise ValidationError('Invalid request length.') from None
            if size is None and not environ.get('wsgi.input_terminated'):
                return respond({'error': 'A request length or terminated input stream is required.'}, '411 Length Required')
            if size is not None and (size <= 0 or size > MAX_BODY):
                return respond({'error': 'Send a JSON request smaller than 1 MB.'}, '413 Content Too Large')
            # Gunicorn exposes terminated streams for proxy-forwarded chunked bodies.
            raw = environ['wsgi.input'].read(MAX_BODY + 1 if size is None else size)
            if len(raw) > MAX_BODY:
                return respond({'error': 'Send a JSON request smaller than 1 MB.'}, '413 Content Too Large')
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                raise ValidationError('Request body is not valid JSON.') from None
            if path == '/api/predict':
                if not isinstance(payload, dict) or not isinstance(payload.get('rows'), list) or not 1 <= len(payload['rows']) <= 100:
                    raise ValidationError('Send between 1 and 100 telemetry rows per prediction request.')
                rows, warnings = clean_rows(payload['rows'], load_model()['medians'])
                values = predict_quickml(rows, environ=environ)
                return respond({'provider':'quickml','predictions':values,'warnings':warnings})
            if path == '/api/scenario':
                if not isinstance(payload,dict) or not isinstance(payload.get('run_id'),str):
                    raise ValidationError('Choose a forecast run before simulating a scenario.')
                baseline=get_run(payload['run_id'],session,environ)
                if not baseline:
                    return respond({'error':'Forecast run was not found for this browser session.'},'404 Not Found')
                rows=baseline['rows']
                predictions=[r['target_demand_kw'] for r in rows]
                points,summary,events,battery=build_dispatch(rows,predictions,payload.get('battery'))
                return respond({'baseline_id':baseline['id'],'baseline_summary':baseline['summary'],
                    'rows':points,'summary':summary,'events':events,'battery':battery,
                    'capacity_advice':capacity_advice(rows,predictions,battery),
                    'notice':'Battery-only scenario. Forecast demand and competition switching rules are held fixed; no new model inference was performed.'})
            run = forecast(payload, environ=environ)
            save_run(run,session,environ)
            return respond(run)
        if method == 'GET' and path in ('/', '/index.html', '/app.js', '/styles.css', '/favicon.svg'):
            target = STATIC / ('index.html' if path == '/' else path.lstrip('/'))
            if target.is_file():
                return respond(target.read_bytes(), content_type=mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        if path.startswith('/api/'):
            return respond({'error': 'API route not found.'}, '404 Not Found')
        return respond('Page not found', '404 Not Found', 'text/plain; charset=utf-8')
    except ValidationError as error:
        return respond({'error': str(error)}, '422 Unprocessable Content')
    except QuickMLError as error:
        return respond({'error': str(error)}, '502 Bad Gateway')
    except HistoryError as error:
        return respond({'error':str(error)}, '503 Service Unavailable')
    except Exception:
        logger.exception('Request failed: %s %s', method, path)
        return respond({'error': 'The server could not complete this request. Check the server log.'}, '500 Internal Server Error')


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv('X_ZOHO_CATALYST_LISTEN_PORT', os.getenv('PORT', '8080')))
    host = os.getenv('HOST', '127.0.0.1')
    print(f'GridLens is running at http://{host}:{port}', flush=True)
    with make_server(host, port, application, server_class=ThreadingWSGIServer) as server:
        server.serve_forever()
