"""Forecast diagnostics and feasibility sizing, separate from dispatch rules."""
import math

from .controller import battery_settings, build_dispatch


def capacity_advice(rows, predictions, config):
    config = battery_settings(config)
    points, summary, _, _ = build_dispatch(rows, predictions, config)
    required_power = max((p['target_demand_kw'] for p in points if p['grid_mode'] == 'renewable_storage'), default=0)
    sizing_config = {**config, 'max_discharge_kw': max(config['max_discharge_kw'], required_power)}
    # Search for energy capacity with adequate output power. Report the power
    # upgrade separately; larger energy capacity cannot fix a power limit.
    def shortfall(capacity):
        return build_dispatch(rows, predictions, {**sizing_config,'capacity_kwh':capacity})[1]['storage_shortfall_kwh']
    upper = 1_000_000
    if shortfall(upper) > 0.01:
        minimum = None
    else:
        lower = 1.0
        for _ in range(24):
            middle = (lower+upper)/2
            if shortfall(middle) > 0.01: lower = middle
            else: upper = middle
        minimum = math.ceil(upper)
    return {'minimum_capacity_kwh':minimum,'required_discharge_kw':round(required_power,2),
            'power_limit_insufficient':required_power>config['max_discharge_kw'],
            'planned_load_served_pct':round(100*(1-summary['storage_shortfall_kwh']/max(summary['total_kwh'],1e-9)),2),
            'notice':'Minimum capacity is a feasibility estimate for this forecast, fixed initial/reserve percentages, charging rate and efficiency; not a cost optimum. Required discharge power must also be available.'}


def diagnostics(points, model, provider, imputed_count=0):
    ranges = model.get('ranges', {})
    shifted = [p['timestamp'] for p in points if any(p[key] < bounds[0] or p[key] > bounds[1] for key,bounds in ranges.items())]
    uncertainty = model.get('uncertainty') if provider == 'local_preview' else None
    for point in points:
        if uncertainty:
            point['lower_demand_kw'] = round(max(0,point['target_demand_kw']-uncertainty['radius_kw']),4)
            point['upper_demand_kw'] = round(point['target_demand_kw']+uncertainty['radius_kw'],4)
            point['threshold_watch'] = point['target_demand_kw']<200<=point['upper_demand_kw']
        else:
            point['lower_demand_kw'] = None
            point['upper_demand_kw'] = None
            point['threshold_watch'] = False
    return {'imputed_values':imputed_count,'out_of_training_range_hours':len(shifted),
            'out_of_training_range_timestamps':shifted,'uncertainty':uncertainty,
            'threshold_watch_hours':sum(p['threshold_watch'] for p in points),
            'notice':'Weather range diagnostics use the supplied historical training data; they are not a guarantee of model validity.'}
