import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_cost', ROOT / 'scripts/build_cost.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CostDataTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/cost.json').read_text())
        self.registry = {m['id']: m for m in json.loads((ROOT / 'data/models.json').read_text())['models']}
    def test_valid(self):
        self.assertEqual(module.validate(self.data, self.registry), [])
    def test_profile_evidence_hashes_and_dimensions(self):
        for profile in self.data['profiles']:
            for source in profile['sources']:
                snapshot = ROOT / source['snapshot_file']
                self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), source['snapshot_sha256'])
            config_source = next(s for s in profile['sources'] if s['snapshot_file'].endswith('.config.json'))
            config = json.loads((ROOT / config_source['snapshot_file']).read_text())
            for key, original in [('layers','num_hidden_layers'), ('kv_heads','num_key_value_heads'), ('head_dim','head_dim')]:
                self.assertEqual(profile['config'][key], config[original])
            artifact = profile['artifact']
            tree = json.loads((ROOT / 'sources/cost/models' / (artifact['repository'].replace('/', '__') + '.tree.json')).read_text())
            selected = next(f for f in tree if f['path'] == artifact['filename'])
            self.assertEqual(artifact['bytes'], selected['size'])
    def test_history_same_sku_and_not_sellable(self):
        hardware = {h['id']:h for h in self.data['hardware']}
        for offer in self.data['offers']:
            if offer.get('source_type') == 'historical_record':
                self.assertEqual(offer['sku'], hardware[offer['hardware_id']]['sku'])
                self.assertIsNone(offer['available'])
    def test_unknown_model(self):
        self.data['profiles'][0]['model_id'] = 'invented'
        self.assertTrue(module.validate(self.data, self.registry))
    def test_missing_source(self):
        self.data['profiles'][0]['sources'] = []
        self.assertTrue(module.validate(self.data, self.registry))
    def test_invalid_prices_and_future(self):
        for value in [-1, float('nan'), float('inf')]:
            data = copy.deepcopy(self.data)
            data['offers'][0]['price_jpy'] = value
            self.assertTrue(module.validate(data, self.registry))
        self.data['offers'][0]['observed_at'] = '2099-01-01T00:00:00Z'
        self.assertTrue(module.validate(self.data, self.registry))
    def test_missing_kv_config(self):
        self.data['profiles'][0]['config']['kv_heads'] = None
        self.assertTrue(module.validate(self.data, self.registry))
    def test_mixed_sku_rejected(self):
        next(o for o in self.data['offers'] if o['hardware_id'] == 'rtx-5060-ti-16gb')['sku'] = 'another-variant'
        self.assertTrue(module.validate(self.data, self.registry))
    def test_duplicates(self):
        self.data['offers'].append(copy.deepcopy(self.data['offers'][0]))
        self.assertTrue(module.validate(self.data, self.registry))

if __name__ == '__main__':
    unittest.main()
