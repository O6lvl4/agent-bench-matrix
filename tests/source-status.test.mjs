import { JSDOM } from 'jsdom';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import test from 'node:test';

const root = new URL('../docs/', import.meta.url);
const html = await fs.readFile(new URL('index.html', root), 'utf8');
const original = JSON.parse(await fs.readFile(new URL('data.json', root), 'utf8'));
const warning = '最新未確認・保存データ';
let serial = 0;

async function setup(status) {
  const data = structuredClone(original);
  const table = data.tables.find(t => t.id === 'assistantbench');
  assert(table, 'AssistantBench fixture must exist');
  // Use two independently scoped boards, even if production later adds more statuses.
  data.tables = [table, data.tables.find(t => t.id !== table.id)];
  for (const t of data.tables) delete t.refresh;
  if (status) table.refresh = {
    status, checked: '2026-11-07', last_successful_check: '2026-10-02',
    runtime_stage: 'RUNTIME_ERROR', reason_ja: '<img src=x onerror="alert(1)"> 公式を確認できません。',
    audit: 'sources/assistantbench/audit.json',
  };
  const dom = new JSDOM(html, { url: 'https://example.test/#/table/assistantbench', pretendToBeVisual: true });
  for (const key of ['window', 'document', 'Node', 'location', 'history', 'URLSearchParams']) globalThis[key] = dom.window[key];
  globalThis.fetch = async name => ({ ok: name === 'data.json', status: 404, json: async () => data });
  await import(new URL(`app.js?source-status-test=${++serial}`, root));
  for (let i = 0; !document.querySelector('.table-head') && i < 100; i++) await new Promise(r => setTimeout(r, 10));
  assert(document.querySelector('.table-head'), 'app booted');
  const goto = async hash => {
    await new Promise(resolve => { window.addEventListener('hashchange', resolve, { once: true }); location.hash = hash; });
  };
  return { dom, table, data, goto };
}

for (const status of ['unavailable', 'review_required', 'current', null]) {
  test(`source status ${status || 'absent'} remains scoped across views`, async () => {
    const { dom, table, data, goto } = await setup(status);
    try {
      const saved = status === 'unavailable' || status === 'review_required';
      const view = () => document.querySelector('#view');
      const checkStatus = container => {
        assert.equal(container.textContent.includes(warning), saved);
        assert.equal(Boolean(container.querySelector('.source-status')), Boolean(status));
        if (status) {
          const notice = container.querySelector('.source-status');
          assert(notice.textContent.includes(`保存データ取得 ${table.retrieved}`));
          assert(notice.textContent.includes('最終成功確認 2026-10-02'));
          assert(notice.textContent.includes('最終確認試行 2026-11-07'));
          assert.equal(notice.querySelector('a').href, 'https://github.com/O6lvl4/agent-bench-matrix/blob/main/sources/assistantbench/audit.json');
          assert.equal(notice.querySelector('a').rel, 'noopener noreferrer');
          assert.equal(notice.querySelector('img'), null);
          if (saved) assert(notice.textContent.includes('<img src=x'));
        }
      };
      checkStatus(view());
      assert.equal(view().querySelectorAll('.plain tbody tr').length, table.rows.length);
      const beforeScores = [...view().querySelectorAll('.plain tbody tr')].map(row => row.children[4].textContent);
      assert(beforeScores.some(score => score !== '—'));
      await goto('#/benchmarks');
      const cards = [...view().querySelectorAll('.card')];
      checkStatus(cards.find(c => c.querySelector('h3').textContent === table.name));
      assert(!cards.find(c => c.querySelector('h3').textContent !== table.name).querySelector('.source-status'));
      await goto('#/matrix?all=1&guess=0');
      const headers = [...view().querySelectorAll('thead tr.col th')];
      const index = headers.findIndex(h => h.querySelector('.colhead').textContent.startsWith(table.name));
      assert(index >= 0);
      assert.equal(headers[index].textContent.includes(warning), saved);
      assert.equal(Boolean(headers[index].querySelector('.source-status-compact')), Boolean(status));
      headers.filter((_, i) => i !== index).forEach(h => assert(!h.textContent.includes(warning)));
      const button = [...view().querySelectorAll('tbody tr')].map(row => row.querySelectorAll('td')[index]?.querySelector('button')).find(Boolean);
      const score = button.textContent;
      button.click();
      assert.equal(document.querySelector('#drawer').hidden, false);
      checkStatus(document.querySelector('#drawer-body'));
      assert(document.querySelector('#drawer-body .score').textContent.includes(score));
      document.querySelector('#drawer-close').click();
      assert.equal(document.querySelector('#drawer').hidden, true);
      button.click();
      document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
      assert.equal(document.querySelector('#drawer').hidden, true);
      button.click();
      await goto('#/table/assistantbench');
      assert.equal(document.querySelector('#drawer').hidden, true);
      checkStatus(view());
      assert.deepEqual([...view().querySelectorAll('.plain tbody tr')].map(row => row.children[4].textContent), beforeScores);
      await goto(`#/table/${data.tables[1].id}`);
      assert(!view().querySelector('.source-status'));
    } finally { dom.window.close(); }
  });
}

test('missing successful check is not replaced by retrieval or attempt; unsafe audit is omitted', async () => {
  const { dom, table, goto } = await setup('unavailable');
  try {
    table.refresh.last_successful_check = null;
    table.refresh.audit = 'javascript:alert(1)';
    await goto('#/benchmarks');
    const notice = document.querySelector('.source-status');
    assert(notice.textContent.includes('最終成功確認 記録なし'));
    assert.equal(notice.querySelector('a'), null);
  } finally { dom.window.close(); }
});
