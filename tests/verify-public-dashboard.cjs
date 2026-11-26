// Run with Playwright available on NODE_PATH (see verify-public-pages.yml).
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { chromium } = require('playwright');

async function main() {
  const site = 'https://realjerryking.github.io/global-epidemic-tracker/';
  const dashboard = new URL('docs/v2.html', site);
  dashboard.searchParams.set('verify', Date.now());
  const target = new URL('data/v2/epidemics.json', site).href;
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const snapshotResponse = page.waitForResponse(response => {
      const url = new URL(response.url());
      return `${url.origin}${url.pathname}` === target && response.request().resourceType() === 'fetch';
    }, { timeout: 25000 });
    const [response, navigation] = await Promise.all([
      snapshotResponse, page.goto(dashboard.href, { waitUntil: 'domcontentloaded', timeout: 25000 }),
    ]);
    assert.ok(navigation?.ok(), 'dashboard navigation failed');
    assert.ok(response.ok(), `browser snapshot returned HTTP ${response.status()}`);
    const snapshot = await response.json();
    assert.equal(snapshot.schema_version, 2);
    assert.equal(snapshot.legacy, false);
    assert.deepEqual(snapshot, JSON.parse(readFileSync('data/v2/epidemics.json', 'utf8')), 'browser received a different publication');
    await page.locator('#records li').first().waitFor({ timeout: 15000 });
    await page.waitForFunction(stamp => {
      const updated = document.querySelector('#updated');
      return (updated?.querySelector('time')?.dateTime || updated?.dataset.lastUpdate || updated?.dateTime) === stamp;
    }, snapshot.last_update, { timeout: 15000 });
    console.log(`Dashboard fetched and rendered ${target} (${snapshot.last_update})`);
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
