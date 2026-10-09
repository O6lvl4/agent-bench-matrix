"""2026-10-09 audit/extraction recipe. Reads retained primary-source bodies only.
Run from the repository root after collect_tool_general_20261005.py.
No network access; never executes downloaded code. Changes only validated tables.
"""
import ast,copy,hashlib,json,pathlib,re,os
from lxml import html
ROOT=pathlib.Path('.');DATE='2026-10-09';OUT=ROOT/'sources/audits'/DATE
CACHE=pathlib.Path(os.environ.get('ABM_TOOL_CACHE','/tmp/abm-tool-20261009'));INDEX=json.loads((CACHE/'index.json').read_text());IX={x['url']:x for x in INDEX}
TABLES=[json.loads(p.read_text())for p in (ROOT/'data/tables').glob('*.json')if json.loads(p.read_text())['category']in ('terminal','tool-use','general')]
AUD=[];CURRENT={};USED={}
def txt(u):
 r=IX[u];assert 'file'in r,r.get('error','No retained body')
 p=pathlib.Path(r['file']);p=p if p.is_absolute()else CACHE/p;b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256'];return b.decode()
def obj(u):return json.loads(txt(u))
def save(p,o):pathlib.Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=1)+'\n')
def rsc(raw):
 out=[]
 for a in html.fromstring(raw).xpath('//script/text()'):
  for m in re.finditer(r'self\.__next_f\.push\(',a):
   try:
    v=json.JSONDecoder().raw_decode(a[m.end():])[0]
    if isinstance(v,list)and len(v)>1 and isinstance(v[1],str):out.append(v[1])
   except ValueError:pass
 return ''.join(out)
def vals(s,k):
 out=[]
 for m in re.finditer('"'+re.escape(k)+'"\\s*:',s):
  try:out.append(json.JSONDecoder().raw_decode(s[m.end():].lstrip())[0])
  except ValueError:pass
 return out
