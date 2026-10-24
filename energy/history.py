"""Durable, session-isolated forecast history in Catalyst Data Store."""
import base64
import hashlib
import json
import logging
import os
import uuid
import zlib

from .catalyst import managed_client

TABLE_NAME = 'GridLensRuns'
SUMMARY_KEYS = ('id','created_at','provider','window_start','window_end','summary')


class HistoryError(RuntimeError):
    pass


class CloudHistory:
    def __init__(self,environ):
        self.table_id = os.getenv('GRIDLENS_HISTORY_TABLE','')
        if not self.table_id.isdigit():
            raise HistoryError('Forecast history storage is not configured correctly.')
        try:
            self.client = managed_client(environ)
        except Exception as error:
            self._fail(error)

    @staticmethod
    def _fail(error):
        logging.getLogger('gridlens').warning('Cloud history failed: %s',type(error).__name__)
        raise HistoryError('Forecast history is temporarily unavailable. Please try again.') from None

    @staticmethod
    def session_key(session):
        return hashlib.sha256(session.encode()).hexdigest()

    def _query(self,query):
        try:
            rows = self.client.zcql().execute_query(query)
            return [row[TABLE_NAME] for row in rows if TABLE_NAME in row]
        except Exception as error:
            self._fail(error)

    def save(self,run,session):
        raw = json.dumps(run,allow_nan=False,separators=(',',':')).encode()
        payload = base64.b64encode(zlib.compress(raw)).decode('ascii')
        summary = json.dumps({key:run[key] for key in SUMMARY_KEYS},allow_nan=False,separators=(',',':'))
        if len(payload)>10000 or len(summary)>10000:
            raise HistoryError('This forecast is too large for the configured history record.')
        try:
            self.client.datastore().table(self.table_id).insert_row({
                'RunKey':str(uuid.UUID(run['id'])),'SessionKey':self.session_key(session),
                'CreatedAt':run['created_at'],'Summary':summary,'Payload':payload})
        except Exception as error:
            self._fail(error)

    def get(self,run_id,session):
        try:
            run_key=str(uuid.UUID(run_id))
        except (ValueError,TypeError,AttributeError):
            return None
        # Interpolated values are canonical UUIDs and SHA-256 hex, never user SQL.
        records=self._query(f"SELECT Payload FROM {TABLE_NAME} WHERE RunKey = '{run_key}' AND SessionKey = '{self.session_key(session)}' LIMIT 1")
        if not records:return None
        try:
            decoder=zlib.decompressobj()
            raw=decoder.decompress(base64.b64decode(records[0]['Payload'],validate=True),1_000_001)
            if len(raw)>1_000_000 or not decoder.eof:
                raise ValueError('Invalid saved forecast size')
            return json.loads(raw)
        except Exception as error:
            self._fail(error)

    def list(self,session):
        records=self._query(f"SELECT Summary FROM {TABLE_NAME} WHERE SessionKey = '{self.session_key(session)}' ORDER BY CreatedAt DESC LIMIT 20")
        try:
            return [json.loads(row['Summary']) for row in records]
        except Exception as error:
            self._fail(error)
