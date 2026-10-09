#!/usr/bin/env python3
"""Primary-source web/computer extraction recipe for October 9, 2026 JST.

Use through webcomputer-audit.py to preserve unchanged tables and source bytes.
The audit wrapper can replay entirely offline from the compressed response
artifacts and validates each raw response SHA-256 before parsing it. Numeric
values are extracted from primary-source data; fetched code is never executed.
No model registry or compiled output changes are made by this recipe.
"""
import argparse,collections,copy,csv,datetime,hashlib,io,json,pathlib,re,urllib.request,subprocess
from lxml import html
import openpyxl
ROOT=pathlib.Path(__file__).resolve().parents[3]
DATE='2026-10-09'
parser=argparse.ArgumentParser();parser.add_argument('--cache',default='/tmp/abm-web-oct7');P=pathlib.Path(parser.parse_args().cache)
ix=json.loads((P/'index.json').read_text())
BASE='af0325ce49fdeb5200bd9730b195cc0537c63f05'
def baseline(path):return subprocess.check_output(['git','show',BASE+':'+str(path)],cwd=ROOT).decode()
T={}
for path in subprocess.check_output(['git','ls-tree','--name-only',BASE,'data/tables/'],cwd=ROOT).decode().splitlines():
 t=json.loads(baseline(path))
 if t['category'] in ('web','computer-use'):T[t['id']]=t
AUD=[];MODELS=[]
def dump(p,d):
 p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True)
 indent=2
 if p.exists():
  m=re.search(r'\n( +)\"',p.read_text());indent=len(m[1]) if m else 2
 p.write_text(json.dumps(d,ensure_ascii=False,indent=indent)+'\n')
def fetch(u):
 q=ix[u];assert q.get('status')==200,(u,q);return pathlib.Path(q['path']).read_bytes()
def txt(u):return fetch(u).decode('utf-8-sig')
def obj(u):return json.loads(txt(u))
def old(t):return json.loads(baseline(t['snapshot']))
def no_null(d):
 if isinstance(d,dict):return {k:no_null(v) for k,v in d.items() if v is not None}
 if isinstance(d,list):return [no_null(x) for x in d]
 return d
def row(t,system):return copy.deepcopy(next(x for x in t['rows'] if x['system']==system))
def newrow(system):return dict(rank=None,system=system,agent=None,model_raw=[],model_ids=[],model_config=None,score=None,score_extra={},date=None,verified=None,open_source=None,org=None,row_url=None)
def ranks(rs):
 rs.sort(key=lambda x:-(x['score'] if x['score'] is not None else -1));
 for i,r in enumerate(rs,1):r['rank']=i
 return rs
def save(t,snapshot,urls,method,oldrows=None,new=False):
 oldrows=copy.deepcopy(t['rows']) if oldrows is None else oldrows
 if snapshot is not None:
  p=ROOT/t['snapshot'];p.parent.mkdir(parents=True,exist_ok=True)
  if oldrows==t['rows'] and not new and not t['id'].startswith('osworld-2-') and t['id']!='browsecomp-kaggle':snapshot=baseline(t['snapshot'])
  if isinstance(snapshot,str):p.write_text(snapshot)
  elif isinstance(snapshot,bytes):p.write_bytes(snapshot)
  else:dump(t['snapshot'],snapshot)
 t['retrieved']=DATE;t['fetched']=urls;t['newest_row_date']=max([x['date'] for x in t['rows'] if x['date']],default=None)
 dump('data/tables/'+t['id']+'.json',t)
 a={'id':t['id'],'retrieved':DATE,'status':'new' if new else ('changed' if oldrows!=t['rows'] else 'unchanged'),'old_rows':len(oldrows),'rows':len(t['rows']),'method':method,'sources':[]}
 for u in urls:
  if u in ix and ix[u].get('status')==200:
   q=ix[u];a['sources'].append({'url':u,'http_status':q['status'],'bytes':q['bytes'],'sha256':hashlib.sha256(fetch(u)).hexdigest(),'last_modified':q.get('headers',{}).get('Last-Modified') or q.get('headers',{}).get('last-modified'),'request_json':q.get('request_json')})
 dump('sources/audits/2026-10-09/webcomputer-table-audits/'+t['id']+'.json',a);AUD.append(a)
def unchanged_json(id):
 t=T[id];u=t['fetched'][0];n=obj(u);assert n==old(t),id;save(t,n,[u],'Parsed entire JSON artifact and compared every record/value with previous mechanically extracted snapshot')
