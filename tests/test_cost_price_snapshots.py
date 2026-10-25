import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / 'sources/cost/prices'
spec = importlib.util.spec_from_file_location('extract_cost_prices', PRICES / 'extract_model_cost_prices.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CostPriceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads((PRICES / 'snapshots/2026-10-25.json').read_text())
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        self.addCleanup(self.directory.cleanup)

    def write(self, name, snapshot):
        path = self.path / name
        path.write_text(json.dumps(snapshot, ensure_ascii=False))
        return path

    def test_refresh_retains_original_seller_time_and_deduplicates_history(self):
        first = self.write('2026-10-25.json', self.snapshot)
        later = copy.deepcopy(self.snapshot)
        later['retrieved_at'] = '2026-10-26T06:37:14Z'
        later['sources'][0]['price_text'] = '138,000円'
        second = self.write('2026-10-26.json', later)
        result = module.extract_snapshots(self.path)

        offers = [row for row in result['offers'] if row['source_id'] == 'dospara-palit-5060ti']
        self.assertEqual([(row['observed_at'], row['price_jpy']) for row in offers],
                         [('2026-10-25T06:37:14Z', 129800), ('2026-10-26T06:37:14Z', 138000)])
        self.assertEqual(len(result['offers']), 2 * len(self.snapshot['reviewed_offers']))
        self.assertEqual(len(result['history']), 29)
        self.assertEqual(result['observed_at'], later['retrieved_at'])
        self.assertEqual(result, module.extract_snapshots(self.path))
        for row, path in zip(offers, [first, second]):
            self.assertEqual(row['provenance'][0]['snapshot_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(row['provenance'][0]['url'], row['url'])
        self.assertEqual(len(result['history'][0]['provenance']), 2)
        self.assertEqual(result['history'][0]['retrieved_at'], self.snapshot['retrieved_at'])

    def test_identical_same_timestamp_observations_are_deduplicated(self):
        self.write('2026-10-25.json', self.snapshot)
        self.write('2026-10-25-copy.json', self.snapshot)
        result = module.extract_snapshots(self.path)
        self.assertEqual(len(result['offers']), len(self.snapshot['reviewed_offers']))
        self.assertEqual(len(result['offers'][0]['provenance']), 2)
        self.assertEqual(len(result['history']), 29)

    def test_conflicting_same_timestamp_seller_observation_is_rejected(self):
        self.write('2026-10-25.json', self.snapshot)
        conflicting = copy.deepcopy(self.snapshot)
        conflicting['sources'][0]['price_text'] = '138,000円'
        self.write('2026-10-25-conflict.json', conflicting)
        with self.assertRaisesRegex(ValueError, 'Conflicting offers observation'):
            module.extract_snapshots(self.path)

    def test_conflicting_historical_price_is_rejected_across_refreshes(self):
        self.write('2026-10-25.json', self.snapshot)
        conflicting = copy.deepcopy(self.snapshot)
        conflicting['retrieved_at'] = '2026-10-26T06:37:14Z'
        source = next(item for item in conflicting['sources'] if item['id'] == 'kakaku-palit-history')
        source['history_rows'][0] = source['history_rows'][0].replace('138,000', '139,000')
        self.write('2026-10-26.json', conflicting)
        with self.assertRaisesRegex(ValueError, 'Conflicting history observation'):
            module.extract_snapshots(self.path)

    def test_refresh_can_contain_only_new_seller_evidence(self):
        self.write('2026-10-25.json', self.snapshot)
        later = copy.deepcopy(self.snapshot)
        later['retrieved_at'] = '2026-10-26T06:37:14Z'
        later['sources'] = [later['sources'][0]]
        later['reviewed_offers'] = [later['reviewed_offers'][0]]
        self.write('2026-10-26.json', later)
        result = module.extract_snapshots(self.path)
        self.assertEqual(len(result['history']), 29)
        self.assertEqual(len(result['offers']), len(self.snapshot['reviewed_offers']) + 1)

    def test_refresh_uses_new_reviewed_delivery_and_stock_labels(self):
        self.write('2026-10-25.json', self.snapshot)
        later = copy.deepcopy(self.snapshot)
        later['retrieved_at'] = '2026-10-26T06:37:14Z'
        reviewed = next(row for row in later['reviewed_offers'] if row['source_id'] == 'bic-mini-m5-pro-24')
        reviewed['lead_time_ja'] = '東京都の初期表示先へ10月28日お届け予定'
        reviewed['availability_label_ja'] = '在庫あり（10月26日確認）'
        self.write('2026-10-26.json', later)
        result = module.extract_snapshots(self.path)
        offers = [row for row in result['offers'] if row['source_id'] == 'bic-mini-m5-pro-24']
        self.assertEqual(offers[0]['lead_time_ja'], '東京都の初期表示先へ10月26日お届け予定')
        self.assertEqual(offers[1]['lead_time_ja'], reviewed['lead_time_ja'])
        self.assertEqual(offers[1]['availability_label_ja'], reviewed['availability_label_ja'])

    def test_missing_reviewed_delivery_label_is_rejected(self):
        del self.snapshot['reviewed_offers'][0]['lead_time_ja']
        self.write('2026-10-25.json', self.snapshot)
        with self.assertRaisesRegex(ValueError, 'Explicit reviewed lead_time_ja required'):
            module.extract_snapshots(self.path)


if __name__ == '__main__':
    unittest.main()
