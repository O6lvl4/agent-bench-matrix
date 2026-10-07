#!/usr/bin/env python3
"""Refresh the research/security/long-horizon batch from this run's source cache.

Wrap the checked-in mechanical parsers with transactional writes: parse failures
and semantically unchanged tables retain byte-exact table and snapshot files.
Run with --cache-index PATH --audit PATH. No network or registry writes.
"""
import argparse
import copy
import hashlib
import io
import tarfile
import json
import pathlib
import subprocess
import refresh_research_security_horizon as legacy

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATE = '2026-10-07'
legacy.DATE = DATE
BASE_COMMIT = 'b02f0c0505f70d1a8a71456d2615a0ba299e506a'
# Read only the approved baseline for repeatable identity mappings and comparisons.
archive = subprocess.check_output(['git', 'archive', BASE_COMMIT, 'data/tables', 'data/models.json'], cwd=ROOT)
BASE_TABLES = {}
BASE_MODELS = []
legacy.MODELS.clear()
with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
    for member in contents:
        if not member.isfile():
            continue
        if member.name == 'data/models.json':
            BASE_MODELS = json.load(contents.extractfile(member))['models']
            continue
        if not member.name.startswith('data/tables/'):
            continue
        table = json.load(contents.extractfile(member))
        BASE_TABLES[table['id']] = table
        for row in table['rows']:
            if len(row['model_raw']) == len(row['model_ids']) == 1:
                legacy.MODELS.setdefault(row['model_raw'][0], (row['model_ids'], row['model_config']))

for model in BASE_MODELS:
    for name in [model['id'], model['name'], *model.get('aliases', [])]:
        legacy.MODELS.setdefault(name, ([model['id']], None))


