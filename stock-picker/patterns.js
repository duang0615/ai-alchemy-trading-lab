'use strict';
const P=window.PatternEngine,$p=s=>document.querySelector(s),safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const CYCLES={day:'日線',week:'週線',month:'月線'};
let catalog,market,mode=new URLSearchParams(location.search).get('mode')||'candles',group=1,chosen=new Set(),custom=[],trash=null;
let candidates=[],visibleRows=[],lastSpec=null,scanId=0,chartHandle=null,chartObserver=null,editingId=null,drawPoints=[],drawIndex=0,drawing=false;
const favorites=new Set(JSON.parse(localStorage.getItem('picker-favorites')||'[]')),cycleCache=new Map();
try{custom=JSON.parse(localStorage.getItem('alchemy-custom-patterns')||'[]').filter(P.validateCustom);}catch{custom=[];}
function persist(){try{localStorage.setItem('alchemy-custom-patterns',JSON.stringify(custom));return true;}catch{$p('#pattern-note-status').textContent='瀏覽器儲存空間不足，請先匯出型態JSON。';return false;}}
function num(v,digits=2){return typeof v==='number'?v.toLocaleString('zh-TW',{maximumFractionDigits:digits}):'資料不足';}
function allPatterns(){return mode==='candles'?catalog.candles:mode==='shapes'?catalog.shapes:custom;}
function linePreview(values){const n=P.normalize(values)||values.map(()=>.5);return `<svg class="pattern-preview" viewBox="0 0 300 110" role="img" aria-label="走勢輪廓示意"><path d="M10 95H290" stroke="#344054"/><polyline points="${n.map((v,i)=>`${10+i*280/(n.length-1)},${95-v*80}`).join(' ')}" fill="none" stroke="#78a7ff" stroke-width="3"/><text x="10" y="15" fill="#8d9bb0" font-size="11">輪廓示意</text></svg>`;}
function candlePreview(p){
 const samples={hammer:[[103,104,94,104]],shooting:[[101,111,100,102]],doji:[[100,105,95,100.4]],gravestone:[[100,110,99.8,100.3]],inverted:[[100,110,99.8,101]],cross:[[100,106,94,100.1]],long_red:[[95,106,94,105]],long_black:[[105,106,94,95]],marubozu:[[95,105,95,105]],lower_shadow:[[102,105,90,104]],upper_shadow:[[100,115,99,102]],four_equal:[[100,100,100,100]],bull_engulf:[[105,106,97,98],[97,107,96,106]],bear_engulf:[[98,106,97,105],[106,107,96,97]],piercing:[[105,106,94,95],[94,102,93,101]],dark_cloud:[[95,106,94,105],[106,107,98,99]],harami:[[95,106,94,105],[101,104,99,100]],harami_doji:[[95,106,94,105],[101,104,99,101.2]],outside:[[99,104,98,102],[104,108,94,97]],counter:[[106,107,97,98],[93,99,92,98]],belt:[[105,106,94,95],[95,105,95,104]],morning:[[110,111,99,100],[99,100,97,98],[99,108,98,107]],evening:[[100,111,99,110],[111,113,110,112],[111,112,103,104]],soldiers:[[95,102,94,101],[99,106,98,105],[103,110,102,109]],crows:[[110,111,103,104],[106,107,99,100],[102,103,95,96]],inside_up:[[110,111,99,100],[102,107,101,106],[106,114,105,113]],inside_down:[[100,111,99,110],[108,109,103,104],[104,105,96,97]],rising_methods:[[95,108,94,107],[105,106,101,104],[103,104,99,102],[101,103,98,100],[100,111,99,110]],falling_methods:[[107,108,94,95],[97,101,96,98],[99,103,98,100],[101,105,100,102],[102,103,90,91]]};
 const bars=samples[p.id],lo=Math.min(...bars.map(x=>x[2]))-2,hi=Math.max(...bars.map(x=>x[1]))+2,y=v=>95-(v-lo)/(hi-lo)*75,w=24;
 return `<svg class="pattern-preview" viewBox="0 0 300 110" role="img" aria-label="${safe(p.name)}示意"><text x="10" y="15" fill="#8d9bb0" font-size="11">K線示意</text>${bars.map(([o,h,l,c],i)=>{const x=150+(i-(bars.length-1)/2)*44,col=c>o?'#ef6767':c<o?'#48bc93':'#b8c4d4';return `<path d="M${x} ${y(h)}V${y(l)}" stroke="${col}" stroke-width="2"/><rect x="${x-w/2}" y="${Math.min(y(o),y(c))}" width="${w}" height="${Math.max(2,Math.abs(y(o)-y(c)))}" fill="${col}"/>`;}).join('')}</svg>`;
}
function renderCards(){
 const q=$p('#pattern-search').value.trim();let list=allPatterns().filter(p=>p.name.includes(q));if(mode==='candles')list=list.filter(p=>group===3?p.bars>=3:p.bars===group);
 $p('#pattern-selected').textContent=`已選${chosen.size}個 ／ ${list.length}個型態`;
 $p('#pattern-cards').innerHTML=list.map(p=>`<article class="strategy"><div class="card-title"><input type="checkbox" data-pick="${safe(p.id)}" aria-label="選擇 ${safe(p.name)}" ${chosen.has(p.id)?'checked':''}><h3>${safe(p.name)}</h3></div>${mode==='candles'?candlePreview(p):linePreview(p.points)}<p class="description">${mode==='candles'?`${p.bars}根K線`:`${mode==='custom'?`${CYCLES[p.cycle]} ${p.days}根 / ≥${p.threshold}%`:'收盤輪廓比對'}`}</p><details><summary>本版判定規格</summary><p>${safe(p.rule||p.description||'自訂輪廓，採重採樣與RMSE比對。')}</p></details><div class="pattern-card-actions"><button data-run-pattern="${safe(p.id)}">執行 ${safe(p.name)}</button>${mode==='custom'?`<button data-edit="${safe(p.id)}">編輯</button><button data-delete="${safe(p.id)}">刪除</button>`:''}</div></article>`).join('')||'<p class="empty">還沒有符合的型態。自訂頁可按「新增型態」，畫一條自己的走勢。</p>';
 if(trash&&mode==='custom')$p('#pattern-cards').insertAdjacentHTML('beforeend','<button id="restore-pattern">復原剛才刪除的型態</button>');
}
function setMode(m){mode=['candles','shapes','custom'].includes(m)?m:'candles';chosen.clear();
 document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-selected',b.dataset.mode===mode));
 $p('#page-title').textContent=mode==='candles'?'K線型態選股':mode==='shapes'?'走勢型態選股':'畫出自己的選股型態';
 for(const id of ['length-label','threshold-label'])$p('#'+id).hidden=mode!=='shapes';
 for(const id of ['recent-label','candle-params','candle-groups'])$p('#'+id).hidden=mode!=='candles';
 for(const id of ['add-pattern','export-patterns'])$p('#'+id).hidden=mode!=='custom';$p('.import-button').hidden=mode!=='custom';
 $p('#cycle').disabled=mode==='custom';
 $p('#method-note').textContent=mode==='candles'?'使用開高低收依本版規格判定。多根分類中，上升／下降三法需要5根K線。組合AND要求同一根訊號日符合全部型態。':mode==='shapes'?'輪廓相似度 = 100 × max(0, 1 − RMSE)。數值代表收盤線相似程度；一字形底另採振幅規則，並不驗證突破或成交量。':'型態存於此瀏覽器。匯出JSON可備份、給同學或交給AI；每個型態保存自己的K棒數、週期與門檻。';
 renderCards();
}
function barsFor(row,cycle){const key=row.symbol+'|'+cycle;if(!cycleCache.has(key))cycleCache.set(key,P.aggregate(row.bars,cycle,market.asof));return cycleCache.get(key);}
function candleOpts(){const opt={small:Number($p('#small-body').value)/100,doji:Number($p('#doji-body').value)/100,long:Number($p('#long-body').value)/100,shadow:Number($p('#shadow-ratio').value)};P.candles([['2000-01-01',1,2,1,2]],opt);return opt;}
async function runPatterns(ids){
 let patterns=allPatterns().filter(p=>ids.includes(p.id));if(!patterns.length){$p('#pattern-selected').textContent='請先勾選型態';return;}
 let spec;
 try{spec={mode,names:patterns.map(p=>p.name),ids:patterns.map(p=>p.id),combine:$p('#pattern-combine').value,cycle:$p('#cycle').value,days:Number($p('#length').value),threshold:Number($p('#threshold').value),recent:Number($p('#recent').value),minVolume:Number($p('#pattern-min-volume').value),options:mode==='candles'?candleOpts():null,asof:market.asof,universe:market.rows.length};
 if(!Number.isFinite(spec.minVolume)||spec.minVolume<0)throw Error('最低量須為非負數');
 if(mode==='shapes'&&(!Number.isInteger(spec.days)||spec.days<5||spec.days>120||!Number.isFinite(spec.threshold)||spec.threshold<50||spec.threshold>100))throw Error('K棒數5～120，相似門檻50～100');
 }catch(e){$p('#pattern-selected').textContent=e.message;return;}
 const token=++scanId;lastSpec=spec;candidates=[];$p('#pattern-stock-search').value='';$p('#pattern-rows').innerHTML='';
 $p('#pattern-results-title').textContent=patterns.map(p=>p.name).join(spec.combine==='and'?' ＆ ':' ／ ');
 $p('#result-spec').textContent=mode==='candles'?`${CYCLES[spec.cycle]}，最近${spec.recent}根；小實體≤${spec.options.small*100}%，十字≤${spec.options.doji*100}%，長實體≥${spec.options.long*100}%，影線倍數${spec.options.shadow}。`:mode==='shapes'?`${CYCLES[spec.cycle]}，最近${spec.days}根，比對門檻${spec.threshold}%。`:'各型態依自己的週期、K棒數與門檻計算。';
 $p('#result-spec').textContent+=` 最新日最低量${spec.minVolume}張；${spec.combine.toUpperCase()}。`;if(!$p('#pattern-results').open)$p('#pattern-results').showModal();
 $p('#pattern-chart-title').textContent='點選股票查看K線';$p('#pattern-chart-note').textContent='';if(chartHandle){chartHandle.remove();chartHandle=null;}if(chartObserver){chartObserver.disconnect();chartObserver=null;}$p('#pattern-chart-readout').textContent='';
 let missing=0,filtered=0;
 for(let offset=0;offset<market.rows.length;offset+=120){
  if(token!==scanId)return;
  for(const row of market.rows.slice(offset,offset+120)){
   if(spec.minVolume>0&&(row.volume==null||row.volume<spec.minVolume)){filtered++;continue;}
   let matches=[],value=null,date=null,unknown=false;
   if(spec.mode==='candles'){
    const bs=barsFor(row,spec.cycle);let assessed=false;
    for(let lag=0;lag<spec.recent&&bs.length-lag>0;lag++){
     const tail=bs.slice(0,bs.length-lag),r=P.candles(tail,spec.options);
     const need=Math.max(...patterns.map(p=>['hammer','shooting','inverted'].includes(p.id)?6:p.bars));
     if(tail.length<need||!tail.slice(-need).every(P.valid)){unknown=true;continue;}assessed=true;
     const yes=patterns.filter(p=>r.matches.includes(p.id));const hit=spec.combine==='and'?yes.length===patterns.length:yes.length>0;
     if(hit){matches=yes.map(p=>p.name);value=100;date=tail.at(-1)[0];break;}
    }
    if(!assessed)unknown=true;else if(!matches.length)unknown=false;
   }else{
    const scores=patterns.map(p=>{const cycle=spec.mode==='custom'?p.cycle:spec.cycle,length=spec.mode==='custom'?p.days:spec.days,threshold=spec.mode==='custom'?p.threshold:spec.threshold;const bars=barsFor(row,cycle),score=P.score(bars,p.points,length);return {p,score,threshold,cycle,length,date:bars.at(-1)?.[0]};});
    unknown=scores.some(s=>s.score===null);const yes=scores.filter(s=>s.score!=null&&s.score+1e-9>=s.threshold);
    const hit=spec.combine==='and'?yes.length===patterns.length:yes.length>0;
    if(hit){matches=yes.map(s=>s.p.name);value=spec.combine==='and'?Math.min(...yes.map(s=>s.score)):Math.max(...yes.map(s=>s.score));const best=yes.reduce((a,b)=>a.score>b.score?a:b);date=best.date;candidates.push({row,score:value,date,matches,cycle:best.cycle,template:best.p.points,days:best.length});}
   }
   if(unknown)missing++;
   if(matches.length&&spec.mode==='candles')candidates.push({row,score:value,date,matches,cycle:spec.cycle,template:null,days:Math.max(20,spec.recent)});
  }
  $p('#scan-status').textContent=`掃描中 ${Math.min(offset+120,market.rows.length)}／${market.rows.length}檔…`;await new Promise(resolve=>requestAnimationFrame(resolve));
 }
 if(token!==scanId)return;candidates.sort((a,b)=>b.score-a.score);$p('#scan-status').textContent=`找到${candidates.length}檔 ／ ${market.rows.length}檔，資料日${market.asof}；${missing}檔有相關資料不足，${filtered}檔未通過最低量。`;renderResults();
 if(candidates.length)showChart(candidates[0]);
}
function renderResults(){const q=$p('#pattern-stock-search').value.trim();visibleRows=candidates.filter(x=>(x.row.symbol+x.row.name).includes(q));$p('#pattern-rows').innerHTML=visibleRows.map(x=>`<tr><td><button data-chart-symbol="${x.row.symbol}">${safe(x.row.name)} ${x.row.symbol}</button><small>${safe(x.matches.join('、'))}</small></td><td>${lastSpec.mode==='candles'?'規則符合':num(x.score)+'%'}</td><td>${safe(x.date)}</td><td>${num(x.row.price)}</td><td>${num(x.row.volume,0)}</td><td><button data-favorite="${x.row.symbol}" aria-label="收藏 ${x.row.symbol}" aria-pressed="${favorites.has(x.row.symbol)}">${favorites.has(x.row.symbol)?'★':'☆'}</button></td></tr>`).join('')||'<tr><td colspan="6">沒有符合的股票。先核對週期、資料範圍與缺值，再決定是否改條件。</td></tr>';}
function showChart(x){
 if(chartHandle)chartHandle.remove();if(chartObserver)chartObserver.disconnect();
 const host=$p('#pattern-stock-chart'),LC=window.LightweightCharts;if(!LC){$p('#pattern-chart-note').textContent='圖表函式庫未載入，請重新整理。';return;}
 chartHandle=LC.createChart(host,{width:host.clientWidth,height:350,layout:{background:{color:'#101721'},textColor:'#aeb8ca'},grid:{vertLines:{color:'#1e293b'},horzLines:{color:'#1e293b'}},handleScroll:{vertTouchDrag:false},timeScale:{timeVisible:false},rightPriceScale:{borderColor:'#344054'}});
 const series=chartHandle.addSeries(LC.CandlestickSeries,{upColor:'#ef6767',downColor:'#48bc93',wickUpColor:'#ef6767',wickDownColor:'#48bc93',borderVisible:false});
 const bs=barsFor(x.row,x.cycle).slice(-Math.max(x.days,60));series.setData(bs.map(b=>P.valid(b)?{time:b[0],open:b[1],high:b[2],low:b[3],close:b[4]}:{time:b[0]}));LC.createSeriesMarkers(series,[{time:x.date,position:'belowBar',color:'#f4cc65',shape:'circle',text:'判定日'}]);
 if(x.template&&P.normalize(x.template)){const windowBars=bs.slice(-x.days),close=windowBars.map(b=>b[4]),min=Math.min(...close),range=Math.max(...close)-min;const points=P.normalize(P.resample(x.template,windowBars.length));const overlay=chartHandle.addSeries(LC.LineSeries,{color:'#f4cc65',lineWidth:2,priceLineVisible:false,lastValueVisible:false});overlay.setData(points.map((v,i)=>({time:windowBars[i][0],value:min+v*range})));}
 chartHandle.timeScale().fitContent();$p('#pattern-chart-title').textContent=`${x.row.name} ${x.row.symbol}｜${CYCLES[x.cycle]}`;
 $p('#pattern-chart-note').textContent=`OHLC依同一基準換算，${market.price_basis}。${x.template?'黃色線：匹配的示意輪廓；':'紅漲綠跌；'}拖曳、縮放或移動游標查看數值。`;
 $p('#pattern-chart-readout').textContent='圖形辨識只提供候選，還需要自己的進出場規則。';
 chartHandle.subscribeCrosshairMove(param=>{const b=param.seriesData.get(series);if(b&&b.open!=null)$p('#pattern-chart-readout').textContent=`${param.time}　開${num(b.open)}　高${num(b.high)}　低${num(b.low)}　收${num(b.close)}`;});
 chartObserver=new ResizeObserver(()=>{if(chartHandle)chartHandle.applyOptions({width:host.clientWidth});});chartObserver.observe($p('#pattern-chart-panel'));
}
function download(name,content,type){const url=URL.createObjectURL(new Blob(['\uFEFF'+content],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function draw(){const canvas=$p('#draw-canvas'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#1e293b';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#354257';for(let i=1;i<6;i++){ctx.beginPath();ctx.moveTo(0,h*i/6);ctx.lineTo(w,h*i/6);ctx.stroke();}if(drawPoints.length){ctx.strokeStyle='#78a7ff';ctx.lineWidth=3;ctx.beginPath();drawPoints.forEach((v,i)=>{let x=20+i*(w-40)/(drawPoints.length-1),y=20+(1-v)*(h-40);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();ctx.fillStyle='#f4cc65';ctx.beginPath();ctx.arc(20+drawIndex*(w-40)/(drawPoints.length-1),20+(1-drawPoints[drawIndex])*(h-40),6,0,Math.PI*2);ctx.fill();}$p('#draw-status').textContent=drawPoints.length?`已繪製${drawPoints.length}個點；目前第${drawIndex+1}點高度${num(drawPoints[drawIndex]*100,0)}%。`:'尚未繪製，請畫線或載入範例。';}
function pointer(e){let rect=$p('#draw-canvas').getBoundingClientRect(),x=(e.clientX-rect.left)/rect.width,y=(e.clientY-rect.top)/rect.height;const idx=Math.max(0,Math.min(59,Math.round((x*900-20)/860*59))),v=Math.max(0,Math.min(1,(340-y*360)/320));if(!drawPoints.length)drawPoints=Array(60).fill(.5);let from=drawIndex,previous=drawPoints[from];if(drawing&&from!==idx){let a=Math.min(from,idx),b=Math.max(from,idx);for(let i=a;i<=b;i++)drawPoints[i]=previous+(v-previous)*(i-from)/(idx-from);}drawIndex=idx;drawPoints[idx]=v;draw();}
function openDraw(id=null){editingId=id;$p('#draw-dialog').classList.remove('drawing-expanded');$p('#draw-fullscreen').textContent='全螢幕繪圖';const p=custom.find(p=>p.id===id);$p('#draw-name').value=p?.name||'';$p('#draw-description').value=p?.description||'';$p('#draw-days').value=p?.days||60;$p('#draw-threshold').value=p?.threshold||80;$p('#draw-cycle').value=p?.cycle||'day';drawPoints=p?P.resample(p.points):[];drawIndex=0;$p('#draw-title').textContent=p?'編輯選股型態':'新增選股型態';updateDrawLabels();$p('#draw-dialog').showModal();draw();}
function updateDrawLabels(){$p('#draw-days-value').textContent=$p('#draw-days').value;$p('#draw-threshold-value').textContent=$p('#draw-threshold').value+'%';}
$p('#pattern-cards').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.runPattern)runPatterns([b.dataset.runPattern]);if(b.dataset.edit)openDraw(b.dataset.edit);if(b.dataset.delete){trash=custom.find(p=>p.id===b.dataset.delete);custom=custom.filter(p=>p.id!==b.dataset.delete);chosen.delete(b.dataset.delete);persist();renderCards();}if(b.id==='restore-pattern'&&trash){custom.push(trash);trash=null;persist();renderCards();}});
$p('#pattern-cards').addEventListener('change',e=>{if(e.target.dataset.pick){e.target.checked?chosen.add(e.target.dataset.pick):chosen.delete(e.target.dataset.pick);renderCards();}});
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));document.querySelectorAll('[data-group]').forEach(b=>b.onclick=()=>{group=Number(b.dataset.group);document.querySelectorAll('[data-group]').forEach(t=>t.classList.toggle('active',t===b));renderCards();});
$p('#pattern-search').oninput=renderCards;$p('#pattern-run-selected').onclick=()=>runPatterns([...chosen]);$p('#pattern-clear-selected').onclick=()=>{chosen.clear();renderCards();};$p('#pattern-results-close').onclick=()=>{scanId++;$p('#pattern-results').close();};$p('#pattern-results').addEventListener('cancel',()=>scanId++);$p('#pattern-stock-search').oninput=renderResults;
$p('#pattern-rows').onclick=e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.chartSymbol)showChart(candidates.find(x=>x.row.symbol===b.dataset.chartSymbol));if(b.dataset.favorite){const id=b.dataset.favorite;favorites.has(id)?favorites.delete(id):favorites.add(id);localStorage.setItem('picker-favorites',JSON.stringify([...favorites]));renderResults();}};
$p('#pattern-csv').onclick=()=>{const cell=x=>'"'+String(x??'').replaceAll('"','""')+'"';download('型態候選_'+market.asof+'.csv',[['股號','名稱','型態','相似度_非勝率','訊號日','最新日價格','最新日成交量_張'],...visibleRows.map(x=>[x.row.symbol,x.row.name,x.matches.join('、'),lastSpec.mode==='candles'?'規則符合':x.score,x.date,x.row.price,x.row.volume])].map(a=>a.map(cell).join(',')).join('\r\n'),'text/csv;charset=utf-8');};
$p('#add-pattern').onclick=()=>openDraw();$p('#draw-close').onclick=()=>{expandDrawing(false);$p('#draw-dialog').close();};$p('#draw-example').onclick=()=>{drawPoints=P.resample(catalog.shapes.find(p=>p.id==='w').points);drawIndex=0;draw();};$p('#draw-clear').onclick=()=>{drawPoints=[];drawIndex=0;draw();};
async function expandDrawing(expand){$p('#draw-dialog').classList.toggle('drawing-expanded',expand);$p('#draw-fullscreen').textContent=expand?'縮回繪圖':'全螢幕繪圖';try{if(expand&&!document.fullscreenElement)await $p('#draw-dialog').requestFullscreen();else if(!expand&&document.fullscreenElement)await document.exitFullscreen();}catch{if(expand)$p('#draw-status').textContent='已切換網頁內放大繪圖；按Esc或「縮回繪圖」恢復。';}}
$p('#draw-fullscreen').onclick=()=>expandDrawing(!$p('#draw-dialog').classList.contains('drawing-expanded'));
$p('#draw-dialog').addEventListener('cancel',e=>{if($p('#draw-dialog').classList.contains('drawing-expanded')){e.preventDefault();expandDrawing(false);}});
for(const id of ['draw-days','draw-threshold'])$p('#'+id).oninput=updateDrawLabels;
$p('#draw-canvas').onpointerdown=e=>{drawIndex=Math.max(0,Math.min(59,Math.round((e.offsetX/$p('#draw-canvas').clientWidth)*59)));drawing=false;pointer(e);drawing=true;$p('#draw-canvas').setPointerCapture(e.pointerId);};$p('#draw-canvas').onpointermove=e=>{if(drawing)pointer(e);};$p('#draw-canvas').onpointerup=()=>drawing=false;$p('#draw-canvas').onpointercancel=()=>drawing=false;
$p('#draw-canvas').onkeydown=e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();if(!drawPoints.length)drawPoints=Array(60).fill(.5);if(e.key==='ArrowLeft')drawIndex=Math.max(0,drawIndex-1);if(e.key==='ArrowRight')drawIndex=Math.min(59,drawIndex+1);if(e.key==='ArrowUp')drawPoints[drawIndex]=Math.min(1,drawPoints[drawIndex]+.05);if(e.key==='ArrowDown')drawPoints[drawIndex]=Math.max(0,drawPoints[drawIndex]-.05);draw();};
$p('#draw-form').onsubmit=e=>{e.preventDefault();const p={id:editingId||'custom-'+crypto.randomUUID(),name:$p('#draw-name').value.trim(),description:$p('#draw-description').value.trim(),days:Number($p('#draw-days').value),threshold:Number($p('#draw-threshold').value),cycle:$p('#draw-cycle').value,points:drawPoints.slice(),updated:new Date().toISOString()};if(!P.validateCustom(p)){$p('#draw-status').textContent='請填名稱並畫出有起伏的輪廓，至少5點；K棒數5～120、門檻50～100。';return;}custom=custom.filter(x=>x.id!==p.id);custom.push(p);persist();expandDrawing(false);$p('#draw-dialog').close();setMode('custom');};
$p('#export-patterns').onclick=()=>download('我的選股型態.json',JSON.stringify({schema:'alchemy-patterns-v1',patterns:custom},null,2),'application/json');
$p('#import-patterns').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>2e6)throw Error('檔案超過2MB');const v=JSON.parse((await file.text()).replace(/^\uFEFF/,''));if(v.schema!=='alchemy-patterns-v1'||!Array.isArray(v.patterns)||v.patterns.length>100||!v.patterns.every(P.validateCustom))throw Error('格式或型態規格不合法');for(const p of v.patterns)custom.push({...p,id:'custom-'+crypto.randomUUID()});persist();renderCards();$p('#pattern-note-status').textContent=`已匯入${v.patterns.length}個型態，保留現有型態。`;}catch(err){$p('#pattern-note-status').textContent='匯入未完成：'+err.message;}e.target.value='';};
for(const id of ['pattern-hypothesis','pattern-observation']){$p('#'+id).value=localStorage.getItem(id)||'';$p('#'+id).oninput=()=>localStorage.setItem(id,$p('#'+id).value);}
$p('#pattern-export-md').onclick=()=>{download('我的型態實作紀錄.md',`# 我的型態實作紀錄\n\n資料來源：雪鴞\n資料日：${market.asof}\n資料範圍：${market.mode} / ${market.rows.length}檔\n\n## 我的假設\n${$p('#pattern-hypothesis').value||'待填'}\n\n## 修改與觀察\n${$p('#pattern-observation').value||'待填'}\n\n## 本次執行規格\n\`\`\`json\n${JSON.stringify(lastSpec,null,2)}\n\`\`\`\n候選數：${candidates.length}\n\n## 自訂型態\n\`\`\`json\n${JSON.stringify(custom,null,2)}\n\`\`\`\n\n## 下一步\n- 核對一個符合、一個不符合、資料不足案例\n- 一次修改一項，保存原版本與反例\n- 補上進出場、部位與成本，再用雪鴞api.bt驗證\n- 相似度不是勝率，圖形像不代表必然上漲\n`,'text/markdown;charset=utf-8');$p('#pattern-note-status').textContent='已產生Markdown下載，請存進自己的Obsidian。';};
async function init(){try{catalog=await(await fetch('pattern-catalog.json')).json();let r;if(['localhost','127.0.0.1'].includes(location.hostname))r=await fetch('local-pattern-data.json');if(!r?.ok)r=await fetch('pattern-demo.json');if(!r.ok)throw Error('請先產生型態資料');market=await r.json();if(!market.rows.length)throw Error('沒有股票資料');$p('#pattern-status').textContent=`資料日${market.asof}｜${market.source}｜${market.mode==='teaching_sample'?'公開教學樣本':'本機資料範圍'}${market.rows.length}檔${market.mode==='teaching_sample'?'，含事後挑選例子，非全市場':'（含興櫃）'}。使用盤後OHLC；完整週、月線可能較最新日線早。`;setMode(mode);}catch(e){$p('#pattern-status').textContent='載入失敗：'+e.message;}}
init();
