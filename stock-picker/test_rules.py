import unittest
import pandas as pd
import numpy as np
from rules import numeric_dates,trend_signal,daily_rules,eps_rule,revenue_rule,margin_rule
class RulesTest(unittest.TestCase):
    def setUp(self):
        self.idx=pd.date_range('2026-01-01',periods=100)
        self.c=pd.DataFrame({'A':np.arange(100.)+100,'B':np.full(100,100.)},index=self.idx)
        self.v=pd.DataFrame(1000.,index=self.idx,columns=['A','B']);self.f=self.v*0+500;self.t=self.v*0+200
    def calc(self):return daily_rules(self.c,self.c+1,self.c-1,self.v,self.f,self.t,self.c['B'])
    def test_trend_needs_three_days(self):
        s=trend_signal(self.c);self.assertFalse(s['A'].iloc[60]);self.assertTrue(s['A'].iloc[61]);self.assertFalse(s['B'].iloc[-1])
    def test_top_and_foreign_missing(self):
        self.f.loc[self.idx[-1],'A']=np.nan;m,_,_=self.calc();self.assertFalse(m['foreign']['A']);self.assertTrue(m['foreign']['B'])
    def test_volume_prior_baseline_lots(self):
        self.v.loc[self.idx[-1],'A']=5000;m,x,_=self.calc();self.assertTrue(m['volume']['A']);self.assertEqual(x['volume_ratio']['A'],5)
    def test_cutoff_drops_future(self):
        d=numeric_dates(self.c,self.idx[-2]);self.assertEqual(len(d),99);self.assertEqual(d.index[-1],self.idx[-2])
    def test_zero_volume_baseline_not_a_multiple(self):
        self.v['A']=0.;self.v.loc[self.idx[-1],'A']=5000
        self.assertFalse(self.calc()[0]['volume']['A'])
    def test_duplicate_dates_rejected(self):
        d=self.c.copy();d.index=[self.idx[0]]*100
        with self.assertRaises(ValueError):numeric_dates(d,self.idx[-1])
    def test_eps_full_history_positive_pe(self):
        e=pd.DataFrame({'A':np.arange(23.)+1,'B':np.arange(23.)+1});p=pd.Series({'A':10,'B':-10});self.assertTrue(eps_rule(e,p)['A']);self.assertFalse(eps_rule(e,p)['B']);e.iloc[-1,0]=np.nan;self.assertFalse(eps_rule(e,p)['A'])
    def test_revenue_sum_and_missing(self):
        r=pd.DataFrame({'A':np.arange(60.)+50,'B':np.arange(60.)+50});m,y=revenue_rule(r);self.assertTrue(m['A'])
        self.assertAlmostEqual(y['A'],(324/288-1)*100);r.iloc[-1,0]=np.nan;self.assertFalse(revenue_rule(r)[0]['A'])
    def test_margin_annual_weighted_and_missing(self):
        ix=[f'{y}-Q{q}' for y in range(2022,2026) for q in range(1,5)];r=pd.DataFrame({'A':100.,'B':100.},index=ix);p=r.copy()
        for i,y in enumerate(range(2022,2026)):p.loc[[x for x in ix if x.startswith(str(y))]]=10+i
        self.assertTrue(margin_rule(r,p,p,p,2026)['A']);p.iloc[-1,0]=np.nan;self.assertFalse(margin_rule(r,p,p,p,2026)['A'])
if __name__=='__main__':unittest.main()
