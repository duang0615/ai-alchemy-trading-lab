"""Build a current snapshot locally; public demo is a tiny derived teaching sample."""
import argparse,contextlib,io,json,sys,datetime
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from owl_login import login
from rules import numeric_dates,daily_rules,eps_rule,revenue_rule,margin_rule
ROOT=Path(__file__).resolve().parent
DEMO=['2330','2317','6533','3037','3443','2357','2033','1709','5013','3701','6708','2454','2308','2382','2603','2881']
def finite(value):
    try:return float(value) if pd.notna(value) and np.isfinite(value) else None
    except (TypeError,ValueError):return None

def build(env,demo=False,output=None):
    today=datetime.date.today();errors={};cache={}
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):api=login(env)
    def get(table,field,daily=False):
        key=(table,field)
        if key in cache:return cache[key]
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):d=api.MSMP.get(table,field).copy()
        d.columns=d.columns.astype(str)
        if daily:d=numeric_dates(d,today)
        cache[key]=d;return d
    c=get('日_K','Close',True); asof=c.index[-1]
    info=api.MSMP.INFO.copy();info.columns=info.columns.astype(str)
    # Derive names from INFO only; its metadata date can be later than the prices.
    codecol=next((x for x in info.columns if x in ('代號','股票代號','symbol','Symbol','stock_id')),None)
    if codecol:info=info.set_index(codecol)
    info.index=info.index.astype(str)
    namecol=next((x for x in info.columns if x in ('名稱','股票名稱','name','Name','商品名稱')),None)
    if namecol is None:raise ValueError('INFO name column not identified: '+str(info.columns.tolist()))
    universe=[s for s in c.columns if len(s)==4 and s.isdigit() and not s.startswith('0') and pd.notna(c[s].iloc[-1]) and c[s].iloc[-1]>0]
    if 'ETF' in info:universe=[s for s in universe if s in info.index and info.loc[s,'ETF']==0]
    c=c[universe];h=get('日_K','High',True).reindex_like(c);l=get('日_K','Low',True).reindex_like(c);v=get('日_K','Volume',True).reindex_like(c)
    def aligned(table,field):return get(table,field,True).reindex_like(c)
    foreign=aligned('日_三大法人','外資買賣超張數');trust=aligned('日_三大法人','投信買賣超張數')
    idx=get('TSE','Close',True).iloc[:,0]
    masks,metrics,trend=daily_rules(c,h,l,v,foreign,trust,idx)
    pe=aligned('日_指標','本益比').iloc[-1]
    eps=get('季財報_損益表_千','eps').reindex(columns=universe)
    masks['eps']=eps_rule(eps,pe)
    rev=get('月_營收','金額_千').reindex(columns=universe)
    # An all-empty placeholder month is not an available monthly report.
    rev=rev.dropna(how='all');masks['revenue'],metrics['revenue3_yoy']=revenue_rule(rev)
    annual=[get('季財報_損益表_千',field).reindex(columns=universe) for field in ('營業收入','營業毛利','營業淨利','稅後純益')]
    masks['margins']=margin_rule(*annual,today.year)
    holders=[]
    for bin_ in ('400到600','600到800','800到1000','1000張以上'):
        field='張數'+bin_+'_人數' if bin_!='1000張以上' else '張數1000張以上_人數'
        holders.append(get('週_大小股東持股',field,True).reindex(columns=universe))
    large=sum(holders)
    large_increase=large.tail(5).notna().all() & large.diff().tail(4).gt(0).all()
    masks['holders']=large_increase & v.gt(v.rolling(20,min_periods=20).mean()).rolling(5,min_periods=5).sum().iloc[-1].eq(5)&trend.iloc[-1]
    rows=[]
    extra={
      '主力買賣超':('日_三大法人','主力買賣超張數',True), '三大法人':('日_三大法人','三大法人買賣超_張數',True),
      '自營':('日_三大法人','自營自行買賣超_張數',True),'自營避險':('日_三大法人','自營避險買賣超_張數',True),'八大官股':('日_三大法人','八大行庫_買賣超張數',True),
      '家數差':('其他_籌碼集中','家數差_1日',True),'籌碼集中度':('其他_籌碼集中','籌碼集中度_1日',True),
      '融資增減':('日_融資券','融資增減_張',True),'融券增減':('日_融資券','融券增減_張',True),'借券賣出餘額':('日_融資券','借券賣出餘額_張',True),
      '當沖量':('日_K','當沖量',True),'ROE季':('季財報_財務指標','ROE_稅後權益報酬率',False),'ROA季':('季財報_財務指標','ROA_稅後資產報酬率',False),
      '負債比率':('季財報_財務指標','負債比率',False),'流動比率':('季財報_財務指標','流動比率',False),'Beta一年':('日_CAPM','Beta一年',True),
      '股價淨值比':('日_指標','股價淨值比',True),'年度殖利率':('季股利資訊','年殖利率',False),
      '月營收年增':('月_營收','YoY',False),'月營收月增':('月_營收','MoM',False)}
    for label in ('營業收入','營業毛利','營業費用','營業淨利','營業外收入及支出','稅前純益','所得稅費用','稅後純益','eps'):extra[label]=('季財報_損益表_千',label,False)
    for label in ('資產','資產_流動','現金','庫存','總應收帳款','資產_非流動','資產_無形','固定資產','負債總額','負債_流動','負債_非流動','股東權益_總額'):extra[label]=('季財報_資產負債表_千',label,False)
    for label in ('營運現金流','投資現金流','籌資現金流','資本支出','自由現金流','淨現金流_千'):extra[label]=('季財報_現金流表_千',label,False)
    latest={};periods={}
    for label,(tab,field,daily) in extra.items():
        try:
            df=get(tab,field,daily).reindex(columns=universe).dropna(how='all')
            latest[label]=df.iloc[-1];periods[label]=str(df.index[-1])
        except Exception as e:errors[label]=type(e).__name__;latest[label]=pd.Series(dtype=float)
    weekly=c.resample('W-FRI').last()
    if weekly.index[-1]>asof:weekly=weekly.iloc[:-1]
    largepct=sum(get('週_大小股東持股',f,True).reindex(columns=universe) for f in ('張數400到600_比例','張數600到800_比例','張數800到1000_比例','張數1000張以上_比例'))
    selected=[s for s in DEMO if s in universe] if demo else universe
    for s in selected:
        row={'symbol':s,'name':str(info.loc[s,namecol]) if s in info.index else s,'price':finite(c[s].iloc[-1]),'change':finite((c[s].iloc[-1]/c[s].iloc[-2]-1)*100),'volume':finite(v[s].iloc[-1]),'pe':finite(pe.get(s))}
        for n in (5,10,20,30,60):row['ma'+str(n)]=finite(c[s].tail(n).mean()) if c[s].tail(n).count()==n else None
        for n in (5,10,20):row['wma'+str(n)]=finite(weekly[s].tail(n).mean()) if weekly[s].tail(n).count()==n else None
        row.update({k:finite(data.get(s)) for k,data in metrics.items()});row.update({k:finite(data.get(s)) for k,data in latest.items()})
        row['外資']=finite(foreign[s].iloc[-1]);row['投信']=finite(trust[s].iloc[-1]);row['大戶人數']=finite(large[s].iloc[-1]);row['大戶比例']=finite(largepct[s].iloc[-1])
        row['passes']=[k for k,mask in masks.items() if bool(mask.get(s,False))]
        # Public chart is derived normalized closing-price trend. No wholesale raw history.
        history=c[s].tail(60 if demo else 120).dropna();base=history.iloc[0]
        row['chart']=[{'date':str(d.date()),'value':finite(value/base*100)} for d,value in history.items()]
        row['chart_unit']='第一日收盤=100'
        rows.append(row)
    # Demo ranking must use demo universe rather than carry full-market Top150.
    if demo:
        ranking=sorted(rows,key=lambda r:r['gain3'] if r['gain3'] is not None else -float('inf'),reverse=True)
        for r in rows:
            r['passes']=[k for k in r['passes'] if k!='gain']
            if r in ranking[:min(150,len(rows))] and r['gain3'] is not None:r['passes'].append('gain')
    payload={'source':'Snowyowl MSMP','asof':str(asof.date()),'built_at':datetime.datetime.now().isoformat(timespec='seconds'),'mode':'teaching_sample' if demo else 'local_market','universe_count':len(rows),'market_count':len(universe),'daily_volume_unit':'張','fundamental_periods':periods,'errors':errors,'rows':rows,'warnings':['目前存續股票清單，非歷史時點成分股。','營收／財報標示會計期間，沒有逐筆公告時間，不能直接當歷史回測輸入。','條件依本專案明確規格計算，資料不足不補零。','候選名單尚未包含買進、賣出、部位與成交條件。']}
    target=Path(output) if output else ROOT.parent/'.local'/'stock-picker-data.json'
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps({'asof':payload['asof'],'rows':len(rows),'errors':errors,'output':str(target)},ensure_ascii=False))
    return payload
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--env',required=True);p.add_argument('--demo',action='store_true');p.add_argument('--output');a=p.parse_args();build(a.env,a.demo,a.output)
