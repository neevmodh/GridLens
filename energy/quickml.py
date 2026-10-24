"""Server-only QuickML REST adapter. No fallback when live inference fails.

Endpoint request shapes vary with the published pipeline: use the sample in the
Catalyst endpoint console to set INPUT_KEY, REQUEST_MODE and FEATURE_SCHEMA.
"""
import json
import logging
import math
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .features import quickml_features
from .catalyst import api_origin, managed_client, organization_id

_token_lock = threading.Lock()
_token_cache = {'value': None, 'expires': 0, 'identity': None}


class QuickMLError(RuntimeError):
    pass


def configured():
    if os.getenv('QUICKML_AUTH_MODE', 'oauth') == 'catalyst':
        return bool(os.getenv('QUICKML_ENDPOINT_KEY') and os.getenv('X_ZOHO_CATALYST_LISTEN_PORT'))
    return bool(os.getenv('QUICKML_ENDPOINT_URL') and os.getenv('QUICKML_ENDPOINT_KEY')
                and organization_id() and (os.getenv('ZOHO_ACCESS_TOKEN') or
                all(os.getenv(k) for k in ('ZOHO_CLIENT_ID', 'ZOHO_CLIENT_SECRET', 'ZOHO_REFRESH_TOKEN'))))


def _read_json(request, timeout=30):
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise QuickMLError('QuickML response exceeds the size limit.')
        return json.loads(raw)
    except HTTPError as error:
        # Never expose upstream response bodies: they can contain sensitive data.
        raise QuickMLError(f'QuickML request returned HTTP {error.code}; check server credentials and endpoint configuration.') from None
    except (URLError, TimeoutError, OSError):
        raise QuickMLError('QuickML could not be reached. Check network access and the endpoint URL.') from None
    except (ValueError, UnicodeDecodeError):
        raise QuickMLError('QuickML returned an invalid JSON response.') from None


def access_token():
    token = os.getenv('ZOHO_ACCESS_TOKEN')
    if token:
        return token
    base = os.getenv('ZOHO_ACCOUNTS_URL', 'https://accounts.zoho.in').rstrip('/')
    if base not in {f'https://accounts.zoho.{suffix}' for suffix in ('com', 'in', 'eu', 'com.au', 'jp', 'com.cn', 'ca', 'sa')}:
        raise QuickMLError('Use the official Zoho Accounts URL for your data center.')
    identity = (base, os.getenv('ZOHO_CLIENT_ID'), os.getenv('ZOHO_REFRESH_TOKEN'))
    with _token_lock:
        if _token_cache['identity'] == identity and _token_cache['expires'] > time.time():
            return _token_cache['value']
        payload = urlencode({'grant_type': 'refresh_token', 'client_id': os.getenv('ZOHO_CLIENT_ID', ''),
                             'client_secret': os.getenv('ZOHO_CLIENT_SECRET', ''),
                             'refresh_token': os.getenv('ZOHO_REFRESH_TOKEN', '')}).encode()
        result = _read_json(Request(base + '/oauth/v2/token', data=payload,
                                   headers={'Content-Type': 'application/x-www-form-urlencoded'}))
        if not isinstance(result, dict) or not result.get('access_token'):
            raise QuickMLError('Zoho token refresh failed. Check OAuth client, scope and data center.')
        _token_cache.update(value=result['access_token'], expires=time.time() + max(0, float(result.get('expires_in', 3600)) - 60), identity=identity)
        return result['access_token']


def extract_predictions(response, expected):
    result = response
    if isinstance(result, dict):
        if result.get('status') in ('error', 'failure', 'failed'):
            raise QuickMLError('QuickML reported an inference error. Check the endpoint model schema.')
        if 'predictions' in result:
            result = result['predictions']
        elif 'result' in result:
            result = result['result']
        elif 'data' in result:
            return extract_predictions(result['data'], expected)
        elif 'prediction' in result or 'target_demand_kw' in result:
            result = [result]
    if not isinstance(result, list) or len(result) != expected:
        raise QuickMLError(f'QuickML must return exactly {expected} prediction(s). Check its response schema.')
    predictions = []
    for item in result:
        if isinstance(item, dict):
            item = item.get('target_demand_kw', item.get('prediction'))
        try:
            if isinstance(item, bool):
                raise ValueError()
            value = float(item)
        except (TypeError, ValueError):
            raise QuickMLError('QuickML returned a nonnumeric demand prediction.') from None
        if not math.isfinite(value) or value < 0:
            raise QuickMLError('QuickML demand predictions must be finite and nonnegative.')
        predictions.append(value)
    return predictions


