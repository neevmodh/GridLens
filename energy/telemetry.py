import csv
import io
import math
from datetime import datetime, timedelta

WEATHER = ('ambient_temp_c', 'humidity_pct', 'solar_irradiance_wm2')
COLUMNS = ('timestamp', *WEATHER)
LIMITS = {'ambient_temp_c': (-60, 65), 'humidity_pct': (0, 100),
          'solar_irradiance_wm2': (0, 1500)}


class ValidationError(ValueError):
    pass


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not reader.fieldnames or any(c not in reader.fieldnames for c in COLUMNS):
        raise ValidationError('CSV must contain: ' + ', '.join(COLUMNS))
    if len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValidationError('CSV column names must be unique.')
    rows = list(reader)
    if any(None in row for row in rows):
        raise ValidationError('A CSV row has more values than its header.')
    return rows


def clean_rows(rows, medians, require_window=False):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValidationError('Supply between 1 and 1,000 telemetry rows.')
    if require_window and len(rows) != 24:
        raise ValidationError(f'A forecast window needs exactly 24 rows; received {len(rows)}.')
    cleaned, warnings, times = [], [], []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValidationError(f'Row {index + 1} must be an object.')
        missing = [c for c in COLUMNS if c not in row]
        if missing:
            raise ValidationError(f'Row {index + 1} is missing columns: {", ".join(missing)}.')
        timestamp = row['timestamp']
        if not isinstance(timestamp, str):
            raise ValidationError(f'Row {index + 1}: timestamp must be text.')
        try:
            date = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise ValidationError(f'Row {index + 1}: use timestamp YYYY-MM-DD HH:MM:SS.') from None
        if date.minute or date.second:
            raise ValidationError(f'Row {index + 1}: timestamps must fall on the hour.')
        times.append(date)
        item = {'timestamp': timestamp}
        for column in WEATHER:
            value = row[column]
            if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, float) and math.isnan(value)):
                value = medians[column]
                warnings.append(f'Row {index + 1}: {column} filled with training median ({value:.2f}).')
            if isinstance(value, bool):
                raise ValidationError(f'Row {index + 1}: {column} must be a number.')
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValidationError(f'Row {index + 1}: {column} must be a number.') from None
            low, high = LIMITS[column]
            if not math.isfinite(value) or not low <= value <= high:
                raise ValidationError(f'Row {index + 1}: {column} must be between {low} and {high}.')
            item[column] = value
        cleaned.append(item)
    if require_window and any(b - a != timedelta(hours=1) for a, b in zip(times, times[1:])):
        raise ValidationError('Use 24 consecutive hourly rows in ascending order, without gaps or duplicates.')
    return cleaned, warnings
