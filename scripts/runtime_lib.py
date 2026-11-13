"""Shared, offline parsing for the hosted-inference (提供) layer.

Everything here turns a saved snapshot into price observations. Nothing downloads,
guesses, or converts between pricing models. A source name maps to a registry model
only by exact match after spelling normalisation; anything else stays unmatched and
is counted, never shown under a model it might not be.
"""
import gzip
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = ROOT / 'sources' / 'runtime' / 'snapshots'

SOURCES = {
    'cloudflare-workers-ai': {
        'name': 'Cloudflare Workers AI', 'kind': 'official', 'file': 'cloudflare-workers-ai-pricing.md',
        'url': 'https://developers.cloudflare.com/workers-ai/platform/pricing/',
        'fetched': 'https://developers.cloudflare.com/workers-ai/platform/pricing/index.md',
        'note_ja': '公式の料金ページ。請求は Neuron 単位で、ページが併記するトークン単価を写した。',
    },
    'aws-bedrock': {
        'name': 'Amazon Bedrock', 'kind': 'official', 'file': 'aws-bedrock-us-east-1.json.gz',
        'url': 'https://aws.amazon.com/bedrock/pricing/',
        'fetched': 'https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrock/current/us-east-1/index.json',
        'note_ja': 'AWS Price List API の us-east-1、オンデマンド推論の標準区分だけ。バッチ・flex・priority・他リージョンは入れていない。この一覧に無いモデル(現行の Claude など)は別契約で課金されるため、ここからは取れない。',
    },
    'ollama-cloud': {
        'name': 'Ollama Cloud', 'kind': 'official', 'file': 'ollama-pricing.html',
        'url': 'https://ollama.com/pricing', 'fetched': 'https://ollama.com/pricing',
        'note_ja': '公式の料金ページの従量単価表。月額プランは利用クレジットを含む別体系で、単価には直していない。',
    },
    'openrouter': {
        'name': 'OpenRouter', 'kind': 'aggregator', 'file': 'openrouter-endpoints.json.gz',
        'url': 'https://openrouter.ai/models', 'fetched': 'https://openrouter.ai/api/v1/models/{id}/endpoints',
        'note_ja': 'OpenRouter が各配信元へ中継するときの掲載単価。配信元と直接契約した場合の価格を保証するものではない。',
    },
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return gzip.decompress(raw) if str(path).endswith('.gz') else raw


def norm(text):
    """Spelling only: case, separators. Never drops a size, version or variant."""
    text = text.strip().lower().replace('_', '-').replace(':', '-')
    return re.sub(r'-+', '-', re.sub(r'\s+', '-', text)).strip('-')


def registry_index(models):
    """id, aliases and display name, each normalised, pointing at one registry id."""
    index, clash = {}, set()
    for m in models:
        for key in {norm(m['id']), norm(m['name']), *(norm(a) for a in m.get('aliases') or [])}:
            if key in index and index[key] != m['id']:
                clash.add(key)
            index[key] = m['id']
    for key in clash:  # one spelling for two models identifies neither
        del index[key]
    return index


def money(text):
    value = float(text)
    if not 0 <= value < 100000:
        raise ValueError(f'price out of range: {text!r}')
    return round(value, 6)


# ── Cloudflare Workers AI ───────────────────────────────────────────────────
CF_ROW = re.compile(r'^\|\s*(@cf/[^\s|]+)\s*\|([^|]*)\|')
CF_PRICE = re.compile(r'\$([0-9.]+) per M (input|cached input|output) tokens')
# Deployment suffixes Cloudflare appends to the model's own name.
CF_SUFFIX = [('-fp8-fast', 'fp8'), ('-fp8', 'fp8'), ('-fp16', 'fp16'), ('-awq', 'awq')]


def parse_cloudflare(text):
    rows = []
    section = text.split('## LLM model pricing', 1)
    if len(section) != 2:
        raise ValueError('Cloudflare page has no LLM model pricing section')
    for line in section[1].split('\n## ', 1)[0].splitlines():
        match = CF_ROW.match(line)
        if not match:
            continue
        prices = {kind: money(value) for value, kind in CF_PRICE.findall(match.group(2))}
        if 'input' not in prices or 'output' not in prices:
            raise ValueError(f'Cloudflare row without input/output price: {line[:80]}')
        source_model = match.group(1)
        name, quant = source_model.split('/')[-1], None
        for suffix, q in CF_SUFFIX:
            if name.endswith(suffix):
                name, quant = name[:-len(suffix)], q
                break
        rows.append({'source_model': source_model, 'names': [name, re.sub(r'-(instruct|it)$', '', name)],
                     'provider': 'Cloudflare Workers AI', 'input': prices['input'], 'output': prices['output'],
                     'cached_input': prices.get('cached input'), 'quantization': quant,
                     'context_length': None, 'tier': None, 'region': None})
    if not rows:
        raise ValueError('Cloudflare page yielded no price rows')
    return rows


# ── Amazon Bedrock ──────────────────────────────────────────────────────────
def parse_bedrock(doc):
    found = {}
    for sku, product in doc['products'].items():
        a = product['attributes']
        kind = {'Input tokens': 'input', 'Output tokens': 'output'}.get(a.get('inferenceType'))
        if not kind or a.get('feature') != 'On-demand Inference' or not a.get('model') or not a.get('provider'):
            continue
        dims = [d for term in doc['terms']['OnDemand'].get(sku, {}).values() for d in term['priceDimensions'].values()]
        if len(dims) != 1 or dims[0]['unit'] != '1K tokens' or 'USD' not in dims[0]['pricePerUnit']:
            raise ValueError(f'Unexpected Bedrock price shape for {a["usagetype"]}')
        entry = found.setdefault((a['provider'], a['model']), {})
        price = money(str(float(dims[0]['pricePerUnit']['USD']) * 1000))
        if kind in entry and entry[kind] != price:
            raise ValueError(f'Conflicting Bedrock {kind} price for {a["model"]}')
        entry[kind] = price
    rows = []
    for (vendor, model), p in sorted(found.items()):
        if 'input' not in p:
            continue
        rows.append({'source_model': f'{vendor} / {model}', 'names': [model, f'{vendor} {model}'],
                     'provider': 'Amazon Bedrock', 'input': p['input'], 'output': p.get('output'),
                     'cached_input': None, 'quantization': None, 'context_length': None,
                     'tier': 'on-demand standard', 'region': doc_region(doc)})
    if not rows:
        raise ValueError('Bedrock price list yielded no on-demand token prices')
    return rows


def doc_region(doc):
    regions = {p['attributes'].get('regionCode') for p in doc['products'].values()} - {None}
    if len(regions) != 1:
        raise ValueError('Bedrock snapshot must hold exactly one region')
    return regions.pop()


# ── Ollama Cloud ────────────────────────────────────────────────────────────
def parse_ollama(page):
    text = re.sub(r'<script.*?</script>|<style.*?</style>', '', page, flags=re.S)
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', text)))
    match = re.search(r'Model Input Cached input Output (.*?) Frequently asked questions', text)
    if not match or 'Prices are per million tokens' not in text:
        raise ValueError('Ollama page has no per-million-token price table')
    cell = r'(\$[0-9.]+|-)'
    rows = []
    for name, off, inp, cached, out in re.findall(rf'(\S+)( \(Off-Peak\))? {cell} {cell} {cell}', match.group(1)):
        if inp == '-':
            raise ValueError(f'Ollama row without input price: {name}')
        value = lambda v: None if v == '-' else money(v[1:])
        rows.append({'source_model': name + (' (Off-Peak)' if off else ''), 'names': [name],
                     'provider': 'Ollama Cloud', 'input': value(inp), 'output': value(out),
                     'cached_input': value(cached), 'quantization': None, 'context_length': None,
                     'tier': 'off-peak' if off else None, 'region': None})
    if not rows:
        raise ValueError('Ollama price table yielded no rows')
    return rows


# ── OpenRouter ──────────────────────────────────────────────────────────────
def openrouter_names(model_id):
    """`vendor/slug`; a `:variant` suffix is a different offering and is not mapped."""
    if ':' in model_id or model_id.count('/') != 1:
        return []
    return [model_id.split('/')[1]]


def parse_openrouter(responses):
    rows = []
    for model_id, body in sorted(responses.items()):
        for e in (body.get('data') or {}).get('endpoints') or []:
            pricing = e.get('pricing') or {}
            try:
                inp, out = float(pricing['prompt']), float(pricing['completion'])
            except (KeyError, TypeError, ValueError):
                continue
            if inp < 0 or out < 0:  # negative marks a price decided per request
                continue
            cached = pricing.get('input_cache_read')
            quant = e.get('quantization')
            rows.append({'source_model': f'{model_id} @ {e.get("tag") or e["provider_name"]}', 'names': openrouter_names(model_id),
                         'provider': e['provider_name'], 'input': money(str(inp * 1e6)), 'output': money(str(out * 1e6)),
                         'cached_input': money(str(float(cached) * 1e6)) if cached not in (None, '') else None,
                         'quantization': quant if quant and quant != 'unknown' else None,
                         'context_length': e.get('context_length'), 'tier': e.get('service_tier'),
                         'region': None, 'tiered': bool(pricing.get('overrides'))})
    return rows


def load_registry():
    return json.loads((ROOT / 'data' / 'models.json').read_text(encoding='utf-8'))['models']
