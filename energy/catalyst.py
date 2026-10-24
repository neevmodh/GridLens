"""Request-scoped Catalyst SDK initialization; credentials never leave the server."""
import os
from types import SimpleNamespace


class CatalystConnectionError(RuntimeError):
    pass


def organization_id():
    return (os.getenv('ZOHO_ORG_ID') or os.getenv('CATALYST_ORG_ID')
            or os.getenv('X_ZOHO_CATALYST_ORG_ID'))


def api_origin():
    origin = os.getenv('ZOHO_API_ORIGIN', 'https://api.catalyst.zoho.in')
    if origin not in {f'https://api.catalyst.zoho.{suffix}' for suffix in ('com','in','eu','com.au','jp','sa','ca')}:
        raise CatalystConnectionError('Use the official Catalyst API origin for your data center.')
    return origin


def managed_client(environ):
    if not environ or not os.getenv('X_ZOHO_CATALYST_LISTEN_PORT'):
        raise CatalystConnectionError('Managed authentication requires a hosted AppSail request.')
    headers = {key[5:].replace('_','-'):value for key,value in environ.items() if key.startswith('HTTP_X_ZC_')}
    project = os.getenv('QUICKML_PROJECT_ID')
    if not project or headers.get('X-ZC-PROJECTID') != project or not headers.get('X-ZC-ADMIN-CRED-TOKEN'):
        raise CatalystConnectionError('The Catalyst gateway project identity could not be verified.')
    if organization_id():
        os.environ.setdefault('X_ZOHO_CATALYST_ORG_ID',organization_id())
    os.environ.setdefault('X_ZOHO_CATALYST_CONSOLE_URL',api_origin())
    import zcatalyst_sdk
    return zcatalyst_sdk.initialize(req=SimpleNamespace(headers=headers),scope='admin')