def unchanged_csv(id):
 t=T[id];u=t['fetched'][0];n=txt(u);assert list(csv.reader(io.StringIO(n)))==list(csv.reader(io.StringIO(baseline(t['snapshot']))));save(t,n,[u],'Parsed all CSV cells; exact record/value equality with previous snapshot')
for id in ['macagentbench','venusbench-mobile']:unchanged_json(id)
for id in ['online-mind2web-auto','online-mind2web-human','androidworld-mobileminiwob']:unchanged_csv(id)
# Static HTML tables: compare text and all published links, then keep source excerpt.
for id in ['osuniverse','osworld-mcp','hal-online-mind2web','hal-assistantbench','cua-bench-eda-kicad']:
 t=T[id];u=t['fetched'][0];prev=html.fromstring(baseline(t['snapshot']));n=html.fromstring(txt(u))
 def sig(e):return [(' '.join(x.text_content().split()),x.xpath('.//a/@href')) for x in e.xpath('.//tr')]
 tab=next(x for x in n.xpath('//table') if sig(x)==sig(prev));save(t,html.tostring(tab,encoding='unicode'),[u],'Extracted live HTML table; every row text, numeric cell and hyperlink matches previous snapshot')
# Simple shared JSON source, full extraction with exact source-record preservation.
t=T['mobileworld'];u=t['fetched'][0];n=obj(u);prev=old(t);before=copy.deepcopy(t['rows']);rs=[]
for x in n['results']:
 if x in prev['results']:rs.append(row(t,x['model']));continue
 r=newrow(x['model']);r.update(agent=x.get('agent_type'),model_raw=[x['model']],model_ids=[x['model'].lower()],model_config=f"category={x['category']}; model_type={x['model_type']}; agent_type={x['agent_type']}",score=x['gui_only'],date=x['date'],org=x['organization'],row_url=x.get('link'))
 r['score_extra']={k:x[k] for k in ['user_int','mcp','max_steps','runs','num_images_in_history'] if x.get(k) is not None}
 if x.get('traj_file'):r['score_extra']['trajectory_url']='https://tongyi-mai.github.io/MobileWorld/'+x['traj_file']
 rs.append(r);MODELS.append(dict(id=x['model'].lower(),name=x['model'],vendor=x['organization'],open_weights=None,weights_url=None,aliases=[]))
t['rows']=ranks(rs);save(t,n,[u],'Parsed all result records; retained reviewed normalization for exact old records; mechanically ingested new model and all numeric/configuration fields',before)
# Compare all existing OSWorld release/step/scope snapshots; never merge releases.
u='https://osworld-v2.xlang.ai/static/data/leaderboard/official-results.json';n=obj(u)
for id in [k for k in T if k.startswith('osworld-2-')]:
 t=T[id];assert n==old(t), 'OSWorld source changed; release/scope parser review required'
 save(t,n,[u],'Complete official result records match each saved release-specific snapshot; v2.0/v2.1 tables stay separate')
# OSWorld 1 workbook sheets, lossless numeric cell comparison (None/absent equivalent).
for suffix in ['osworld_verified_results','self_reported_results']:
 u='https://osworld-v1.xlang.ai/static/data/'+suffix+'.xlsx';raw=fetch(u);wb=openpyxl.load_workbook(io.BytesIO(raw),data_only=True)
 for t in [x for x in T.values() if suffix in x['snapshot']]:
  prev=old(t);sheet='Eval Results' if suffix=='osworld_verified_results' else t['snapshot'].split('.')[-2];vs=list(wb[sheet].values)
  conv=lambda x:openpyxl.utils.datetime.to_excel(x) if isinstance(x,datetime.datetime) else x
  rows=[{k:conv(v) for k,v in zip(vs[0],r) if k is not None and v is not None} for r in vs[1:] if any(v is not None for v in r)]
  assert no_null(rows)==no_null(prev['rows']),t['id']
  prev['rows']=rows;prev['fetched']=u
  (ROOT/'sources'/t['id']/(suffix+'.xlsx')).write_bytes(raw)
  save(t,prev,[u],'Parsed every workbook sheet cell and compared all values (blank and absent cells equivalent); prior aggregation unchanged')
