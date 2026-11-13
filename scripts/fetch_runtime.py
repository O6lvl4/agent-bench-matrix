#!/usr/bin/env python3
"""Fetch hosted-inference price sources into a new dated snapshot directory.

Public GET requests only: no credentials, no paid API, no schedule. Each run writes
sources/runtime/snapshots/<UTC date>/ and never touches an older snapshot. Run
scripts/build_runtime.py afterwards to extract (offline) from what was saved.

OpenRouter's per-endpoint speed fields are null without an API key, so this
script cannot and does not collect speed.
"""
import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_lib import SNAPSHOTS, SOURCES, load_registry, openrouter_names, norm, registry_index, sha256

AGENT = 'Mozilla/5.0 (compatible; public-price-snapshot)'
OPENROUTER_MODELS = 'https://openrouter.ai/api/v1/models'


def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.status, response.read()


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    args = parser.parse_args()
    out = SNAPSHOTS / args.date
    if out.exists():
        sys.exit(f'{out} already exists; snapshots are append-only')
    out.mkdir(parents=True)
    files = []

    def save(name, url, body, compress=False):
        (out / name).write_bytes(gzip.compress(body, mtime=0) if compress else body)
        files.append({'file': name, 'url': url, 'bytes': len(body), 'sha256': sha256(body), 'fetched_at': now()})

    for source_id in ['cloudflare-workers-ai', 'ollama-cloud', 'aws-bedrock']:
        source = SOURCES[source_id]
        status, body = get(source['fetched'])
        if status != 200:
            sys.exit(f'{source["fetched"]}: HTTP {status}')
        save(source['file'], source['fetched'], body, compress=source['file'].endswith('.gz'))

    status, body = get(OPENROUTER_MODELS)
    if status != 200:
        sys.exit(f'{OPENROUTER_MODELS}: HTTP {status}')
    save('openrouter-models.json.gz', OPENROUTER_MODELS, body, compress=True)
    index = registry_index(load_registry())
    wanted = [m['id'] for m in json.loads(body)['data'] if any(norm(n) in index for n in openrouter_names(m['id']))]
    responses, failed = {}, []
    for model_id in wanted:
        url = SOURCES['openrouter']['fetched'].format(id=model_id)
        try:
            status, raw = get(url)
            responses[model_id] = json.loads(raw)
        except (urllib.error.URLError, ValueError) as error:
            failed.append({'id': model_id, 'error': str(error)})
        time.sleep(0.25)
    save(SOURCES['openrouter']['file'], SOURCES['openrouter']['fetched'],
         json.dumps(responses, ensure_ascii=False, sort_keys=True).encode(), compress=True)

    manifest = {'schema_version': 1, 'retrieved_at': now(),
                'method': 'Unauthenticated public GET. sha256 and bytes are of the uncompressed response body. '
                          'openrouter-endpoints holds one parsed response per registry-matched model id.',
                'files': files, 'openrouter_requested': len(wanted), 'openrouter_failed': failed}
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'saved {len(files)} files to {out}; OpenRouter {len(responses)}/{len(wanted)} models, {len(failed)} failed')


if __name__ == '__main__':
    main()
