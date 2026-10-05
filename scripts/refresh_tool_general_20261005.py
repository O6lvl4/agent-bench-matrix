"""Reproduce the 2026-10-05 terminal/tool/general source audit.
Run from repository root with PYTHONPATH providing beautifulsoup4.
The cache index maps fetched public URLs to saved response paths; network fetch is separate.
No source content is executed. Existing normalization is retained for exact known model spellings.
"""
import argparse,ast,copy,hashlib,json,pathlib,re,os
from bs4 import BeautifulSoup
ROOT=pathlib.Path('.')
DATE='2026-10-05'
CACHE=pathlib.Path(os.environ.get('ABM_TOOL_CACHE','/tmp/abm-own-fetch'))
INDEX=json.load(open(CACHE/'index.json'))
IX={x['url']:x for x in INDEX if 'file' in x}
AUDIT=[]
def txt(u):return pathlib.Path(IX[u]['file']).read_text()
def obj(u):return json.loads(txt(u))
def table(id):return json.load(open(f'data/tables/{id}.json'))
def snap(t):return pathlib.Path(t['snapshot'])
def write(p,d):pathlib.Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=1)+'\n')
def mark(t,status,urls,detail,oldrows=None):
 t['retrieved']=DATE;t['newest_row_date']=max((r['date'] for r in t['rows'] if r['date']),default=None);write(f'data/tables/{t["id"]}.json',t)
 AUDIT.append({'table':t['id'],'category':t['category'],'status':status,'rows_before':len(oldrows if oldrows is not None else t['rows']),'rows_after':len(t['rows']),'source_urls':urls,'detail':detail})
def unchanged(t,u,kind):
 old=json.loads(snap(t).read_text()) if kind=='json' else snap(t).read_text().strip();new=obj(u) if kind=='json' else txt(u).strip();assert old==new,t['id'];mark(t,'unchanged',[u],'Fetched source snapshot is semantically identical.' if kind=='json' else 'Fetched source snapshot is byte-identical after exterior whitespace.')
def rsc(u):
 s=BeautifulSoup(txt(u),'html.parser');out=[]
 for x in s.find_all('script'):
  a=x.string or x.get_text()
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

