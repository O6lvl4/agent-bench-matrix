"""Offline reproduction from exact source slices. Never evaluates fetched JS."""
from pathlib import Path
import collections, hashlib, json, math, re, sys
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from refresh_research_security_horizon import literal_at
manifest = json.loads((HERE / 'source-slices.json').read_text())
for item in manifest['slices']:
    raw = (ROOT / item['path']).read_bytes()
    assert len(raw) == item['bytes'] == item['end_byte_exclusive'] - item['start_byte_inclusive']
    assert hashlib.sha256(raw).hexdigest() == item['sha256']
tasks = json.loads(literal_at((HERE / 'task-results.literal.js').read_text(), 'tasks:JSON.parse('))
filters = (HERE / 'filters.js').read_text()
excluded = set(literal_at(filters, ',it=new Set('))
assert 'return t||n||r||i||a?$e(e)===`max`:!0' in filters
assert 'e.reasoningEffort?e.reasoningEffort:`max`' in filters
agg = (HERE / 'aggregation.js').read_text()
for expression in ['t.configs.filter(e=>!at(e))', 'if(!rt(t))continue', 'e.reward>=1', 'e.trials.reduce((e,t)=>e+t.partial,0)/e.trials.length']:
    assert expression in agg
snapshot = json.loads((ROOT / 'sources/swe-marathon-v1-1/task_results_trimmed-2026-11-12.json').read_text())
assert set(tasks) == set(snapshot['task_ids'])
groups = collections.defaultdict(list)
for task in tasks.values():
    for config in task['configs']:
        model, agent = config['model'], config['agent']
        effort = config.get('reasoningEffort') or 'max'
        if model in excluded:
            continue
        maxonly = ((agent == 'Codex' and re.fullmatch(r'GPT-5\.6-(?:sol|terra|luna)', model))
                   or (agent == 'Claude Code' and model in ['Claude Opus 5', 'Claude Opus 5.5', 'Claude Sonnet 5', 'GLM 5.3', 'GLM 5.3 Flash', 'Claude Fable 5.1'])
                   or (agent == 'Codex' and model == 'GPT-6 Astra'))
        if maxonly and effort != 'max':
            continue
        groups[(model, agent, effort)].extend(config['trials'])
table = json.loads((ROOT / 'data/tables/swe-marathon-v1-1.json').read_text())
assert len(table['rows']) == len(groups) == 19
for row in table['rows']:
    key = (row['model_raw'][0], row['agent'], row['model_config'].split('reasoning_effort=')[1].split(';')[0])
    trials = groups[key]
    expected = {'trials': len(trials), 'partial_avg_pct': 100 * sum(t['partial'] for t in trials) / len(trials)}
    costs = [t['costUsd'] for t in trials if t.get('costUsd') is not None]
    tokens = [t['tokensRaw'] for t in trials if t.get('tokensRaw', 0) > 0]
    expected['cost_trials'] = len(costs)
    if costs:
        expected['cost_avg_usd'] = sum(costs) / len(costs)
    if tokens:
        expected['tokens_avg_m'] = sum(tokens) / len(tokens) / 1e6
    assert math.isclose(row['score'], 100 * sum(t['reward'] >= 1 for t in trials) / len(trials), abs_tol=1e-10)
    assert set(expected) == set(row['score_extra'])
    assert all(math.isclose(row['score_extra'][k], v, abs_tol=1e-10) for k, v in expected.items())
print('Verified source slice hashes and all 19 rows, including trials, costs, tokens and partial scores.')
