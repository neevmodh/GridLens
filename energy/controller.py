"""Competition dispatch rules and a separate, explicitly simulated battery."""
import math
from datetime import datetime

from .telemetry import ValidationError

DEFAULT_BATTERY = {'capacity_kwh': 4000, 'initial_soc_pct': 80, 'reserve_pct': 20,
                   'charge_kw': 80, 'max_discharge_kw': 350, 'efficiency': 0.95}
BOUNDS = {'capacity_kwh': (1, 1000000), 'initial_soc_pct': (0, 100),
          'reserve_pct': (0, 100), 'charge_kw': (0, 100000),
          'max_discharge_kw': (1, 100000), 'efficiency': (0.5, 1)}


def battery_settings(config=None):
    if config is not None and not isinstance(config, dict):
        raise ValidationError('Battery configuration must be an object.')
    config = config or {}
    if set(config) - set(DEFAULT_BATTERY):
        raise ValidationError('Unknown battery setting.')
    result = {}
    for key, default in DEFAULT_BATTERY.items():
        try:
            if isinstance(config.get(key, default), bool):
                raise ValueError()
            value = float(config.get(key, default))
        except (ValueError, TypeError):
            raise ValidationError(f'Battery {key} must be numeric.') from None
        low, high = BOUNDS[key]
        if not math.isfinite(value) or not low <= value <= high:
            raise ValidationError(f'Battery {key} must be between {low} and {high}.')
        result[key] = value
    if result['initial_soc_pct'] < result['reserve_pct']:
        raise ValidationError('Initial battery charge must be at least the reserve.')
    return result


def dispatch_mode(demand, hour):
    return 'renewable_storage' if demand > 160 or 18 <= hour <= 22 else 'main_grid'


def control_signals(run):
    """Machine-readable scheduled commands; deliberately disconnected from hardware."""
    previous=None
    signals=[]
    for point in run['rows']:
        mode=point['grid_mode']
        signals.append({'timestamp':point['timestamp'],'command':'SET_POWER_SOURCE','source':mode,
                        'transition':previous is not None and previous!=mode,
                        'reason':point['reason'],'critical_overload':point['critical_overload'],
                        'predicted_demand_kw':point['target_demand_kw']})
        previous=mode
    return {'protocol':'gridlens.dispatch.v1','run_id':run['id'],'issued_at':run['created_at'],
            'dry_run':True,'signals':signals,'events':run['events']}


def build_dispatch(rows, predictions, config=None):
    if len(rows) != len(predictions):
        raise ValueError('Prediction count must match telemetry count.')
    config = battery_settings(config)
    energy = config['capacity_kwh'] * config['initial_soc_pct'] / 100
    reserve = config['capacity_kwh'] * config['reserve_pct'] / 100
    results, events = [], []
    previous_mode = None
    for row, demand in zip(rows, predictions):
        if not math.isfinite(demand) or demand < 0:
            raise ValueError('Demand predictions must be finite and nonnegative.')
        hour = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S').hour
        mode = dispatch_mode(demand, hour)
        delivered, charged, shortfall = 0.0, 0.0, 0.0
        if mode == 'renewable_storage':
            delivered = min(demand, config['max_discharge_kw'], max(0, energy - reserve) * config['efficiency'])
            energy -= delivered / config['efficiency']
            shortfall = max(0, demand - delivered)
        else:
            charged = min(config['charge_kw'], (config['capacity_kwh'] - energy) / config['efficiency'])
            energy += charged * config['efficiency']
        reason = 'demand_and_evening' if demand > 160 and 18 <= hour <= 22 else (
            'demand_threshold' if demand > 160 else 'evening_window' if 18 <= hour <= 22 else 'normal_demand')
        point = {**row, 'target_demand_kw': round(demand, 4), 'grid_mode': mode,
                 'reason': reason, 'critical_overload': demand >= 200,
                 'battery_soc_pct': round(100 * energy / config['capacity_kwh'], 2),
                 'battery_discharge_kw': round(delivered, 4), 'battery_charge_kw': round(charged, 4),
                 'storage_shortfall_kwh': round(shortfall, 4)}
        results.append(point)
        if mode != previous_mode:
            events.append({'timestamp': row['timestamp'], 'kind': 'transition', 'mode': mode, 'reason': reason})
        if demand >= 200:
            events.append({'timestamp': row['timestamp'], 'kind': 'critical_overload', 'demand_kw': round(demand, 2)})
        if shortfall > 0.001:
            events.append({'timestamp': row['timestamp'], 'kind': 'storage_shortfall', 'shortfall_kwh': round(shortfall, 2)})
        previous_mode = mode
    total = sum(predictions)
    peak_index = max(range(len(predictions)), key=predictions.__getitem__)
    summary = {'peak_kw': round(max(predictions), 2), 'peak_timestamp': rows[peak_index]['timestamp'],
               'average_kw': round(total / len(predictions), 2), 'total_kwh': round(total, 2),
               'storage_hours': sum(r['grid_mode'] == 'renewable_storage' for r in results),
               'main_grid_hours': sum(r['grid_mode'] == 'main_grid' for r in results),
               'critical_hours': sum(r['critical_overload'] for r in results),
               'end_soc_pct': results[-1]['battery_soc_pct'],
               'storage_delivered_kwh': round(sum(r['battery_discharge_kw'] for r in results), 2),
               'storage_shortfall_kwh': round(sum(r['storage_shortfall_kwh'] for r in results), 2),
               'transitions': max(0, sum(e['kind'] == 'transition' for e in events) - 1)}
    return results, summary, events, config
