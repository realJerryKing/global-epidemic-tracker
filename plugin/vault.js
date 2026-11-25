// Host-only: an OS-protected ciphertext goes into the DSH credentials record.
// Never use Electron's plaintext Linux basic_text fallback. Non-Desktop installs
// without an OS-backed provider remain read-only rather than saving cleartext.
import {createRequire} from 'node:module';
export function protectWith(storage,platform=process.platform){
  const ready=()=>storage?.isEncryptionAvailable?.() && (platform!=='linux'||['gnome_libsecret','kwallet','kwallet5','kwallet6'].includes(storage.getSelectedStorageBackend?.()));
  function check(){if(!ready())throw new Error('OS 安全存储不可用');}
  return {check,seal(s){check();return storage.encryptString(s).toString('base64');},open(s){check();return storage.decryptString(Buffer.from(s,'base64'));}};
}
import {spawnSync} from 'node:child_process';
import {join} from 'node:path';
function windowsVault(){
  const exe=join(process.env.SystemRoot||'C:\\Windows','System32','WindowsPowerShell','v1.0','powershell.exe');
  const transform=(mode,bytes)=>{const script=`$ErrorActionPreference='Stop';Add-Type -AssemblyName System.Security;$b=[Convert]::FromBase64String([Console]::In.ReadToEnd());$r=[Security.Cryptography.ProtectedData]::${mode}($b,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser);[Console]::Write([Convert]::ToBase64String($r))`;const r=spawnSync(exe,['-NoProfile','-NonInteractive','-Command',script],{input:bytes.toString('base64'),encoding:'utf8',timeout:5000,maxBuffer:16384,windowsHide:true});if(r.status!==0||!r.stdout)throw new Error('OS 安全存储不可用');return Buffer.from(r.stdout,'base64');};return {check:()=>transform('Protect',Buffer.from('probe')),seal:s=>transform('Protect',Buffer.from(s)).toString('base64'),open:s=>transform('Unprotect',Buffer.from(s,'base64')).toString('utf8')};
}
export function desktopVault(){if(process.platform==='win32')return windowsVault();let storage;try{storage=createRequire(import.meta.url)('electron').safeStorage;}catch{}return protectWith(storage);}
