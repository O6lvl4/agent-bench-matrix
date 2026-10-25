#!/usr/bin/env python3
"""Deterministic UI projection of reviewed source evidence, not a price fetcher."""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
models = json.loads((ROOT / 'sources/cost/model-research.json').read_text())
prices = json.loads((ROOT / 'sources/cost/prices/model-cost-prices.json').read_text())
profiles = [p for p in models['profiles'] if p['modeled_fit_eligible']]
for p in profiles:
    p['runtime'] = ['llama.cpp CUDA', 'llama.cpp Metal']
    for source in p['sources']:
        source['snapshot_file'] = 'sources/cost/models/' + source['snapshot_file']
history = prices['history']
for row in history:
    row['seller'] = '価格.com掲載最安値（同一SKU）'
# One exact GPU SKU per row/series. Additional sold-out variants remain in research.
offers = [o for o in prices['offers'] if o.get('source_id') != 'dospara-msi-5060ti'
          and o.get('sku') != 'RTX5090AMPEX32G/ZT-B50900B-10P']
for hardware in prices['hardware']:
    if hardware['id'] == 'rtx-5060-ti-16gb':
        hardware.update(name='Palit RTX 5060 Ti 16GB Infinity 3', sku='NE7506T019T1-GB2061S')
    if hardware['id'] == 'rtx-5090-32gb':
        hardware.update(name='PNY RTX 5090 32GB OC', sku='VCG509032TFXPB1-O')
    if hardware['id'] == 'rtx-3090-24gb':
        hardware.update(name='中古 RTX 3090 24GB（じゃんぱら掲載品）', sku='67707793-67')
result = {
    'schema_version': 1, 'retrieved': max(datetime.fromisoformat(models['retrieved_at_utc'].replace('Z', '+00:00')), datetime.fromisoformat(prices['observed_at'].replace('Z', '+00:00'))).isoformat(), 'market': 'JP', 'currency': 'JPY',
    'profiles': profiles, 'hardware': prices['hardware'], 'offers': offers + history,
    'price_provenance': prices['provenance'], 'limitations': prices['limitations'],
    'research_only': [{'model_id': p['model_id'], 'reason_ja': '重みとMXFP4対応ランタイムは確認済みですが、このモデルはsliding/full attentionが混在し、機種ごとの実メモリ確保量は未検証です。このページでは自動のハードウェア容量判定と費用算定の対象外です。非対応ランタイムという意味ではありません。'}
                      for p in models['profiles'] if not p['modeled_fit_eligible']]}
(ROOT / 'data/cost.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
