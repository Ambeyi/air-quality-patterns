import unittest
import pandas as pd
from analyze import analyze, MEASURES

class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({c:[1.,2.,3.] for c in MEASURES})
        self.data['Date'] = ['01/01/2020','02/01/2020','02/01/2020']
        self.data['Time'] = ['08.00.00','08.00.00','09.00.00']
    def test_sentinel_excluded_from_mean_not_denominator(self):
        self.data.loc[1,'CO(GT)'] = -200
        audit,hour,month,metrics = analyze(self.data)
        self.assertEqual(hour.loc[8,'observations'],2)
        self.assertEqual(hour.loc[8,'valid_co'],1)
        self.assertEqual(hour.loc[8,'mean_co'],1)
        self.assertEqual(metrics['mean_co'],2)
        self.assertEqual(audit.loc['CO(GT)','sentinel_missing'],1)
        self.assertEqual(month.loc['2020-01','valid_co'],2)
    def test_blank_distinguished_and_unrelated_missing_retained(self):
        self.data.loc[1,'NMHC(GT)'] = float('nan')
        audit,_,_,metrics = analyze(self.data)
        self.assertEqual(audit.loc['NMHC(GT)','blank_missing'],1)
        self.assertEqual(metrics['valid_co'],3)
        self.assertEqual(metrics['complete_measurement_rows'],2)
    def test_empty_rows_and_unobserved_hours(self):
        d = self.data.reindex(range(4))
        _,hour,_,metrics = analyze(d)
        self.assertEqual(metrics['empty_rows_removed'],1)
        self.assertEqual(hour.loc[0,'valid_co'],0)
        self.assertTrue(pd.isna(hour.loc[0,'mean_co']))
    def test_invalid_timestamp_and_duplicate(self):
        for time in ['bad','08.00.00']:
            d=self.data.copy();d.loc[2,'Time']=time
            with self.assertRaises(ValueError): analyze(d)
    def test_invalid_values_and_missing_schema(self):
        for value in [float('inf'),'invalid']:
            d=self.data.astype(object);d.loc[0,'T']=value
            with self.assertRaises(ValueError): analyze(d)
        with self.assertRaises(ValueError): analyze(self.data.drop(columns='Time'))
    def test_empty_and_no_valid_co(self):
        with self.assertRaises(ValueError): analyze(self.data.iloc[:0])
        self.data['CO(GT)']=-200
        with self.assertRaises(ValueError): analyze(self.data)

if __name__ == '__main__': unittest.main()