def main():
 for id in ['terminal-bench-2-0','terminal-bench-2-1','terminal-bench-3-0','appworld-test-normal','appworld-test-challenge','bfcl-v4']:
  t=table(id);u=next(u for u in t['fetched'] if ('(POST 'in u if t['category']=='terminal' else u.endswith('.json') if id.startswith('appworld') else u.endswith('.csv')));unchanged(t,u,'text' if id=='bfcl-v4' else 'json')
 # New Harbor rows preserve benchmark package/version and retain release-date semantics.
 allts=[json.load(open(p)) for p in pathlib.Path('data/tables').glob('*.json')];lookup={raw:r['model_ids']for t in allts for r in t['rows'] for raw in r['model_raw'] if len(r['model_raw'])==1}
 lookup.update({'Grok 4.7':['grok-4.7'],'Opus 5.5':['claude-opus-5.5']})
 keymap={'accuracy_ci95_half_width':'ci95_half_width','accuracy_stderr':'stderr','passes':'successes','total_cost_usd':'cost_usd','reward_hacks':'reward_hacks_pct','n_trials':'trials'}
 for id in ['terminal-bench-4-0','terminal-bench-science-0-1']:
  t=table(id);u=next(u for u in t['fetched'] if '(POST 'in u);s=obj(u);old=copy.deepcopy(t['rows']);rows=[]
  for r in s['rows']:
   if r['status']!='display':continue
   m=r['metadata'];v=r['metrics'];label=lambda k: m[k].get('label') if isinstance(m.get(k),dict) else m.get(k)
   model=label('model_display');agent=label('agent_display');extra={}
   for k,val in v.items():
    if isinstance(val,(float,int)) and not isinstance(val,bool) and k not in ['accuracy','tasks']:extra[keymap.get(k,k)]=val
   extra['trials']=v['tasks'] if id=='terminal-bench-science-0-1' else r['n_trials']
   if id=='terminal-bench-science-0-1' and r['n_trials']!=v['tasks']:extra['source_n_trials']=r['n_trials']
   if 'partial:' in v.get('display_cost',''):extra['cost_note']=v['display_cost']
   rows.append({'rank':r['rank'],'system':f'{agent} / {model}','agent':agent,'model_raw':[model],'model_ids':lookup[model],'model_config':'reasoning_effort='+m['reasoning_effort'],'score':v['accuracy'],'score_extra':extra,'date':m.get('date',m.get('model_release_date')),'verified':m.get('verified'),'open_source':None,'org':label('agent_org'),'row_url':old[0]['row_url'].rsplit('/',1)[0]+'/'+r['id']})
  t['rows']=rows;write(snap(t),s);mark(t,'changed',[u],'Added source-published rows; all numeric metrics extracted mechanically. Partial-cost qualifier retained.',old)
 # HTML table audits compare the actual complete table, including attributes and links.
 for id in ['hal-gaia','hal-tau-bench-airline','mcp-universe-agent','mcp-universe-react','mcp-universe-fc']:
  t=table(id);u=t['fetched'][0];os=BeautifulSoup(snap(t).read_text(),'html.parser');ns=BeautifulSoup(txt(u),'html.parser')
  if id.startswith('mcp-universe'):
   old=os.find('div',id=re.compile('^panel-'));new=ns.find('div',id=old['id'])
  else:old=os.find('table');new=ns.find('table')
  normalize=lambda x:re.sub(r'\s+',' ',str(x)).strip()
  assert normalize(old)==normalize(new),id
  mark(t,'unchanged',[u],'Complete parsed leaderboard HTML (numeric cells, metadata, links) matches saved snapshot.')
 # APEX emits immutable JSON page props.
 for id in ['apex-agents','apex-agents-corporate-lawyer','apex-agents-management-consultant','apex-agents-investment-banking']:
  t=table(id);u=t['fetched'][0];o=json.loads(snap(t).read_text());p=json.loads(BeautifulSoup(txt(u),'html.parser').find('script',id='__NEXT_DATA__').get_text())['props']['pageProps'];n={k:p[k]for k in o if k!='source'}
  if all(o[k]==n[k]for k in n):mark(t,'unchanged',[u],'All benchmark/domain metadata and leaderboardData page props match snapshot.')
  else:print('PENDING',id,[(k,o[k]==n[k])for k in n]);write('/tmp/abm-apex-new-'+id+'.json',n)
 write('sources/audit-2026-10-05/tool-general.json',{'retrieved':DATE,'tables':AUDIT})

