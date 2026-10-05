#!/usr/bin/env python3
"""Acquire this category batch's public sources. Prints an index for refresh script.
Usage: python scripts/fetch_research_security_horizon.py --out /tmp/research-cache
Follows public pages to current JS bundle URLs; never evaluates fetched scripts.
"""
import argparse,concurrent.futures,hashlib,json,pathlib,re,subprocess,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
tables=[json.loads(p.read_text()) for p in (ROOT/'data/tables').glob('*.json')];tables=[t for t in tables if t['category'] in ['research','security','long-horizon']]
urls={u for t in tables for u in t['fetched']};index={}
def fetch(u):
 p=out/(hashlib.sha256(u.encode()).hexdigest()[:14]+'.source');r=subprocess.run(['curl','-L','--retry','1','--max-time','60','-sS','-o',str(p),'-w','%{http_code}',u],capture_output=True,text=True);b=p.read_bytes() if p.exists() else b''
 return {'url':u,'status':r.stdout,'error':r.stderr,'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def batch(urls):
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
  for r in ex.map(fetch,sorted(set(urls)-set(index))):index[r['url']]=r
batch(urls)
# Rotating module URLs must be discovered from current pages, not guessed.
more=[]
for u in ['https://www.swe-marathon.org/','https://andonlabs.com/evals/vending-bench','https://andonlabs.com/evals/vending-bench-2']:
 if index[u]['status']!='200':continue
 s=pathlib.Path(index[u]['path']).read_text()
 for href in re.findall(r'(?:src|href)=["\']([^"\']+\.js)',s):
  if '/assets/index-' in href or '/immutable/nodes/' in href or '/immutable/chunks/' in href:more.append(urllib.parse.urljoin(u,href))
batch(more)
(out/'index.json').write_text(json.dumps(list(index.values()),indent=2)+'\n');print(out/'index.json')
