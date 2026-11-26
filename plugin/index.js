import {createRequire} from 'node:module';
import path from 'node:path';
// Local bundles may be linked outside the host's node_modules tree.
const hostRoot = process.env.DSH_INSTALL_DIR || (process.resourcesPath && path.join(process.resourcesPath, 'app.asar', 'dsh'));
const hostRequire = createRequire(hostRoot ? path.join(hostRoot, 'package.json') : import.meta.url);
const schemaModule = hostRequire('@deepseek-ai/schemastery');
const Schema = schemaModule.default ?? schemaModule;
const {TypertRemoteService, Remote} = hostRequire('@deepseek-ai/dsh-typert-protocol');
const {credentialKey} = hostRequire('@deepseek-ai/dsh-credentials');
const {defineTool} = hostRequire('@deepseek-ai/dsh-tools');
import {createHash} from 'node:crypto';
import {desktopVault} from './vault.js';
import {Tracker,endpoint} from './core.js';
import {pkg,service,panelDescriptors} from './contract.js';
const descriptors = panelDescriptors(hostRequire('zod'));
const initializers=[];
export default class EpidemicTracker extends TypertRemoteService {
  static inject=['typert','credentials','tools'];
  static Config=Schema.object({backendUrl:Schema.string().default(''),defaultRegion:Schema.string().default('000000')});
  constructor(ctx,config){
    super(ctx,service);for(const initialize of initializers) initialize.call(this);
    const base=endpoint(config.backendUrl);
    const key=credentialKey('epidemic-tracker','backend-'+createHash('sha256').update(base??'disabled').digest('hex'));
    const vault=desktopVault();this.tracker=new Tracker({backend:base,region:config.defaultRegion,store:{
      bound:async()=>Boolean((await ctx.credentials.describeRecord(key))?.configured),
      read:async()=>{const sealed=(await ctx.credentials.readRecord(key))?.payload?.sealed;return sealed?vault.open(sealed):undefined;},
      enroll:issue=>ctx.credentials.modifyRecord(key,async existing=>{if(existing)throw new Error('已绑定');vault.check();return {kind:'grant',payload:{sealed:vault.seal(await issue())}};})
    }});
    ctx.typert.register({package:pkg,face:'host',schemas:[],model:{services:[],events:[],objects:[]},invocations:descriptors});
    ctx.tools.register(defineTool({name:'epidemic_snapshot',description:'读取与疫情侧栏相同的地区社区周报及全球官方背景；仅汇总，不含个人签到。',parameters:{region_code:{type:'string',description:'六位行政区代码；省略时使用默认地区。'}},output:{schema:{type:'string'},render:(_,value)=>[{type:'text',text:value}]},execute:async(args,exec)=>JSON.stringify(await this.tracker.snapshot(args.region_code,exec.signal))}));
  }
  async panel(request){
    if(this.ctx.invocation?.peer.principal.kind!=='owner')throw new Error('仅限宿主所有者');
    try{const {action,...p}=request;const value=action==='snapshot'?await this.tracker.snapshot(p.region_code,this.ctx.invocation.signal):await this.tracker.privateAction(action,p);if(action==='snapshot')this.tracker.region=value.requested_region_code;return {ok:true,value};}catch(e){const safe=['OS 安全存储不可用','参数无效','服务地址须为 HTTPS 或本机回环地址','尚未配置服务','凭据无效','未获授权','未找到记录','当前状态冲突','服务未接受输入','请求过于频繁','请选择星期一','请先绑定一次性邀请码','请确认撤回','请检查输入并明确同意','已绑定'];return {ok:false,error:safe.includes(e.message)?e.message:'操作未完成，请检查连接后重新读取状态。'};}
  }
}
Remote(EpidemicTracker.prototype.panel,{kind:'method',private:false,static:false,name:'panel',addInitializer(fn){initializers.push(fn);}});
