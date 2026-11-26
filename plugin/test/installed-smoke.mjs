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
ctx.provide('credentials');ctx.provide('tools');ctx.set('credentials',{describeRecord:async()=>({configured:false})});ctx.set('tools',{register(t){tool=t;}});ctx.on('internal/error',(err)=>console.error(err));const registry=ctx.plugin(Registry);await new Promise(r=>setImmediate(r));const plugin=ctx.plugin(Plugin,{});await new Promise(r=>setImmediate(r));if(!ctx.epidemicTracker)console.error('status',registry.status,plugin.status,Boolean(ctx.typert),Boolean(ctx.tools),Boolean(ctx.credentials),plugin.error);const host=ctx.epidemicTracker;assert.ok(host);assert.equal(remoteMethods(host)[0].method,'panel');assert.equal(tool.name,'epidemic_snapshot');await assert.rejects(host.panel({action:'setup'}));console.log('PASS: installed Cordis service + Typert registry + owner guard + tool registration (no profile)');
globalThis.fetch=realFetch;
const getSnapshot=async refresh=>JSON.parse(await tool.execute({region_code:'440106',refresh},{}));
const a=await getSnapshot(true),b=await getSnapshot(true),c=await getSnapshot(false);
assert.equal(hits,2);assert.deepEqual([a.official.provenance,b.official.provenance,c.official.provenance],['published','published','cached']);
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
const client=new Context();const calls=[],effects=[];let view,bundle;
client.provide('connection',{interactions:'none',rpc:{open(){},async call(route,endpoint,body){calls.push([route,endpoint,body.args.request.action]);return {ok:true,value:{ok:true,value:{region:'000000',week:'2026-11-23',backend:null}}};}}});
client.provide('slots',{inject:(key,fn)=>fn(),register:(options,component)=>{view=component;}});client.provide('locale',{resolveText:l=>l.en});client.provide('sidebarRightTabs',{register(){return ()=>{};}});
client.plugin(Registry);client.plugin(gateway);
const react={createElement(){},useRef:value=>({current:value}),useState:value=>[value,()=>{}],useEffect:fn=>effects.push(fn)};
runInNewContext(fs.readFileSync(new URL('../client.js',import.meta.url),'utf8'),{window:{__ModuleLoader__:{load:m=>{bundle=m.factory(id=>id==='react'?react:createRequire(path.join(base,'package.json'))(id));}}}});
client.plugin(bundle);for(let i=0;!view&&i<50;i++)await new Promise(r=>setImmediate(r));assert.equal(typeof view,'function');view();effects.forEach(fn=>fn());await new Promise(r=>setImmediate(r));assert.deepEqual(calls,[['/api','epidemicTracker/panel','setup'],['/api','epidemicTracker/panel','snapshot']]);console.log('PASS: installed Client Gateway mounts the namespace and starts independent setup and public snapshot calls through /api (no profile)');
