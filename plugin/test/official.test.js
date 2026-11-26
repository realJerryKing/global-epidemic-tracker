import assert from 'node:assert/strict';
import test from 'node:test';
import {summarizeOfficial} from '../official.js';

const base = 'https://www.who.int/emergencies/disease-outbreak-news/item/';
const notice = (id, day, fields = {}) => ({source:'who_don', disease:`Notice ${id}`, date_reported:`2026-11-${day}`, source_url:base+id, ...fields});

test('brief presents five distinct WHO notices in publication order', () => {
  const rows = [1,2,3,4,5,6].map(i=>notice(`don${i}`,`0${i}`));
  rows.push(notice('don6','02',{source_url:base+'don6/?utm_source=test'}),
    notice('external','28',{source_url:'https://example.org/report'}),
    notice('bad-date','31'),notice('other','29',{source:'who_gho'}));
  const raw = {schema_version:2,legacy:false,last_update:'2026-11-30T00:00:00Z',outbreaks:rows,summary:{report_count:rows.length}};
  const result = summarizeOfficial(raw,'published');
  assert.equal(result.report_count,10);
  assert.deepEqual(result.recent_reports.map(({url})=>url),[6,5,4,3,2].map(i=>base+`don${i}`));
  assert.deepEqual(result.recent_reports[0],{title:'Notice don6',date:'2026-11-06',url:base+'don6'});
  assert.deepEqual(summarizeOfficial(raw,'bundled').recent_reports,result.recent_reports);
});
