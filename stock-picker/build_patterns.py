"""Snowyowl OHLC adapter. Public: 18 normalized teaching histories only."""
import argparse, contextlib, io, json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from owl_login import login
from rules import numeric_dates
ROOT=Path(__file__).resolve().parent

def build(env):
    source=json.loads((ROOT.parent/'.local/stock-picker-data.json').read_text(encoding='utf-8'))
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        api=login(env)
        frames={k:numeric_dates(api.MSMP.get('日_K',k),source['asof']).tail(800) for k in ('Open','High','Low','Close')}
    for frame in frames.values():frame.columns=frame.columns.astype(str)
    dates=frames['Close'].index
    rows=[]
    for row in source['rows']:
        symbol=row['symbol'];df=pd.DataFrame({k:f[symbol].reindex(dates) for k,f in frames.items()})
        valid=df.dropna()
        if valid.empty:continue
        base=float(valid['Close'].iloc[0])
        if base<=0:continue
        df=df/base*100
        # Preserve interior missing sessions. Only trim leading unknown history.
        df=df.loc[valid.index[0]:]
        bars=[[str(d.date()),*[round(float(v),6) if pd.notna(v) else None for v in values]] for d,values in zip(df.index,df.to_numpy())]
        rows.append({'symbol':symbol,'name':row['name'],'price':row['price'],'volume':row['volume'],'bars':bars})
    payload={'source':'Snowyowl MSMP 日_K','asof':source['asof'],'schema':'date,open,high,low,close','price_basis':'第一個有效收盤=100，同一比例換算OHLC；非原始股價','mode':'local_market','market_count':len(rows),'rows':rows}
    p=ROOT.parent/'.local/pattern-data.json'
    p.write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
    ids={r['symbol'] for r in json.loads((ROOT/'demo-data.json').read_text(encoding='utf-8'))['rows']}
    ids.update(('3707','7921'))  # Two explicit post-selected W examples, as of 2026-10-02.
    public={**payload,'mode':'teaching_sample','sample_selection':'原16檔加3707、7921；2026-10-02事後挑選的輪廓案例，非無偏策略評估。','rows':[r for r in rows if r['symbol'] in ids]}
    # Retain enough daily history for 120 completed weekly or 24 monthly bars.
    (ROOT/'pattern-demo.json').write_text(json.dumps(public,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps({'asof':source['asof'],'local_rows':len(rows),'public_rows':len(public['rows']),'daily_bars_max':max(len(r['bars']) for r in rows)},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--env',required=True);build(p.parse_args().env)