def normalized(x):return re.sub(r'\s+',' ',html.tostring(x,encoding='unicode')).strip()
def first_table(raw):return html.fromstring(raw).xpath('self::table|.//table')[0]
def extracted(t):
 id=t['id'];old=pathlib.Path(t['snapshot']).read_text();us=[]
 if id.startswith('terminal-'):
  candidates=[u for u in t['fetched']if '(POST'in u];u=candidates[0]
  if id=='terminal-bench-science-0-1'and 'file'not in IX[u]:u=next(u for u in t['fetched']if '/api/leaderboard?'in u)
  us=[u];o=json.loads(old);n=obj(u)
  if id=='terminal-bench-science-0-1':n={k:n[k] for k in o}
 elif id.startswith('appworld-'):
  u=next(u for u in t['fetched']if u.endswith('.json'));us=[u];o=json.loads(old);n=obj(u)
 elif id=='bfcl-v4':
  u=next(u for u in t['fetched']if u.endswith('.csv'));us=[u];o=old.strip();n=txt(u).strip()
 elif id.startswith('hal-'):
  us=t['fetched'][:1];o=normalized(first_table(old));n=normalized(first_table(txt(us[0])))
 elif id.startswith('mcp-universe-'):
  us=t['fetched'][:1];a=html.fromstring(old).xpath('self::div[starts-with(@id,"panel-")]|.//div[starts-with(@id,"panel-")]')[0];b=html.fromstring(txt(us[0])).get_element_by_id(a.get('id'));o=normalized(a);n=normalized(b)
 elif id.startswith('apex-'):
  us=t['fetched'][:1];o=json.loads(old);page=json.loads(html.fromstring(txt(us[0])).get_element_by_id('__NEXT_DATA__').text)['props']['pageProps'];n={'source':o['source']}
  for k,v in o.items():
   if k=='source':continue
   if isinstance(v,dict):n[k]={kk:page[k][kk]for kk in v}
   elif k=='leaderboardData'and id!='apex-agents':n[k]=[{kk:r[kk]for kk in v[0]if kk in r}for r in page[k]]
   elif k=='domains':n[k]=[{kk:r[kk]for kk in v[0]if kk in r}for r in page[k]]
   else:n[k]=page[k]
 elif id.startswith('mcpmark-'):
  us=t['fetched'][:1];o=json.loads(old);n=copy.deepcopy(o);vv=vals(rsc(txt(us[0])),'data');n['main']['data']=next(v for v in vv if isinstance(v,list)and v and isinstance(v[0],dict)and 'passAtOne'in v[0]);n['per_service']['data']=next(v for v in vv if isinstance(v,list)and v and isinstance(v[0],dict)and 'models'in v[0]);assert o['updated_at_on_page']in rsc(txt(us[0]))
 elif id.startswith('toolathlon'):
  us=[t['fetched'][1]];o=[normalized(x)for x in html.fromstring(old).xpath('//table')];n=[normalized(x)for x in html.fromstring(txt(us[0])).xpath('//table')];assert len(o)==len(n)==2
 elif id=='mcp-atlas':
  us=t['fetched'][:1];o=json.loads(old);n=copy.deepcopy(o);n['entries']=next(v for v in vals(rsc(txt(us[0])),'entries')if isinstance(v,list)and v and 'score'in v[0]);assert o['methodology_table_all1000_vs_public500']['rows']in vals(rsc(txt(us[0])),'rows')
 elif id.startswith('tau'):
  mu=next(u for u in t['fetched']if u.endswith('manifest.json'));us=[mu];o=json.loads(old);n={'manifest':obj(mu),'submissions':{}}
  # Full manifest plus every table-selected submission must be available; partial successes do not refresh a table.
  missing=[]
  for k in o['submissions']:
   u=mu.replace('manifest.json',k+'/submission.json');us.append(u)
   if 'file'not in IX.get(u,{}):missing.append(u)
   else:n['submissions'][k]=obj(u)
  relevant='voice_submissions'if id.startswith('tau3-voice')else 'legacy_submissions'if 'legacy'in id else 'submissions'
  assert not missing,'Incomplete selected submission set: '+str(len(missing))+' missing primary bodies'
  assert n['manifest'][relevant]==o['manifest'][relevant],'Manifest changed; domain-specific extraction needs review'
 elif id=='gaia2-cli':
  us=t['fetched'][:1];o=json.loads(old);tree=ast.parse(txt(us[0]));n=next(ast.literal_eval(x.value)for x in tree.body if isinstance(x,ast.Assign)and isinstance(x.targets[0],ast.Name)and x.targets[0].id=='_GAIA2_CLI_DATA')
 elif id in ('gaia','gaia2'):
  u=t['fetched'][0];event=obj(u)['event_id'];us=[u,u+'/'+event];lines=[x[6:]for x in txt(us[-1]).splitlines()if x.startswith('data: ')];payload=json.loads(lines[-1]);o=json.loads(old);n={k:payload[0][k]for k in o}
 elif id=='mcp-bench':
  us=t['fetched'][-1:];o=json.loads(old);s=txt(us[0]);n=copy.deepcopy(o);n['data']=json.JSONDecoder().raw_decode(s[s.index('=')+1:].lstrip())[0]
 elif id=='theagentcompany':
  us=t['fetched'][-1:];o=json.loads(old);s=txt(us[0]);found=[]
  for match in re.finditer(r'JSON\.parse\(',s):
   tail=s[match.end():]
   if not tail.startswith(('"',"'")):continue
   q=tail[0];end=1
   while end<len(tail):
    if tail[end]=='\\':end+=2;continue
    if tail[end]==q:break
    end+=1
   try:
    v=json.loads(ast.literal_eval(tail[:end+1]));found.append(v)
   except (ValueError,SyntaxError,json.JSONDecodeError):pass
  assert o['data']in found,'Saved data not matched among JSON.parse literals';n=copy.deepcopy(o)
 elif id=='skillsbench':
  us=t['fetched'][-1:];o=json.loads(old);s=txt(us[0]);start=s.index('[{',s.index('leaderboardData'));end=s.index('}]',start)+2;literal=s[start:end];literal=re.sub(r'([\{,])([a-zA-Z][a-zA-Z0-9]*):',r'\1"\2":',literal);n=copy.deepcopy(o);n['leaderboardData']=json.loads(literal)
 else:raise ValueError('Unhandled table '+id)
 USED[id]=us;CURRENT[id]=n
 return o,n,us

