"""Pure screening rules. NaN is unknown, never a pass. Daily volumes in lots."""
import pandas as pd

def numeric_dates(frame, cutoff):
    out=frame.copy(); out.index=pd.to_datetime(out.index)
    if out.index.has_duplicates: raise ValueError('duplicate dates')
    return out.sort_index().loc[lambda d:d.index<=pd.Timestamp(cutoff)]

def trend_signal(c):
    mas=[c.rolling(n,min_periods=n).mean() for n in (5,10,20,30,60)]
    cond=mas[0].notna()
    for a,b in zip(mas,mas[1:]): cond &= a>b
    return cond.rolling(3,min_periods=3).sum().eq(3)

def daily_rules(c,h,l,v,f,t,index_close,top_n=150,volume_min=2000,volume_multiple=5):
    avg20=v.rolling(20,min_periods=20).mean()
    growth3=(c/c.shift(3)-1)*100
    gain=growth3.iloc[-1].rank(method='first',ascending=False)<=top_n
    trend=trend_signal(c)
    new_high=c.gt(c.shift(1).rolling(59,min_periods=59).max()).rolling(5,min_periods=5).sum().ge(1)
    prior_volume=v.shift(1).rolling(20,min_periods=20).mean()
    volume=prior_volume.gt(0)&v.ge(prior_volume*volume_multiple)&v.ge(volume_min)
    foreign=f.ge(500).rolling(5,min_periods=5).sum().eq(5)
    trust=t.ge(200).rolling(3,min_periods=3).sum().eq(3)&growth3.ge(5)
    low20=l.rolling(20,min_periods=20).min();high20=h.rolling(20,min_periods=20).max()
    high60=h.rolling(60,min_periods=60).max()
    box=(high20-low20).div(low20).lt(.1)&v.gt(avg20).rolling(3,min_periods=3).sum().eq(3)&c.gt(high60*.95)&c.lt(high60*1.05)
    idx=index_close.reindex(c.index);rel=(c/c.shift(5)-1).sub(idx/idx.shift(5)-1,axis=0)*100
    relative=rel.ge(10)&v.gt(v.rolling(5,min_periods=5).mean()).rolling(10,min_periods=10).sum().ge(5)
    masks={'gain':gain,'trend':trend.iloc[-1],'high':new_high.iloc[-1],'volume':volume.iloc[-1],'foreign':foreign.iloc[-1],'trust':trust.iloc[-1],'box':box.iloc[-1],'relative':relative.iloc[-1]}
    metrics={'gain3':growth3.iloc[-1],'gain5':(c/c.shift(5)-1).iloc[-1]*100,'relative5':rel.iloc[-1], 'volume_ratio':v.iloc[-1]/v.shift(1).rolling(20,min_periods=20).mean().iloc[-1], 'box_range':(high20-low20).div(low20).iloc[-1]*100}
    return masks,metrics,trend

def eps_rule(eps,pe):
    totals=eps.rolling(4,min_periods=4).sum()
    enough=totals.tail(20).notna().sum().eq(20)
    return enough & totals.iloc[-1].gt(totals.iloc[-20:-1].max()) & pe.gt(0) & pe.lt(20)

def revenue_rule(rev):
    # preserve missing latest months; do not forward-fill an unreported month
    summed=rev.rolling(3,min_periods=3).sum()
    yoy=(summed/summed.shift(12)-1)*100
    enough=rev.tail(60).notna().sum().eq(60)
    mask=enough & yoy.iloc[-1].gt(10) & rev.iloc[-1].gt(rev.iloc[-60:-1].max())
    return mask,yoy.iloc[-1]

def margin_rule(revenue,gross,operating,net,current_year):
    annual=[]
    for data in (revenue,gross,operating,net):
        df=data.copy();df.index=pd.Index([int(str(i)[:4]) for i in df.index])
        df=df.loc[df.index<current_year]
        counts=df.groupby(level=0).count();sums=df.groupby(level=0).sum(min_count=4)
        annual.append(sums.where(counts.eq(4)).tail(4))
    result=pd.Series(True,index=revenue.columns)
    for values in annual[1:]:
        rate=values/annual[0].where(annual[0].gt(0))
        result &= rate.tail(4).notna().sum().eq(4)&rate.diff().tail(3).gt(0).all()
    return result