# Additional extractions are invoked after the baseline snapshot comparisons.
def more():
 reg=json.load(open('data/models.json'))['models'];norm=lambda s:re.sub('[^a-z0-9]','',s.lower());lu={norm(a):x['id']for x in reg for a in [x['id'],x['name']]+x['aliases']}
 additions={
  'Grok 4.7':('grok-4.7','xAI'), 'Opus 5.5':('claude-opus-5.5','Anthropic'),
  'GPT-6 Luna':('gpt-6-luna','OpenAI'),'GPT-6 Sol':('gpt-6-sol','OpenAI'),
  'Qwen 3.8 27B':('qwen3.8-27b','Alibaba'),'Sonnet 5.5':('claude-sonnet-5.5','Anthropic'),
  'GPT-6.1 Sol':('gpt-6.1-sol','OpenAI'),'Gemini 4 Argon':('gemini-4-argon','Google'),
  'MiMo V2.6 Pro':('mimo-v2.6-pro','Xiaomi')}
 for name,(id,vendor)in additions.items():lu[norm(name)]=id;lu[norm(id)]=id
 write('/tmp/abm-own-models.json',[{'id':id,'name':name if not name.startswith(('Opus','Sonnet')) else 'Claude '+name,'vendor':vendor,'open_weights':None,'weights_url':None,'aliases':[],'source':'https://www.mercor.com/apex/apex-agents-leaderboard/'}for name,(id,vendor) in additions.items()])
 def model_id(name,k):
  cs=[k,k.split('/')[-1],name,'claude-'+name];cs +=[re.sub(r'-(?:max-pro|max|high|xhigh|medium|preview-high)$','',x) for x in cs];hits={lu[norm(x)]for x in cs if norm(x)in lu};assert len(hits)==1,(name,k,hits);return list(hits)
 apex=json.load(open('/tmp/abm-apex-new-apex-agents.json'));metas={r['model_id']:r for r in apex['leaderboardData']}
 for id in ['apex-agents','apex-agents-corporate-lawyer','apex-agents-management-consultant','apex-agents-investment-banking']:
  t=table(id);old=copy.deepcopy(t['rows']);s=json.load(open('/tmp/abm-apex-new-'+id+'.json'));isoverall=id=='apex-agents';rows=[]
  if not isoverall:
   s['domain']={k:v for k,v in s['domain'].items() if k in ['title','category','date','slug','leaderboard','benchmarkDisplayName','numTasks']}
   keep=['model_name','model_display_name','overall_score','company','effort','release_date'];s['leaderboardData']=[{k:r[k]for k in keep if k in r}for r in s['leaderboardData']]
  else:
   # Keep benchmark provenance/config, not unrelated SEO/FAQ marketing payload.
   keep=['benchmarkId','displayName','availableHarnesses','availablePasses','description','dataLink','blogLink','codeLink','numTasks'];s['benchmark']={k:v for k,v in s['benchmark'].items()if k in keep}
   s['domains']=[{k:v for k,v in d.items()if k in ['title','category','slug','numTasks']}for d in s['domains']]
  for r in s['leaderboardData']:
   k=r['model_id']if isoverall else r['model_name'];name=r['model_name']if isoverall else r['model_display_name'];m=metas[k];v=r['score']if isoverall else r['overall_score'];h='loop_truncated_tools_agent';ex={'pass_at_1':v['pass-1'][h]}
   if isoverall:ex.update({'mean_score_error':r['error']['mean-score'][h],'pass_at_1_error':r['error']['pass-1'][h],'n_samples':r['n_samples']})
   config=('effort: '+r['effort']+'; 'if r.get('effort')else '')+'model_id: '+k
   rows.append({'rank':None,'system':name,'agent':'Loop','model_raw':[name],'model_ids':model_id(name,k),'model_config':config,'score':v['mean-score'][h],'score_extra':ex,'date':r.get('release_date') or None,'verified':None,'open_source':None,'org':m['providerName'],'row_url':None})
  rows.sort(key=lambda r:-r['score'])
  for i,r in enumerate(rows):r['rank']=i+1
  t['tasks']=240 if isoverall else s['domain']['numTasks']
  t['tasks_note']='全体は240タスク。v1.1告知ブログの80 tasks per domainと、現在の職種別ページ3件のnumTasks=80が一致する。' if isoverall else '職種別ページの現在のnumTasks=80。v1.1告知ブログの80 tasks per domainと一致する。'
  t['rows']=rows;s={'source':t['fetched'][0]+' (__NEXT_DATA__ props.pageProps; task trajectories omitted)',**s};write(snap(t),s);mark(t,'changed',[t['fetched'][0]],'53 published configurations retained separately, including duplicate display names with different effort. Mean score and Pass@1 remain distinct; v1.1 dataset link unchanged.',old)
 for id in ['mcpmark-verified','mcpmark-legacy']:
  t=table(id);s=json.loads(snap(t).read_text());rr=rsc(t['fetched'][0]);vv=vals(rr,'data');main=next(v for v in vv if isinstance(v,list)and v and isinstance(v[0],dict)and 'passAtOne'in v[0]);assert main==s['main']['data'];per=next(v for v in vv if isinstance(v,list)and v and isinstance(v[0],dict)and 'models'in v[0]);assert per==s['per_service']['data'];mark(t,'unchanged',[t['fetched'][0]],'Main table and every per-service data row extracted from current RSC are identical.')
 for id in ['toolathlon','toolathlon-verified']:
  t=table(id);a=BeautifulSoup(snap(t).read_text(),'html.parser').find_all('table');b=BeautifulSoup(txt(t['fetched'][1]),'html.parser').find_all('table');assert len(a)==len(b)==2;assert all(re.sub(r'\s+',' ',str(x))==re.sub(r'\s+',' ',str(y))for x,y in zip(a,b));mark(t,'unchanged',[t['fetched'][1]],'Both current Verified and historical leaderboard HTML tables are identical; kept as separate tables.')
 t=table('mcp-atlas');old=copy.deepcopy(t['rows']);s=json.loads(snap(t).read_text());entries=next(v for v in vals(rsc(t['fetched'][0]),'entries') if isinstance(v,list) and v and 'score' in v[0]);oldby={r['system']:r for r in old};rows=[]
 newmap={'Fable 5.1':('claude-fable-5.1',None),'Qwen3.8-2.4T-A95B (xHigh)':('qwen3.8-2.4t-a95b','xHigh'),'GLM 5.3':('glm-5.3',None),'Gemini 3.5 Flash (high)':('gemini-3.5-flash','high'),'Nemotron 3 Ultra (thinking)':('nemotron-3-ultra','thinking')}
 for r in entries:
  name=r['model'];rr=copy.deepcopy(oldby.get(name))
  if rr is None:
   mid,conf=newmap[name];rr={'rank':None,'system':name,'agent':None,'model_raw':[name],'model_ids':[mid],'model_config':conf,'score':None,'score_extra':{},'date':None,'verified':None,'open_source':None,'org':None,'row_url':None}
  rr.update(rank=r['rank'],score=r['score'],score_extra={'ci_plus_minus':r['confidenceInterval_upper']},date=r['createdAt'][:10],org=r['company']);rows.append(rr)
 t['rows']=rows;s['entries']=entries;write(snap(t),s);mark(t,'changed',[t['fetched'][0]],'Source RSC entries extracted; existing configurations and confidence-interval ranking retained.',old)
 p=pathlib.Path('sources/audit-2026-10-05/tool-general.json');existing=json.loads(p.read_text());existing['tables']+=AUDIT;write(p,existing)