def audit():
 for t in sorted(TABLES,key=lambda t:t['id']):
  a={'id':t['id'],'category':t['category'],'rows_before':len(t['rows']),'retrieved_before':t['retrieved']}
  try:
   old,new,us=extracted(t);a.update(status='unchanged'if old==new else 'changed-source',sources=[{k:v for k,v in IX[u].items()if k!='file'}for u in us]);
   if old!=new:save('/tmp/abm-tool-current-'+t['id']+'.json',new)
  except Exception as e:a.update(status='preserved-gap',error=str(e),tried=t['fetched'],failed_sources=[IX[u]for u in t['fetched']if u in IX and 'error'in IX[u]and '/submissions/'in u])
  AUD.append(a);print(a['id'],a['status'],a.get('error',''))
 save('/tmp/abm-tool-general-preliminary.json',{'retrieved':DATE,'network_status':'Acquisition execution cancellation surfaced on poll; only retained complete successful response bodies used; no retry.','tables':AUD})
if __name__=='__main__':audit()

# Explicit evidence-backed identity proposals; parent owns registry edits.
PROPOSALS=[
 {'id':'mimo-v2.6-flash-rl','name':'MiMo V2.6 Flash RL','vendor':'Xiaomi','open_weights':None,'weights_url':None,'aliases':[],'source':'https://www.mercor.com/apex/apex-agents-leaderboard/','source_model_id':'mimo-v2.6-flash-rl'},
 {'id':'claude-haiku-5.5','name':'Claude Haiku 5.5','vendor':'Anthropic','open_weights':None,'weights_url':None,'aliases':[],'source':'https://www.mercor.com/apex/apex-agents-leaderboard/','source_model_id':'claude-haiku-5-5'}]