# BrowserGym immutable revision, enumerate every current result JSON from live manifest.
u='https://huggingface.co/api/spaces/ServiceNow/browsergym-leaderboard';meta=obj(u);sha=meta['sha']
for id in [k for k in T if k.startswith('browsergym-')]:
 t=T[id];bench=id.removeprefix('browsergym-');urls=['https://huggingface.co/spaces/ServiceNow/browsergym-leaderboard/resolve/'+sha+'/'+x['rfilename'] for x in meta['siblings'] if x['rfilename'].startswith('results/') and x['rfilename'].endswith('/'+bench+'.json')];records=[]
 for url in urls:
  x=obj(url);records.extend(x if isinstance(x,list) else [x])
 prev=old(t);assert sorted(records,key=lambda x:x['agent_name'])==sorted(prev,key=lambda x:x['agent_name']),(id,len(records),len(prev))
 save(t,records,[u]+urls,'Enumerated live HF manifest and parsed every benchmark result at immutable commit '+sha+'; all source records match')
# REAL task-level data: explicit version selection and published tab membership.
u='https://www.realevals.xyz/api/getVerifiedModelData';models=obj(u)['aiModels']
for id in [k for k in T if k.startswith('real-')]:
 t=T[id];prev=old(t);tag={'Models':'model_score','Frameworks':'framework_score','Open Arena':'arena_score'}[prev['tab']];records=[];computed=[]
 for m in models:
  if tag not in (m.get('tag') or []):continue
  tasks=[{k:x.get(k) for k in ['id','points','evalsPassed','evalsFailed','difficulty']} for w in m['websites'] for x in w['tasks'] if x['id'].startswith('v2.')==(prev['version']=='v2')]
  if not any(x['points'] is not None for x in tasks):continue
  r={k:m.get(k) for k in ['id','name','run_id','verified','tag']};r['tasks']=tasks;records.append(r)
  passed=sum((x['points'] or 0)>0 if prev['version']=='v2' else bool(x['evalsPassed']) and not x['evalsFailed'] for x in tasks);computed.append(dict(name=m['name'],id=m['id'],run_id=m['run_id'],passed=passed,tasks=len(tasks),value=round(passed/len(tasks)*100,1)))
 assert len(records)==len(prev['models']) and all(x in prev['models'] for x in records),id
 assert len(computed)==len(prev['computed']) and all(x in prev['computed'] for x in computed),(id,computed)
 prev['models']=records;prev['computed']=computed;save(t,prev,[u,'https://www.realevals.xyz/_next/static/chunks/app/(main)/page-89fe682a64228531.js'],'Flattened all task-level records; selected version and tab, recomputed v1 pass as nonempty evalsPassed and empty evalsFailed; v2 pass as points>0; passed/tasks ×100 rounded to 1 decimal; all records and scores match')
# AssistantBench current Gradio config contains full initialized board.
t=T['assistantbench'];u='https://assistantbench-leaderboard.hf.space/config';data=next(x for x in obj(u)['components'] if x['type']=='dataframe')['props']['value'];prev=old(t);assert data['headers']==prev['headers'] and data['data']==prev['data'];save(t,data,[u],'Extracted initialized Gradio dataframe with all 184 numeric rows; full equality with prior test board')
# BearCubs published Typescript array is JSON, no runtime evaluation.
t=T['bearcubs'];u=t['fetched'][0];s=txt(u);records=json.loads(s[s.index('['):s.rindex(']')+1]);prev=old(t);assert records==prev['ts_data'];save(t,{'ts_data':records},[u],'Parsed published Typescript JSON array; compared every numeric field and row')
# Google Sheets: main board rows, subset/human sections kept out of normalization.
t=T['webchorearena'];u=t['fetched'][0];records=list(csv.reader(io.StringIO(txt(u))));prev=old(t);assert records==prev['csv_rows'];save(t,prev,[u],'Parsed every CSV cell including main/subset metadata; exact equality')
for id in ['webarena','visualwebarena']:
 t=T[id];u,hu=t['fetched'];records=list(csv.reader(io.StringIO(txt(u))));prev=old(t);offset=1 if id=='webarena' else 4;main=records[offset:offset+len(prev['rows'])]
 assert main==[x['cells'] for x in prev['rows']],id
 # Verify no additional main-board rows are hidden outside the prior slice.
 if id=='webarena':assert all(not any(x) for x in records[offset+len(main):records.index(next(x for x in records if x[0]=='WebArena Subset'))])
 else:assert len(records)==offset+len(main)
 (ROOT/'sources'/id/'leaderboard-2026-10-07.csv').write_text(txt(u))
 (ROOT/'sources'/id/'leaderboard-2026-10-07.html').write_text(txt(hu))
 save(t,prev,[u,hu],'Parsed all current CSV rows; exact main-board rows equality; verified subset/human boundaries and retained separate full CSV/HTML artifacts')
