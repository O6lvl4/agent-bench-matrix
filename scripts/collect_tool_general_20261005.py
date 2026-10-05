"""Fetch public terminal/tool-use/general sources once per shared URL.
Usage: python scripts/collect_tool_general_20261005.py /path/to/cache
Then: ABM_TOOL_CACHE=/path/to/cache python scripts/refresh_tool_general_20261005.py
This is the dated 2026-10-05 extraction recipe, not a future unattended updater.
Raw responses are retained; failed responses never replace a good table snapshot.
"""
import concurrent.futures,hashlib,json,pathlib,sys,urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
cache=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/abm-own-fetch');cache.mkdir(parents=True,exist_ok=True)
ts=[json.loads(p.read_text()) for p in (root/'data/tables').glob('*.json') if json.loads(p.read_text())['category'] in ['terminal','tool-use','general']]
urls=sorted({u for t in ts for u in t['fetched'] if 's3.us-west-2.amazonaws.com/submissions/' not in u or u.endswith('manifest.json')})
def fetch(u):
 try:
  if ' (POST ' in u:
   url,body=u.split(' (POST ');req=urllib.request.Request(url,data=body[:-1].encode(),headers={'Content-Type':'application/json'})
  elif '/gradio_api/call/' in u and u.rsplit('/',1)[1] in ['refresh','refresh_legacy']:
   req=urllib.request.Request(u,data=b'{"data":[]}',headers={'Content-Type':'application/json'})
  else:req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (public benchmark data audit)'})
  with urllib.request.urlopen(req,timeout=100) as r:b=r.read();status=r.status;final_url=r.url
  path=cache/hashlib.sha256(u.encode()).hexdigest()[:14];path.write_bytes(b)
  return {'url':u,'file':str(path.resolve()),'status':status,'final_url':final_url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 except Exception as e:return {'url':u,'error':str(e)}
def batch(items):
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:return list(ex.map(fetch,items))
responses=batch(urls);ix={r['url']:r for r in responses if 'file'in r};extra=[]
mu='https://sierra-tau-bench-public.s3.us-west-2.amazonaws.com/submissions/manifest.json'
if mu in ix:
 manifest=json.load(open(ix[mu]['file']));extra +=[mu.replace('manifest.json',s+'/submission.json')for group in manifest.values()for s in group]
for u,r in ix.items():
 if '/gradio_api/call/' in u:extra.append(u+'/'+json.load(open(r['file']))['event_id'])
responses+=batch(sorted(set(extra)));(cache/'index.json').write_text(json.dumps(responses,indent=2)+'\n')
errors=[r for r in responses if 'error'in r];print(f'{len(responses)} shared-source requests; {len(errors)} failures')
if errors:print(json.dumps(errors,indent=2));sys.exit(1)
