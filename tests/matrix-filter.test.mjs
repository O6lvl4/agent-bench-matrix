import { JSDOM } from 'jsdom';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

const root = new URL('../docs/', import.meta.url);
const html = await fs.readFile(new URL('index.html', root), 'utf8');
const row = (id, date) => ({ model_ids: [id], model_raw: [id], score: 50, date, system: id });
const table = (id, rows) => ({ id, name: id, category: 'coding', unit: '%', higher_is_better: true, rows });
const data = {
  generated: '2026-11-13', claims: [], gaps: [],
  models: ['recent', 'old', 'undated'].map(id => ({ id, name: id, vendor: 'Test', open_weights: id === 'old' })),
  tables: [table('recent-board', [row('recent', '2026-11-01')]),
    table('old-board', [row('old', '2024-01-01')]), table('undated-board', [row('undated', null)])],
};

test('matrix defaults to all dates and preserves explicit filters, links and navigation', async () => {
  const dom = new JSDOM(html, { url: 'https://example.test/', pretendToBeVisual: true });
  for (const key of ['window', 'document', 'Node', 'location', 'history', 'URLSearchParams']) globalThis[key] = dom.window[key];
  globalThis.fetch = async name => ({ ok: name === 'data.json', status: 404, json: async () => structuredClone(data) });
  await import(new URL('app.js?matrix-filter-test', root));
  const wait = async fn => { for (let i = 0; !fn() && i < 100; i++) await new Promise(r => setTimeout(r, 10)); assert(fn()); };
  const goto = async hash => { await new Promise(resolve => { window.addEventListener('hashchange', resolve, { once: true }); location.hash = hash; }); };
  const count = () => document.querySelectorAll('.matrix tbody tr').length;
  const toggle = () => [...document.querySelectorAll('label')].find(l => l.textContent.includes('古いモデル・表も出す')).querySelector('input');
  try {
    await wait(() => document.querySelector('.matrix'));
    assert.equal(count(), 3);
    assert.equal(toggle().checked, true);
    assert.equal(document.querySelectorAll('thead tr.col th').length, 3);
    toggle().click();
    assert.equal(count(), 1);
    assert(location.hash.includes('all=0'));
    assert.equal(toggle().checked, false);
    await goto('#/matrix?all=1&guess=0');
    assert.equal(count(), 3);
    await goto('#/matrix?all=0&guess=0');
    assert.equal(count(), 1);
    toggle().click();
    assert.equal(count(), 3);
    assert(location.hash.includes('all=1'));
    assert(location.hash.includes('guess=0'));
    await goto('#/matrix?q=undated');
    assert.equal(count(), 1);
    assert(document.querySelector('.matrix').textContent.includes('undated'));
    await goto('#/matrix?open=1');
    assert.equal(count(), 1);
    assert(document.querySelector('.matrix').textContent.includes('old'));
    await goto('#/matrix?all=0');
    await goto('#/matrix');
    assert.equal(count(), 3);
    history.back();
    await wait(() => count() === 1);
    history.forward();
    await wait(() => count() === 3);
  } finally { dom.window.close(); }
});
