// Real browser QA of the unchanged static application; no deployment is needed.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
const root = new URL('../docs/', import.meta.url);
const artifacts = new URL('../.qa/cost/', import.meta.url);
await mkdir(artifacts, { recursive: true });
const allowed = new Set(['index.html', 'app.js', 'cost.js', 'style.css', 'data.json', 'cost-data.json']);
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
  await page.goto(base + '#/ability?open=1');
  await page.locator('.ability').waitFor();
  assert(await page.locator('.cost-model-link').count() > 0);
  await page.locator('#tabs a[data-view="cost"]').click();
  await page.locator('#cost-model').waitFor();
  assert.equal(await page.locator('#cost-context').inputValue(), '4096');
  assert.equal(await page.locator('.cost-chart-point.historical').count(), 29);
  assert.equal(await page.locator('.cost-chart path, .cost-chart polyline').count(), 0, 'Do not fabricate price interpolation');
  const baseline = await page.locator('.cost-memory-summary').innerText();
  await page.getByRole('button', { name: '8k', exact: true }).click();
  assert.equal(await page.locator('#cost-context').inputValue(), '8192');
  assert.notEqual(await page.locator('.cost-memory-summary').innerText(), baseline);
  await page.locator('#cost-model').selectOption('qwen3-32b');
  assert((await page.locator('.cost-tiers').innerText()).includes('599,800'));
  await page.locator('#cost-history-select').selectOption('mac-studio-m5-max-64gb');
  await page.locator('.cost-history-empty').waitFor();
  assert((await page.locator('#view').innerText()).includes('5〜6週間'));
  await page.locator('#cost-watts').fill('600');
  await page.locator('#cost-watts').press('Tab');
  assert((await page.locator('.cost-energy-result').innerText()).includes('1,116'));
  assert(page.url().includes('watts=600'));
  await page.locator('#cost-model').selectOption('gpt-oss-20b');
  assert((await page.locator('.cost-unsupported').innerText()).includes('MXFP4'));
  await page.locator('#cost-model').selectOption('gpt-5');
  await page.locator('.cost-unsupported').waitFor();
  assert.equal(await page.locator('.cost-energy-result').count(), 0);
  await page.goto(base + '#/cost?model=unknown');
  await page.waitForFunction(() => document.querySelector('.cost-unsupported')?.textContent.includes('登録されていない'));
  assert((await page.locator('.cost-unsupported').innerText()).includes('登録されていない'));
  await page.goto(base + '#/cost?model=qwen3-8b&context=-1&watts=Infinity');
  assert.equal(await page.locator('#cost-context').inputValue(), '4096');
  assert.equal(await page.locator('#cost-watts').inputValue(), '300');
  await page.locator('#tabs a[data-view="ability"]').click();
  await page.locator('.ability').waitFor();
  await page.goBack();
  await page.locator('#cost-model').waitFor();
  await page.goForward();
  await page.locator('.ability').waitFor();
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: width === 1440 ? 1000 : 844 });
    await page.goto(base + '#/cost?model=qwen3-8b&hardware=rtx-5060-ti-16gb');
    await page.locator('.cost-chart').waitFor();
    await page.locator('#cost-model').selectOption('qwen3-32b');
    await page.locator('#cost-model').selectOption('qwen3-8b');
    await page.getByRole('button', { name: '8k', exact: true }).click();
    assert.equal(await page.locator('#cost-context').inputValue(), '8192');
    await page.getByRole('button', { name: '4k', exact: true }).click();
    const overflow = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
    assert(overflow.document <= overflow.viewport + 1, `Page overflows at ${width}px: ${JSON.stringify(overflow)}`);
    const chart = await page.locator('.cost-chart').boundingBox();
    const axisLabel = await page.locator('.cost-chart text').first().boundingBox();
    assert(axisLabel && axisLabel.height >= 9, `Chart axis text too small at ${width}px`);
    assert(chart && chart.x >= 0 && chart.x + chart.width <= width + 1, `Chart overflows at ${width}px`);
    assert.equal(await page.locator('.cost-chart-point.historical').count(), 29);
    assert(!/NaN|undefined/.test(await page.locator('#view').innerText()));
    await page.screenshot({ path: new URL(`cost-${width}.png`, artifacts).pathname, fullPage: true });
    await page.locator('.cost-chart').screenshot({ path: new URL(`history-${width}.png`, artifacts).pathname });
  }
  assert.deepEqual(errors, []);
  console.log('PASS: Chromium desktop/390/320, navigation, model/context/electricity, invalid inputs, history, no page/chart overflow.');
} catch (error) {
  if (page) await page.screenshot({ path: new URL('failure.png', artifacts).pathname, fullPage: true }).catch(() => {});
  throw error;
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
