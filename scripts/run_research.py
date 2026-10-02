"""雪鴞 api.bt 多策略研究。私有原始資料留在 .local，公開衍生研究結果。"""
from pathlib import Path
import argparse, contextlib, io, json, sys, hashlib
import numpy as np
import pandas as pd
from owl_login import login

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'strategies/momentum_eod/spec.json').read_text(encoding='utf-8'))

def get_frames(api):
    k = api.MSMP.日_K
    fields = {f: getattr(k, 'adj_' + f) for f in ['Open','High','Low','Close']}
    fields['Volume'] = k.Volume
    result = {}
    for symbol in SPEC['symbols']:
        f = pd.DataFrame({key: matrix[symbol] for key,matrix in fields.items()}).sort_index()
        f = f.dropna(subset=['Open','High','Low','Close','Volume'])
        f = f[(f[['Open','High','Low','Close']] > 0).all(axis=1) & (f.Volume > 0)].copy()
        f['ret5'] = f.Close.pct_change(5, fill_method=None)
        f['ret10'] = f.Close.pct_change(10, fill_method=None)
        f['core'] = (f.ret5 >= .05) & (f.ret10 >= .03)
        f['ma20'] = f.Close.rolling(20).mean()
        f.index.name='DateTime'
        result[symbol]=f
    return result

def run_one(api, f, symbol, variant, hold, extra_fee, start, end):
    bars=f.loc[start:end].copy().reset_index()
    bars['sig'] = bars.core
    if variant=='volume_1000': bars['sig'] &= bars.Volume >= 1000
    if variant=='trend_ma20': bars['sig'] &= bars.Close > bars.ma20
    if variant=='buy_hold_50pct': bars['sig']=True
    bars['idx']=range(len(bars))
    decisions=[]
    class Strategy(api.bt.Core):
        def on_init(self):
            self.entry_index=None
        def on_bar(self,row):
            i=int(row['idx'])
            if self.global_qty > 0 and self.entry_index is None: self.entry_index=i
            if self.global_qty == 0: self.entry_index=None
            closing = i == len(bars)-2
            timed = self.entry_index is not None and i-self.entry_index >= hold-1
            should_exit = closing or (variant!='buy_hold_50pct' and (timed or not bool(row['core'])))
            if self.global_qty>0 and should_exit:
                self.Condition.Global(True,-self.global_qty,0,self.PriceType.market_ioc,None,'boundary' if closing else 'exit')
                decisions.append({'signal_date':str(row['DateTime'])[:10],'side':'sell','bar':i})
            elif self.global_qty==0 and bool(row['sig']) and i<len(bars)-2:
                self.Condition.Global(True,SPEC['allocation'],0,self.PriceType.market_ioc,None,'entry')
                decisions.append({'signal_date':str(row['DateTime'])[:10],'side':'buy','bar':i})
    core=Strategy()
    core.feed_data(bars,['DateTime','Open','High','Low','Close','Volume'],columns=['sig','core','idx'])
    cfg=api.bt.config(name=variant,symbol=symbol,fee=SPEC['fee_each_side']+extra_fee,
        tax_long=0,tax_short=SPEC['sell_tax'],unit=SPEC['unit'])
    rp=api.bt.generate_report({cfg:core},capital=SPEC['capital_per_independent_run'])
    return rp,bars,decisions

def audit(rp,bars,decisions):
    trades=rp.trade_detail.copy()
    checks=[]
    # Verify engine fills against the next bar after an actual submitted signal.
    expected={(d['side'],str(bars.iloc[d['bar']+1].DateTime)[:10]):float(bars.iloc[d['bar']+1].Open) for d in decisions}
    for _,t in trades.iterrows():
        for side,timekey,pricekey in [('buy','entry_time','entry_price'),('sell','exit_time','exit_price')]:
            date=str(t[timekey])[:10]
            target=expected.get((side,date))
            checks.append(target is not None and np.isclose(float(t[pricekey]),target,atol=.011))
    return {'trade_count':len(trades),'all_next_open_prices_match':bool(all(checks)),'checks':len(checks),
        'all_positions_closed':bool(trades.empty or trades.exit_time.notna().all()),
        'trade_columns':list(trades.columns),'daily_columns':list(rp.daily.columns)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--env',required=True,help='本機 .env 路徑；不會複製到輸出')
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    private=ROOT/'.local'; private.mkdir(exist_ok=True)
    out=private/'smoke' if args.smoke else ROOT/'reports'; out.mkdir(exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        api=login(args.env)
        frames=get_frames(api)
    common=sorted(set.intersection(*(set(f.index) for f in frames.values())))
    eligible=common[SPEC['warmup_days']:]
    cut=int(len(eligible)*SPEC['development_fraction'])
    periods={'development':(eligible[0],eligible[cut-1]),'out_of_sample':(eligible[cut],eligible[-1]),'full':(eligible[0],eligible[-1])}
    metadata={'engine':'Snowyowl api.bt','data_start':str(common[0])[:10],'data_end':str(common[-1])[:10],
      'periods':{p:[str(d)[:10] for d in dates] for p,dates in periods.items()},'spec_sha256':hashlib.sha256(json.dumps(SPEC,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest(),
      'price_basis':SPEC['price_basis'],'universe':SPEC['symbols'],'notes':['每檔與每策略獨立一千萬元，不能把報酬相加當作組合','樣本外為事先固定時序切分；策略來源既已看過市場，不是從未接觸過的新資料','存活者偏差與四檔人工選樣；不能外推全市場','未模擬漲跌停排隊、流動性、實際滑價與除權息現金事件']}
    summaries=[]; audits=[]
    jobs=[]
    for symbol in SPEC['symbols']:
        for period in periods:
            for variant in SPEC['comparison']: jobs.append((symbol,period,variant,5,0))
        for hold in [3,10]: jobs.append((symbol,'out_of_sample','base',hold,0))
        for variant in SPEC['comparison'][:3]: jobs.append((symbol,'out_of_sample',variant,5,.001))
    if args.smoke: jobs=jobs[:1]
    for n,(symbol,period,variant,hold,extra) in enumerate(jobs,1):
        key=f'{symbol}_{period}_{variant}_h{hold}_cost{extra:g}'
        with contextlib.redirect_stdout(io.StringIO()):
            rp,bars,decisions=run_one(api,frames[symbol],symbol,variant,hold,extra,*periods[period])
        folder=out/key; folder.mkdir(exist_ok=True)
        for name in ['report','trade_detail','daily']:
            getattr(rp,name).to_csv(folder/f'{name}.csv',encoding='utf-8-sig')
        a=audit(rp,bars,decisions);a['run']=key;audits.append(a)
        if not a['all_next_open_prices_match'] or not a['all_positions_closed']: raise AssertionError(json.dumps(a))
        metrics=rp.report.iloc[:,0].to_dict()
        summaries.append({'run':key,'symbol':symbol,'period':period,'variant':variant,'hold':hold,'extra_fee':extra,**metrics})
        # Private provider data is never published.
        bars.to_csv(private/f'{key}_bars.csv',index=False)
        pd.DataFrame(decisions).to_csv(private/f'{key}_decisions.csv',index=False)
        print(f'{n}/{len(jobs)} {key}: {len(rp.trade_detail)} trades',flush=True)
    pd.DataFrame(summaries).to_csv(out/'comparison.csv',index=False,encoding='utf-8-sig')
    (out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'audit.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE')

if __name__=='__main__':main()
