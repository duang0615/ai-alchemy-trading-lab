const test=require('node:test'),assert=require('node:assert/strict');require('./pattern-engine.js');const P=globalThis.PatternEngine;
const bar=(date,o,h,l,c)=>[date,o,h,l,c];
const history=[105,104,103,102,101].map((c,i)=>bar(`2026-09-${21+i}`,c,c+1,c-1,c));
test('hammer requires prior decline and long lower shadow',()=>{
 const h=bar('2026-09-28',100,101.1,95,101);assert(P.candles([...history,h]).matches.includes('hammer'));
 assert(!P.candles([h]).matches.includes('hammer'));
 assert(!P.candles([...history,bar('2026-09-28',100,105,99,101)]).matches.includes('hammer'));
});
test('four equal does not masquerade as doji or long body',()=>{const m=P.candles([bar('2026-09-28',100,100,100,100)]).matches;assert(m.includes('four_equal'));assert(!m.includes('doji'));assert(!m.includes('long_red'));});
test('body engulfing differs from full range outside bar',()=>{const m=P.candles([bar('2026-09-28',105,110,95,100),bar('2026-09-29',99,108,97,106)]).matches;assert(m.includes('bull_engulf'));assert(!m.includes('outside'));});
test('missing OHLC and missing intervening pattern bars cannot pass',()=>{assert(P.candles([bar('2026-09-28',null,105,95,101)]).unknown);assert(!P.candles([bar('2026-09-28',105,106,95,96),bar('2026-09-29',null,102,98,100),bar('2026-09-30',96,106,95,105)]).matches.includes('morning'));});
test('rising three methods needs five bars and contained correction',()=>{
 const bs=[[95,108,94,107],[105,106,101,104],[103,104,99,102],[101,103,98,100],[100,111,99,110]].map((b,i)=>bar(`2026-09-${21+i}`,...b));
 assert(P.candles(bs).matches.includes('rising_methods'));assert(!P.candles(bs.slice(-3)).matches.includes('rising_methods'));
 bs[2][2]=120;assert(!P.candles(bs).matches.includes('rising_methods'));
});
test('weekly aggregation excludes unfinished and future bars',()=>{
 const bs=[bar('2026-09-28',100,102,99,101),bar('2026-09-29',101,105,100,104),bar('2026-10-02',104,106,103,105),bar('2026-10-05',105,999,104,998)];
 assert.equal(P.aggregate(bs,'week','2026-10-01').length,0);
 assert.deepEqual(P.aggregate(bs,'week','2026-10-02'),[bar('2026-10-02',100,106,99,105)]);
});
test('monthly aggregation excludes current partial month',()=>{const bs=[bar('2026-09-28',100,102,99,101),bar('2026-09-30',101,106,100,105),bar('2026-10-02',105,107,104,106)];assert.deepEqual(P.aggregate(bs,'month','2026-10-02'),[bar('2026-09-30',100,106,99,105)]);});
test('shape score is scale and level invariant, not direction invariant',()=>{const w=[.9,.1,.7,.1,.9],m=w.map(v=>1-v);assert(Math.abs(P.similarity(w,w)-100)<1e-9);assert(Math.abs(P.similarity(w.map(v=>50+v*200),w)-100)<1e-9);assert(P.similarity(m,w)<50);assert.equal(P.similarity([1,null,3],w),null);});
test('missing and insufficient shape windows remain unknown',()=>{const bs=history;assert.equal(P.score(bs,[0,1,0],60),null);bs[2]=bar('2026-09-23',null,103,101,102);assert.equal(P.score(bs,[0,1,0],5),null);});
test('flat template uses explicit range rule',()=>{const bs=[100,100,100,100,100].map((c,i)=>bar(`2026-09-${21+i}`,c,c+1,c-1,c));assert.equal(P.score(bs,[.5,.5,.5],5),100);assert.equal(P.similarity([1,1,1],[.5,.5,.5]),null);});
test('custom file rejects invalid ranges, constants and nonfinite values',()=>{const p={name:'W底',description:'測試',days:60,threshold:80,cycle:'day',points:[.9,.1,.7,.1,.9]};assert(P.validateCustom(p));for(const v of [{...p,points:[1,1,1,1,1]},{...p,days:999},{...p,threshold:NaN},{...p,cycle:'minute'},{...p,points:[0,.2,Infinity,.3,1]}])assert(!P.validateCustom(v));});
test('wrong candlestick options fail rather than change definitions silently',()=>{assert.throws(()=>P.candles(history,{small:.1,doji:.3}));assert.throws(()=>P.candles(history,{long:NaN}));});
