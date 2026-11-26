// Run with the DSH Desktop node executable in Electron node mode. No profile load.
import assert from 'node:assert/strict';import {registerHooks,createRequire} from 'node:module';import {pathToFileURL,fileURLToPath} from 'node:url';import path from 'node:path';import fs from 'node:fs';
const base=process.env.DSH_INSTALL_DIR;assert.ok(base);const resolve=createRequire(path.join(base,'package.json')).resolve;
// Electron's ESM loader uses native realpath; supply ASAR files via its readFile shim.
let resolving=false;registerHooks({resolve(s,c,next){if(resolving)return next(s,c);if(s.startsWith('@deepseek-ai/')||(!s.startsWith('node:')&&!s.startsWith('.')&&!s.includes(':')&&c.parentURL?.includes('app.asar/'))){let r;resolving=true;try{r=c.parentURL?.includes('app.asar/')?createRequire(c.parentURL).resolve(s):resolve(s);}finally{resolving=false;}if(!path.isAbsolute(r))return next(s,c);return {url:pathToFileURL(r).href,shortCircuit:true};}return next(s,c);},load(url,c,next){if(url.includes('app.asar/')&&url.endsWith('.js')){const filename=fileURLToPath(url);let d=path.dirname(filename);while(!fs.existsSync(path.join(d,'package.json')))d=path.dirname(d);const format=JSON.parse(fs.readFileSync(path.join(d,'package.json'),'utf8')).type==='module'?'module':'commonjs';return {format,source:fs.readFileSync(filename,'utf8'),shortCircuit:true}}return next(url,c)}});
const {default:Plugin}=await import('../index.js');const {Context}=await import('@deepseek-ai/cordis');const {default:Registry}=await import('@deepseek-ai/dsh-typert-registry');const {remoteMethods}=await import('@deepseek-ai/dsh-typert-protocol');const ctx=new Context();let tool;
// Inject public HTTP responses at the fetch boundary before the only Host mount.
const {OFFICIAL_URL}=await import('../official.js');
const live=process.argv.includes('--live');
const realFetch=globalThis.fetch;let hits=0;
globalThis.fetch=async (url,opts)=>{
  assert.equal(url,OFFICIAL_URL);assert.equal(opts.cache,'no-store');assert.equal(opts.redirect,'error');assert.equal(opts.headers.Authorization,undefined);
  const count=++hits;
  if(live)return realFetch(url,opts);
  return Response.json({schema_version:2,last_update:`2099-01-0${count}T00:00:00Z`,legacy:false,outbreaks:Array.from({length:count},()=>({source:'who_don'})),summary:{report_count:count}});
};
const legacy=process.argv.includes('--legacy-host');
// Match the ws ESM entry even though the ASAR resolver uses require.resolve.
const wsEntry=createRequire(resolve('@deepseek-ai/dsh-api-gateway')).resolve('ws');
registerHooks({resolve(specifier,context,next){
  if(specifier==='ws'&&context.parentURL?.includes('/dsh-api-gateway/'))return {url:pathToFileURL(path.join(path.dirname(wsEntry),'wrapper.mjs')).href,shortCircuit:true};
  return next(specifier,context);
},load(url,context,next){
  if(url.includes('app.asar/')&&url.endsWith('/ws/wrapper.mjs'))return {format:'module',source:fs.readFileSync(fileURLToPath(url),'utf8'),shortCircuit:true};
  return next(url,context);
}});
const {default:HostGateway}=await import('@deepseek-ai/dsh-api-gateway');
let dispatch;
ctx.provide('remoteAccess',{decide:()=>({kind:'deny',reason:'test'})});
ctx.provide('connection',{rpc:{intercept(route,_claims,handler){assert.equal(route,'/api');dispatch=handler;}}});
const {panelDescriptors}=await import('../contract.js');
const z=createRequire(path.join(base,'package.json'))('zod');
class TestRegistry extends Registry {
  register(bundle){
    if(legacy && bundle.package==='@local/dsh-epidemic-tracker'){
      const invocations=panelDescriptors({...z,enum:values=>z.enum(values.filter(value=>value!=='official'))});
      bundle={...bundle,invocations};
    }
    return super.register(bundle);
  }
}
ctx.provide('credentials');ctx.provide('tools');ctx.set('credentials',{describeRecord:async()=>({configured:false})});ctx.set('tools',{register(t){tool=t;}});ctx.on('internal/error',(err)=>console.error(err));const registry=ctx.plugin(TestRegistry);ctx.plugin(HostGateway);await new Promise(r=>setImmediate(r));const plugin=ctx.plugin(Plugin,{});await new Promise(r=>setImmediate(r));if(!ctx.epidemicTracker)console.error('status',registry.status,plugin.status,Boolean(ctx.typert),Boolean(ctx.tools),Boolean(ctx.credentials),plugin.error);const host=ctx.epidemicTracker;assert.ok(host);assert.equal(remoteMethods(host)[0].method,'panel');assert.equal(tool.name,'epidemic_snapshot');await assert.rejects(host.panel({action:'setup'}));console.log('PASS: installed Cordis service + Typert registry + owner guard + tool registration (no profile)');
globalThis.fetch=realFetch;
const getSnapshot=async refresh=>JSON.parse(await tool.execute({region_code:'440106',refresh},{}));
const a=await getSnapshot(true);
assert.equal(a.official.provenance,'published');
let b=await getSnapshot(true);
const watch=live&&process.argv.includes('--watch-next');
if(watch){
  console.log('Waiting for a newer live Pages snapshot from',a.official.snapshot_time);
  for(let attempt=0;attempt<80&&b.official.snapshot_time<=a.official.snapshot_time;attempt++){
    await new Promise(resolve=>setTimeout(resolve,15000).ref());
    b=await getSnapshot(true);
  }
  assert.ok(b.official.snapshot_time>a.official.snapshot_time,'No newer live snapshot appeared within the verification window');
}
const c=await getSnapshot(false);
assert.ok(watch?hits>=2:hits===2);assert.deepEqual([a.official.provenance,b.official.provenance,c.official.provenance],['published','published','cached']);
assert.equal(b.official.report_count,c.official.report_count);
assert.equal(b.official.source_url,OFFICIAL_URL);
if(live){
  assert.ok(b.official.snapshot_time>=a.official.snapshot_time);
  console.log('PASS: live Pages v2 refreshes', [a,b].map(({official})=>({snapshot_time:official.snapshot_time,report_count:official.report_count,provenance:official.provenance})));
}else{
  assert.deepEqual([a.official.report_count,b.official.report_count,c.official.report_count],[1,2,2]);assert.ok(b.official.snapshot_time>a.official.snapshot_time);
  console.log('PASS: two v2 refreshes on one mounted plugin; next ordinary read is cached (public HTTP fixtures)');
}
// Exercise the compiled Client in the real Gateway/Cordis fibers, with only the carrier and UI slots stubbed.
const {runInNewContext}=await import('node:vm');
const gateway=await import('@deepseek-ai/dsh-api-gateway/client');
const client=new Context();const calls=[],effects=[];let view,bundle,official;
assert.equal(typeof dispatch,'function');
const peer={principal:{kind:'owner'},signal:new AbortController().signal};
client.provide('connection',{interactions:'none',rpc:{open(){},async call(route,endpoint,body){
  const reply=await dispatch(endpoint,JSON.parse(JSON.stringify(body)),peer.signal,peer);
  calls.push([route,endpoint,body.args.request.action,reply.ok?null:reply.error.code]);
  return reply;
}}});
client.provide('slots',{inject:(key,fn)=>fn(),register:(options,component)=>{view=component;}});client.provide('locale',{resolveText:l=>l.en});client.provide('sidebarRightTabs',{register(){return ()=>{};}});
client.plugin(Registry);client.plugin(gateway);
const react={createElement(){},useRef:value=>({current:value}),useState:value=>[value,next=>{if(next?.snapshot_time)official=next;}],useEffect:fn=>effects.push(fn)};
runInNewContext(fs.readFileSync(new URL('../client.js',import.meta.url),'utf8'),{window:{__ModuleLoader__:{load:m=>{bundle=m.factory(id=>id==='react'?react:createRequire(path.join(base,'package.json'))(id));}}}});
client.plugin(bundle);for(let i=0;!view&&i<50;i++)await new Promise(r=>setImmediate(r));assert.equal(typeof view,'function');view();effects.forEach(fn=>fn());for(let i=0;!official&&i<50;i++)await new Promise(r=>setImmediate(r));
assert.deepEqual(calls,legacy?[
  ['/api','epidemicTracker/panel','official','gateway/input-invalid'],
  ['/api','epidemicTracker/panel','snapshot',null],
]:[['/api','epidemicTracker/panel','official',null]]);
assert.equal(official?.snapshot_time,b.official.snapshot_time);
assert.equal(official?.report_count,b.official.report_count);
console.log(`PASS: installed Client and Host Gateway (${legacy?'legacy strict codec with read-only fallback':'current strict codec'}, no profile)`);
