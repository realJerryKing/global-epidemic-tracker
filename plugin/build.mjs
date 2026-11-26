import fs from 'node:fs/promises';
const read=name=>fs.readFile(new URL(name,import.meta.url),'utf8');
const contract=(await read('contract.js')).replace(/^export /gm,'');
const {SITE,summarizeOfficial}=await import('./official.js');
// This repository's checked-in v2-shaped dataset is the offline build seed.
const bundled=summarizeOfficial(JSON.parse(await read('../docs/data/epidemics.json')),'bundled');
const catalog=(await import('../docs/regions.js')).regions.map(({code,name})=>({code,name}));
const assets=`export const publicMapUrl=${JSON.stringify(SITE+'docs/v2.html')};\nexport const bundledOfficial=${JSON.stringify(bundled)};\nexport const publicRegions=${JSON.stringify(catalog)};\n`;
await fs.writeFile(new URL('public-data.js',import.meta.url),assets);
const client=`window.__ModuleLoader__.load({id:'@local/dsh-epidemic-tracker', factory(require){\n${contract}\n${assets.replace(/^export /gm,'')}\n${await read('panel.src.js')}\n}});\n`;
new Function('window',client); // validate before replacing the installable artifact
await fs.writeFile(new URL('client.js',import.meta.url),client);