def new_rows(t,n):
 id=t['id'];old=t['rows']
 if id.startswith('terminal-'):
  allts=[json.loads(p.read_text())for p in pathlib.Path('data/tables').glob('*.json')];lookup={raw:r['model_ids']for ts in allts for r in ts['rows']for raw in r['model_raw']if len(r['model_raw'])==1 and len(r['model_ids'])==1}
  reg=json.loads(pathlib.Path('data/models.json').read_text())['models'];norm=lambda s:re.sub('[^a-z0-9]','',s.lower());lu={norm(a):r['id']for r in reg for a in [r['id'],r['name']]+r['aliases']}
  lookup['Qwen3.8-Max-0902']=['qwen3.8-max'] # Date suffix retained verbatim in model_raw and source date.
  def mid(label):
   if label in lookup:return lookup[label]
   hits={lu[norm(x)]for x in [label,'Claude '+label]if norm(x)in lu};assert len(hits)==1,(label,hits);return list(hits)
  km={'accuracy_ci95_half_width':'ci95_half_width','accuracy_stderr':'stderr','passes':'successes','total_cost_usd':'cost_usd','reward_hacks':'reward_hacks_pct','n_trials':'trials'};rows=[]
  for r in n['rows']:
   if r['status']!='display':continue
   m=r['metadata'];v=r['metrics'];label=lambda k:m[k].get('label')if isinstance(m.get(k),dict)else m.get(k);model=label('model_display');agent=label('agent_display');extra={km.get(k,k):val for k,val in v.items()if isinstance(val,(float,int))and not isinstance(val,bool)and k not in ('accuracy','tasks')}
   extra['trials']=v['tasks']if id=='terminal-bench-science-0-1'else r['n_trials']
   if id=='terminal-bench-science-0-1'and r['n_trials']!=v['tasks']:extra['source_n_trials']=r['n_trials']
   if 'partial:'in v.get('display_cost',''):extra['cost_note']=v['display_cost']
   rows.append({'rank':r['rank'],'system':f'{agent} / {model}','agent':agent,'model_raw':[model],'model_ids':mid(model),'model_config':'reasoning_effort='+m['reasoning_effort'],'score':v['accuracy'],'score_extra':extra,'date':m.get('date',m.get('model_release_date')),'verified':m.get('verified'),'open_source':None,'org':label('agent_org'),'row_url':old[0]['row_url'].rsplit('/',1)[0]+'/'+r['id']})
  return rows
 if id.startswith('apex-'):
  isoverall=id=='apex-agents';key='model_id'if isoverall else'model_name';oldsource=json.loads(pathlib.Path(t['snapshot']).read_text());oldby={r[key]:next(rr for rr in old if rr['model_config'].endswith('model_id: '+r[key]))for r in oldsource['leaderboardData']};metas={r['model_id']:r for r in CURRENT['apex-agents']['leaderboardData']};pmap={r['source_model_id']:r['id']for r in PROPOSALS};pmap['muse-spark-1-3-max']='muse-spark-1.3';rows=[]
  for r in n['leaderboardData']:
   k=r[key];name=r['model_name']if isoverall else r['model_display_name'];v=r['score']if isoverall else r['overall_score'];h='loop_truncated_tools_agent';ex={'pass_at_1':v['pass-1'][h]}
   if isoverall:ex.update({'mean_score_error':r['error']['mean-score'][h],'pass_at_1_error':r['error']['pass-1'][h],'n_samples':r['n_samples']})
   ids=oldby[k]['model_ids']if k in oldby else[pmap[k]]
   rows.append({'rank':None,'system':name,'agent':'Loop','model_raw':[name],'model_ids':ids,'model_config':('effort: '+r['effort']+'; 'if r.get('effort')else'')+'model_id: '+k,'score':v['mean-score'][h],'score_extra':ex,'date':r.get('release_date')or None,'verified':None,'open_source':None,'org':metas[k]['providerName'],'row_url':None})
  rows.sort(key=lambda r:-r['score'])
  for i,r in enumerate(rows):r['rank']=i+1
  return rows
 if id=='mcp-atlas':
  by={r['system']:r for r in old};rows=[]
  for r in n['entries']:
   rr=copy.deepcopy(by[r['model']]);rr.update(rank=r['rank'],score=r['score'],score_extra={'ci_plus_minus':r['confidenceInterval_upper']},date=r['createdAt'][:10],org=r['company']);rows.append(rr)
  return rows
 if id=='gaia':
  o=json.loads(pathlib.Path(t['snapshot']).read_text());oldmap={(r[0],r[1],r[2]):out for r,out in zip(o['data'],old)};rows=[]
  for i,r in enumerate(n['data']):
   oldr=oldmap.get((r[0],r[1],r[2]));a=html.fromstring(r[0]);name=a.text_content().strip();links=a.xpath('self::a|.//a');raw=[x.strip()for x in r[1].split(',')if x.strip()]
   rr=copy.deepcopy(oldr)if oldr else {'rank':None,'system':name or r[2],'agent':None,'model_raw':raw,'model_ids':[],'model_config':None,'score':None,'score_extra':{},'date':None,'verified':None,'open_source':None,'org':r[2]or None,'row_url':(links[0].get('href')or None)if links else None}
   assert rr['system'];rr.update(rank=i+1,score=r[3],date=r[7]or None);rr['score_extra']={'level1':r[4],'level2':r[5],'level3':r[6]}
   if not name:rr['score_extra']['agent_name_empty_on_board']=True
   if len(rr['model_raw'])>1 and len(rr['model_ids'])==1:rr['model_ids']=[]
   rows.append(rr)
  return rows
 raise ValueError('No extraction recipe for changed '+id)