def remaining():
 for gid in ['gaia','gaia2']:
  gu=table(gid)['fetched'][0]; event=obj(gu)['event_id']; response=txt(gu+'/'+event); payload=json.loads([line[6:] for line in response.splitlines() if line.startswith('data: ')][-1]); write('/tmp/abm-'+gid+'-gradio.json',payload)
 # Tau source manifest defines the complete candidate set; all 67 submissions fetched once.
 mu='https://sierra-tau-bench-public.s3.us-west-2.amazonaws.com/submissions/manifest.json';manifest=obj(mu)
 for p in pathlib.Path('data/tables').glob('tau*.json'):
  t=table(p.stem);old=copy.deepcopy(t['rows']);s=json.loads(snap(t).read_text());changes=[]
  for k,o in s['submissions'].items():
   n=obj(mu.replace('manifest.json',k+'/submission.json'))
   if o!=n:changes.append(k)
  assert not changes,(t['id'],changes)
  relevant='voice_submissions' if t['id'].startswith('tau3-voice')else 'legacy_submissions'if 'legacy'in t['id']else 'submissions'
  added=set(manifest[relevant])-set(s['manifest'][relevant]);removed=set(s['manifest'][relevant])-set(manifest[relevant]);assert not removed
  assert added in [set(),{'gpt-live-1-astra-high-banking_openai_2026-09-16'}],added
  if t['id']=='tau3-voice-banking' and added:
   k=next(iter(added));u=mu.replace('manifest.json',k+'/submission.json');n=obj(u);v=n['results']['banking_knowledge'];c=n['methodology'];voice=n['voice_config'];verification=c['verification']
   row={'rank':None,'system':n['model_name'],'agent':None,'model_raw':[n['model_name']],'model_ids':['gpt-live-1'],'model_config':'reasoning: '+n['reasoning_effort']+'; user sim: '+c['user_simulator']+'; retrieval: '+v['retrieval_config']+'; voice model: '+voice['model']+'; submission type: '+n['submission_type']+'; one trial; full reviewer: openai/gpt-5.5; entire high run selected from two complete candidates (high and xhigh), no per-task best-of mixing; priority service','score':v['pass_1'],'score_extra':{},'date':n['submission_date'],'verified':verification.get('modified_prompts') is False and verification.get('omitted_questions') is False,'open_source':None,'org':n['submitting_organization'],'row_url':u}
   t['rows'].append(row);t['rows'].sort(key=lambda r:-r['score']);s['submissions'][k]=n;t['fetched'].append(u)
  elif added:
   for k in added:assert set(obj(mu.replace('manifest.json',k+'/submission.json'))['results'])=={'banking_knowledge'}
  for row in t['rows']:
   if 'Backend: GPT-6 Astra' in (row['model_config'] or '') and row['model_ids']==['gpt-live-1']:
    row['model_raw'].append('GPT-6 Astra');row['model_ids'].append('gpt-6-astra')
  s['manifest']=manifest;write(snap(t),s);mark(t,'changed'if len(t['rows'])!=len(old)else 'unchanged',[mu]+[mu.replace('manifest.json',k+'/submission.json')for k in s['submissions']], 'All existing selected submissions identical; the sole new manifest submission is banking-only and is excluded from retail/airline/telecom and overall.',old)
 # Current official GAIA 2 Python constant and Gradio data, no remote code execution.
 t=table('gaia2-cli');u=t['fetched'][0];tree=ast.parse(txt(u));n=next(ast.literal_eval(x.value)for x in tree.body if isinstance(x,ast.Assign)and isinstance(x.targets[0],ast.Name)and x.targets[0].id=='_GAIA2_CLI_DATA');assert n==json.loads(snap(t).read_text());mark(t,'unchanged',[u],'AST literal extraction matches all 7 rows.')
 t=table('gaia2');n=json.load(open('/tmp/abm-gaia2-gradio.json'))[0];o=json.loads(snap(t).read_text());assert n['headers']==o['headers']and n['data']==o['data'];mark(t,'unchanged',[t['fetched'][0]],'Gradio refresh_legacy response matches all headers and rows.')
 t=table('gaia');o=json.loads(snap(t).read_text());old=copy.deepcopy(t['rows']);n=json.load(open('/tmp/abm-gaia-gradio.json'))[0];oldmap={(r[0],r[1],r[2]):out for r,out in zip(o['data'],old)};rows=[]
 for i,r in enumerate(n['data']):
  oldr=oldmap.get((r[0],r[1],r[2]));a=BeautifulSoup(r[0],'html.parser');name=a.get_text().strip();link=a.find('a');raw=[x.strip()for x in r[1].split(',')if x.strip()]
  rr=copy.deepcopy(oldr)if oldr else {'rank':None,'system':name or r[2],'agent':None,'model_raw':raw,'model_ids':[],'model_config':None,'score':None,'score_extra':{},'date':None,'verified':None,'open_source':None,'org':r[2]or None,'row_url':link.get('href')or None if link else None}
  assert rr['system'];rr.update(rank=i+1,score=r[3],date=r[7]or None);rr['score_extra']={'level1':r[4],'level2':r[5],'level3':r[6]}
  if not name:rr['score_extra']['agent_name_empty_on_board']=True
  if len(rr['model_raw'])>1 and len(rr['model_ids'])==1:rr['model_ids']=[]
  rows.append(rr)
 t['rows']=rows;write(snap(t),{'headers':n['headers'],'data':n['data']});t['notes_ja']=re.sub(r'データセットには全[0-9]+件','データセット全件から上位100件',t['notes_ja']);mark(t,'changed',[t['fetched'][0]],'Official Gradio top-100 display re-extracted; rank/levels/date preserved; unnamed agents use source organisation. New ambiguous or multi-model labels are not assigned a single model.',old)
 # Static JS contains a JSON object / JSON.parse string / data literal. Parse data only.
 t=table('mcp-bench');u=t['fetched'][-1];s=txt(u);n=json.JSONDecoder().raw_decode(s[s.index('=')+1:].lstrip())[0];assert n==json.loads(snap(t).read_text())['data'];mark(t,'unchanged',[u],'Parsed LEADERBOARD_DATA JSON literal is identical.')
 t=table('theagentcompany');u=t['fetched'][-1];s=txt(u);o=json.loads(snap(t).read_text())['data'];found=False
 for match in re.finditer(r'JSON\.parse\(',s):
  tail=s[match.end():]
  if not tail.startswith(('"',"'")):continue
  q=tail[0];end=1
  while end<len(tail):
   if tail[end]=='\\':end+=2;continue
   if tail[end]==q:break
   end+=1
  try:
   value=ast.literal_eval(tail[:end+1])
   if json.loads(value)==o:found=True
  except (ValueError,SyntaxError,json.JSONDecodeError):pass
 assert found;mark(t,'unchanged',[u],'Data-only JSON.parse literal matches saved leaderboard object.')
 t=table('skillsbench');u=t['fetched'][-1];s=txt(u);start=s.index('[{',s.index('leaderboardData'));end=s.index('}]',start)+2;literal=s[start:end];literal=re.sub(r'([\{,])([a-zA-Z][a-zA-Z0-9]*):',r'\1"\2":',literal);n=json.loads(literal);assert n==json.loads(snap(t).read_text())['leaderboardData'];mark(t,'unchanged',[u],'Parsed leaderboardData array matches all 25 configurations and numeric fields.')
 p=pathlib.Path('sources/audit-2026-10-05/tool-general.json');existing=json.loads(p.read_text());existing['tables']+=AUDIT;write(p,existing)

if __name__=='__main__':
 main()
 AUDIT.clear()
 more()
 AUDIT.clear()
 remaining()