# AndroidWorld: source rows define rank and month; model normalization retained only for exact model names.
t=T['androidworld'];u=t['fetched'][0];records=list(csv.reader(io.StringIO(txt(u))));before=copy.deepcopy(t['rows']);prev=list(csv.reader(io.StringIO(baseline(t['snapshot']))));old_source=[x for x in prev[2:] if len(x)>8 and x[2] and (x[8] or x[10]) and x[2]!='Human'];rs=[]
for x in records[2:]:
 if len(x)<13 or not x[2] or not (x[8] or x[10]) or x[2]=='Human' or x[6]=='Human':continue
 # stop at board's distinct human baseline section
 if not re.match(r'^\d{1,2}/\d{4}$',x[1]):continue
 # Source identity uses result source, model raw and model size for repeated MAI-UI names.
 olds=[z for z in old_source if z[2]==x[2] and z[6]==x[6] and z[5]==x[5]]
 old_score=(float(olds[0][8]) if olds[0][8] else None) if olds else None
 candidates=[a for a in before if olds and a['system']==x[2].strip() and a['score']==old_score]
 if len(candidates)==1 and olds:r=copy.deepcopy(candidates[0])
 elif x[2] in ['Kirk Engine','MobileRun']:
  r=newrow(x[2]);r['agent']=x[2]
  if x[2]=='Kirk Engine':r['model_raw']=[z.strip() for z in x[6].split('/')];r['model_ids']=['gpt-4o','gpt-5.4']
  else:r['model_raw']=[x[6]];r['model_ids']=['gpt-6-astra']
 else:
  # Unambiguous fallback uses score+exact result source for duplicate vendor entries.
  candidates=[a for a in before if a['system']==x[2].strip() and a['score']==(float(x[8]) if x[8] else None)]
  assert len(candidates)==1,(x,candidates);r=copy.deepcopy(candidates[0])
 r.update(rank=int(x[0]) if x[0].isdigit() else None,score=float(x[8]) if x[8] else None,date=f"{x[1].split('/')[1]}-{int(x[1].split('/')[0]):02}",verified=False,open_source=x[4]=='✔')
 if not r['model_config']:
  r['model_config']='type='+x[3]+'; screen='+x[7]
  if x[5] and x[5]!='-':r['model_config']+='; model_size='+x[5]
 r['score_extra']={k:v for k,v in r['score_extra'].items() if k not in ['trials']}
 if x[9].strip():r['score_extra']['trials']=float(x[9]) if '.' in x[9] else int(x[9])
 if x[12].strip():r['score_extra']['note']=x[12].strip()
 if x[11].startswith('https://'):r['row_url']=x[11]
 rs.append(r)
assert len(rs)==47,len(rs);t['rows']=rs;save(t,txt(u),[u],'Parsed all main-board CSV rows/ranks/months and notes; preserved exact known model identity mappings; retained self-reported verification=false',before)
# Kaggle public API: source model metadata may grow, compare all leaderboard fields.
t=T['browsecomp-kaggle'];u='https://www.kaggle.com/api/i/benchmarks.BenchmarkService/GetBenchmarkLeaderboard';n=obj(u);prev=old(t)
assert len(n['rows'])==len(prev['rows'])
for a,b,r in zip(prev['rows'],n['rows'],t['rows']):
 assert a['results']==b['results'] and a['modelVersion']['slug']==b['modelVersion']['slug']
 assert r['score']==b['results'][0]['numericResult']['value']
 assert r['score_extra']['confidence_interval']==b['results'][0]['numericResult']['confidenceInterval']
 assert r['date']==b['results'][0]['evaluationDate'][:10]
 assert r['system']==(b['modelVersion'].get('displayName') or b['modelVersion']['name'])
 assert r['row_url']==b['modelVersion'].get('externalUrl')
save(t,n,[u],'POST versionIdentifier.versionIdSelector.id=35; mechanically extracted/compared all 42 scores, confidence intervals, row dates, model identities and links; API metadata additions retained')
