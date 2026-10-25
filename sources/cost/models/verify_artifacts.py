import urllib.request,json,datetime,pathlib,hashlib,concurrent.futures
p=pathlib.Path(__file__).resolve().parent
repos=['Qwen/Qwen3-8B-GGUF','Qwen/Qwen3-32B-GGUF','ggml-org/Qwen3-Coder-30B-A3B-Instruct-GGUF','ggml-org/gpt-oss-20b-GGUF','ggml-org/gpt-oss-120b-GGUF']
# Keep first-party redirect metadata, not transient signed CDN URLs.
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self, req, fp, code, msg, headers, newurl): return None
opener=urllib.request.build_opener(NoRedirect)
def run(repo):
 name=repo.replace('/','__'); meta=json.load(open(p/(name+'.api.json')));tree=json.load(open(p/(name+'.tree.json')))
 f=next(f for f in tree if f['path'].endswith('.gguf') and ('Q4_K_M' in f['path'] or 'MXFP4' in f['path']))
 url='https://huggingface.co/'+repo+'/resolve/'+meta['sha']+'/'+f['path'];when=datetime.datetime.now(datetime.timezone.utc).isoformat()
 try:
  with opener.open(urllib.request.Request(url,method='HEAD'),timeout=60) as r: status=r.status;headers=r.headers
 except urllib.error.HTTPError as e:status=e.code;headers=e.headers
 selected={k.lower():v for k,v in headers.items() if k.lower() in ['content-length','x-linked-size','x-linked-etag','x-repo-commit','content-type','date']}
 out={'url':url,'retrieved_at_utc':when,'status':status,'headers':selected,'bytes_from_tree':f['size'],'matches_linked_size':int(selected.get('x-linked-size','-1'))==f['size']}
 (p/(name+'.artifact-head.json')).write_text(json.dumps(out,indent=2));print(repo,out,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:list(ex.map(run,repos))
