import {regions} from './regions.js';
import {centers} from './china-map.js';
import {outlines} from './outlines.js';

const $ = id => document.getElementById(id);
const el = (tag, text, cls) => {const n=document.createElement(tag); n.textContent=text; if(cls)n.className=cls; return n;};
const svgNS='http://www.w3.org/2000/svg';
const sourceNames={who_don:'WHO 疾病暴发新闻',who_gho:'WHO 全球卫生观察站',owid:'WHO 数据（经 OWID 整理）'};
const periodNames={annual:'统计年度',publication:'发布日期',cumulative:'累计截至'};
const regionBy=new Map(regions.map(r=>[r.code,r]));
const children=code=>regions.filter(r=>r.parent_code===code);
let official=[],pageSize=20,officialState='loading';
let selected='000000',invalidRegion=false,request=0,controller;
const project=([lon,lat])=>[(lon+180)*2,(90-lat)*2];

function pin(layer,coords,r,label,chosen,onClick){
  const [cx,cy]=project(coords),dot=document.createElementNS(svgNS,'circle');
  for(const [k,v] of Object.entries({cx,cy,r,tabindex:'0',role:'button','aria-label':label,'aria-pressed':String(chosen)}))dot.setAttribute(k,v);
  if(chosen)dot.classList.add('chosen');
  dot.style.strokeWidth=String(r*.23);const t=document.createElementNS(svgNS,'title');t.textContent=label;dot.append(t);
  dot.addEventListener('click',onClick);dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onClick();}});layer.append(dot);
}
function options(select,items,empty,preferred=''){
  select.replaceChildren(new Option(empty,''),...items.map(([id,name])=>new Option(name,id)));
  if(items.some(([id])=>id===preferred))select.value=preferred;
}
function urlFor(raw){try{const url=new URL(raw);return /^https?:$/.test(url.protocol)&&!url.username&&!url.password?url.href:null;}catch{return null;}}
function placeOf(row){return row.country && row.country!=='Not specified'?row.country:'地点未注明';}
function validPoint(r){return Number.isFinite(r.latitude)&&Math.abs(r.latitude)<=90&&Number.isFinite(r.longitude)&&Math.abs(r.longitude)<=180;}
function dateSpan(r){
  if(r.period_type==='annual'){const y=String(r.period_label??'').match(/^\d{4}$/)?.[0];return y?[`${y}-01-01`,`${y}-12-31`]:null;}
  const day=String(r.date_reported??'').slice(0,10);return /^\d{4}-\d\d-\d\d$/.test(day)?[day,day]:null;
}
function listed(r){
  const item=document.createElement('li');item.append(el('span',`${r.disease || '未注明疾病'} · ${placeOf(r)}`,'record-title'));
  const period=r.period_type==='annual'?r.period_label:r.date_reported?.slice(0,10)||r.period_label;
  const meta=[sourceNames[r.source]||r.source||'来源未注明',`${periodNames[r.period_type]||'记录日期'}：${period || '未注明'}`];
  if(r.legacy)meta.push('历史快照');item.append(el('p',meta.join(' ｜ '),'record-meta'));
  const href=urlFor(r.source_url);if(href){const a=el('a','查看来源 ↗','source-link');a.href=href;a.target='_blank';a.rel='noopener noreferrer';a.setAttribute('aria-label',`${r.disease || '报告'}：查看来源（新窗口）`);item.append(a);}return item;
}
function refreshGlobal(){
  if(officialState!=='ready')return;
  const [source,disease,from,to]=['source','disease','from','until'].map(k=>$(k).value);
  const inverted=Boolean(from&&to&&from>to);
  const rows=official.filter(r=>{if(inverted||(source&&r.source!==source)||(disease&&r.disease!==disease))return false;if(!from&&!to)return true;
    const span=dateSpan(r);return span&&(!from||span[1]>=from)&&(!to||span[0]<=to);});
  const places=[...new Set(rows.map(placeOf))].sort((a,b)=>a.localeCompare(b));options($('place'),places.map(v=>[v,v]),'全部地点',$('place').value);
  const filterPlace=$('place').value,visible=rows.filter(r=>!filterPlace||placeOf(r)===filterPlace);
  const groups=new Map();for(const r of rows){if(!validPoint(r))continue;const key=placeOf(r);if(!groups.has(key))groups.set(key,{point:[r.longitude,r.latitude],count:0});groups.get(key).count++;}
  const layer=$('world-map').querySelector('.pins');layer.replaceChildren();for(const [key,g] of groups)pin(layer,g.point,3.35,`${key}：${g.count} 条报告`,filterPlace===key,()=>{$('place').value=filterPlace===key?'':key;pageSize=20;refreshGlobal();$('place').focus({preventScroll:true});});
  const missing=visible.filter(r=>!validPoint(r)).length;
  $('summary').textContent=inverted?'起始日期不能晚于结束日期。':visible.length?`${visible.length} 条报告 · 已显示 ${Math.min(pageSize,visible.length)} 条${missing?` · ${missing} 条无可靠坐标，仅列于目录`:''}`:'当前条件下没有报告。请调整筛选；无报告不代表无病例。';
  $('records').replaceChildren(...visible.slice(0,pageSize).map(listed));$('more').hidden=visible.length<=pageSize;
}
async function loadOfficial(){
  try{const response=await fetch('data/epidemics.json');if(!response.ok)throw Error();const data=await response.json();if(data.schema_version!==2||!Array.isArray(data.outbreaks))throw Error();
    official=data.outbreaks.filter(r=>r&&typeof r==='object').sort((a,b)=>(dateSpan(b)?.[1]||'').localeCompare(dateSpan(a)?.[1]||''));
    for(const key of ['source','disease']){const keys=[...new Set(official.map(r=>r[key]).filter(Boolean))].sort();options($(key),keys.map(v=>[v,key==='source'?sourceNames[v]||v:v]),key==='source'?'全部来源':'全部条目');}
    $('updated').textContent=`${data.legacy?'历史快照':'数据快照'}${data.last_update?' · '+String(data.last_update).slice(0,10):''}`;
    $('legacy-note').hidden=!data.legacy;officialState='ready';refreshGlobal();
  }catch{officialState='error';$('summary').textContent='无法读取官方报告快照，请刷新后重试。';}
}
$('filters').addEventListener('change',()=>{pageSize=20;refreshGlobal();});$('filters').addEventListener('reset',e=>{e.preventDefault();for(const id of ['source','disease','from','until','place'])$(id).value='';pageSize=20;refreshGlobal();});
$('place').addEventListener('change',()=>{pageSize=20;refreshGlobal();});$('more').onclick=()=>{pageSize+=20;refreshGlobal();};

