#!/usr/bin/env python3
"""Extract checked price observations from dated, manually reviewed web snapshots.

This is an offline parser, not a scraper. Source URLs, source retrieval metadata,
the precise product/SKU, excerpts and review decisions live in the input JSON.
It never downloads, infers missing prices, fills gaps, or converts sold-out listings
into currently orderable offers. Append a new dated file to snapshots/ for every
refresh; never replace an older snapshot. Re-running preserves all observed dates.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


def price(text):
    match = re.search(r'(?:[¥￥]\s*)?([0-9][0-9,]*)\s*(?:円|(?=（税込）)|(?=\s*\|))', text)
    if not match:
        raise ValueError(f'No explicit yen amount in {text!r}')
    value = int(match.group(1).replace(',', ''))
    if value <= 0:
        raise ValueError('Price must be positive')
    return value


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def extract(input_path):
    raw = input_path.read_bytes()
    snapshot = json.loads(raw)
    retrieved_at = snapshot['retrieved_at']
    timestamp(retrieved_at)
    try:
        snapshot_file = input_path.resolve().relative_to(Path(__file__).parent.resolve()).as_posix()
    except ValueError:
        snapshot_file = input_path.name
    provenance = {'snapshot_file': snapshot_file,
                  'snapshot_sha256': hashlib.sha256(raw).hexdigest(),
                  'retrieved_at': retrieved_at,
                  'method': snapshot['method']}
    sources = {s['id']: s for s in snapshot['sources']}
    hardware_ids = {h['id'] for h in snapshot['hardware']}
    offers = []
    for review in snapshot['reviewed_offers']:
        for field in ['availability_label_ja', 'lead_time_ja']:
            if not isinstance(review.get(field), str) or not review[field].strip():
                raise ValueError(f'Explicit reviewed {field} required for {review.get("source_id")}')
        source = sources[review['source_id']]
        if source['source_last_crawled'] != 'today':
            raise ValueError('Only crawled-today seller sources belong in current offers')
        evidence = source
        if 'source_entry_index' in review:
            evidence = source['price_entries'][review['source_entry_index']]
        assert review['hardware_id'] in hardware_ids
        offer = {**review,
                 'id': f"{source['id']}-{review.get('source_entry_index', 0)}-{retrieved_at}",
                 'observed_at': snapshot['retrieved_at'],
                 'retrieved_at': snapshot['retrieved_at'],
                 'source_type': 'seller_page',
                 'price_jpy': price(evidence['price_text']),
                 'currency': 'JPY',
                 'url': source['url'],
                 'sku': evidence.get('sku', source.get('sku')),
                 'source_last_crawled': source['source_last_crawled'],
                 'price_scope': 'gpu_card_only' if review['hardware_id'].startswith('rtx-') else 'computer_only'}
        offer.pop('source_entry_index', None)
        if 'price_ex_tax_text' in source:
            offer['price_ex_tax_jpy'] = price(source['price_ex_tax_text'])
        offers.append(offer)

    history_source = sources.get('kakaku-palit-history')
    history = []
    for row in history_source['history_rows'] if history_source else []:
        m = re.fullmatch(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*\|\s*¥([\d,]+)\s*\|\s*[+\d,]+', row)
        if not m:
            raise ValueError(f'Unrecognized historical record {row!r}')
        y, month, day, amount = m.groups()
        date = f'{int(y):04d}-{int(month):02d}-{int(day):02d}'
        history.append({'hardware_id':'rtx-5060-ti-16gb',
                        'sku':history_source['sku'],
                        'observed_at':date,
                        'observed_date':date,
                        'time_precision':'day',
                        'retrieved_at':snapshot['retrieved_at'],
                        'price_jpy':int(amount.replace(',', '')),
                        'tax_included':True,
                        'shipping_jpy':None,
                        'available':None,
                        'condition':'new',
                        'currency':'JPY',
                        'source_type':'historical_record',
                        'metric':'same_sku_aggregator_daily_minimum',
                        'source_id':history_source['id'],
                        'tax_source_id':'kakaku-tax',
                        'url':history_source['url']})
    history.sort(key=lambda x: x['observed_at'])
    assert len({h['observed_at'] for h in history}) == len(history)
    for row in offers + history:
        row['provenance'] = [{**provenance, 'source_id': row['source_id'], 'url': row['url']}]
    return {'schema_version':1,
            'market':'JP',
            'currency':'JPY',
            'observed_at':snapshot['retrieved_at'],
            'provenance':{**provenance, 'extractor':'extract_model_cost_prices.py'},
            'hardware':snapshot['hardware'],
            'offers':offers,
            'history':history,
            'sources':snapshot['sources'],
            'limitations':snapshot['limitations']}


def extract_snapshots(input_path):
    """Deterministically union observations, rejecting conflicting evidence."""
    paths = sorted(input_path.glob('*.json')) if input_path.is_dir() else [input_path]
    if not paths:
        raise ValueError(f'No reviewed snapshots found in {input_path}')
    snapshots = sorted((extract(path) for path in paths),
                       key=lambda item: (timestamp(item['observed_at']), item['provenance']['snapshot_file']))
    observations = {'offers': {}, 'history': {}}
    hardware, source_records, limitations = {}, [], []
    ignored_metadata = {'id', 'retrieved_at', 'provenance'}
    for snapshot in snapshots:
        for item in snapshot['hardware']:
            hardware[item['id']] = item
        for source in snapshot['sources']:
            source_records.append({**source, 'snapshot_provenance': snapshot['provenance']})
        for limitation in snapshot['limitations']:
            if limitation not in limitations:
                limitations.append(limitation)
        for kind, rows in observations.items():
            for row in snapshot[kind]:
                key = (row['hardware_id'], row.get('seller'), row['url'], row['sku'],
                       timestamp(row['observed_at']).isoformat())
                existing = rows.get(key)
                if existing is None:
                    rows[key] = row
                    continue
                comparable = lambda value: {k: v for k, v in value.items() if k not in ignored_metadata}
                if comparable(existing) != comparable(row):
                    raise ValueError(f'Conflicting {kind} observation for {key}')
                for evidence in row['provenance']:
                    if evidence not in existing['provenance']:
                        existing['provenance'].append(evidence)
    order = lambda row: (timestamp(row['observed_at']), row['hardware_id'], row['url'], row['sku'])
    return {'schema_version': 1, 'market': 'JP', 'currency': 'JPY',
            'observed_at': snapshots[-1]['observed_at'],
            'provenance': {
                'method': 'Append-preserving union of dated reviewed snapshots; no interpolation or replacement of older observations.',
                'extractor': 'extract_model_cost_prices.py',
                'snapshots': [item['provenance'] for item in snapshots]},
            'hardware': list(hardware.values()),
            'offers': sorted(observations['offers'].values(), key=order),
            'history': sorted(observations['history'].values(), key=order),
            'sources': source_records, 'limitations': limitations}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('snapshots'),
                        help='Directory of append-only dated JSON snapshots, or a single snapshot')
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('model-cost-prices.json'))
    args = parser.parse_args()
    result = extract_snapshots(args.input)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Extracted {len(result['offers'])} seller observations and {len(result['history'])} genuine historical records -> {args.output}")
