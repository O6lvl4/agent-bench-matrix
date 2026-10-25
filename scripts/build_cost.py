#!/usr/bin/env python3
"""Validate the separately sourced local-run estimates; never alter benchmark data."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def validate(data, registry):
    errors = []
    def require(ok, message):
        if not ok:
            errors.append(message)
    def positive(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0
    def url(v):
        return isinstance(v, str) and v.startswith('https://')
    def date(v):
        try:
            d = datetime.fromisoformat(v.replace('Z', '+00:00'))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, AttributeError):
            return None
    observed = date(data.get('retrieved'))
    require(observed is not None, 'retrieved must be ISO timestamp')
    require(observed is None or observed <= datetime.now(timezone.utc), 'retrieved must not be in the future')
    ids = set()
    for p in data.get('profiles', []):
        mid = p.get('model_id')
        require(mid in registry and registry[mid].get('open_weights') is True, f'{mid}: requires verified open weights')
        require(mid not in ids, f'{mid}: duplicate profile')
        ids.add(mid)
        artifact = p.get('artifact', {})
        require(positive(artifact.get('bytes')) and isinstance(artifact.get('bytes'), int), f'{mid}: exact artifact bytes required')
        require(url(artifact.get('url')) and bool(artifact.get('quantization')), f'{mid}: artifact URL/quantization required')
        require(bool(p.get('runtime')), f'{mid}: runtime required')
        license = p.get('license', {})
        require(bool(license.get('name')) and url(license.get('url')), f'{mid}: license source required')
        require(bool(p.get('sources')) and all(url(s.get('url') if isinstance(s, dict) else s) for s in p.get('sources', [])), f'{mid}: source URLs required')
        cfg = p.get('config', {})
        require(all(positive(cfg.get(k)) and isinstance(cfg.get(k), int) for k in ['layers', 'kv_heads', 'head_dim']), f'{mid}: exact KV config required')
        require(bool(p.get('notes_ja')), f'{mid}: limitations required')
    hardware_ids = set()
    for hw in data.get('hardware', []):
        hid = hw.get('id')
        require(hid and hid not in hardware_ids, f'{hid}: missing/duplicate hardware ID')
        hardware_ids.add(hid)
        require(hw.get('kind') in ['gpu', 'computer'], f'{hid}: invalid hardware kind')
        require(positive(hw.get('memory_gib')), f'{hid}: memory required')
        reserve = hw.get('reserve_gib')
        require(isinstance(reserve, (int, float)) and 0 <= reserve < hw.get('memory_gib', 0), f'{hid}: invalid reserve')
        require(bool(hw.get('runtime')), f'{hid}: runtime required')
    hardware_by_id = {h['id']: h for h in data.get('hardware', [])}
    offers = set()
    for i, offer in enumerate(data.get('offers', [])):
        tag = f'offer {i}'
        require(offer.get('hardware_id') in hardware_ids, f'{tag}: unknown hardware')
        expected_sku = hardware_by_id.get(offer.get('hardware_id'), {}).get('sku')
        require(not expected_sku or offer.get('sku') == expected_sku, f'{tag}: SKU does not match hardware series')
        require(positive(offer.get('price_jpy')), f'{tag}: positive JPY price required')
        d = date(offer.get('observed_at'))
        require(d is not None and (observed is None or d <= observed), f'{tag}: invalid/future observation')
        require(offer.get('tax_included') in [True, False, None], f'{tag}: tax status required')
        require(offer.get('available') in [True, False, None], f'{tag}: availability invalid')
        shipping = offer.get('shipping_jpy')
        require(shipping is None or isinstance(shipping, (int, float)) and math.isfinite(shipping) and shipping >= 0, f'{tag}: invalid shipping')
        require(url(offer.get('url')) and bool(offer.get('seller')) and bool(offer.get('condition')), f'{tag}: seller URL/condition required')
        key = (offer.get('hardware_id'), offer.get('seller'), offer.get('observed_at'), offer.get('url'))
        require(key not in offers, f'{tag}: duplicate observation')
        offers.add(key)
    require(bool(ids) and bool(hardware_ids), 'at least one profile and hardware item required')
    return errors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Verify committed bundle without rewriting')
    args = parser.parse_args()
    data = json.loads((ROOT / 'data/cost.json').read_text())
    registry = {m['id']: m for m in json.loads((ROOT / 'data/models.json').read_text())['models']}
    errors = validate(data, registry)
    if errors:
        raise SystemExit('\n'.join(errors))
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    target = ROOT / 'docs/cost-data.json'
    if args.check:
        if not target.exists() or target.read_text() != rendered:
            raise SystemExit('docs/cost-data.json is stale; run python scripts/build_cost.py')
    else:
        target.write_text(rendered)
    print(f"Cost data valid: {len(data['profiles'])} profiles, {len(data['hardware'])} hardware, {len(data['offers'])} observations")

if __name__ == '__main__':
    main()
