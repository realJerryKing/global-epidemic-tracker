// Host-only data boundary. No session, transcript, telemetry or UI storage dependencies.
export const SITE = 'https://realJerryKing.github.io/global-epidemic-tracker/';
const isoDate = /^\d{4}-\d{2}-\d{2}$/;
const codePattern = /^\d{6}$/;
const symptoms = ['new','ongoing','none'];
const observations = ['more','usual','less'];
const trends = ['insufficient_baseline','no_clear_rise','possible_rise'];
export const isCode = value => typeof value === 'string' && codePattern.test(value);
function requireValue(ok, message = '参数无效') { if (!ok) throw new Error(message); }
export function endpoint(value) {
  if (!value) return null;
  const u = new URL(value);
  requireValue(!u.search && !u.hash && !u.username && !u.password && (u.protocol === 'https:' || (u.protocol === 'http:' && ['localhost','127.0.0.1','[::1]'].includes(u.hostname))), '服务地址须为 HTTPS 或本机回环地址');
  return u.href.replace(/\/+$/, '');
}
export function weekOf(date = new Date()) {
  const dt = new Date(date.getTime() + 8 * 3600000);
  dt.setUTCDate(dt.getUTCDate() - (dt.getUTCDay() + 6) % 7);
  return dt.toISOString().slice(0,10);
}
export function validWeek(value) {
  if (typeof value !== 'string' || !isoDate.test(value)) return false;
  const d = new Date(value+'T00:00:00Z');
  return d.getUTCDay() === 1 && d.toISOString().slice(0,10) === value;
}
async function jsonRequest(fetcher,url,options={},limit=1024*1024) {
  const timeout=AbortSignal.timeout(10000);
  const res=await fetcher(url,{...options,signal:options.signal?AbortSignal.any([timeout,options.signal]):timeout,redirect:'error',cache:'no-store'});
  if (!res.ok) { await res.body?.cancel(); const err=new Error(({401:'凭据无效',403:'未获授权',404:'未找到记录',409:'当前状态冲突',422:'服务未接受输入',429:'请求过于频繁'})[res.status]||'服务暂不可用'); err.status=res.status; throw err; }
  if(res.status===204) return null;
  const chunks=[]; let n=0; for await(const chunk of res.body){n+=chunk.length;requireValue(n<=limit,'响应超出限制');chunks.push(chunk);}
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
function releasedReport(data,code) {
  const s=data?.status; requireValue(data?.requested_region_code===code && ['available','unavailable','suppressed'].includes(s));
  const out={status:s,requested_region_code:code,region_code:null,week_start:null,week_end:null,metrics:null};
  if (validWeek(data.week_start) && isoDate.test(data.week_end)) Object.assign(out,{week_start:data.week_start,week_end:data.week_end});
  if(s!=='available')return out;
  const m=data.metrics;
  requireValue(isCode(data.region_code) && out.week_start && m && ['30-59','60-119','120+'].includes(m.sample_band) && /^(?:[0-8]?0-[0-8]?9|90-100)%$/.test(m.new_share_band) && trends.includes(m.trend));
  const levels=['district','city','province','country'];requireValue(levels.includes(data.level)&&levels.includes(data.requested_level));
  return {...out,region_code:data.region_code,requested_level:data.requested_level,level:data.level,metrics:{sample_band:m.sample_band,new_share_band:m.new_share_band,trend:m.trend}};
}
export class Tracker {
  constructor({backend='',region='000000',fetcher=fetch,store}){this.base=endpoint(backend);this.region=isCode(region)?region:'000000';this.fetcher=fetcher;this.store=store;this.cache=new Map();this.officialCache=null;}
  async api(path,{method='GET',body,token,signal}={}){requireValue(this.base,'尚未配置服务');return jsonRequest(this.fetcher,this.base+path,{method,signal,headers:{Accept:'application/json',...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{})});}
  async official(signal){if(this.officialCache?.until>Date.now())return this.officialCache.value;
    const raw=await jsonRequest(this.fetcher,SITE+'data/epidemics.json',{signal},12*1024*1024);
    requireValue(raw.schema_version===2 && Array.isArray(raw.outbreaks) && Number.isSafeInteger(raw.summary?.report_count) && raw.summary.report_count>=0);
    const allowed=['who_don','who_gho','owid'];const sources=allowed.filter(s=>raw.outbreaks.some(r=>r.source===s));
    requireValue(typeof raw.last_update==='string' && Number.isFinite(Date.parse(raw.last_update)));
    const value={status:'available',scope:'global',snapshot_time:new Date(raw.last_update).toISOString(),legacy:raw.legacy===true,report_count:raw.summary.report_count,sources};
    this.officialCache={value,until:Date.now()+5*60000};return value;}
  async snapshot(code=this.region,signal){requireValue(isCode(code));signal?.throwIfAborted();
    const old=this.cache.get(code); if(old?.until>Date.now())return old.value;
    const [official,community]=await Promise.all([this.official(signal).catch(()=>({status:'unavailable',scope:'global'})),this.base?this.api('/v1/reports/latest?region_code='+code,{signal}).then(d=>releasedReport(d,code)).catch(()=>({status:'offline',requested_region_code:code,metrics:null})):Promise.resolve({status:'not_configured',requested_region_code:code,metrics:null})]);signal?.throwIfAborted();
    const guidance=community.status!=='available'?'无可用于本区判断的周报；请参阅当地疾控部门公告，不能把缺失视为零。':community.region_code!==code?'仅说明所示上级地区自选样本趋势，不能推断请求地区正在上升。请结合当地疾控公告。':community.metrics.trend==='possible_rise'?'本区自选样本提示可能上升，不是疫情预警；可关注当地疾控公告。':'未建立明确上升证据不代表没有传播；可关注当地疾控公告。';
    const value={requested_region_code:code,community,official,guidance,prevention:[{advice:community.status==='available'&&community.metrics.trend==='possible_rise'?'在拥挤或通风不佳的室内，尤其与高风险人群接触时，可佩戴贴合面部的优质口罩。':'在拥挤的室内交通工具或照护患病家人时，可考虑佩戴贴合的口罩。',source:'CDC · Masks and respiratory viruses',url:'https://www.cdc.gov/respiratory-viruses/prevention/masks.html'},{advice:'擤鼻涕、咳嗽或打喷嚏后清洁双手；咳嗽时用纸巾或肘部遮挡。',source:'CDC · Hygiene and respiratory viruses',url:'https://www.cdc.gov/respiratory-viruses/prevention/hygiene.html'}],map_url:SITE+'?region='+code,interpretation:'社区自报样本不是确诊病例、发病率或个人风险。全球官方背景不能替代地区周报。'};
    if(this.cache.size>=100)this.cache.delete(this.cache.keys().next().value);this.cache.set(code,{value,until:Date.now()+60000});return value;}
  async privateAction(action,p={}){
    if(action==='setup')return {backend:this.base,bound:this.base?(this.store.bound?await this.store.bound():Boolean(await this.store.read())):false,region:this.region,week:weekOf()};
    if(action==='regions'){const raw=await this.api('/v1/regions');requireValue(Array.isArray(raw.regions));return raw.regions.filter(r=>isCode(r.code)&&typeof r.name==='string').slice(0,6500).map(r=>({code:r.code,name:r.name.slice(0,64),parent_code:isCode(r.parent_code)?r.parent_code:null}));}
    requireValue(this.base,'尚未配置服务');
    if(action==='enroll'){requireValue(typeof p.invite_code==='string'&&p.invite_code.length>=1&&p.invite_code.length<=256);await this.store.enroll(async()=>{const data=await this.api('/v1/enroll',{method:'POST',body:{invite_code:p.invite_code}});requireValue(typeof data?.token==='string'&&data.token.length>=16&&data.token.length<=4096,'凭据无效');return data.token;});return {ok:true};}
    requireValue(['read','save','withdraw'].includes(action));requireValue(validWeek(p.date),'请选择星期一');
    const token=await this.store.read();requireValue(token,'请先绑定一次性邀请码');
    const path='/v1/checkins/'+p.date;
    if(action==='withdraw'){requireValue(p.confirm===true,'请确认撤回');await this.api(path,{method:'DELETE',token});return {ok:true};}
    if(action==='save'){requireValue(p.consent===true && isCode(p.region_code) && symptoms.includes(p.symptom) && (p.observation==null||observations.includes(p.observation)),'请检查输入并明确同意');await this.api(path,{method:'PUT',token,body:{region_code:p.region_code,symptom:p.symptom,observation:p.observation??null,consent:true}});return {ok:true};}
    try{const d=await this.api(path,{token});requireValue(d.date===p.date&&isCode(d.region_code)&&symptoms.includes(d.symptom)&&(d.observation==null||observations.includes(d.observation)));return {date:d.date,region_code:d.region_code,symptom:d.symptom,observation:d.observation??null};}catch(e){if(e.status===404)return null;throw e;}
  }
}
