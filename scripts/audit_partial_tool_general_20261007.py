#!/usr/bin/env python3
"""Audit only bytes retained before the fetch execution was cancelled.
Never resumes network; missing responses preserve good tables and old dates.
"""
import ast,copy,hashlib,json,pathlib,re
from lxml import html
ROOT=pathlib.Path(__file__).resolve().parents[1];CACHE=pathlib.Path('/tmp/abm-tool-oct7');DATE='2026-10-07'
T=[json.loads(p.read_text()) for p in (ROOT/'data/tables').glob('*.json') if json.loads(p.read_text())['category'] in ('terminal','tool-use','general')]
AUD=[]
def fetch(u):
 p=CACHE/hashlib.sha256(u.encode()).hexdigest()[:14];assert p.exists(),'Incomplete cache: source unavailable after cancelled execution; not retried.'
 return p.read_text()
def rsc(raw):
 out=[]
 for a in html.fromstring(raw).xpath('//script/text()'):
  for m in re.finditer(r'self\.__next_f\.push\(',a):
   try:
    v=json.JSONDecoder().raw_decode(a[m.end():])[0]
    if isinstance(v,list) and len(v)>1 and isinstance(v[1],str):out.append(v[1])
   except ValueError:pass
 return ''.join(out)
def vals(s,k):
 out=[]
 for m in re.finditer('"'+re.escape(k)+'"\\s*:',s):
  try:out.append(json.JSONDecoder().raw_decode(s[m.end():].lstrip())[0])
  except ValueError:pass
 return out
for t in sorted(T,key=lambda t:t['id']):
 id=t['id'];used=[]
 try:
  old=(ROOT/t['snapshot']).read_text()
  if id.startswith('appworld-'):
   u=next(u for u in t['fetched'] if u.endswith('.json'));used=[u];assert json.loads(fetch(u))==json.loads(old)
  elif id=='bfcl-v4':
   u=next(u for u in t['fetched'] if u.endswith('.csv'));used=[u];assert fetch(u).strip()==old.strip()
  elif id in ('hal-gaia','hal-tau-bench-airline'):
   u=t['fetched'][0];used=[u];norm=lambda x:re.sub(r'\s+',' ',html.tostring(x,encoding='unicode')).strip();a=html.fromstring(fetch(u)).xpath('//table')[0];b=html.fromstring(old);b=b if b.tag=='table' else b.xpath('//table')[0];assert norm(a)==norm(b)
  elif id=='gaia2-cli':
   u=t['fetched'][0];used=[u];tree=ast.parse(fetch(u));n=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='_GAIA2_CLI_DATA');assert n==json.loads(old)
  elif id=='mcp-atlas':
   u=t['fetched'][0];used=[u];entries=next(v for v in vals(rsc(fetch(u)),'entries') if isinstance(v,list) and v and 'score' in v[0]);assert entries==json.loads(old)['entries'],'Current MCP-Atlas source differs; exact model/config mapping requires review.'
  else:raise ValueError('Required source set incomplete after cancelled execution. Partial landing-page/app source bytes are insufficient to certify leaderboard rows; existing table and retrieval date preserved.')
  AUD.append({'id':id,'status':'unchanged','rows':len(t['rows']),'sources':[{'url':u,'sha256':hashlib.sha256(fetch(u).encode()).hexdigest(),'http_status':None,'collector_completed':False} for u in used]})
 except Exception as e:AUD.append({'id':id,'status':'preserved-gap','error':str(e),'retained_retrieval_date':t['retrieved'],'tried':t['fetched']})
(CACHE/'partial-audit.json').write_text(json.dumps({'retrieved':DATE,'fetch_session':'cancelled; not retried','tables':AUD},ensure_ascii=False,indent=2)+'\n')
for a in AUD:print(a['id'],a['status'],a.get('error',''))
