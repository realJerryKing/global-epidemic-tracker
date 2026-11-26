import fs from 'node:fs/promises';
const read=name=>fs.readFile(new URL(name,import.meta.url),'utf8');
const contract=(await read('contract.js')).replace(/^export /gm,'');
const raw=JSON.parse(await read('../docs/data/epidemics.json'));
if(raw.schema_version!==2 || !Number.isFinite(Date.parse(raw.last_update)) || !Array.isArray(raw.outbreaks) || !raw.outbreaks.length || raw.outbreaks.length!==raw.summary.report_count)throw Error('Invalid public snapshot');
const bundled={status:'available',scope:'global',snapshot_time:new Date(raw.last_update).toISOString(),legacy:raw.legacy===true,report_count:raw.outbreaks.length,sources:['who_don','who_gho','owid'].filter(s=>raw.outbreaks.some(r=>r.source===s)),provenance:'bundled',source_url:'https://realJerryKing.github.io/global-epidemic-tracker/data/epidemics.json'};
const catalog=(await import('../docs/regions.js')).regions.map(({code,name})=>({code,name}));
const assets=`export const bundledOfficial=${JSON.stringify(bundled)};\nexport const publicRegions=${JSON.stringify(catalog)};\n`;
await fs.writeFile(new URL('public-data.js',import.meta.url),assets);
const client=`window.__ModuleLoader__.load({id:'@local/dsh-epidemic-tracker', factory(require){\n${contract}\n${assets.replace(/^export /gm,'')}\n${await read('panel.src.js')}\n}});\n`;
new Function('window',client); // validate before replacing the installable artifact
await fs.writeFile(new URL('client.js',import.meta.url),client);
