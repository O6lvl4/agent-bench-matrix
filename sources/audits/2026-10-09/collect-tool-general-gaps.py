"""2026-10-09 primary gap source rechecks, never executes fetched code."""
import concurrent.futures,hashlib,json,pathlib,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[3]
CACHE=pathlib.Path('/tmp/abm-tool-gaps-20261009');CACHE.mkdir(exist_ok=True)
IDS=['terminal-bench-1-0','terminal-bench-challenges','harbor-index','livemcpbench','gaia-validation','galileo-agent-leaderboard-v2','crmarena']
urls=sorted({u for id in IDS for u in json.loads((ROOT/f'data/gaps/{id}.json').read_text())['tried']})
def fetch(u):
 try:
  if ' (POST ' in u:
   url,body=u.split(' (POST ');req=urllib.request.Request(url,data=body[:-1].encode(),headers={'Content-Type':'application/json'})
  else:req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (public benchmark data audit)'})
  with urllib.request.urlopen(req,timeout=60) as r:b=r.read();status=r.status;final=r.url
  p=CACHE/hashlib.sha256(u.encode()).hexdigest()[:14];p.write_bytes(b)
  out={'url':u,'file':str(p),'status':status,'final_url':final,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 except Exception as e:out={'url':u,'error':str(e)}
 print(json.dumps({k:v for k,v in out.items()if k!='file'}),flush=True)
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=5)as ex:rs=list(ex.map(fetch,urls))
(CACHE/'index.json').write_text(json.dumps(rs,indent=2)+'\n')
