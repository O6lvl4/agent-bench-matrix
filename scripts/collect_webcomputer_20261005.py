#!/usr/bin/env python3
"""Fetch public read-only sources for refresh_webcomputer_20261005.py.
Run from any directory. No authentication, paid evaluations, or submissions.
python scripts/collect_webcomputer_20261005.py --cache /tmp/abm-webcomputer-fetch
python scripts/refresh_webcomputer_20261005.py --cache /tmp/abm-webcomputer-fetch
"""
import argparse,concurrent.futures,hashlib,json,pathlib,subprocess,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--cache',default='/tmp/abm-webcomputer-fetch');P=pathlib.Path(p.parse_args().cache);P.mkdir(parents=True,exist_ok=True)
BASE='ddbc61d';urls=set()
for path in subprocess.check_output(['git','ls-tree','--name-only',BASE,'data/tables/'],cwd=ROOT).decode().splitlines():
 t=json.loads(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT))
 if t['category'] not in ('web','computer-use'):continue
 for u in t['fetched']:
  if '<agent>' in u or u.endswith('/GetBenchmark') or '/call/refresh' in u:continue
  urls.add(u.replace('http://osworld-v1','https://osworld-v1'))
urls.update(['https://assistantbench-leaderboard.hf.space/config','https://osworld-v2.xlang.ai/static/js/leaderboard.js?v=leaderboard-v21-v1','https://osworld-v2.xlang.ai/','https://arena.xlang.ai/leaderboard','https://arena.xlang.ai/','https://raw.githubusercontent.com/MinorJerry/WebVoyager/main/README.md','https://raw.githubusercontent.com/PALIN2018/BrowseComp-ZH/main/README.md','https://microsoft.github.io/WindowsAgentArena/','https://raw.githubusercontent.com/huggingface/screensuite/main/README.md','https://macos-world.github.io/','https://www.hud.ai/leaderboards','https://www.hud.ai/','https://huggingface.co/api/spaces/ST-WebAgentBench/st-webagentbench-leaderboard','https://st-webagentbench-st-webagentbench-leaderboard.hf.space/config','https://openai.com/index/browsecomp/','https://raw.githubusercontent.com/openai/simple-evals/main/README.md','https://huggingface.co/spaces/ST-WebAgentBench/st-webagentbench-leaderboard/raw/main/app.py','https://huggingface.co/api/datasets/ST-WebAgentBench/st-webagentbench-data'])
def fetch(u):
 path=P/hashlib.sha256(u.encode()).hexdigest()[:16];body=None
 if 'GetBenchmarkLeaderboard' in u:body={'versionIdentifier':{'versionIdSelector':{'id':35}}}
 req=urllib.request.Request(u,data=json.dumps(body).encode() if body else None,headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/json'} if body else {'User-Agent':'Mozilla/5.0'})
 try:
  with urllib.request.urlopen(req,timeout=45) as r:
   b=r.read();path.write_bytes(b);q=dict(path=str(path),status=r.status,url=r.url,bytes=len(b),headers=dict(r.headers))
   if body:q['request_json']=body
 except urllib.error.HTTPError as e:q={'status':e.code,'error':str(e)}
 except Exception as e:q={'error':str(e)}
 print(u,q.get('status'),q.get('bytes'),q.get('error'),flush=True);return u,q
ix={}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:ix.update(pool.map(fetch,sorted(urls)))
u='https://huggingface.co/api/spaces/ServiceNow/browsergym-leaderboard';m=json.loads(pathlib.Path(ix[u]['path']).read_text());urls=['https://huggingface.co/spaces/ServiceNow/browsergym-leaderboard/resolve/'+m['sha']+'/'+x['rfilename'] for x in m['siblings'] if x['rfilename'].startswith('results/') and x['rfilename'].endswith('.json')]
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:ix.update(pool.map(fetch,urls))
(P/'index.json').write_text(json.dumps(ix,indent=2)+'\n')
