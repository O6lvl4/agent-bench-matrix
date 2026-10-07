#!/usr/bin/env python3
"""Recheck current public web/computer snapshots with the reviewed Oct 5 recipe.
Runs only local repository extraction code. The fetched bytes are never executed.
Preserves source files and tables byte-for-byte for unchanged or failed sources.
The dated working recipe is saved beside the source audit for reproducibility.
"""
import ast,copy,json,pathlib,subprocess,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];CACHE=pathlib.Path('/tmp/abm-web-oct7')
source=(ROOT/'scripts/extract_webcomputer_20261007.py').read_text();tree=ast.parse(source);state={'__file__':str(ROOT/'scripts/refresh_webcomputer_20261005.py'),'__name__':'audit_recipe'}
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
def save(t,snapshot,urls,method,oldrows=None,new=False):
 before=json.loads(subprocess.check_output(['git','show','HEAD:data/tables/'+t['id']+'.json'],cwd=ROOT))
 changed={k:v for k,v in t.items() if k not in ('retrieved','fetched')}!={k:v for k,v in before.items() if k not in ('retrieved','fetched')}
 if changed:original_save(t,snapshot,urls,method,before['rows'],False)
 else:
  ix=state['ix'];audit={'id':t['id'],'retrieved':'2026-10-07','status':'unchanged','old_rows':len(before['rows']),'rows':len(t['rows']),'method':method,'sources':[]}
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
(CACHE/'audit.json').write_text(json.dumps({'retrieved':'2026-10-07','tables':state['AUD'],'parser_errors':errors,'model_proposals':state['MODELS']},ensure_ascii=False,indent=2)+'\n')
for a in state['AUD']:print(a['id'],a['status'],a.get('error',''))