def apply():
 details={
 'terminal-bench-4-0':'Extracted 8 new official-agent configurations plus source ranks. Preserved effort, release dates, 330 trials, costs, confidence intervals, and pass@k; no scoring aggregation.',
 'terminal-bench-science-0-1':'Retained complete official site API response used because the already-attempted Harbor POST returned HTTP 500. Same leaderboard/package/version and same 17 overall scores/costs; site API n_trials is now 210 on five previously inconsistent source rows. Domain metric payload retained in snapshot, not mixed into the overall table.',
 'gaia':'Re-extracted official top-100 display, including six new multi-model/ambiguous Shadow rows. Such rows retain empty model_ids. Model variants, level metrics, source dates, links and organisations preserved.',
 'mcp-atlas':'Current RSC rows preserve all 34 scores/configurations; official rank values are now consecutively renumbered.',
 }
 for a in AUD:
  t=next(t for t in TABLES if t['id']==a['id']);old=copy.deepcopy(t['rows'])
  if a['status']=='preserved-gap':
   a['rows_after']=len(old);a['retrieved_after']=t['retrieved'];continue
  if a['status']=='changed-source':
   n=CURRENT[t['id']];t['rows']=new_rows(t,n);save(t['snapshot'],n);a['status']='changed'if old!=t['rows']else'unchanged';a['detail']=details.get(t['id'],'Extracted 56 published configurations separately; source display names and all score/error/sample fields rechecked against APEX v1.1 Loop page props. Mean score remains distinct from Pass@1.')
  else:
   a['detail']='All comparison-relevant leaderboard rows and fields extracted from current retained primary response and matched the previous snapshot. Existing table bytes/retrieval date retained because data did not change.'
   a['rows_after']=len(old);a['retrieved_after']=t['retrieved'];a['checked_at']=DATE;a['rows_added_net']=0;a['row_values_changed']=False;continue
  notes={'mcp-atlas': 'rank は現行RSCデータの値(1〜34)を転記。ページが読み込む共通レンダラーも entry.rank を直接表示する。一方、ページ脚注は信頼区間上限による「Rank (UB)」の説明のままで、現行データの連番順位と一致しない。± は ci_plus_minus。date は掲載データの createdAt(登録日)。2026年4月に採点方法を更新し全モデルを再採点したとページに記載。ページ上部の「83.6% Top Pass Rate」は表の最高値(88.1)と食い違う。', 'terminal-bench-science-0-1': '分野別の成績 (domain_metrics) はスナップショットに残した。task_matrix はサイズの都合で除いた。日付はモデル公開日。費用(cost_usd)とtotal_tokensは全試行の合計。試行数は各行のmetrics.tasks(70タスク×3試行＝210)から取り、今回取得した公式サイトAPIのn_trialsも全行210で一致する。以前のn_trials=0との不一致を示すsource_n_trialsは解消した。'}
  if t['id']in notes:t['notes_ja']=notes[t['id']]
  t['retrieved']=DATE;t['newest_row_date']=max((r['date']for r in t['rows']if r['date']),default=None);save('data/tables/'+t['id']+'.json',t);a['rows_after']=len(t['rows']);a['retrieved_after']=DATE
  a['rows_added_net']=len(t['rows'])-len(old);a['row_values_changed']=old!=t['rows']
  assert all(r['date']is None or r['date']<=DATE for r in t['rows'])
 save(OUT/'tool-general-model-proposals.json',PROPOSALS)
 save(OUT/'tool-general.json',{'retrieved':DATE,'table_count':len(TABLES),'collection_recipe':'scripts/collect_tool_general_20261005.py /tmp/abm-tool-20261009','network_status':'Acquisition execution cancellation surfaced on poll. Retained completed index contains 57 successful bodies and 53 errors. No retry or alternate-route network requests performed.','tables':AUD})
 save(OUT/'tool-general-fetch-index.json',[{k:v for k,v in r.items()if k!='file'}for r in INDEX])
 # Parent consolidates current-run incomplete coverage into the aggregate gap.

if __name__=='__main__':apply()
