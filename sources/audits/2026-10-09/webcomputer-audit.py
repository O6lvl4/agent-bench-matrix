#!/usr/bin/env python3
"""Reproduce the October 9 web/computer-source comparison offline.

Run: python sources/audits/2026-10-09/webcomputer-audit.py
Optional fresh local cache: add --cache /path/to/cache
No network calls are made. Unchanged and inaccessible tables and tracked source
files are preserved byte-for-byte. Each independent table reports its outcome.
"""
import argparse,ast,copy,gzip,hashlib,json,pathlib,subprocess,sys,tarfile,tempfile,traceback
ROOT=pathlib.Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--cache',type=pathlib.Path);args=parser.parse_args()
if args.cache:CACHE=args.cache
else:
 temporary=tempfile.TemporaryDirectory(prefix='abm-webcomputer-replay-');CACHE=pathlib.Path(temporary.name)
 manifest=json.loads((ROOT/'sources/audits/2026-10-09/webcomputer-fetch-index.json').read_text())
 rebuilt={}
 for u,x in manifest.items():
  q=dict(x)
  if x.get('snapshot'):
   with tarfile.open(ROOT/x['snapshot'],'r:gz') as archive:raw=archive.extractfile(x['archive_member']).read()
   assert len(raw)==x['bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256']
   path=CACHE/hashlib.sha256(u.encode()).hexdigest()[:16];path.write_bytes(raw);q['path']=str(path)
  rebuilt[u]=q
 (CACHE/'index.json').write_text(json.dumps(rebuilt))
source=(ROOT/'sources/audits/2026-10-09/webcomputer-extract.py').read_text();tree=ast.parse(source);state={'__file__':str(ROOT/'sources/audits/2026-10-09/webcomputer-extract.py'),'__name__':'audit_recipe'}
sys.argv=['recipe','--cache',str(CACHE)]
errors=[]
def log_error(exc):
 t=state.get('t');ident=t.get('id') if isinstance(t,dict) else state.get('id')
 errors.append({'id':ident,'error':type(exc).__name__+': '+str(exc)})
state['_log_error']=log_error
# Load setup and definitions before the first independent table batch.
first=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For) and n.lineno>55)
exec(compile(ast.Module(tree.body[:first],[]),'local-recipe','exec'),state)
original_save=state['save']
before_files={t['id']:{str(p.relative_to(ROOT)) for p in (ROOT/'sources'/t['id']).rglob('*') if p.is_file()} for t in state['T'].values()}
def save(t,snapshot,urls,method,oldrows=None,new=False):
 before=json.loads(subprocess.check_output(['git','show','HEAD:data/tables/'+t['id']+'.json'],cwd=ROOT))
 changed={k:v for k,v in t.items() if k not in ('retrieved','fetched')}!={k:v for k,v in before.items() if k not in ('retrieved','fetched')}
 if changed:original_save(t,snapshot,urls,method,before['rows'],False)
 else:
  ix=state['ix'];audit={'id':t['id'],'retrieved':'2026-10-09','status':'unchanged','old_rows':len(before['rows']),'rows':len(t['rows']),'method':method,'sources':[]}
  for u in urls:
   q=ix.get(u,{})
   if q.get('status')==200:audit['sources'].append({'url':u,'http_status':q['status'],'bytes':q['bytes'],'sha256':state['hashlib'].sha256(pathlib.Path(q['path']).read_bytes()).hexdigest(),'request_json':q.get('request_json')})
  state['AUD'].append(audit)
state['save']=save
# Group straight-line source extraction by top-level comments so exceptions skip
# the remainder of that one table, not a different table later in the file.
lines=source.splitlines();boundaries=[i+1 for i,s in enumerate(lines) if s.startswith('#') and i+1>tree.body[first].lineno]
nodes=tree.body[first:];groups=[];current=[];last=0
for n in nodes:
 group=sum(b<=n.lineno for b in boundaries)
 if group!=last and current:groups.append(current);current=[]
 current.append(n);last=group
if current:groups.append(current)
for group in groups:
 for n in group:
  if isinstance(n,ast.For):
   handler=ast.ExceptHandler(type=ast.Name('Exception',ast.Load()),name='_exc',body=[ast.Expr(ast.Call(ast.Name('_log_error',ast.Load()),[ast.Name('_exc',ast.Load())],[]))])
   n.body=[ast.Try(body=n.body,handlers=[handler],orelse=[],finalbody=[])]
 module=ast.fix_missing_locations(ast.Module(group,[]))
 try:exec(compile(module,'local-recipe','exec'),state)
 except Exception as e:log_error(e)
covered={a['id'] for a in state['AUD']}
for tid,t in state['T'].items():
 if tid not in covered:state['AUD'].append({'id':tid,'status':'preserved-gap','error':next((x['error'] for x in errors if x['id']==tid),'A changed/inaccessible shared source prevented the reviewed extraction recipe from completing this table.')})
# Revert stray support writes made before an unchanged/failed table's final save.
for a in state['AUD']:
 if a['status']=='changed':continue
 tid=a['id'];paths=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD','sources/'+tid],cwd=ROOT).decode().splitlines()
 for p in paths:(ROOT/p).write_bytes(subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT))
 for p in (ROOT/'sources'/tid).rglob('*'):
  if p.is_file() and str(p.relative_to(ROOT)) not in before_files[tid]:p.unlink()
(CACHE/'audit.json').write_text(json.dumps({'retrieved':'2026-10-09','tables':state['AUD'],'parser_errors':errors,'model_proposals':state['MODELS']},ensure_ascii=False,indent=2)+'\n')
for a in state['AUD']:print(a['id'],a['status'],a.get('error',''))
