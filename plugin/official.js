export const SITE = 'https://realJerryKing.github.io/global-epidemic-tracker/';
export const OFFICIAL_URL = SITE + 'data/v2/epidemics.json';
const sources = ['who_don', 'who_gho', 'owid'];

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
  };
}
