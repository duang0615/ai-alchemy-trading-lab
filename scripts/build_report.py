"""核對 api.bt 逐筆帳務，將相同起始資金口徑圖像化；不另做撮合。"""
from pathlib import Path
import json, html
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports'
CAPITAL=10_000_000

def main():
    summary=pd.read_csv(OUT/'comparison.csv')
    meta=json.loads((OUT/'metadata.json').read_text(encoding='utf-8'))
    results=[];curves={};examples=[];checks=[];annual=[];block_comparisons=[]
    return_series={}
    for _,r in summary.iterrows():
        folder=OUT/r['run']
        trades=pd.read_csv(folder/'trade_detail.csv',index_col=0)
        daily=pd.read_csv(folder/'daily.csv',index_col=0,parse_dates=True)
        # Audit only local licensed bars; on students' rerun the same files exist.
        bars=pd.read_csv(ROOT/'.local'/f"{r['run']}_bars.csv",parse_dates=['DateTime'])
        calendar=pd.DatetimeIndex(bars.DateTime)
        pnl=daily.profit_loss.reindex(calendar).ffill().fillna(0)
        equity=CAPITAL+pnl
        returns=equity.pct_change().fillna((equity.iloc[0]/CAPITAL)-1)
        return_series[r['run']]=returns
        drawdown=equity/equity.cummax().clip(lower=CAPITAL)-1
        years=(calendar[-1]-calendar[0]).days/365.25
        amount=trades.qty*trades.unit
        gross=(trades.exit_price-trades.entry_price)*amount
        costs=amount*((trades.entry_price+trades.exit_price)*(.001425+r.extra_fee)+trades.exit_price*.003)
        cash_ok=bool(np.allclose(trades.pnl,gross-costs,atol=.05))
        fee_ok=bool(np.allclose(trades.cost,costs,atol=.05))
        pnl_ok=bool(np.isclose(trades.pnl.sum(),pnl.iloc[-1],atol=.05))
        signal_ok=bool(np.allclose(bars.ret5.iloc[10:],bars.Close.pct_change(5,fill_method=None).iloc[10:],equal_nan=True) and np.allclose(bars.ret10.iloc[10:],bars.Close.pct_change(10,fill_method=None).iloc[10:],equal_nan=True))
        checks.append({'run':r['run'],'fee_formula_match':fee_ok,'pnl_formula_match':cash_ok,'final_equity_match':pnl_ok,'signal_uses_only_past_bars':signal_ok})
        if not all([cash_ok,fee_ok,pnl_ok,signal_ok]):raise AssertionError(checks[-1])
        profits=trades.pnl[trades.pnl>0];losses=trades.pnl[trades.pnl<0]
        q=np.quantile(trades.pnl,[.05,.5,.95]).tolist() if len(trades) else [0,0,0]
        ci=[None,None]
        if len(trades)>1:
            rng=np.random.default_rng(20261002)
            bootstrap=rng.choice(trades.pnl.to_numpy(),(5000,len(trades)),replace=True).mean(axis=1)
            ci=np.quantile(bootstrap,[.025,.975]).tolist()
        # A fixed-P/L reorder stress test: same trades, different sequence, not a forecast.
        rng=np.random.default_rng(20261002)
        mdds=[]
        for _ in range(2000):
            path=CAPITAL+np.r_[0,np.cumsum(rng.permutation(trades.pnl.to_numpy()))]
            mdds.append(float(np.min(path/np.maximum.accumulate(path)-1)))
        row={'run':r['run'],'symbol':str(r.symbol),'period':r.period,'variant':r.variant,'hold':int(r.hold),'extra_fee':r.extra_fee,
          'account_return':float(equity.iloc[-1]/CAPITAL-1),'account_cagr':float((equity.iloc[-1]/CAPITAL)**(1/years)-1),
          'account_mdd':float(drawdown.min()),'account_sharpe':float(returns.mean()/returns.std()*np.sqrt(252)) if returns.std()>0 else 0,
          'net_profit':float(trades.pnl.sum()),'cost':float(trades.cost.sum()),'gross_profit':float(gross.sum()),
          'trades':len(trades),'win_rate':float((trades.pnl>0).mean()),'profit_factor':float(profits.sum()/abs(losses.sum())) if len(losses) else None,
          'pnl_quantiles_05_50_95':q,'top3_profit_share':float(profits.nlargest(3).sum()/profits.sum()) if profits.sum()>0 else None,
          'mean_trade_pnl_bootstrap95':ci,
          'trade_reorder_mdd_quantiles_05_50_95':np.quantile(mdds,[.05,.5,.95]).tolist(),
          'without_best3_net':float(trades.pnl.sum()-profits.nlargest(3).sum()),
          'engine_total_returns':float(r.TotalReturns),'engine_mdd':float(r.MaxDrawdown)}
        results.append(row)
        for year,g in returns.groupby(returns.index.year):
            annual.append({'run':r['run'],'year':int(year),'account_return':float((1+g).prod()-1),'observations':len(g),'partial_year':len(g)<200})
        curves[r['run']]=[{'date':str(d)[:10],'equity':round(float(e),2)} for d,e in equity.items()]
        pd.DataFrame({'equity':equity,'account_return':equity/CAPITAL-1,'drawdown':drawdown}).to_csv(folder/'account_equity.csv',encoding='utf-8-sig')
        if r.period=='out_of_sample' and r.variant=='base' and r.hold==5 and r.extra_fee==0:
            for kind,t in [('best',trades.loc[trades.pnl.idxmax()]),('worst',trades.loc[trades.pnl.idxmin()])]:
                ed=pd.to_datetime(t.entry_time);xd=pd.to_datetime(t.exit_time)
                entry_i=bars.index[bars.DateTime==ed][0];signal=bars.iloc[entry_i-1]
                examples.append({'symbol':str(r.symbol),'kind':kind,'signal_date':str(signal.DateTime)[:10],
                  'ret5':float(signal.ret5),'ret10':float(signal.ret10),'entry_date':str(ed)[:10],'exit_date':str(xd)[:10],
                  'entry_adjusted_price':float(t.entry_price),'exit_adjusted_price':float(t.exit_price),'lots':int(t.qty),'cost':float(t.cost),'pnl':float(t.pnl),'exit_rule':t.exit_rule,
                  'note':'事後挑選本次樣本外最好／最差交易，只作教學解剖，非事前推薦'})
    for symbol in meta['universe']:
        key=f'{symbol}_out_of_sample_base_h5_cost0'
        for variant in ['volume_1000','trend_ma20']:
            other=f'{symbol}_out_of_sample_{variant}_h5_cost0'
            delta=(return_series[other]-return_series[key]).to_numpy()
            rng=np.random.default_rng(20261002);n=len(delta);means=[];block=20
            for _ in range(3000):
                indices=np.concatenate([(np.arange(block)+s)%n for s in rng.integers(0,n,size=int(np.ceil(n/block)))])[:n]
                means.append(delta[indices].mean()*252)
            block_comparisons.append({'symbol':symbol,'variant':variant,'mean_annualized_daily_return_difference':float(delta.mean()*252),'block20_bootstrap95':np.quantile(means,[.025,.975]).tolist(),'note':'相同日期配對、20日區塊重抽樣；探索性，未調整多重比較，不是複利報酬差'})
    pd.DataFrame(results).to_csv(OUT/'account_comparison.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(annual).to_csv(OUT/'yearly_returns.csv',index=False,encoding='utf-8-sig')
    (OUT/'block_comparisons.json').write_text(json.dumps(block_comparisons,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'accounting_audit.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    payload={'metadata':meta,'results':results,'curves':curves,'examples':examples,'block_comparisons':block_comparisons}
    (OUT/'research.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    template=(ROOT/'scripts/report_template.html').read_text(encoding='utf-8')
    (ROOT/'index.html').write_text(template.replace('__RESEARCH__',json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('</','<\\/')),encoding='utf-8')
    print(pd.DataFrame(results).query("period=='out_of_sample' and hold==5 and extra_fee==0") [['symbol','variant','account_return','account_mdd','trades']].to_string(index=False))
    print(f'ACCOUNTING AUDIT PASS: {len(checks)} runs')

if __name__=='__main__':main()
