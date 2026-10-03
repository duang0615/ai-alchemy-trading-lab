/* Single calculation module used by browser and Node tests. No stock APIs here. */
(function(root){'use strict';
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const valid=b=>Array.isArray(b)&&b.length===5&&b.slice(1).every(finite)&&b[3]>0&&b[2]>=Math.max(b[1],b[4])&&b[3]<=Math.min(b[1],b[4]);
const parts=b=>{const [d,o,h,l,c]=b,range=h-l,body=Math.abs(c-o);return {o,h,l,c,range,body,ratio:range>0?body/range:0,upper:h-Math.max(o,c),lower:Math.min(o,c)-l,bull:c>o,bear:c<o};};
function candles(bars,opt={}){
 const small=opt.small??.3,doji=opt.doji??.1,shadow=opt.shadow??2,long=opt.long??.65;
 if(![small,doji,shadow,long].every(finite)||small<=0||small>=1||doji<0||doji>=small||shadow<1||long<=small||long>1)throw Error('K線門檻不合法');
 const n=bars.length,now=bars[n-1];if(!valid(now))return {matches:[],unknown:true};
 const a=parts(now),p=valid(bars[n-2])?parts(bars[n-2]):null,q=valid(bars[n-3])?parts(bars[n-3]):null;
 const older=bars.slice(-6,-1);const trendKnown=older.length===5&&older.every(valid);
 const down=trendKnown&&older[4][4]<older[0][4],up=trendKnown&&older[4][4]>older[0][4];
 const hits=[];const add=(id,test)=>{if(test)hits.push(id);};
 const short=a.range>0&&a.ratio<=small&&a.ratio>doji;
 const hammer=short&&a.lower>=shadow*a.body&&a.upper<=.1*a.range;
 const inverted=short&&a.upper>=shadow*a.body&&a.lower<=.1*a.range;
 add('hammer',hammer&&down);add('shooting',inverted&&up);add('inverted',inverted&&down);
 add('doji',a.range>0&&a.ratio<=doji);
 add('gravestone',a.range>0&&a.ratio<=doji&&a.lower<=.05*a.range&&a.upper>=.8*a.range);
 add('cross',a.range>0&&a.ratio<=.05&&a.upper>=.3*a.range&&a.lower>=.3*a.range);
 add('long_red',a.bull&&a.ratio>=long&&a.upper<=.2*a.range&&a.lower<=.2*a.range);
 add('long_black',a.bear&&a.ratio>=long&&a.upper<=.2*a.range&&a.lower<=.2*a.range);
 add('marubozu',a.range>0&&a.upper<=.05*a.range&&a.lower<=.05*a.range);
 add('lower_shadow',a.range>0&&a.lower>=.6*a.range&&a.lower>=shadow*a.body);
 add('upper_shadow',a.range>0&&a.upper>=.6*a.range&&a.upper>=shadow*a.body);
 add('four_equal',a.range===0&&a.body===0);
 if(p){
  const inside=Math.max(a.o,a.c)<Math.max(p.o,p.c)&&Math.min(a.o,a.c)>Math.min(p.o,p.c);
  add('bull_engulf',p.bear&&a.bull&&a.o<=p.c&&a.c>=p.o&&a.body>p.body);
  add('bear_engulf',p.bull&&a.bear&&a.o>=p.c&&a.c<=p.o&&a.body>p.body);
  add('piercing',p.bear&&a.bull&&a.o<p.c&&a.c>(p.o+p.c)/2&&a.c<p.o);
  add('dark_cloud',p.bull&&a.bear&&a.o>p.c&&a.c<(p.o+p.c)/2&&a.c>p.o);
  add('harami',inside&&p.ratio>=long&&a.ratio<=small);
  add('harami_doji',inside&&p.ratio>=long&&a.ratio<=doji&&a.range>0);
  add('outside',a.h>p.h&&a.l<p.l);
  add('counter',((p.bear&&a.bull)||(p.bull&&a.bear))&&a.ratio>=long&&p.ratio>=long&&Math.abs(a.c-p.c)/p.c<=.005);
  add('belt',a.ratio>=long&&((a.bull&&a.lower<=.05*a.range)||(a.bear&&a.upper<=.05*a.range)));
 }
 if(p&&q){
  add('morning',q.bear&&q.ratio>=long&&p.ratio<=small&&a.bull&&a.ratio>=long&&a.c>(q.o+q.c)/2&&Math.max(p.o,p.c)<(q.o+q.c)/2);
  add('evening',q.bull&&q.ratio>=long&&p.ratio<=small&&a.bear&&a.ratio>=long&&a.c<(q.o+q.c)/2&&Math.min(p.o,p.c)>(q.o+q.c)/2);
  const three=[q,p,a],bulls=three.every(x=>x.bull&&x.ratio>=.5&&x.upper<=.25*x.range),bears=three.every(x=>x.bear&&x.ratio>=.5&&x.lower<=.25*x.range);
  add('soldiers',bulls&&q.c<p.c&&p.c<a.c&&p.o>q.o&&p.o<q.c&&a.o>p.o&&a.o<p.c);
  add('crows',bears&&q.c>p.c&&p.c>a.c&&p.o<q.o&&p.o>q.c&&a.o<p.o&&a.o>p.c);
  const pin=Math.max(p.o,p.c)<Math.max(q.o,q.c)&&Math.min(p.o,p.c)>Math.min(q.o,q.c);
  add('inside_up',q.bear&&pin&&p.bull&&a.bull&&a.c>q.o);
  add('inside_down',q.bull&&pin&&p.bear&&a.bear&&a.c<q.o);
 }
 const five=bars.slice(-5);
 if(five.length===5&&five.every(valid)){
  const [first,...rest]=five.map(parts),last=rest.at(-1),mid=rest.slice(0,3);
  const within=mid.every(x=>x.h<=first.h&&x.l>=first.l&&x.ratio<=small);
  add('rising_methods',first.bull&&first.ratio>=long&&within&&last.bull&&last.ratio>=long&&last.c>first.c);
  add('falling_methods',first.bear&&first.ratio>=long&&within&&last.bear&&last.ratio>=long&&last.c<first.c);
 }
 return {matches:hits,unknown:false,trendKnown};
}
function aggregate(bars,cycle,asof){
 const sorted=bars.filter(b=>b[0]<=asof).slice().sort((a,b)=>a[0].localeCompare(b[0]));
 if(cycle==='day')return sorted;
 if(!['week','month'].includes(cycle))throw Error('不支援的K線週期');
 const groups=new Map();
 for(const b of sorted){let d=new Date(b[0]+'T00:00:00Z'),end;
  if(cycle==='week'){let day=d.getUTCDay();d.setUTCDate(d.getUTCDate()+((5-day+7)%7));end=d.toISOString().slice(0,10);}
  else end=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).toISOString().slice(0,10);
  if(end>asof)continue;let list=groups.get(end)||[];list.push(b);groups.set(end,list);
 }
 return [...groups].map(([date,bs])=>bs.every(valid)?[date,bs[0][1],Math.max(...bs.map(b=>b[2])),Math.min(...bs.map(b=>b[3])),bs.at(-1)[4]]:[date,null,null,null,null]);
}
function normalize(values){if(!Array.isArray(values)||values.length<2||!values.every(finite))return null;const lo=Math.min(...values),hi=Math.max(...values);if(hi===lo)return null;return values.map(v=>(v-lo)/(hi-lo));}
function resample(values,n=60){if(!Array.isArray(values)||values.length<2||!values.every(finite))return null;return Array.from({length:n},(_,i)=>{const x=i*(values.length-1)/(n-1),j=Math.floor(x),k=Math.min(j+1,values.length-1);return values[j]+(values[k]-values[j])*(x-j);});}
function similarity(values,template){const a=normalize(resample(values)),b=normalize(resample(template));if(!a||!b)return null;const mse=a.reduce((s,v,i)=>s+(v-b[i])**2,0)/a.length;return Math.max(0,100*(1-Math.sqrt(mse)));}
function score(bars,template,length){if(!Number.isInteger(length)||length<5||length>120)throw Error('K棒數須介於5至120');if(bars.length<length)return null;const recent=bars.slice(-length);if(!recent.every(valid))return null;const values=recent.map(b=>b[4]);if(template.every(v=>v===template[0])){const mean=values.reduce((a,b)=>a+b,0)/values.length;return Math.max(0,100*(1-(Math.max(...values)-Math.min(...values))/(mean*.05)));}return similarity(values,template);}
function validateCustom(p){return !!p&&typeof p.name==='string'&&p.name.trim().length>0&&p.name.length<=60&&typeof p.description==='string'&&p.description.length<=500&&Number.isInteger(p.days)&&p.days>=5&&p.days<=120&&finite(p.threshold)&&p.threshold>=50&&p.threshold<=100&&['day','week','month'].includes(p.cycle)&&Array.isArray(p.points)&&p.points.length>=5&&p.points.length<=600&&p.points.every(v=>finite(v)&&v>=0&&v<=1)&&Math.max(...p.points)-Math.min(...p.points)>.01;}
const api={valid,parts,candles,aggregate,normalize,resample,similarity,score,validateCustom};if(typeof module!=='undefined')module.exports=api;root.PatternEngine=api;
})(typeof window!=='undefined'?window:globalThis);
