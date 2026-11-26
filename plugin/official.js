export const SITE = 'https://realJerryKing.github.io/global-epidemic-tracker/';
export const OFFICIAL_URL = SITE + 'data/v2/epidemics.json';
const sources = ['who_don', 'who_gho', 'owid'];

function recentReports(rows) {
  const reports = new Map();
  for (const row of rows) {
    if (row.source !== 'who_don') continue;
    const date = row.date_reported;
    if (typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0,10) !== date) continue;
    const title = [row.title, row.disease].find(value => typeof value === 'string' && value.trim())?.trim().slice(0, 200);
    if (!title) continue;
    let url;
    try { url = new URL(row.source_url); } catch { continue; }
    if (url.origin !== 'https://www.who.int' || url.username || url.password || !/^\/emergencies\/disease-outbreak-news\/item\/[a-z0-9-]+\/?$/i.test(url.pathname)) continue;
    const href = url.origin + url.pathname.replace(/\/$/, '');
    if (!reports.has(href) || reports.get(href).date < date) reports.set(href, { title, date, url: href });
  }
  return [...reports.values()].sort((a, b) => b.date.localeCompare(a.date) || a.url.localeCompare(b.url)).slice(0, 5);
}

export function summarizeOfficial(raw, provenance) {
  if (raw?.schema_version !== 2 || typeof raw.legacy !== 'boolean' ||
      typeof raw.last_update !== 'string' || !Number.isFinite(Date.parse(raw.last_update)) ||
      !Array.isArray(raw.outbreaks) || raw.summary?.report_count !== raw.outbreaks.length ||
      (provenance !== 'bundled' && (raw.legacy || raw.outbreaks.length === 0))) {
    throw new Error('Invalid v2 public snapshot');
  }
  const seen = new Set();
  for (const row of raw.outbreaks) {
    if (!sources.includes(row?.source)) throw new Error('Invalid v2 snapshot source');
    seen.add(row.source);
  }
  return {
    status: 'available', scope: 'global', provenance,
    source_url: provenance === 'bundled' ? null : OFFICIAL_URL,
    publication_url: OFFICIAL_URL,
    snapshot_time: new Date(raw.last_update).toISOString(), legacy: raw.legacy,
    report_count: raw.summary.report_count, sources: sources.filter(source => seen.has(source)),
    recent_reports: recentReports(raw.outbreaks),
  };
}
