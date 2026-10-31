"""Audit semicolon-delimited air-quality data and summarize CO patterns."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MEASURES = ['CO(GT)', 'PT08.S1(CO)', 'NMHC(GT)', 'C6H6(GT)',
            'PT08.S2(NMHC)', 'NOx(GT)', 'PT08.S3(NOx)', 'NO2(GT)',
            'PT08.S4(NO2)', 'PT08.S5(O3)', 'T', 'RH', 'AH']

def analyze(frame):
    required = ['Date', 'Time'] + MEASURES
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    d = frame[required].dropna(how='all').copy()
    if d.empty:
        raise ValueError('No observations')
    times = pd.to_datetime(d.Date + ' ' + d.Time, format='%d/%m/%Y %H.%M.%S', errors='raise')
    if times.isna().any() or times.duplicated().any():
        raise ValueError('Timestamps must be present and unique')
    values = d[MEASURES].apply(pd.to_numeric, errors='raise')
    if np.isinf(values.to_numpy()).any():
        raise ValueError('Infinite readings are not supported')
    sentinel = values.eq(-200).sum()
    blanks = values.isna().sum()
    values = values.mask(values.eq(-200))
    audit = pd.DataFrame({'valid': values.count(), 'sentinel_missing': sentinel,
                          'blank_missing': blanks, 'missing_percent': values.isna().mean() * 100})
    audit.index.name = 'variable'
    if values['CO(GT)'].count() == 0:
        raise ValueError('At least one valid CO(GT) reading is required')
    co = pd.DataFrame({'co': values['CO(GT)'], 'hour': times.dt.hour,
                       'month': times.dt.strftime('%Y-%m')})
    hourly = co.groupby('hour').co.agg(['size', 'count', 'mean', 'median']).reindex(range(24))
    hourly[['size','count']] = hourly[['size','count']].fillna(0).astype(int)
    hourly.columns = ['observations', 'valid_co', 'mean_co', 'median_co']
    monthly = co.groupby('month').co.agg(['size', 'count', 'mean', 'median'])
    monthly.columns = hourly.columns
    metrics = {'input_rows': len(frame), 'observations': len(d),
               'empty_rows_removed': len(frame)-len(d),
               'start': str(times.min()), 'end': str(times.max()),
               'valid_co': int(values['CO(GT)'].count()),
               'mean_co': float(values['CO(GT)'].mean()),
               'complete_measurement_rows': int(values.notna().all(axis=1).sum())}
    return audit, hourly, monthly, metrics

def run(source, output):
    audit, hourly, monthly, metrics = analyze(pd.read_csv(source, sep=';', decimal=','))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output/'missingness.csv')
    hourly.to_csv(output/'hourly_co.csv')
    monthly.to_csv(output/'monthly_co.csv')
    (output/'summary.json').write_text(json.dumps(metrics, indent=2)+'\n')
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={'height_ratios':[2,1]})
    axes[0].plot(hourly.index, hourly.mean_co, marker='o', color='#176B87')
    axes[0].set_ylabel('Mean CO(GT) (input units)')
    axes[0].set_title('CO readings by hour of day')
    axes[0].grid(alpha=.2)
    axes[1].bar(hourly.index, hourly.valid_co, color='#64A6BD')
    axes[1].set_ylabel('Valid readings'); axes[1].set_xlabel('Hour in supplied timestamps')
    axes[1].set_xticks(range(24))
    fig.tight_layout(); fig.savefig(output/'hourly_co.svg'); plt.close(fig)
    return metrics

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, default=Path('results'))
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output), indent=2))
