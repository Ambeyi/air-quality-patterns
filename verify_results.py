"""Independently check output counts and means using Python's standard library."""
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

source, output = Path(sys.argv[1]), Path(sys.argv[2])
with source.open(newline='') as f:
    rows = [r for r in csv.DictReader(f, delimiter=';') if r['Date']]

def reading(row, name):
    raw=row[name].strip()
    if not raw: return None
    value=float(raw.replace(',','.'))
    return None if value == -200 else value

with (output/'missingness.csv').open() as f:
    for summary in csv.DictReader(f):
        name=summary['variable']
        valid=sum(reading(r,name) is not None for r in rows)
        blank=sum(not r[name].strip() for r in rows)
        sentinel=len(rows)-valid-blank
        assert valid==int(summary['valid'])
        assert blank==int(summary['blank_missing'])
        assert sentinel==int(summary['sentinel_missing'])
        assert math.isclose(float(summary['missing_percent']),100*(blank+sentinel)/len(rows),abs_tol=1e-10)
for filename, key in [('hourly_co.csv', lambda r:str(int(r['Time'].split('.')[0]))),
                      ('monthly_co.csv', lambda r:r['Date'][6:10]+'-'+r['Date'][3:5])]:
    groups=defaultdict(list)
    for row in rows: groups[key(row)].append(row)
    with (output/filename).open() as f:
        for summary in csv.DictReader(f):
            group=groups[next(iter(summary.values()))]
            values=[reading(r,'CO(GT)') for r in group if reading(r,'CO(GT)') is not None]
            assert int(summary['observations'])==len(group)
            assert int(summary['valid_co'])==len(values)
            if values:
                assert math.isclose(float(summary['mean_co']),statistics.mean(values),rel_tol=1e-12)
                assert math.isclose(float(summary['median_co']),statistics.median(values),rel_tol=1e-12)
print('Independent checks passed: all missingness counts/rates and all hourly/monthly counts, means and medians.')
