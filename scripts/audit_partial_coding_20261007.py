#!/usr/bin/env python3
"""Audit source bytes retained before a interrupted fetch session; never resumes network.
The cancelled process never wrote its response index. File presence proves only that
urlopen succeeded (the original collector writes only inside that success branch).
HTTP statuses and redirect URLs were lost, so they remain unknown in the audit.
Missing sources and missing pricing support retain the complete prior tables.
"""
import copy,json,pathlib,re,subprocess
import refresh_coding_sources as c
ROOT=c.ROOT;DATE='2026-10-07';CACHE=pathlib.Path('/tmp/abm-coding-oct7')
T=[c.load(p) for p in sorted((ROOT/'data/tables').glob('*.json')) if c.load(p)['category']=='coding']
IX=[]
for u,ids in c.source_jobs(T).items():
 p=CACHE/c.sha(u.encode())[:16]
 x={'request_description':u,'url':u.split(' (POST ')[0],'file':p.name,'tables':ids,'retrieved':DATE,'http_status':None,'final_url':None,'collector_completed':False}
 if p.exists():x.update(cache_received=True,bytes=p.stat().st_size,sha256=c.sha(p.read_bytes()),evidence='Original collector wrote response bytes only after a successful urlopen; response index was lost when the acquisition process was interrupted.')
 else:x.update(cache_received=False,error='Source not available in the incomplete cache; the cancelled execution was not retried.')
 IX.append(x)
class Partial(c.Refresh):
 def text(self,tid,n=0):
  e=self.sources[tid][n];assert e.get('cache_received'),e.get('error');b=(self.cache/e['file']).read_bytes();assert c.sha(b)==e['sha256'];return b.decode()
W=Partial(CACHE,DATE,T,IX);audit=[]
for t in T:
 before=copy.deepcopy(t);p=ROOT/('data/tables/'+t['id']+'.json');snapshot=ROOT/t['snapshot'];prior=snapshot.read_bytes();old=json.loads(prior) if prior.lstrip()[:1]in(b'{',b'[') else prior.decode()
 try:
  if t['id'].startswith('deepswe-'):raise ValueError('Raw leaderboard response retained, but current frontend pricing support was not fetched before execution cancellation; prior costs/configuration preserved.')
  if not all(e.get('cache_received') for e in W.sources[t['id']]):raise ValueError('Incomplete source cache from cancelled execution; prior table retained.')
  new,same=W.project(t,old)
  if not same:
   rows=W.changed_rows(t,new);t['rows']=rows;t['retrieved']=DATE;t['newest_row_date']=max((r['date'] for r in rows if r.get('date')),default=None)
   assert all(not r.get('date') or r['date']<=DATE for r in rows)
   assert all(mid in W.registry for r in rows for mid in r['model_ids'])
   # No unknown identity is silently guessed by the existing extractor.
   assert not W.proposals
   if rows!=before['rows']:
    c.dump(p,t);snapshot.write_text(new if isinstance(new,str) else json.dumps(new,ensure_ascii=False,indent=2)+'\n')
  substantive=t['rows']!=before['rows']
  audit.append({'id':t['id'],'status':'changed' if substantive else 'unchanged','rows_before':len(before['rows']),'rows_after':len(t['rows']),'snapshot_changed':not same,'snapshot_sha256':c.sha(snapshot.read_bytes()),'sources':W.sources[t['id']]})
 except Exception as e:
  assert p.read_bytes()==subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
  assert snapshot.read_bytes()==prior
  audit.append({'id':t['id'],'status':'preserved-gap','error':str(e),'sources':W.sources[t['id']]})
c.dump(CACHE/'partial-audit.json',{'retrieved':DATE,'fetch_session':'cancelled; not retried','tables':audit})
for a in audit:print(a['id'],a['status'],a.get('error',''))