class Refresh(legacy.Refresh):
    def save(self, table, content, path=None):
        self.pending[path or table['snapshot']] = content

    def get(self, url):
        record = self.idx[url]
        content = pathlib.Path(record['path']).read_bytes()
        assert hashlib.sha256(content).hexdigest() == record['sha256'], ('cache hash mismatch', url)
        return super().get(url)

    def parse(self, table):
        if table['id'] in ['cybergym-agent-focused', 'cybergym-model-focused']:
            page = self.get('https://www.cybergym.io/cybergym/')
            display = self.get('https://www.cybergym.io/assets/js/leaderboard.js')
            assert 'rows: (j) => (j.level1 || []).filter((r) => r.trials === 1)' in page
            assert 'leadPredicate: (r) => (r.score_10 || 0) > 0.90' in page
            assert 'cfg._rankOffset = leadSorted.length' in display
            rows = super().parse(table)
            if table['id'] == 'cybergym-model-focused':
                assert all(row['score'] <= 90 for row in rows), 'New model-focused lead card requires explicit display-rule extraction'
            # The public board numbers the table after the unranked lead cards.
            lifted = sum(bool(row['score_extra'].get('lead_card_unranked')) for row in rows)
            for row in rows:
                if row['rank'] is not None:
                    row['rank'] += lifted
            table['notes_ja'] = table['notes_ja'].replace(
                'ボードの Type フィルタで分けた表(trials=1 の行のみ表示される)。',
                'ボードの Type フィルタで分けた表(trials=1、dynamic と test-time mem. の両方を含む)。')
            if 'カード数を含めた順位' not in table['notes_ja']:
                table['notes_ja'] += '通常の表の rank は、先頭に表示されるカード数を含めた順位。'
            self.save(table, page, str(pathlib.Path(table['snapshot']).parent / 'display-page.html'))
            self.save(table, display, str(pathlib.Path(table['snapshot']).parent / 'leaderboard.js'))
            return rows
        if table['id'] == 'cybergym-e2e':
            text = self.get(table['fetched'][0])
            data = json.loads(text)
            page = self.get(table['source'])
            assert 'rows: (j) => (j.results || []).filter((r) => !r.hidden)' in page
            assert "(r.focus || 'model') === 'agent'" in page
            rows = []
            for entry in data['results']:
                if entry.get('hidden'):
                    continue
                config = 'Budget: ' + entry['budget']
                matches = [row for row in table['rows'] if row['model_raw'] == [entry['model']] and row['agent'] == entry['harness'] and row['score_extra']['task_set'] == entry['task_set'] and row['model_config'] == config]
                assert len(matches) <= 1, ('ambiguous previous row', entry)
                row = copy.deepcopy(matches[0]) if matches else legacy.base()
                if not matches:
                    row['model_ids'], _ = legacy.model(entry['model'])
                focus = entry.get('focus', 'model')
                assert focus in ['model', 'agent']
                parts = [entry['harness'], entry['model']] if focus == 'agent' else [entry['model'], entry['harness']]
                system = ' · '.join(filter(None, parts))
                if entry['task_set'] == 615:
                    system += ' †'
                row.update(system=system, agent=entry['harness'], model_raw=[entry['model']], model_config=config, score=entry['s3'], date=entry.get('date'), org=entry.get('source'), row_url=entry.get('source_url'))
                row['score_extra'] = {key:entry[source] for key,source in [('patch_only_pct','patch_only'),('s1_pct','s1'),('s2_pct','s2'),('s4_pct','s4'),('task_set','task_set')] if entry.get(source) is not None}
                row['score_extra']['focus'] = focus
                if entry.get('note'):
                    row['score_extra']['note'] = entry['note']
                rows.append(row)
            table['harness_ja'] = '基準行は CyberGym-E2E チームが既成の CLI エージェントを実行。独自の足場による各チームの agent-focused 提出も含む。費用・時間の上限は model_config、タスク集合と区分は score_extra に保持。'
            table['notes_ja'] = 'S1〜S4 は前段をすべて通過したうえでの累積成功率で、ボードの既定の並びは S3。S1〜S3 通過が「発見して修正」成功、S4 は正解の脆弱性との一致。行ごとの公開日付・出典・予算を保持。615 タスク版と 920 タスク版、model-focused と agent-focused の条件差に注意。'
            self.save(table, text)
            self.save(table, page, 'sources/cybergym-e2e/display-page.html')
            return legacy.rank(rows)
        return super().parse(table)

    def run(self, ids=None):
        for path in sorted((ROOT / 'data/tables').glob('*.json')):
            table = json.loads(path.read_text())
            if table['category'] not in ['research', 'security', 'long-horizon'] or (ids and table['id'] not in ids):
                continue
            table = copy.deepcopy(BASE_TABLES[table['id']])
            old = copy.deepcopy(table)
            self.used = []
            self.pending = {}
            proposals_before = copy.deepcopy(legacy.PROPOSALS)
            try:
                rows = self.parse(table)
                assert rows, (table['id'], 'empty result')
                table['rows'] = rows
                table['newest_row_date'] = max((r['date'] for r in rows if r['date']), default=None)
                assert not any(r['date'] and r['date'] > DATE for r in rows), 'future row date'
                def semantic(value):
                    return {k:v for k,v in value.items() if k not in ['retrieved', 'fetched']}
                changed = semantic(table) != semantic(old)
                if changed:
                    table['retrieved'] = DATE
                    for snapshot, content in self.pending.items():
                        target = ROOT / snapshot
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(content)
                    legacy.dump(path.relative_to(ROOT), table)
                before = {json.dumps(r, sort_keys=True, ensure_ascii=False) for r in old['rows']}
                after = {json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows}
                result = {'id':table['id'], 'status':'refreshed_changed' if changed else 'refreshed_unchanged', 'rows_before':len(old['rows']), 'rows_after':len(rows), 'rows_changed_or_added':len(after-before), 'rows_removed_or_changed':len(before-after), 'sources':[self.idx[u] for u in dict.fromkeys(self.used)]}
            except Exception as error:
                legacy.PROPOSALS.clear()
                legacy.PROPOSALS.update(proposals_before)
                result = {'id':table['id'], 'status':'preserved', 'rows_before':len(old['rows']), 'reason':f'{type(error).__name__}: {error}', 'sources':[self.idx[u] for u in dict.fromkeys(self.used)]}
            self.audit.append(result)
            print(table['id'], result['status'], result.get('rows_after'), result.get('reason',''), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache-index', required=True)
    parser.add_argument('--audit', required=True)
    parser.add_argument('--only', nargs='*')
    args = parser.parse_args()
    refresh = Refresh(json.loads(pathlib.Path(args.cache_index).read_text()))
    refresh.run(args.only)
    audit_path = pathlib.Path(args.audit)
    audit_path.write_text(json.dumps({'retrieved':DATE, 'tables':refresh.audit, 'model_proposals':list(legacy.PROPOSALS.values())}, ensure_ascii=False, indent=2) + '\n')
