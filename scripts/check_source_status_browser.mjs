// Browser regression coverage for the actual generated bundle, without deployment.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';

const root = new URL('../docs/', import.meta.url);
const artifacts = new URL('../.qa/source-status/', import.meta.url);
const data = JSON.parse(await readFile(new URL('data.json', root), 'utf8'));
const table = data.tables.find(t => t.id === 'assistantbench');
assert(table?.refresh, 'Generated AssistantBench refresh metadata is required');
const saved = ['unavailable', 'review_required'].includes(table.refresh.status);
const warning = '最新未確認・保存データ';
const source = JSON.parse(await readFile(new URL('../data/tables/assistantbench.json', root), 'utf8'));
assert.deepEqual(table.rows, source.rows, 'Generated scores must match the preserved source table');
await mkdir(artifacts, { recursive: true });
const allowed = new Set(['index.html', 'app.js', 'cost.js', 'runtime.js', 'style.css', 'data.json', 'cost-data.json', 'runtime-data.json']);
const server = createServer(async (req, res) => {
  const name = new URL(req.url, 'http://localhost').pathname.slice(1) || 'index.html';
  if (!allowed.has(name)) { res.writeHead(404); res.end(); return; }
  try {
    const body = await readFile(new URL(name, root));
    res.setHeader('Content-Type', name.endsWith('.js') ? 'text/javascript' : name.endsWith('.css') ? 'text/css' : name.endsWith('.json') ? 'application/json' : 'text/html');
    res.end(body);
  } catch { res.writeHead(500); res.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}/`;
let browser, page;
try {
  browser = await chromium.launch({ headless: true });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, colorScheme: 'light' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const checkNotice = async notice => {
    await notice.waitFor({ state: 'visible' });
    const text = await notice.innerText();
    assert.equal(text.includes(warning), saved);
    assert(text.includes(`保存データ取得 ${table.retrieved}`));
    assert(text.includes(`最終成功確認 ${table.refresh.last_successful_check || '記録なし'}`));
    assert(text.includes(`最終確認試行 ${table.refresh.checked}`));
    assert.equal(await notice.getByRole('link', { name: '確認記録' }).getAttribute('href'),
      `https://github.com/O6lvl4/agent-bench-matrix/blob/main/${table.refresh.audit}`);
  };
  const checkFits = async (locator, width) => {
    const box = await locator.boundingBox();
    assert(box && box.x >= -1 && box.x + box.width <= width + 1, `Notice/card overflows ${width}px: ${JSON.stringify(box)}`);
  };
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: width === 1440 ? 1000 : 844 });
    await page.goto(base + '#/table/assistantbench');
    const notice = page.locator('#view .source-status');
    await checkNotice(notice);
    await checkFits(notice, width);
    assert.equal(await page.locator('.plain tbody tr').count(), table.rows.length);
    const scores = await page.locator('.plain tbody tr td:nth-child(5)').allTextContents();
    const expectedScores = [...table.rows].sort((a, b) => (b.score ?? -Infinity) - (a.score ?? -Infinity))
      .map(r => typeof r.score === 'number' ? r.score.toFixed(1) : '—');
    assert.deepEqual(scores, expectedScores, 'Rendered scores must remain unchanged');
    await page.screenshot({ path: new URL(`table-${width}.png`, artifacts).pathname });

    await page.locator('#tabs a[data-view="benchmarks"]').click();
    const card = page.locator('.card').filter({ has: page.locator('h3 a[href="#/table/assistantbench"]') });
    await card.scrollIntoViewIfNeeded();
    await checkNotice(card.locator('.source-status'));
    await checkFits(card, width);
    await card.screenshot({ path: new URL(`card-${width}.png`, artifacts).pathname });
    const otherCard = page.locator('.card').filter({ has: page.locator('h3 a[href="#/table/hal-assistantbench"]') });
    if (await otherCard.count()) assert.equal(await otherCard.locator('.source-saved').count(), 0);

    // all=1 retains this undated board; restrict to web and a measured model for a readable screenshot.
    const modelId = table.rows.find(r => r.model_ids.length === 1 && typeof r.score === 'number').model_ids[0];
    await page.goto(base + `#/matrix?all=1&guess=0&cat=web&q=${encodeURIComponent(modelId)}`);
    const header = page.locator('thead tr.col th').filter({ has: page.locator('.colhead').filter({ hasText: table.name }) });
    await header.scrollIntoViewIfNeeded();
    assert.equal((await header.innerText()).includes(warning), saved);
    assert((await header.locator('.source-status-compact').getAttribute('title')).includes(`最終確認試行 ${table.refresh.checked}`));
    await page.screenshot({ path: new URL(`matrix-${width}.png`, artifacts).pathname });
    const headers = await page.locator('thead tr.col th .colhead').allTextContents();
    const index = headers.findIndex(text => text.startsWith(table.name));
    assert(index >= 0);
    const cell = page.locator(`.matrix tbody tr td:nth-child(${index + 2}) button`).first();
    const score = await cell.innerText();
    for (const closeWith of ['button', 'Escape']) {
      await cell.click();
      await checkNotice(page.locator('#drawer-body .source-status'));
      assert((await page.locator('#drawer-body .score').first().innerText()).includes(score));
      await checkFits(page.locator('#drawer-body .source-status'), width);
      if (closeWith === 'button') {
        await page.screenshot({ path: new URL(`drawer-${width}.png`, artifacts).pathname });
        await page.locator('#drawer-close').click();
      } else await page.keyboard.press('Escape');
      assert.equal(await page.locator('#drawer').isVisible(), false);
    }
    await cell.click();
    await page.locator('#drawer-body a[href="#/table/assistantbench"]').click();
    await checkNotice(page.locator('#view .source-status'));
    assert.equal(await page.locator('#drawer').isVisible(), false);
    assert.deepEqual(await page.locator('.plain tbody tr td:nth-child(5)').allTextContents(), scores);
    await page.goBack();
    await header.waitFor({ state: 'visible' });
    assert.equal(await page.locator('#drawer').isVisible(), false);
    await page.goForward();
    await checkNotice(page.locator('#view .source-status'));
  }
  assert.deepEqual(errors, []);
  console.log('PASS: actual bundle, preserved rows/scores, scoped source warning/dates/audit, desktop/390/320, cards, matrix, drawer, repeated Close/Escape, hash and back/forward navigation.');
} catch (error) {
  if (page) await page.screenshot({ path: new URL('failure.png', artifacts).pathname, fullPage: true }).catch(() => {});
  throw error;
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
