"""Chronological model selection, residual calibration and development holdout.

Train dependencies are optional; exported inference remains standard-library-only.
"""
import csv
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from energy.config import ROOT
from energy.features import engineer, advanced_features
from energy.local_model import predict_local
from energy.telemetry import WEATHER


def metric(y, p):
    return {'rmse_kw': round(float(np.sqrt(np.mean((y-p)**2))), 4),
            'mae_kw': round(float(np.mean(np.abs(y-p))), 4)}


def train(rows, kind):
    feature_fn = engineer if kind == 'legacy' else advanced_features
    names = list(feature_fn(rows[0]))
    x = np.array([[feature_fn(row)[key] for key in names] for row in rows])
    y = np.array([float(row['target_demand_kw']) for row in rows])
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale < 1e-12] = 1
    ridge = Ridge(alpha=0.1 if kind == 'legacy' else 10).fit((x-mean)/scale, y)
    weights = [float(ridge.intercept_), *ridge.coef_.tolist()]
    model = {'feature_version': 1 if kind == 'legacy' else 2, 'features': names,
             'means': mean.tolist(), 'scales': scale.tolist(), 'weights': weights,
             'medians': {key: statistics.median(float(row[key]) for row in rows) for key in WEATHER}}
    if kind in ('boosted', 'hybrid'):
        target = y if kind == 'boosted' else y-ridge.predict((x-mean)/scale)
        booster = GradientBoostingRegressor(n_estimators=250 if kind=='boosted' else 120,
                    max_depth=3 if kind=='boosted' else 2, learning_rate=0.04,
                    min_samples_leaf=15, subsample=0.9, random_state=42).fit(x,target)
        if kind == 'boosted':
            model['weights'] = [float(booster.init_.constant_[0,0])] + [0.0]*len(names)
        else:
            model['weights'][0] += float(booster.init_.constant_[0,0])
        model['learning_rate'] = float(booster.learning_rate)
        model['trees'] = []
        for estimator in booster.estimators_[:,0]:
            tree = estimator.tree_
            model['trees'].append({'left': tree.children_left.tolist(), 'right': tree.children_right.tolist(),
                'feature': tree.feature.tolist(), 'threshold': tree.threshold.tolist(),
                'value': tree.value[:,0,0].tolist()})
        exported = np.array(predict_local(rows, model))
        reference = booster.predict(x)+(ridge.predict((x-mean)/scale) if kind=='hybrid' else 0)
        if not np.allclose(exported,np.maximum(0,reference),atol=0.00006):
            raise RuntimeError('Portable model does not match the training library.')
    return model


def main():
    with (ROOT/'data/train_telemetry.csv').open() as stream:
        rows=sorted(csv.DictReader(stream),key=lambda row:row['timestamp'])
    names={'legacy':'Original ridge baseline','additive':'Weather + hourly interactions',
           'boosted':'Gradient boosted trees','hybrid':'Weather/calendar + residual boosting'}
    folds=[(1600,2000),(2400,2800)]
    candidates=[]
    for kind,name in names.items():
        errors=[];fold_scores=[]
        for start,end in folds:
            model=train(rows[:start],kind)
            actual=np.array([float(r['target_demand_kw']) for r in rows[start:end]])
            predicted=np.array(predict_local(rows[start:end],model))
            errors.extend((actual-predicted).tolist())
            fold_scores.append({'train_rows':start,'test_rows':end-start,**metric(actual,predicted)})
        score=round(math.sqrt(statistics.mean(error**2 for error in errors)),4)
        candidates.append({'kind':kind,'name':name,'cv_rmse_kw':score,'folds':fold_scores})
        print(name,score,flush=True)
    best=min(candidates,key=lambda item:item['cv_rmse_kw'])
    # Prefer a simpler extrapolating regression when its score is within one
    # fold standard error of the best score (the conventional one-SE rule).
    standard_error=statistics.stdev(f['rmse_kw'] for f in best['folds'])/math.sqrt(len(folds))
    complexity={'legacy':0,'additive':1,'boosted':2,'hybrid':3}
    eligible=[c for c in candidates if c['cv_rmse_kw']<=best['cv_rmse_kw']+standard_error]
    selected=min(eligible,key=lambda item:complexity[item['kind']])
    # Calibrate on rows 2800:3200 with a model fit only on rows 0:2800.
    calibration_model=train(rows[:2800],selected['kind'])
    actual=np.array([float(r['target_demand_kw']) for r in rows[2800:3200]])
    residuals=sorted(np.abs(actual-np.array(predict_local(rows[2800:3200],calibration_model))).tolist())
    rank=min(len(residuals),math.ceil((len(residuals)+1)*0.9))
    radius=residuals[rank-1]
    # This point evaluation uses the same 3200:4000 holdout as v1.
    test_model=train(rows[:3200],selected['kind'])
    actual=np.array([float(r['target_demand_kw']) for r in rows[3200:]])
    predicted=np.array(predict_local(rows[3200:],test_model))
    baseline=np.array(predict_local(rows[3200:],train(rows[:3200],'legacy')))
    # Reference band transfer is reported empirically; time dependence and
    # refitting prevent claiming an exchangeable-sample conformal guarantee.
    coverage=float(np.mean(np.abs(actual-predicted)<=radius)*100)
    validation={**metric(actual,predicted),'fit_rows':3200,'validation_rows':800,
                'strategy':'chronological final 800 rows; model selected on earlier rolling origins',
                'previous_rmse_kw':metric(actual,baseline)['rmse_kw'],
                'mean_baseline_rmse_kw':round(float(np.sqrt(np.mean((actual-np.mean([float(r['target_demand_kw']) for r in rows[:3200]]))**2))),4)}
    report={'selected':selected['kind'],'selected_name':selected['name'],'candidates':candidates,
            'selection_policy':'Simplest model within one fold standard error of best rolling-origin RMSE',
            'one_standard_error_kw':round(standard_error,4),
            'validation':validation,'uncertainty':{'label':'90% empirical residual reference band',
              'nominal_pct':90,'radius_kw':round(radius,4),'calibration_rows':400,
              'calibration_start':rows[2800]['timestamp'],'calibration_end':rows[3199]['timestamp'],
              'heldout_coverage_pct':round(coverage,2),
              'notice':'Historical residual reference only. Serial dependence, seasonal shift and final refitting mean future coverage is not guaranteed.'}}
    final=train(rows,selected['kind'])
    final['uncertainty']=report['uncertainty']
    final['ranges']={key:[min(float(r[key]) for r in rows),max(float(r[key]) for r in rows)] for key in WEATHER}
    final['metadata']={'name':selected['name'],'training_rows':len(rows),'training_start':rows[0]['timestamp'],
        'training_end':rows[-1]['timestamp'],'validation':validation,'benchmark':report,
        'notice':'Local model. Metrics are development backtests, not QuickML or hidden-test results.'}
    (ROOT/'models/local-preview.json').write_text(json.dumps(final,separators=(',',':'))+'\n')
    (ROOT/'models/benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
