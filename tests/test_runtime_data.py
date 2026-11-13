import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import runtime_lib as lib  # noqa: E402

CLOUDFLARE = '''# Pricing
## LLM model pricing

| Model | Price in Tokens | Price in Neurons |
| - | - | - |
| @cf/zai-org/glm-5.3 | $1.400 per M input tokens <br> $0.260 per M cached input tokens <br> $4.400 per M output tokens | 127273 neurons |
| @cf/meta/llama-3.3-70b-instruct-fp8-fast | $0.293 per M input tokens <br> $2.253 per M output tokens | 26668 neurons |

## Embeddings model pricing

| @cf/baai/bge-m3 | $0.012 per M input tokens | 1075 neurons |
'''


def bedrock(products):
    doc = {'products': {}, 'terms': {'OnDemand': {}}}
    for i, (model, kind, feature, usd) in enumerate(products):
        sku = f'SKU{i}'
        doc['products'][sku] = {'attributes': {'provider': 'Qwen', 'model': model, 'inferenceType': kind, 'feature': feature,
                                               'usagetype': f'USE1-{model}-{kind}', 'regionCode': 'us-east-1'}}
        doc['terms']['OnDemand'][sku] = {'t': {'priceDimensions': {'d': {'unit': '1K tokens', 'pricePerUnit': {'USD': usd}}}}}
    return doc


class RuntimeExtraction(unittest.TestCase):
    def test_cloudflare_reads_only_the_llm_table_and_keeps_the_deployment_suffix_as_quantization(self):
        rows = lib.parse_cloudflare(CLOUDFLARE)
        self.assertEqual([r['source_model'] for r in rows], ['@cf/zai-org/glm-5.3', '@cf/meta/llama-3.3-70b-instruct-fp8-fast'])
        self.assertEqual((rows[0]['input'], rows[0]['cached_input'], rows[0]['output']), (1.4, 0.26, 4.4))
        self.assertIsNone(rows[1]['cached_input'])
        self.assertEqual(rows[1]['quantization'], 'fp8')
        self.assertIn('llama-3.3-70b', rows[1]['names'])

    def test_cloudflare_without_the_section_is_an_error_not_an_empty_result(self):
        with self.assertRaises(ValueError):
            lib.parse_cloudflare('# Pricing\n')

    def test_bedrock_keeps_standard_on_demand_only_and_converts_per_1k_to_per_million(self):
        rows = lib.parse_bedrock(bedrock([
            ('Qwen3 32B', 'Input tokens', 'On-demand Inference', '0.0001500000'),
            ('Qwen3 32B', 'Output tokens', 'On-demand Inference', '0.0006000000'),
            ('Qwen3 32B', 'Output tokens', 'Batch Inference', '0.0003000000'),
            ('Qwen3 32B', 'Output tokens priority', 'On-demand Inference', '0.0010500000'),
        ]))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['input'], rows[0]['output'], rows[0]['region']), (0.15, 0.6, 'us-east-1'))

    def test_bedrock_conflicting_prices_for_one_model_stop_the_build(self):
        with self.assertRaises(ValueError):
            lib.parse_bedrock(bedrock([
                ('Qwen3 32B', 'Input tokens', 'On-demand Inference', '0.0001500000'),
                ('Qwen3 32B', 'Input tokens', 'On-demand Inference', '0.0002000000'),
            ]))

    def test_ollama_reads_missing_cells_as_missing_and_marks_off_peak(self):
        page = ('<p>Prices are per million tokens.</p><table><tr><td>Model</td><td>Input</td><td>Cached input</td><td>Output</td></tr>'
                '<tr><td>clef</td><td>$0.24</td><td>-</td><td>-</td></tr>'
                '<tr><td>gpt-oss:120b</td><td>$0.15</td><td>$0.014</td><td>$0.60</td></tr>'
                '<tr><td>deepseek-v4-pro (Off-Peak)</td><td>$0.66</td><td>$0.022</td><td>$1.98</td></tr></table>'
                '<h2>Frequently asked questions</h2>')
        rows = lib.parse_ollama(page)
        self.assertEqual([(r['names'][0], r['input'], r['cached_input'], r['output'], r['tier']) for r in rows], [
            ('clef', 0.24, None, None, None), ('gpt-oss:120b', 0.15, 0.014, 0.6, None),
            ('deepseek-v4-pro', 0.66, 0.022, 1.98, 'off-peak')])

    def test_openrouter_skips_variants_and_dynamic_prices_and_never_reads_speed(self):
        endpoint = {'provider_name': 'DeepInfra', 'tag': 'deepinfra/fp4', 'quantization': 'fp4', 'context_length': 1000,
                    'pricing': {'prompt': '0.0000005', 'completion': '0.000002', 'input_cache_read': '0.0000001'},
                    'throughput_last_30m': {'p50': 99.0}, 'latency_last_30m': {'p50': 1.0}}
        rows = lib.parse_openrouter({
            'z-ai/glm-5.3': {'data': {'endpoints': [endpoint, {**endpoint, 'pricing': {'prompt': '-1', 'completion': '-1'}},
                                                    {**endpoint, 'quantization': 'unknown', 'pricing': {'prompt': 'x'}}]}},
            'z-ai/glm-5.3:free': {'data': {'endpoints': [endpoint]}},
        })
        self.assertEqual([(r['names'], r['input'], r['output'], r['cached_input']) for r in rows],
                         [(['glm-5.3'], 0.5, 2.0, 0.1), ([], 0.5, 2.0, 0.1)])
        self.assertFalse(any('throughput' in key or 'latency' in key or 'speed' in key for r in rows for key in r))

    def test_one_spelling_shared_by_two_models_maps_to_neither(self):
        index = lib.registry_index([{'id': 'a-1', 'name': 'Same Name', 'aliases': []}, {'id': 'b-1', 'name': 'same name', 'aliases': ['b_1']}])
        self.assertNotIn('same-name', index)
        self.assertEqual((index['a-1'], index['b-1']), ('a-1', 'b-1'))


class RuntimeBundle(unittest.TestCase):
    def test_committed_bundle_is_what_the_newest_snapshot_builds(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_runtime.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_bundle_holds_no_speed_value_and_every_offering_names_a_saved_source(self):
        data = json.loads((ROOT / 'docs' / 'runtime-data.json').read_text(encoding='utf-8'))
        registry = {m['id'] for m in lib.load_registry()}
        sources = {s['id']: s for s in data['sources']}
        self.assertEqual(data['speed']['status'], 'not_collected')
        for source in sources.values():
            self.assertTrue((ROOT / source['snapshot']).exists(), source['snapshot'])
        for offering in data['offerings']:
            self.assertIn(offering['model_id'], registry)
            self.assertIn(offering['source_id'], sources)
            self.assertGreaterEqual(offering['input_per_mtok'], 0)
            self.assertFalse({'speed', 'throughput', 'latency', 'tokens_per_second'} & set(offering))


if __name__ == '__main__':
    unittest.main()
