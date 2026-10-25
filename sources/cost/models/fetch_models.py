import urllib.request,json,datetime,pathlib,hashlib,concurrent.futures
OUT=pathlib.Path(__file__).resolve().parent
repos=['Qwen/Qwen3-8B','Qwen/Qwen3-32B','Qwen/Qwen3-Coder-30B-A3B-Instruct','openai/gpt-oss-20b','openai/gpt-oss-120b','Qwen/Qwen3-8B-GGUF','Qwen/Qwen3-32B-GGUF','ggml-org/Qwen3-Coder-30B-A3B-Instruct-GGUF','ggml-org/gpt-oss-20b-GGUF','ggml-org/gpt-oss-120b-GGUF']
def get(url,name):
 now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with urllib.request.urlopen(url,timeout=60) as r:
  data=r.read(); headers={k:v for k,v in r.headers.items() if k.lower() not in ["set-cookie", "authorization"]}; status=r.status; resolved=r.url
 (OUT/name).write_bytes(data)
 meta={'source_url':url,'resolved_url':resolved,'retrieved_at_utc':now,'status':status,'sha256':hashlib.sha256(data).hexdigest(),'snapshot_file':name,'headers':headers}
 (OUT/(name+'.meta.json')).write_text(json.dumps(meta,indent=2))
 return data
def repo_run(repo):
 name=repo.replace('/','__')
 try:
  meta=json.loads(get('https://huggingface.co/api/models/'+repo,name+'.api.json')); sha=meta['sha']
  tree=json.loads(get('https://huggingface.co/api/models/'+repo+'/tree/'+sha+'?recursive=true',name+'.tree.json'))
  for f in ['config.json','README.md','LICENSE','.src_sha']:
   if any(t['path']==f for t in tree): get('https://huggingface.co/'+repo+'/resolve/'+sha+'/'+f,name+'.'+f.replace('/','_'))
  print(repo,'SHA',sha,'GGUF',[(x['path'],x['size']) for x in tree if x['path'].endswith('.gguf')],flush=True)
 except Exception as e: print(repo,type(e).__name__,str(e),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:list(ex.map(repo_run,repos))
