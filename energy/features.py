"""Target-free features. Identical transformations at training and inference."""
import math
from datetime import datetime


def engineer(row):
    time = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
    temp = float(row['ambient_temp_c'])
    humidity = float(row['humidity_pct']) / 100
    solar = float(row['solar_irradiance_wm2']) / 500
    cooling = max(0, temp - 24)
    heating = max(0, 18 - temp)
    result = {'temperature': temp, 'humidity': humidity, 'solar': solar,
              'cooling': cooling, 'heating': heating,
              'cooling_squared': cooling ** 2, 'heating_squared': heating ** 2,
              'cooling_humidity': cooling * humidity,
              'weekend': int(time.weekday() >= 5)}
    for harmonic in (1, 2, 3):
        angle = 2 * math.pi * time.hour * harmonic / 24
        result[f'hour_sin_{harmonic}'] = math.sin(angle)
        result[f'hour_cos_{harmonic}'] = math.cos(angle)
    result['evening'] = int(18 <= time.hour <= 22)
    return result


def quickml_features(row, schema='raw'):
    if schema == 'raw':
        return dict(row)
    if schema == 'engineered':
        return advanced_features(row)
    raise ValueError('QUICKML_FEATURE_SCHEMA must be raw or engineered.')


def advanced_features(row):
    """Calendar/weather interactions without unavailable lagged demand."""
    result = engineer(row)
    time = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
    result['temperature_squared'] = result['temperature'] ** 2
    result['solar_temperature'] = result['solar'] * result['temperature']
    for hour in range(24):
        active = float(time.hour == hour)
        result[f'hour_{hour:02d}'] = active
        result[f'cooling_hour_{hour:02d}'] = active * result['cooling']
    return result
