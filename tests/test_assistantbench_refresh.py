import ast
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('refresh_assistantbench', ROOT / 'scripts/refresh_assistantbench.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = dt.datetime(2026, 11, 7, 12, 30, tzinfo=dt.timezone.utc)


class AssistantBenchRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in [module.TABLE_PATH, 'sources/assistantbench/board_test.json', 'data/models.json', 'sources/audits/2026-10-09/webcomputer.json']:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.table = json.loads((self.root / module.TABLE_PATH).read_text())
        self.table.pop('refresh', None)
        module.write_json(self.root / module.TABLE_PATH, self.table)
        self.snapshot = (self.root / self.table['snapshot']).read_bytes()
        self.board = json.loads(self.snapshot)
        self.meta = dict(id=module.SPACE_ID, host=module.CONFIG_URL.removesuffix('/config'), sha=module.REVIEWED_REVISION, runtime={'stage': 'RUNNING'})
        self.config = {'components': [{'type': 'dataframe', 'props': {'value': self.board}}]}
        self.responses = {module.SPACE_URL: (200, self.meta), module.CONFIG_URL: (200, self.config)}
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        status, body = self.responses[url]
        raw = json.dumps(body).encode()
        return {'url': url, 'status': status, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}, raw

    def run_refresh(self):
        result = module.refresh(self.root, fetcher=self.fetch, now=NOW)
        self.after = json.loads((self.root / module.TABLE_PATH).read_text())
        return result

    def assert_preserved(self):
        self.assertEqual({k: v for k, v in self.after.items() if k != 'refresh'}, self.table)
        self.assertEqual((self.root / self.table['snapshot']).read_bytes(), self.snapshot)

    def test_runtime_error_skips_config_and_preserves_values(self):
        self.meta['runtime']['stage'] = 'RUNTIME_ERROR'
        result = self.run_refresh()
        self.assertEqual(self.calls, [module.SPACE_URL])
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(self.after['refresh']['last_successful_check'], '2026-10-09')
        self.assertEqual(self.after['refresh']['checked'], '2026-11-07')
        self.assert_preserved()
        self.assertTrue((self.root / self.after['refresh']['audit']).exists())

    def test_health_failure_does_not_claim_unchanged(self):
        self.responses[module.SPACE_URL] = (503, 'unavailable')
        self.assertEqual(self.run_refresh()['status'], 'unavailable')
        self.assertEqual(self.calls, [module.SPACE_URL])
        self.assert_preserved()

    def test_running_but_config_fails(self):
        self.responses[module.CONFIG_URL] = (503, 'unavailable')
        self.assertEqual(self.run_refresh()['status'], 'unavailable')
        self.assert_preserved()

    def test_recovery_unchanged_clears_stale_without_changing_retrieval(self):
        self.meta['runtime']['stage'] = 'RUNTIME_ERROR'
        self.run_refresh()
        self.meta['runtime']['stage'] = 'RUNNING'
        later = NOW + dt.timedelta(seconds=1)
        result = module.refresh(self.root, fetcher=self.fetch, now=later)
        self.after = json.loads((self.root / module.TABLE_PATH).read_text())
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(self.after['refresh']['status'], 'current')
        self.assertEqual(self.after['refresh']['last_successful_check'], '2026-11-07')
        self.assert_preserved()

    def test_changed_score_is_mechanically_extracted(self):
        self.board['data'][0][1] = '**51.70**'
        result = self.run_refresh()
        self.assertEqual(result['status'], 'changed')
        self.assertEqual(self.after['rows'][0]['score'], 51.7)
        self.assertEqual(self.after['rows'][0]['model_ids'], self.table['rows'][0]['model_ids'])
        self.assertEqual(self.after['retrieved'], '2026-11-07')
        self.assertNotEqual(self.after['snapshot'], self.table['snapshot'])
        self.assertEqual((self.root / self.table['snapshot']).read_bytes(), self.snapshot)
        self.assertEqual(len(self.after['rows']), 184)

    def test_new_submission_uses_only_reviewed_base_model_mapping(self):
        row = copy.deepcopy(self.board['data'][-1])
        row[0] = '[A new submission](https://example.org/model)'
        self.board['data'].append(row)
        self.assertEqual(self.run_refresh()['status'], 'changed')
        self.assertEqual(len(self.after['rows']), 185)
        self.assertEqual(self.after['rows'][-1]['model_ids'], self.table['rows'][-1]['model_ids'])

    def test_new_model_identity_requires_review(self):
        row = copy.deepcopy(self.board['data'][-1])
        row[0], row[8] = '[New model]()', 'unreviewed-model-name'
        self.board['data'].append(row)
        self.assertEqual(self.run_refresh()['status'], 'review_required')
        self.assert_preserved()

    def test_removed_submission_requires_review(self):
        self.board['data'].pop()
        self.assertEqual(self.run_refresh()['status'], 'review_required')
        self.assert_preserved()

    def test_changed_revision_or_host_is_not_accepted(self):
        for key, value in [('sha', 'a' * 40), ('host', 'https://unrelated.example')]:
            with self.subTest(key=key):
                original = self.meta[key]
                self.meta[key] = value
                result = module.refresh(self.root, fetcher=self.fetch, now=NOW + dt.timedelta(seconds=len(self.calls)))
                self.assertEqual(result['status'], 'review_required')
                self.assertNotIn(module.CONFIG_URL, self.calls)
                self.meta[key] = original

    def test_malformed_frame_properties_record_review_required(self):
        self.config["components"][0]["props"] = None
        self.assertEqual(self.run_refresh()["status"], "review_required")
        self.assert_preserved()

    def test_malformed_runtime_stage_records_review_required(self):
        self.meta["runtime"]["stage"] = {}
        self.assertEqual(self.run_refresh()["status"], "review_required")
        self.assertIsNone(self.after["refresh"]["runtime_stage"])
        self.assert_preserved()

    def test_missing_or_multiple_frames_require_review(self):
        for components in [[], self.config['components'] * 2]:
            with self.subTest(count=len(components)):
                with self.assertRaises(module.ReviewRequired):
                    module.extract_board({'components': components})

    def test_malformed_board_never_reaches_normalized_rows(self):
        for mutate in [lambda b: b.update(headers=['Accuracy']), lambda b: b.update(data=[]),
                       lambda b: b['data'][0].__setitem__(1, float('nan')),
                       lambda b: b['data'][0].__setitem__(1, True),
                       lambda b: b['data'][0].__setitem__(1, 101),
                       lambda b: b['data'][0].__setitem__(0, '[bad](javascript:alert(1))'),
                       lambda b: b['data'].append(copy.deepcopy(b['data'][0]))]:
            board = copy.deepcopy(self.board)
            mutate(board)
            with self.assertRaises(module.ReviewRequired):
                module.validate_board(board)

    def test_stale_cache_is_not_a_new_successful_check(self):
        cache = self.root / 'cache'
        module.collect_to_cache(cache, self.fetch, NOW - dt.timedelta(days=1))
        before = (self.root / module.TABLE_PATH).read_bytes()
        with self.assertRaisesRegex(ValueError, '本日'):
            module.refresh(self.root, cache=cache, now=NOW)
        self.assertEqual((self.root / module.TABLE_PATH).read_bytes(), before)

    def test_corrupt_cache_is_rejected(self):
        cache = self.root / 'cache'
        module.collect_to_cache(cache, self.fetch, NOW)
        (cache / 'assistantbench-config.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'digest'):
            module.refresh(self.root, cache=cache, now=NOW)

    def test_legacy_collectors_and_recipes_delegate_to_health_gate(self):
        for name in ['collect_webcomputer_20261005.py', 'collect_webcomputer_20261007.py']:
            source = (ROOT / 'scripts' / name).read_text()
            ast.parse(source)
            self.assertIn('urls.discard(CONFIG_URL)', source)
            self.assertIn('ix=collect_to_cache(P)', source)
        for name in ['refresh_webcomputer_20261005.py', 'extract_webcomputer_20261007.py']:
            source = (ROOT / 'scripts' / name).read_text()
            ast.parse(source)
            self.assertNotIn("t=T['assistantbench']", source)
            self.assertIn('"status":"managed-separately"', source)

    def test_current_snapshot_normalizes_identically(self):
        registry = {m['id'] for m in json.loads((self.root / 'data/models.json').read_text())['models']}
        self.assertEqual(module.normalize(self.board, self.board, self.table, registry), self.table['rows'])


if __name__ == '__main__':
    unittest.main()
