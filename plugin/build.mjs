import fs from 'node:fs/promises';
const read=name=>fs.readFile(new URL(name,import.meta.url),'utf8');
const contract=(await read('contract.js')).replace(/^export /gm,'');
const client=`window.__ModuleLoader__.load({id:'@local/dsh-epidemic-tracker', factory(require){\n${contract}\n${await read('panel.src.js')}\n}});\n`;
new Function('window',client); // validate before replacing the installable artifact
await fs.writeFile(new URL('client.js',import.meta.url),client);
