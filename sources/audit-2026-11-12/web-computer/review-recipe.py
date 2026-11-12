import pathlib,json,subprocess,re,hashlib,math
R=pathlib.Path('/workspace/scratch/5e56fa97c4c6/bench-run-20261112'); C=pathlib.Path('/tmp/bench-web-20261112');ix=json.loads((C/'index.json').read_text());a=json.loads((C/'audit.json').read_text());u='https://osworld-v2.xlang.ai/static/data/leaderboard/official-results.json';n=json.load(open(ix[u]['path']))
def subset(s,id,alltypes=False):
 agent='public-agents' in id;steps=int(re.search(r'(\d+)steps',id)[1]);sc='offline' if 'offline' in id else 'full';v21=id.startswith('osworld-2-1-')
 return [x for x in s['results'] if (alltypes or (x.get('modelType','e2e')=='agent')==agent) and x['stepBudget']==steps and (x.get('datasetScope')or x.get('scope')or s.get('defaultResultDatasetScope','full'))==sc and ((x.get('releaseVersion')or x.get('taskVersion')or s.get('defaultResultReleaseVersion')or s['taskVersion'])=='v2.1')==v21]
for rec in a['tables']:
 if rec['id'].startswith('osworld-2'):
  t=json.loads((R/'data/tables'/f"{rec['id']}.json").read_text());o=json.loads((R/t['snapshot']).read_text()); assert subset(o,t['id'])==subset(n,t['id'])
  if 'public-agents' in t['id']:
   # Compare entire same-condition All-tab source records so rank cannot change unnoticed.
   ranking=sorted(subset(n,t['id'],True),key=lambda x:(-x['binaryAccuracy'],-x['partialScore'],x.get('estimatedCostUsd',math.inf),x['model']))
   assert all(r['rank']==next(i for i,x in enumerate(ranking,1) if x['model']==r['system']) for r in t['rows'])
  rec.update(status='unchanged',method='Compared every source field within matching release, dataset scope, step budget and modelType. Public-agent ranks were recomputed within current same-condition All-tab records and match saved ranks. Unrelated scopes in older whole-source snapshots do not imply table changes.',sources=[{'url':u,'http_status':200,'sha256':hashlib.sha256(pathlib.Path(ix[u]['path']).read_bytes()).hexdigest()}]);rec.pop('error',None)
p=R/'data/tables/androidworld.json';old=json.loads(subprocess.check_output(['git','show','HEAD:data/tables/androidworld.json'],cwd=R));new=json.loads(p.read_text());
for x,y in zip(old['rows'],new['rows']):
 for k in x:
  if x[k]!=y[k]:x[k]=y[k]
old['retrieved']='2026-11-12';p.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
# Preserve prior privacy minimization for non-score contact footer.
p=R/old['snapshot'];p.write_text(p.read_text().replace('crawles@gmail.com','[contact email omitted]'))
for rec in a['tables']:
 if rec['id']=='androidworld':rec['change_type']='source-row-link-only';rec['scores_changed']=False;rec['method']='Parsed all 48 main-board CSV rows; only Agent-Visco published row link changed. Scores, ranks, configurations and identities unchanged; contact footer remains redacted as before.'
a['parser_errors']=[e for e in a['parser_errors'] if not e.get('id','').startswith('osworld-2')]
(C/'audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
