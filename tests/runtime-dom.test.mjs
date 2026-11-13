import { JSDOM } from 'jsdom';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

const root = new URL('../docs/', import.meta.url).pathname;
const html = await fs.readFile(root + 'index.html', 'utf8');
const runtime = JSON.parse(await fs.readFile(root + 'runtime-data.json', 'utf8'));

test('hosted prices stay apart from scores, name their source, and never invent speed', async () => {
  const dom = new JSDOM(html, { url: 'https://example.test/#/runtime', pretendToBeVisual: true });
  for (const k of ['window', 'document', 'Node', 'location', 'history', 'URLSearchParams']) globalThis[k] = dom.window[k];
  globalThis.fetch = async name => ({ ok: true, json: async () => JSON.parse(await fs.readFile(root + name, 'utf8')) });
  await import(root + 'app.js?runtime-test');
  const waitFor = async predicate => { const end = Date.now() + 10000; while (!predicate()) { if (Date.now() > end) throw new Error('timed out'); await new Promise(r => setTimeout(r, 20)); } };
  const goto = async hash => { await new Promise(resolve => { window.addEventListener('hashchange', resolve, { once: true }); location.hash = hash; }); };
  const view = () => document.querySelector('#view');
  try {
    await waitFor(() => document.querySelector('.runtime-index'));
    const models = new Set(runtime.offerings.map(o => o.model_id));
    assert.equal(view().querySelectorAll('.runtime-index tbody tr').length, models.size);
    assert(view().querySelector('.runtime-speed').textContent.includes('速度はまだ取得できていません'));
    assert(!/NaN|undefined/.test(view().textContent));

    const sample = runtime.offerings.find(o => o.source_id === 'cloudflare-workers-ai');
    await goto('#/runtime?model=' + encodeURIComponent(sample.model_id));
    const expected = runtime.offerings.filter(o => o.model_id === sample.model_id);
    const rows = [...view().querySelectorAll('.runtime-table tbody tr')];
    assert.equal(rows.length, expected.length);
    const row = rows.find(r => r.textContent.includes(sample.source_model));
    assert(row.textContent.includes('公式の料金表'));
    assert.equal(row.querySelector('a').rel, 'noopener noreferrer');
    assert(rows.some(r => r.textContent.includes('経由')) === expected.some(o => o.source_id === 'openrouter'));
    assert(!/NaN|undefined/.test(view().textContent));
    // No column, cell or number for speed exists anywhere in the price table.
    assert(![...view().querySelectorAll('.runtime-table th')].some(th => /速度|トークン\/秒/.test(th.textContent)));

    await goto('#/runtime?model=' + encodeURIComponent(sample.model_id) + '&source=cloudflare-workers-ai');
    assert.equal(view().querySelectorAll('.runtime-table tbody tr').length, expected.filter(o => o.source_id === 'cloudflare-workers-ai').length);

    await goto('#/runtime?model=no-such-model');
    assert(view().querySelector('.runtime-empty').textContent.includes('記録にありません'));
    assert(view().querySelector('.runtime-index'));

    await goto('#/ability');
    await waitFor(() => document.querySelector('.ability'));
    assert(document.querySelector('.runtime-model-link'));
  } finally { dom.window.close(); }
});
