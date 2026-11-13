#!/usr/bin/env python3
"""Build docs/runtime-data.json from the newest saved snapshot. Offline.

    python3 scripts/build_runtime.py           # write
    python3 scripts/build_runtime.py --check   # fail if the committed file differs

Prices are observations of one source on one date. They are not benchmark data
and never enter data.json or the fit. Speed is recorded as not collected, with
the reason, rather than left out.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_lib import (ROOT, SNAPSHOTS, SOURCES, load_registry, norm, parse_bedrock, parse_cloudflare,
                         parse_ollama, parse_openrouter, read, registry_index, sha256)

OUTPUT = ROOT / 'docs' / 'runtime-data.json'
PARSERS = {
    'cloudflare-workers-ai': lambda raw: parse_cloudflare(raw.decode('utf-8')),
    'aws-bedrock': lambda raw: parse_bedrock(json.loads(raw)),
    'ollama-cloud': lambda raw: parse_ollama(raw.decode('utf-8')),
    'openrouter': lambda raw: parse_openrouter(json.loads(raw)),
}
SPEED = {
    'status': 'not_collected',
    'reason_ja': '配信元ごとの速度(トークン/秒・初回応答)を認証なしで機械的に取得できる公開元が見つかっていない。'
                 'OpenRouter のエンドポイント API は throughput_last_30m / latency_last_30m を持つが、'
                 'API キーなしの要求には null を返すと仕様に明記されている。このリポジトリは認証情報を使わないので、値を入れていない。',
    'tried': ['https://openrouter.ai/api/v1/models/{id}/endpoints', 'https://openrouter.ai/api/v1/benchmarks'],
}


def build(snapshot_dir):
    manifest = json.loads((snapshot_dir / 'manifest.json').read_text(encoding='utf-8'))
    recorded = {f['file']: f for f in manifest['files']}
    index = registry_index(load_registry())
    sources, offerings, unmatched = [], [], {}
    for source_id, meta in SOURCES.items():
        raw = read(snapshot_dir / meta['file'])
        record = recorded[meta['file']]
        if sha256(raw) != record['sha256']:
            raise ValueError(f'{meta["file"]} does not match the sha256 in its manifest')
        rows = PARSERS[source_id](raw)
        missed = []
        for row in rows:
            ids = {index[norm(n)] for n in row['names'] if norm(n) in index}
            if len(ids) != 1:
                missed.append(row['source_model'])
                continue
            offerings.append({
                'model_id': ids.pop(), 'provider': row['provider'], 'source_id': source_id,
                'source_model': row['source_model'], 'pricing_model': 'per_token', 'currency': 'USD',
                'input_per_mtok': row['input'], 'output_per_mtok': row['output'],
                'cached_input_per_mtok': row['cached_input'], 'context_length': row['context_length'],
                'quantization': row['quantization'], 'tier': row['tier'], 'region': row['region'],
                'tiered': bool(row.get('tiered')),
            })
        unmatched[source_id] = {'rows': len(rows), 'unmatched': len(missed), 'examples': sorted(missed)[:12]}
        sources.append({'id': source_id, 'name': meta['name'], 'kind': meta['kind'], 'url': meta['url'],
                        'fetched': meta['fetched'], 'retrieved_at': record['fetched_at'],
                        'snapshot': f'sources/runtime/snapshots/{snapshot_dir.name}/{meta["file"]}',
                        'sha256': record['sha256'], 'note_ja': meta['note_ja']})
    offerings.sort(key=lambda o: (o['model_id'], o['source_id'], o['provider'], o['source_model']))
    if not offerings:
        raise ValueError('No offering matched a registry model')
    return {'schema_version': 1, 'retrieved': manifest['retrieved_at'], 'snapshot': f'sources/runtime/snapshots/{snapshot_dir.name}',
            'sources': sources, 'offerings': offerings, 'unmatched': unmatched, 'speed': SPEED,
            'limitations_ja': [
                '料金は取得時点の掲載単価の写しで、現在の請求額を保証しない。',
                '単位は 100 万トークンあたりの米ドル。入力長で単価が変わる提供は基本区分の単価を載せ、段階制の印を付けた。',
                '名前の綴りを正規化して登録簿と完全一致したものだけをモデルに対応づけた。対応づかなかった行は数だけを残している。',
            ]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    dirs = sorted(d for d in SNAPSHOTS.iterdir() if (d / 'manifest.json').exists())
    if not dirs:
        sys.exit('No runtime snapshot. Run scripts/fetch_runtime.py first.')
    text = json.dumps(build(dirs[-1]), ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding='utf-8') != text:
            sys.exit('docs/runtime-data.json is not what the newest snapshot builds. Run scripts/build_runtime.py')
        print('runtime data matches the newest snapshot')
        return
    OUTPUT.write_text(text, encoding='utf-8')
    data = json.loads(text)
    print(f'{len(data["offerings"])} offerings, {len({o["model_id"] for o in data["offerings"]})} models, from {dirs[-1].name}')


if __name__ == '__main__':
    main()
