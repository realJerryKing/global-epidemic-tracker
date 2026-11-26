// node tests/dashboard-browser-smoke.mjs [existing screenshot directory]
// Node >=22; set BROWSER_BIN to a Chromium executable on other platforms.
// Uses only localhost fixtures and a disposable browser profile; no live health API calls.
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as delay} from 'node:timers/promises';
const root=fileURLToPath(new URL('../',import.meta.url));
const bin=process.env.BROWSER_BIN||'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const profile=await mkdtemp(path.join(os.tmpdir(),'atlas-browser-smoke-'));
const official=JSON.parse(await readFile(path.join(root,'docs/data/epidemics.json'),'utf8'));
let mode='available',officialFailure=true,browser,socket;
const server=http.createServer(async(req,res)=>{
  try{
    const u=new URL(req.url,'http://localhost');
    if(u.pathname==='/docs/data/epidemics.json'&&officialFailure){res.writeHead(503);return res.end();}
    if(u.pathname==='/docs/config.js'){res.setHeader('Content-Type','text/javascript');return res.end("window.EPIDEMIC_CONFIG={publicApiBase:'/community'}");}
    if(u.pathname==='/community/v1/reports/latest'){
      res.setHeader('Content-Type','application/json');return res.end(JSON.stringify({requested_region_code:u.searchParams.get('region_code'),region_code:'440100',status:mode,week_start:'2026-11-09',week_end:'2026-11-15',metrics:mode==='available'?{sample_band:'30-59',new_share_band:'0-9%',trend:'insufficient_baseline'}:null}));
    }
    if(!/^\/(index\.html|docs\/(?:data\/epidemics\.json|[\w.-]+))$/.test(u.pathname)){res.writeHead(404);return res.end();}
    const bytes=await readFile(path.join(root,u.pathname));res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.json':'application/json','.svg':'image/svg+xml'})[path.extname(u.pathname)]);res.end(bytes);
  }catch{res.writeHead(404);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
try{
  browser=spawn(bin,['--headless=new','--disable-gpu','--disable-extensions','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
  let startError;browser.on('error',e=>{startError=e;});let tab;
  for(let i=0;i<100&&!tab;i++){
    await delay(100);if(startError)throw startError;if(browser.exitCode!==null)throw Error('Browser startup failed: exit '+browser.exitCode);
    try{const port=(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split(/\r?\n/)[0];tab=(await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t=>t.type==='page');}catch{/* startup */}
  }
  assert.ok(tab,'browser did not expose DevTools');socket=new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  const pending=new Map(),errors=[];let seq=0;
  socket.onmessage=e=>{const d=JSON.parse(e.data);if(pending.has(d.id)){pending.get(d.id)(d);pending.delete(d.id);}if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.text);};
  const rpc=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq,t=setTimeout(()=>{pending.delete(id);reject(Error('Timed out: '+method));},5000);pending.set(id,d=>{clearTimeout(t);if(d.error)reject(Error(JSON.stringify(d.error)));else resolve(d.result);});socket.send(JSON.stringify({id,method,params}));});
  const js=async expression=>{const r=await rpc('Runtime.evaluate',{expression,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.text);return r.result.value;};
  const check=async(expression,label)=>{for(let i=0;i<60;i++){if(await js(expression)){console.log('PASS '+label);return;}await delay(100);}throw Error(label);};
  const snap=async name=>{if(process.argv[2])await writeFile(path.join(process.argv[2],name+'.png'),Buffer.from((await rpc('Page.captureScreenshot')).data,'base64'));};
  await rpc('Runtime.enable');await rpc('Page.enable');await rpc('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await rpc('Page.navigate',{url:`http://127.0.0.1:${server.address().port}/index.html?region=440106`});
  await check("document.querySelector('#weekly-body')?.textContent.includes('上级回退')",'root deep link and explicit parent release');
  await check("document.querySelector('#district').value==='440106'&&document.querySelectorAll('#china-map circle').length===11",'Guangzhou district map and selector');await snap('china-weekly');
  mode='suppressed';await js("document.querySelector('#district').value='440103';document.querySelector('#district').dispatchEvent(new Event('change'))");await check("document.querySelector('#weekly-body').textContent.includes('小样本已隐藏')",'suppression');
  await js("document.querySelector('#global-tab').click()");await check("document.querySelector('#official-retry').hidden===false",'official source failure exposed');officialFailure=false;await js("document.querySelector('#official-retry').click()");await check("document.querySelectorAll('#source-coverage li').length===3",'retry restores source coverage');await check(`document.querySelectorAll('#records li').length===${Math.min(20,official.outbreaks.length)}&&document.querySelectorAll('#world-map circle').length>0`,'official snapshot and map');await snap('world-desktop');
  await js("document.querySelector('#world-map circle').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))");await check("Boolean(document.querySelector('#place').value)",'keyboard map selection');
  await js("document.querySelector('#filters').reset();document.querySelector('#source').value='who_gho';document.querySelector('#source').dispatchEvent(new Event('change',{bubbles:true}))");await check("document.querySelector('#records').textContent.includes('统计年度')",'annual record filtering');
  await rpc('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await check('document.documentElement.scrollWidth===390','390px mobile width');await snap('world-mobile');assert.deepEqual(errors,[]);
}finally{
  socket?.close();if(browser&&browser.exitCode===null)browser.kill();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
  // Only remove the exact temporary directory returned by mkdtemp for this run.
  if(path.dirname(profile)===os.tmpdir()&&path.basename(profile).startsWith('atlas-browser-smoke-'))await rm(profile,{recursive:true,force:true,maxRetries:3,retryDelay:200}).catch(()=>console.warn('Profile still in use:',profile));
}
