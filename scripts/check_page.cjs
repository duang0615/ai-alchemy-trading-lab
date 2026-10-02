const fs=require('fs'),vm=require('vm'),assert=require('assert');
const page=fs.readFileSync(require('path').join(__dirname,'../index.html'),'utf8');
const code=page.match(/<script>([\s\S]*)<\/script>/)[1];
const nodes={};for(const id of ['symbol','period','comparison','dates','chart','examples','sensitivity','note','save','boundary'])nodes[id]={value:'',innerHTML:'',textContent:''};
nodes.symbol.value='6533';nodes.period.value='out_of_sample';
const storage={};let clicked=false;
const ctx={document:{getElementById:id=>nodes[id],createElement:()=>({click:()=>clicked=true})},localStorage:{getItem:k=>storage[k],setItem:(k,v)=>storage[k]=v},Blob,URL,setTimeout:fn=>fn()};
vm.createContext(ctx);vm.runInContext(code,ctx);
for(const symbol of ['6533','3037','3443','2357'])for(const period of ['development','out_of_sample','full']){
 nodes.symbol.value=symbol;nodes.period.value=period;vm.runInContext('render()',ctx);
 assert.equal((nodes.comparison.innerHTML.match(/<tr>/g)||[]).length,5);
 assert.equal((nodes.examples.innerHTML.match(/class="card"/g)||[]).length,2);
 assert.equal((nodes.chart.innerHTML.match(/<polyline/g)||[]).length,4);
 assert(!nodes.chart.innerHTML.includes('NaN'));
}
nodes.note.value='我的假設';nodes.note.oninput();assert.equal(storage['alchemy-note'],'我的假設');nodes.save.onclick();assert(clicked);
console.log('PASS: 12 stock/period combinations, charts, examples, note storage and download event');