function regionPath(code){const path=[];while(regionBy.has(code)){const r=regionBy.get(code);path.unshift(r);code=r.parent_code;}return path;}
function renderChina(){
  const path=regionPath(selected);const [country,province,city,district]=path;
  for(const [id,parent,choice,all] of [['province',country,province,'全国'],['city',province,city,'全省级地区'],['district',city,district,'全市']]){
    const choices=parent?children(parent.code):[];options($(id),choices.map(r=>[r.code,r.name]),choices.length||id==='province'?all:'此层级暂不可选',choice?.code);$(id).disabled=!choices.length;
  }
  const map=$('china-map'),layer=map.querySelector('.pins');layer.replaceChildren();
  let mapped=children('000000'),view=[502,69,133,84];
  if(city){mapped=children(city.code);const xy=mapped.filter(r=>centers[r.code]).map(r=>project(centers[r.code]));if(xy.length){const xs=xy.map(p=>p[0]),ys=xy.map(p=>p[1]);view=[Math.min(...xs)-.32,Math.min(...ys)-.28,Math.max(...xs)-Math.min(...xs)+.64,Math.max(...ys)-Math.min(...ys)+.56];}}
  else if(province&&children(province.code).length){mapped=children(province.code);const [x,y]=project(centers[province.code]);view=[x-6,y-4,12,8];}
  map.setAttribute('viewBox',view.join(' '));
  const base=map.querySelector('.outlines');base.replaceChildren();
  const codes=city?[city.code==='110100'?'110000':city.code]:province&&children(province.code).length?[province.code,...children(province.code).map(r=>r.code)]:children('000000').map(r=>r.code);
  for(const code of codes){if(!outlines[code])continue;const polygon=document.createElementNS(svgNS,'path');polygon.setAttribute('d',outlines[code]);polygon.setAttribute('class','area'+(code===province?.code?' selected':''));polygon.setAttribute('vector-effect','non-scaling-stroke');polygon.setAttribute('aria-hidden','true');if(!city)polygon.onclick=()=>navigate(code);base.append(polygon);}
  for(const r of mapped){if(centers[r.code])pin(layer,centers[r.code],view[2]*.009,r.name,selected===r.code,()=>{navigate(r.code);$('province').focus({preventScroll:true});});}
  const desc=city?'试点区县导航':province&&children(province.code).length?'试点城市导航':'省级地区导航';map.setAttribute('aria-label',desc);$('china-map-title').textContent=desc;$('china-map-legend').textContent=city?'选择区县':province&&children(province.code).length?'选择城市':'选择省份';
  $('coverage').textContent=invalidRegion?'链接中的地区代码不在当前目录；请选择有效地区。':province&&!children(province.code).length?'此省级地区暂未收录市、区县；当前仅查询省级周报。':city?'可选试点区县；未选择时查询市级周报。':'试点城市：北京市辖区、广州市。';
  $('weekly-title').textContent=invalidRegion?'地区未收录':path.map(r=>r.name).join(' / ')+' · 最新周报';lookup();
}
function renderView(code){const china=code!==null;invalidRegion=china&&!regionBy.has(code);selected=regionBy.has(code)?code:'000000';
  $('global').hidden=china;$('china').hidden=!china;$('global-tab').setAttribute('aria-pressed',String(!china));$('china-tab').setAttribute('aria-pressed',String(china));
  if(china)renderChina();else{++request;controller?.abort();}
}
function navigate(code){const u=new URL(location.href);if(code===null)u.searchParams.delete('region');else u.searchParams.set('region',code);if(u.href!==location.href)history.pushState(null,'',u);renderView(code);}
$('global-tab').onclick=()=>navigate(null);$('china-tab').onclick=()=>navigate(selected);window.addEventListener('popstate',()=>renderView(new URL(location.href).searchParams.get('region')));
$('province').onchange=()=>navigate($('province').value||'000000');$('city').onchange=()=>navigate($('city').value||$('province').value||'000000');$('district').onchange=()=>navigate($('district').value||$('city').value||'000000');
function apiRoot(){const value=window.EPIDEMIC_CONFIG?.publicApiBase?.trim();if(!value)return null;const url=new URL(value,location.href);if(!/^https?:$/.test(url.protocol)||url.username||url.password||url.search||url.hash)throw Error('configuration');return url.href.replace(/\/$/,'');}
const levels={country:'全国',province:'省级',city:'市级',district:'区县级'};
const trends={insufficient_baseline:'历史基线不足',no_clear_rise:'未见明确上升',possible_rise:'可能上升'};
function weeklyReport(data){
  if(data.requested_region_code!==selected||!['available','suppressed','unavailable'].includes(data.status))throw Error('invalid report');
  if(data.status!=='available'){return [el('p',data.status==='suppressed'?'尚无可披露周报：未达到发布门槛，小样本已隐藏。':'该地区及可查询的上级地区暂无已发布周报。')];}
  const reported=regionBy.get(data.region_code);if(!reported||!regionPath(selected).some(r=>r.code===reported.code)||!data.metrics||!data.week_start||!data.week_end)throw Error('invalid release');
  const fallback=selected!==reported.code,items=[];
  if(fallback)items.push(el('p',`上级回退：${regionBy.get(selected).name}暂无可披露周报。以下为${reported.name}（${levels[reported.level]}）的汇总，不是所选地区的结果。`,'warning'));
  items.push(el('p',`发布地区：${reported.name}（${levels[reported.level]}） ｜ 周期：${data.week_start} — ${data.week_end}`));
  const dl=document.createElement('dl');for(const [name,value] of [['签到样本量区间',data.metrics.sample_band],['自报新发症状的样本占比',data.metrics.new_share_band],['样本趋势',trends[data.metrics.trend]]]){const group=document.createElement('div');group.append(el('dt',name),el('dd',value||'未提供'));dl.append(group);}items.push(dl);return items;
}
async function lookup(){
  const id=++request;controller?.abort();const aborter=new AbortController();controller=aborter;const box=$('weekly-body');$('retry').hidden=true;
  if(invalidRegion){box.textContent='未对未知地区发起周报查询。';return;}let timer;
  try{const base=apiRoot();if(!base){box.textContent='此站点未配置公共周报 API。地区导航仍可使用，当前不显示社区数据。';return;}
    box.textContent='正在查询最新已发布周报…';timer=setTimeout(()=>aborter.abort(),10000);
    const url=new URL(base+'/v1/reports/latest');url.searchParams.set('region_code',selected);
    const response=await fetch(url,{signal:aborter.signal,credentials:'omit',referrerPolicy:'no-referrer'});if(!response.ok)throw Error();const data=await response.json();if(request===id)box.replaceChildren(...weeklyReport(data));
  }catch{if(request===id){box.textContent='周报服务未能返回可用结果。请稍后重试；这不表示没有签到。';$('retry').hidden=false;}}finally{clearTimeout(timer);}
}
$('retry').onclick=lookup;renderView(new URL(location.href).searchParams.get('region'));loadOfficial();