def _predict_managed(rows, environ):
    schema = os.getenv('QUICKML_FEATURE_SCHEMA', 'raw')
    if schema not in ('raw', 'engineered'):
        raise QuickMLError('QUICKML_FEATURE_SCHEMA must be raw or engineered.')
    mode = os.getenv('QUICKML_REQUEST_MODE', 'single')
    if mode not in ('single','batch'):
        raise QuickMLError('QUICKML_REQUEST_MODE must be single or batch.')
    def failure(error):
        code = str(getattr(error,'code',''))
        safe_code = code if re.fullmatch(r'[A-Z0-9_]{1,80}',code) else 'UNSPECIFIED'
        logging.getLogger('gridlens').warning('Managed QuickML failed: type=%s code=%s',type(error).__name__,safe_code)
        return QuickMLError('Managed QuickML inference failed. Check the published endpoint and AppSail gateway configuration.')
    if mode == 'batch':
        try:
            client = managed_client(environ)
            credential_type, token = client.credential.token()
            prefixes = {'AccessTokenCredential':'Zoho-oauthtoken ', 'TicketCredential':'Zoho-ticket '}
            if credential_type not in prefixes or not organization_id():
                raise QuickMLError('Managed prediction credentials are unavailable.')
            environment = os.getenv('QUICKML_ENVIRONMENT',client.config.get('environment','Development'))
            if environment not in ('Development','Production'):
                raise QuickMLError('Invalid QuickML environment.')
            headers = {'Content-Type':'application/json','Authorization':prefixes[credential_type]+token,
                       'CATALYST-ORG':organization_id(),'Environment':environment,
                       'X-Catalyst-Environment':environment,'X-CATALYST-USER':'admin',
                       'PROJECT_ID':str(client.config['project_key']),
                       'X-QUICKML-ENDPOINT-KEY':os.environ['QUICKML_ENDPOINT_KEY']}
            endpoint = api_origin()+'/quickml/v1/project/'+os.environ['QUICKML_PROJECT_ID']+'/endpoints/predict'
            payload = {'data':[quickml_features(row,schema) for row in rows]}
            response = _read_json(Request(endpoint,data=json.dumps(payload,allow_nan=False).encode(),headers=headers,method='POST'),timeout=120)
        except Exception as error:
            raise failure(error) from None
        return extract_predictions(response,len(rows))
    def request(row):
        try:
            # Initialize inside each worker: Catalyst credentials are thread-local.
            client = managed_client(environ)
            response = client.quick_ml().predict(os.environ['QUICKML_ENDPOINT_KEY'], quickml_features(row, schema))
        except Exception as error:
            raise failure(error) from None
        return extract_predictions(response, 1)[0]
    with ThreadPoolExecutor(max_workers=4) as executor:
        return list(executor.map(request, rows))


def predict_quickml(rows, environ=None):
    auth_mode = os.getenv('QUICKML_AUTH_MODE', 'oauth')
    if auth_mode == 'catalyst':
        return _predict_managed(rows, environ)
    if auth_mode != 'oauth':
        raise QuickMLError('QUICKML_AUTH_MODE must be oauth or catalyst.')
    if not configured():
        raise QuickMLError('QuickML is not configured. Set the endpoint URL, key, organization ID and Zoho OAuth credentials on the server.')
    endpoint = os.environ['QUICKML_ENDPOINT_URL']
    parsed = urlparse(endpoint)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise QuickMLError('QUICKML_ENDPOINT_URL must be a valid HTTPS URL without embedded credentials.')
    environment = os.getenv('QUICKML_ENVIRONMENT', os.getenv('CATALYST_ENVIRONMENT', 'Development'))
    if environment not in ('Development', 'Production'):
        raise QuickMLError('QUICKML_ENVIRONMENT must be Development or Production.')
    headers = {'Content-Type': 'application/json', 'X-QUICKML-ENDPOINT-KEY': os.environ['QUICKML_ENDPOINT_KEY'],
               'Authorization': 'Zoho-oauthtoken ' + access_token(),
               'CATALYST-ORG': organization_id(), 'Environment': environment}
    schema = os.getenv('QUICKML_FEATURE_SCHEMA', 'raw')
    if schema not in ('raw', 'engineered'):
        raise QuickMLError('QUICKML_FEATURE_SCHEMA must be raw or engineered.')
    records = [quickml_features(row, schema) for row in rows]
    input_key = os.getenv('QUICKML_INPUT_KEY', 'data')
    mode = os.getenv('QUICKML_REQUEST_MODE', 'single')

    def request(data, count):
        payload = {input_key: data} if input_key else data
        response = _read_json(Request(endpoint, data=json.dumps(payload, allow_nan=False).encode(), headers=headers, method='POST'))
        return extract_predictions(response, count)

    if mode == 'batch':
        return request(records, len(records))
    if mode != 'single':
        raise QuickMLError('QUICKML_REQUEST_MODE must be single or batch.')
    # map preserves input order even when requests finish out of order.
    with ThreadPoolExecutor(max_workers=4) as executor:
        return [result[0] for result in executor.map(lambda row: request(row, 1), records)]
