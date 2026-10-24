import csv
import io
import json
import math
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import app
from energy.controller import battery_settings, build_dispatch, dispatch_mode
from energy.analytics import capacity_advice, diagnostics
from energy.features import engineer
from energy.local_model import load_model, predict_local
from energy.quickml import QuickMLError, extract_predictions, predict_quickml
from energy.telemetry import ValidationError, clean_rows, parse_csv
from energy.history import CloudHistory, HistoryError
from predict import predict


def sample_rows(count=24):
    return [{'timestamp': (datetime(2026, 10, 24) + timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S'),
             'ambient_temp_c': 28, 'humidity_pct': 65, 'solar_irradiance_wm2': 100} for i in range(count)]


class ControllerTests(unittest.TestCase):
    def test_exact_thresholds_and_time_boundaries(self):
        for demand, hour, expected in [(160, 17, 'main_grid'), (160.0001, 17, 'renewable_storage'),
                                       (0, 18, 'renewable_storage'), (100, 22, 'renewable_storage'),
                                       (160, 23, 'main_grid'), (0, 0, 'main_grid')]:
            with self.subTest(demand=demand, hour=hour):
                self.assertEqual(dispatch_mode(demand, hour), expected)

    def test_critical_alert_independent_of_evening_rule(self):
        rows = sample_rows()
        values = [100.0] * 24
        values[1], values[2] = 199.999, 200.0
        results, summary, events, _ = build_dispatch(rows, values)
        self.assertFalse(results[1]['critical_overload'])
        self.assertTrue(results[2]['critical_overload'])
        self.assertEqual(results[18]['grid_mode'], 'renewable_storage')
        self.assertFalse(results[18]['critical_overload'])
        self.assertEqual(summary['critical_hours'], 1)

    def test_battery_conservation_and_protected_reserve(self):
        config = {'capacity_kwh': 1000, 'initial_soc_pct': 80, 'reserve_pct': 20,
                  'charge_kw': 0, 'max_discharge_kw': 300, 'efficiency': 0.8}
        rows, _, _, _ = build_dispatch(sample_rows(3), [200, 200, 200], config)
        self.assertEqual([r['battery_discharge_kw'] for r in rows], [200, 200, 80])
        self.assertEqual(rows[-1]['battery_soc_pct'], 20)
        self.assertEqual(rows[-1]['storage_shortfall_kwh'], 120)
        # The controller remains in the mandated storage mode despite shortfall.
        self.assertEqual(rows[-1]['grid_mode'], 'renewable_storage')

    def test_power_limit_and_recharging(self):
        rows, _, _, _ = build_dispatch(sample_rows(2), [250, 100], {
            'capacity_kwh': 1000, 'initial_soc_pct': 50, 'reserve_pct': 20,
            'charge_kw': 100, 'max_discharge_kw': 50, 'efficiency': 1})
        self.assertEqual(rows[0]['battery_discharge_kw'], 50)
        self.assertEqual(rows[0]['storage_shortfall_kwh'], 200)
        self.assertEqual(rows[1]['battery_soc_pct'], 55)

    def test_battery_bounds(self):
        for config in [{'efficiency':0}, {'capacity_kwh':float('nan')}, {'initial_soc_pct':10,'reserve_pct':20}, {'unknown':1}]:
            with self.subTest(config=config), self.assertRaises(ValidationError):
                battery_settings(config)


class TelemetryTests(unittest.TestCase):
    def test_training_median_imputation_including_dataframe_nan(self):
        rows = sample_rows(1)
        rows[0]['ambient_temp_c'] = ''
        rows[0]['humidity_pct'] = float('nan')
        clean, warnings = clean_rows(rows, load_model()['medians'])
        self.assertEqual(clean[0]['ambient_temp_c'], load_model()['medians']['ambient_temp_c'])
        self.assertTrue(math.isfinite(clean[0]['humidity_pct']))
        self.assertEqual(len(warnings), 2)

    def test_gaps_duplicates_and_length(self):
        for case in ('gap','duplicate','short'):
            rows = sample_rows()
            if case == 'gap': rows[12]['timestamp'] = '2026-10-25 12:00:00'
            elif case == 'duplicate': rows[12]['timestamp'] = rows[11]['timestamp']
            else: rows.pop()
            with self.subTest(case=case), self.assertRaises(ValidationError):
                clean_rows(rows, load_model()['medians'], require_window=True)

    def test_invalid_feature_values(self):
        for value in ['invalid', float('inf'), True, -1, 101]:
            rows = sample_rows(1); rows[0]['humidity_pct'] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                clean_rows(rows, load_model()['medians'])

    def test_csv_bom_crlf_and_extra_target_not_leaked(self):
        text='\ufefftimestamp,ambient_temp_c,humidity_pct,solar_irradiance_wm2,target_demand_kw\r\n"2026-10-24 00:00:00",28,65,100,900\r\n'
        rows, _ = clean_rows(parse_csv(text), load_model()['medians'])
        self.assertNotIn('target_demand_kw', rows[0])
        self.assertNotIn('target_demand_kw', engineer(rows[0]))
        self.assertTrue(math.isfinite(predict_local(rows)[0]))

    def test_preserves_timestamp_order_for_evaluator(self):
        rows = sample_rows(3)[::-1]
        clean, _ = clean_rows(rows, load_model()['medians'])
        self.assertEqual([r['timestamp'] for r in rows], [r['timestamp'] for r in clean])


class AnalyticsTests(unittest.TestCase):
    def test_capacity_estimate_resolves_energy_shortfall(self):
        rows=sample_rows(3)
        values=[200,200,200]
        config={'capacity_kwh':1000,'initial_soc_pct':80,'reserve_pct':20,
                'charge_kw':0,'max_discharge_kw':300,'efficiency':1}
        advice=capacity_advice(rows,values,config)
        self.assertAlmostEqual(advice['minimum_capacity_kwh'],1000,delta=1)
        solved=build_dispatch(rows,values,{**config,'capacity_kwh':advice['minimum_capacity_kwh']})
        self.assertLessEqual(solved[1]['storage_shortfall_kwh'],0.01)

    def test_capacity_and_power_constraints_are_distinct(self):
        advice=capacity_advice(sample_rows(3),[250]*3,{'max_discharge_kw':50})
        self.assertTrue(advice['power_limit_insufficient'])
        self.assertEqual(advice['required_discharge_kw'],250)

    def test_infeasible_starting_energy_is_reported(self):
        advice=capacity_advice(sample_rows(3),[250]*3,{
            'initial_soc_pct':20,'reserve_pct':20,'charge_kw':0})
        self.assertIsNone(advice['minimum_capacity_kwh'])

    def test_uncertainty_band_is_not_reused_for_quickml(self):
        model={'uncertainty':{'radius_kw':15},'ranges':{}}
        rows=[{**sample_rows(1)[0],'target_demand_kw':190}]
        result=diagnostics(rows,model,'quickml')
        self.assertIsNone(result['uncertainty'])
        self.assertIsNone(rows[0]['upper_demand_kw'])

    def test_threshold_watch_and_out_of_range_input(self):
        model={'uncertainty':{'radius_kw':15},'ranges':{'ambient_temp_c':[10,25]}}
        rows=[{**sample_rows(1)[0],'target_demand_kw':190}]
        result=diagnostics(rows,model,'local_preview',2)
        self.assertTrue(rows[0]['threshold_watch'])
        self.assertEqual(result['threshold_watch_hours'],1)
        self.assertEqual(result['out_of_training_range_hours'],1)
        self.assertEqual(result['imputed_values'],2)


class QuickMLTests(unittest.TestCase):
    def test_managed_batch_uses_one_authenticated_request_in_order(self):
        env={'QUICKML_AUTH_MODE':'catalyst','QUICKML_PROJECT_ID':'project-1','QUICKML_ENDPOINT_KEY':'key',
             'X_ZOHO_CATALYST_LISTEN_PORT':'9000','ZOHO_ORG_ID':'org-1','QUICKML_REQUEST_MODE':'batch'}
        gateway={'HTTP_X_ZC_PROJECTID':'project-1','HTTP_X_ZC_ADMIN_CRED_TOKEN':'gateway-token'}
        client=SimpleNamespace(credential=SimpleNamespace(token=lambda:('TicketCredential','ticket')),
                               config={'project_key':'project-key','environment':'Development'})
        sdk=SimpleNamespace(initialize=lambda **kwargs:client)
        rows=list(reversed(sample_rows(3)))
        with patch.dict(os.environ,env,clear=True),patch.dict('sys.modules',{'zcatalyst_sdk':sdk}),patch('energy.quickml._read_json',return_value={'result':[103,102,101]}) as call:
            self.assertEqual(predict_quickml(rows,environ=gateway),[103,102,101])
        call.assert_called_once()
        request=call.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'),'Zoho-ticket ticket')
        self.assertEqual([r['timestamp'] for r in json.loads(request.data)['data']],[r['timestamp'] for r in rows])

    def test_managed_auth_requires_hosted_matching_gateway(self):
        env={'QUICKML_AUTH_MODE':'catalyst','QUICKML_PROJECT_ID':'project-1','QUICKML_ENDPOINT_KEY':'key'}
        gateway={'HTTP_X_ZC_PROJECTID':'project-1','HTTP_X_ZC_ADMIN_CRED_TOKEN':'gateway-token'}
        with patch.dict(os.environ,env,clear=True), self.assertRaises(QuickMLError):
            predict_quickml(sample_rows(1),environ=gateway)
        env['X_ZOHO_CATALYST_LISTEN_PORT']='9000'
        for bad in ({},dict(gateway,HTTP_X_ZC_PROJECTID='different-project')):
            with patch.dict(os.environ,env,clear=True), self.assertRaises(QuickMLError):
                predict_quickml(sample_rows(1),environ=bad)

    def test_managed_auth_uses_sdk_and_preserves_order(self):
        env={'QUICKML_AUTH_MODE':'catalyst','QUICKML_PROJECT_ID':'project-1','QUICKML_ENDPOINT_KEY':'key',
             'X_ZOHO_CATALYST_LISTEN_PORT':'9000'}
        gateway={'HTTP_X_ZC_PROJECTID':'project-1','HTTP_X_ZC_ADMIN_CRED_TOKEN':'gateway-token'}
        def initialize(req,scope):
            self.assertEqual(scope,'admin')
            self.assertEqual(req.headers['X-ZC-ADMIN-CRED-TOKEN'],'gateway-token')
            def run(key,record):
                self.assertEqual(key,'key')
                return {'result':[str(100+int(record['timestamp'][11:13]))],'status':'success'}
            return SimpleNamespace(quick_ml=lambda:SimpleNamespace(predict=run))
        sdk=SimpleNamespace(initialize=initialize)
        with patch.dict(os.environ,env,clear=True),patch.dict('sys.modules',{'zcatalyst_sdk':sdk}):
            self.assertEqual(predict_quickml(sample_rows(3),environ=gateway),[100,101,102])

    def test_response_shapes(self):
        for response in [{'predictions':[1,'2']}, {'status':'success','result':[{'prediction':'1'},{'prediction':2}]},
                         {'data':{'predictions':[1,2]}}, [{'target_demand_kw':1},{'target_demand_kw':2}]]:
            with self.subTest(response=response): self.assertEqual(extract_predictions(response,2),[1,2])

    def test_invalid_responses_rejected(self):
        for response in [{'predictions':[1]}, {'predictions':[1,float('nan')]}, {'predictions':[True,1]},
                         {'status':'error','result':[1,2]}, {'predictions':[-1,2]}]:
            with self.subTest(response=response), self.assertRaises(QuickMLError):
                extract_predictions(response,2)

    def test_unconfigured_submission_fails_without_fallback(self):
        with patch.dict(os.environ, {'GRIDLENS_PREDICT_URL':''}, clear=True), self.assertRaises(QuickMLError):
            predict(sample_rows(2))

    def test_hosted_evaluator_preserves_1000_rows_and_requires_quickml(self):
        rows=sample_rows(1000)
        for i,row in enumerate(rows):row['ambient_temp_c']=10+i/100
        rows.reverse()
        def reply(request,timeout):
            batch=json.loads(request.data)['rows']
            self.assertLessEqual(len(batch),100)
            return {'provider':'quickml','predictions':[float(r['ambient_temp_c']) for r in batch]}
        with patch.dict(os.environ,{},clear=True),patch('predict._read_json',side_effect=reply):
            result=predict(rows)
            self.assertEqual(result,[float(r['ambient_temp_c']) for r in rows])
        with patch.dict(os.environ,{},clear=True),patch('predict._read_json',return_value={'provider':'local_preview','predictions':[1]}),self.assertRaises(QuickMLError):
            predict(rows[:1])

    def test_batch_payload_and_oauth_headers(self):
        env={'QUICKML_ENDPOINT_URL':'https://api.catalyst.zoho.in/quickml/test',
             'QUICKML_ENDPOINT_KEY':'test-key','CATALYST_ORG_ID':'test-org','ZOHO_ACCESS_TOKEN':'test-token',
             'QUICKML_REQUEST_MODE':'batch','QUICKML_INPUT_KEY':'data','QUICKML_FEATURE_SCHEMA':'engineered'}
        with patch.dict(os.environ,env,clear=True), patch('energy.quickml._read_json',return_value={'predictions':[123,124]}) as request:
            self.assertEqual(predict_quickml(sample_rows(2)),[123,124])
            sent=request.call_args.args[0]
            self.assertEqual(sent.get_header('Authorization'),'Zoho-oauthtoken test-token')
            payload=json.loads(sent.data)
            self.assertEqual(len(payload['data']),2)
            self.assertIn('hour_sin_1',payload['data'][0])
            self.assertNotIn('timestamp',payload['data'][0])

    def test_single_requests_preserve_order(self):
        env={'QUICKML_ENDPOINT_URL':'https://api.catalyst.zoho.in/quickml/test',
             'QUICKML_ENDPOINT_KEY':'test-key','ZOHO_ORG_ID':'test-org','ZOHO_ACCESS_TOKEN':'test-token'}
        def fake(request):
            self.assertEqual(request.get_header('Catalyst-org'),'test-org')
            row=json.loads(request.data)['data']
            return {'status':'success','pipeLineType':'prediction','result':[str(int(row['timestamp'][11:13])+100)]}
        with patch.dict(os.environ,env,clear=True),patch('energy.quickml._read_json',side_effect=fake):
            self.assertEqual(predict_quickml(sample_rows(3)),[100,101,102])


class CloudHistoryTests(unittest.TestCase):
    def test_roundtrip_survives_new_store_and_enforces_session_ownership(self):
        with patch.dict(os.environ,{},clear=True):run=app.forecast({'rows':sample_rows()})
        saved=[]
        client=MagicMock()
        client.datastore.return_value.table.return_value.insert_row.side_effect=lambda row:saved.append(row)
        def query(sql):
            matches=[row for row in saved if "'"+row['SessionKey']+"'" in sql]
            return [{'GridLensRuns':row} for row in matches]
        client.zcql.return_value.execute_query.side_effect=query
        with patch.dict(os.environ,{'GRIDLENS_HISTORY_TABLE':'123'},clear=True),patch('energy.history.managed_client',return_value=client):
            CloudHistory({}).save(run,'session-one')
            second=CloudHistory({})
            self.assertEqual(second.get(run['id'],'session-one'),run)
            self.assertEqual(second.list('session-one')[0]['id'],run['id'])
            self.assertIsNone(second.get(run['id'],'session-two'))
            self.assertEqual(second.list('session-two'),[])
            before=client.zcql.return_value.execute_query.call_count
            self.assertIsNone(second.get("x' OR '1'='1",'session-one'))
            self.assertEqual(client.zcql.return_value.execute_query.call_count,before)
        self.assertNotEqual(saved[0]['SessionKey'],'session-one')
        self.assertLessEqual(len(saved[0]['Payload']),10000)

    def test_upstream_history_failure_is_explicit(self):
        with patch.dict(os.environ,{'GRIDLENS_HISTORY_TABLE':'123'},clear=True),patch('energy.history.managed_client',side_effect=RuntimeError('unavailable')),self.assertRaises(HistoryError):
            CloudHistory({})


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.patch=patch.object(app,'DATA_DIR',Path(self.temp.name));self.patch.start()
        self.cookie=''

    def tearDown(self):
        self.patch.stop();self.temp.cleanup()

    def request(self,path,body=None,cookie=None,origin=None,environ_overrides=None):
        raw=json.dumps(body).encode() if body is not None else b''
        environ={'PATH_INFO':path,'REQUEST_METHOD':'POST' if body is not None else 'GET',
                 'CONTENT_LENGTH':str(len(raw)),'CONTENT_TYPE':'application/json','wsgi.input':io.BytesIO(raw),
                 'HTTP_HOST':'localhost:8080','HTTP_COOKIE':self.cookie if cookie is None else cookie}
        if origin:environ['HTTP_ORIGIN']=origin
        environ.update(environ_overrides or {})
        response={}
        def start(status,headers):response.update(status=status,headers=dict(headers))
        result=b''.join(app.application(environ,start))
        self.cookie=response['headers']['Set-Cookie'].split(';')[0]
        response['body']=json.loads(result) if response['headers']['Content-Type'].startswith('application/json') else result
        return response

    def test_forecast_history_restore_export_and_session_scope(self):
        response=self.request('/api/forecast',{'rows':sample_rows(),'provider':'local_preview'})
        self.assertTrue(response['status'].startswith('200'))
        run=response['body'];self.assertEqual(len(run['rows']),24)
        history=self.request('/api/history')['body']['runs'];self.assertEqual(len(history),1)
        self.assertEqual(self.request('/api/runs/'+run['id'])['body']['id'],run['id'])
        exported=self.request('/api/runs/'+run['id']+'/export')['body'].decode()
        self.assertEqual(len(list(csv.DictReader(io.StringIO(exported)))),24)
        self.assertTrue(self.request('/api/runs/'+run['id'],cookie='')['status'].startswith('404'))

    def test_control_signal_export_keeps_alerts_independent(self):
        values=[160]*24;values[0]=200;values[17]=160.0001
        with patch('app.predict_quickml',return_value=values):
            run=self.request('/api/forecast',{'rows':sample_rows(),'provider':'quickml'})['body']
        result=self.request('/api/runs/'+run['id']+'/signals')['body']
        self.assertTrue(result['dry_run'])
        self.assertEqual(len(result['signals']),24)
        self.assertTrue(result['signals'][0]['critical_overload'])
        self.assertEqual(result['signals'][16]['source'],'main_grid')
        self.assertEqual(result['signals'][17]['source'],'renewable_storage')
        self.assertEqual(result['signals'][22]['source'],'renewable_storage')
        self.assertFalse(result['signals'][22]['critical_overload'])
        self.assertEqual(result['signals'][23]['source'],'main_grid')
        self.assertTrue(self.request('/api/runs/'+run['id']+'/signals',cookie='')['status'].startswith('404'))

    def test_validation_failures_and_cross_origin_rejected(self):
        response=self.request('/api/forecast',{'rows':sample_rows(2)})
        self.assertTrue(response['status'].startswith('422'))
        response=self.request('/api/forecast',{'rows':sample_rows()},origin='https://untrusted.example')
        self.assertTrue(response['status'].startswith('403'))

    def test_prediction_relay_uses_only_quickml_and_does_not_store_runs(self):
        with patch('app.predict_quickml',return_value=[100,101]) as live:
            response=self.request('/api/predict',{'rows':sample_rows(2)})
        self.assertTrue(response['status'].startswith('200'))
        self.assertEqual(response['body']['provider'],'quickml')
        self.assertEqual(response['body']['predictions'],[100,101])
        self.assertEqual(len(live.call_args.args[0]),2)
        self.assertEqual(self.request('/api/history')['body']['runs'],[])
        response=self.request('/api/predict',{'rows':sample_rows(101)})
        self.assertTrue(response['status'].startswith('422'))

    def test_proxy_public_origin_is_exact_and_chunked_body_is_bounded(self):
        public='https://gridlens.example'
        proxy={'HTTP_HOST':'internal.proxy','CONTENT_LENGTH':'','wsgi.input_terminated':True}
        with patch.dict(os.environ,{'GRIDLENS_PUBLIC_ORIGIN':public}):
            response=self.request('/api/forecast',{'rows':sample_rows()},origin=public,environ_overrides=proxy)
            self.assertTrue(response['status'].startswith('200'))
            response=self.request('/api/forecast',{'rows':sample_rows()},origin=public+'.evil.example',environ_overrides=proxy)
            self.assertTrue(response['status'].startswith('403'))
            response=self.request('/api/forecast',{'csv':'x'*(app.MAX_BODY+1)},origin=public,environ_overrides=proxy)
            self.assertTrue(response['status'].startswith('413'))
            response=self.request('/api/forecast',{'rows':sample_rows()},origin=public,environ_overrides=dict(proxy,**{'wsgi.input_terminated':False}))
            self.assertTrue(response['status'].startswith('411'))

    def test_missing_quickml_never_returns_local_success(self):
        with patch.dict(os.environ,{},clear=True):
            response=self.request('/api/forecast',{'rows':sample_rows(),'provider':'quickml'})
        self.assertTrue(response['status'].startswith('502'))
        self.assertIn('not configured',response['body']['error'])

    def test_static_allowlist_does_not_expose_secrets(self):
        for path in ['/.env','/energy/config.py','/../.env','/data/train_telemetry.csv']:
            with self.subTest(path=path):self.assertTrue(self.request(path)['status'].startswith('404'))

    def test_scenario_holds_demand_and_dispatch_policy_fixed(self):
        run=self.request('/api/forecast',{'rows':sample_rows(),'provider':'local_preview'})['body']
        scenario=self.request('/api/scenario',{'run_id':run['id'],'battery':{'capacity_kwh':10000}})
        self.assertTrue(scenario['status'].startswith('200'))
        rows=scenario['body']['rows']
        self.assertEqual([r['target_demand_kw'] for r in rows],[r['target_demand_kw'] for r in run['rows']])
        self.assertEqual([r['grid_mode'] for r in rows],[r['grid_mode'] for r in run['rows']])
        self.assertEqual(len(self.request('/api/history')['body']['runs']),1)

    def test_scenario_cannot_read_another_browser_session(self):
        run=self.request('/api/forecast',{'rows':sample_rows(),'provider':'local_preview'})['body']
        response=self.request('/api/scenario',{'run_id':run['id']},cookie='')
        self.assertTrue(response['status'].startswith('404'))

    def test_live_forecast_has_no_local_uncertainty_band(self):
        with patch('app.predict_quickml',return_value=[190]*24):
            result=self.request('/api/forecast',{'rows':sample_rows(),'provider':'quickml'})['body']
        self.assertIsNone(result['diagnostics']['uncertainty'])
        self.assertTrue(all(r['lower_demand_kw'] is None for r in result['rows']))


if __name__ == '__main__':
    unittest.main()
