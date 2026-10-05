#!/usr/bin/env python3
"""Mechanically refresh research/security/long-horizon public artifacts.

Use --cache-index PATH for an index of freshly fetched URL/status/path entries.
Cached responses must belong to this run. Failed/unparseable tables stay intact.
No model registry writes: proposals are emitted with unknown open_weights=null.
Dependencies: Python 3, lxml, PyYAML; curl only for acquisition.
"""
import argparse,copy,csv,datetime,hashlib,io,json,pathlib,re,subprocess,urllib.parse
from lxml import html
import yaml
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATE='2026-10-05'
class Literal:
 def __init__(self,s):self.s=s;self.p=0
 def ws(self):
  while self.p<len(self.s) and self.s[self.p].isspace():self.p+=1
 def value(self):
  self.ws();s=self.s;p=self.p;c=s[p]
  if c in '\"\'`':
   q=c;self.p+=1;o=''
   while self.p<len(s):
    c=s[self.p];self.p+=1
    if c==q:return o
    if c=='\\':
     c=s[self.p];self.p+=1
     if c=='u':o+=chr(int(s[self.p:self.p+4],16));self.p+=4
     elif c=='x':o+=chr(int(s[self.p:self.p+2],16));self.p+=2
     else:o+={'n':'\n','r':'\r','t':'\t','b':'\b','f':'\f'}.get(c,c)
    else:o+=c
   raise ValueError('unterminated string')
  if c in '[{':
   self.p+=1;o=[] if c=='[' else {};end=']' if c=='[' else '}'
   self.ws()
   while s[self.p]!=end:
    if c=='{':
     self.ws()
     if s[self.p] in '\"\'`':k=self.value()
     else:
      m=re.match(r'[\w$]+',s[self.p:]);assert m; k=m[0];self.p+=len(k)
     self.ws();assert s[self.p]==':';self.p+=1;o[k]=self.value()
    else:o.append(self.value())
    self.ws()
    if s[self.p]==',':self.p+=1;self.ws()
    else:assert s[self.p]==end,(self.p,s[self.p:self.p+80]);break
   self.p+=1;return o
  for v,x in [('!0',True),('!1',False),('true',True),('false',False),('null',None)]:
   if s.startswith(v,p):self.p+=len(v);return x
  m=re.match(r'-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',s[p:]);assert m,(p,s[p:p+80]);self.p+=len(m[0]);return float(m[0]) if any(t in m[0] for t in '.eE') else int(m[0])
def literal_at(s,needle):return Literal(s[s.index(needle)+len(needle):]).value()
def compact(s):return ' '.join(s.split())
def num(s):
 if s is None or str(s).strip() in ['', '-', 'N/A','N/A%']:return None
 return float(re.sub(r'[$,%]','',str(s).strip()))
def dump(p,d):p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def rank(rows):
 rows.sort(key=lambda r:-(r['score'] if r['score'] is not None else -1e99))
 for i,r in enumerate(rows):r['rank']=i+1
 return rows
MODELS={}
for p in (ROOT/'data/tables').glob('*.json'):
 for r in json.loads(p.read_text())['rows']:
  if len(r['model_raw'])==1 and len(r['model_ids'])==1:MODELS.setdefault(r['model_raw'][0],(r['model_ids'],r['model_config']))
PROPOSALS={}
def model(raw,vendor=None):
 if raw in MODELS:return MODELS[raw][0],None
 ident=re.sub('[^a-z0-9.]+','-',raw.lower()).strip('-')
 PROPOSALS[ident]={'id':ident,'name':raw,'vendor':vendor,'open_weights':None,'weights_url':None,'aliases':[]}
 return [ident],None
BASE=dict(rank=None,system=None,agent=None,model_raw=[],model_ids=[],model_config=None,score=None,score_extra={},date=None,verified=None,open_source=None,org=None,row_url=None)
def base():return copy.deepcopy(BASE)
class Refresh:
 def __init__(self,index):self.idx={x['url']:x for x in index};self.used=[];self.audit=[]
 def get(self,u):
  x=self.idx[u];assert x['status']=='200',(u,x['status']);self.used.append(u);return pathlib.Path(x['path']).read_text()
 def save(self,t,content,path=None):
  p=ROOT/(path or t['snapshot']);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
 def oldmatch(self,t,**kw):
  matches=[r for r in t['rows'] if all(r.get(k)==v for k,v in kw.items())];assert len(matches)==1,(t['id'],kw,len(matches));return copy.deepcopy(matches[0])
 def parse(self,t):
  tid=t['id'];old=copy.deepcopy(t['rows'])
  if tid.startswith('hal-'):
   page=html.fromstring(self.get(t['fetched'][0]));tables=page.xpath('//table[contains(@class,"min-w-full")]');assert len(tables)==1
   rows=[]
   for tr in tables[0].xpath('.//tbody/tr'):
    td=tr.findall('td');a=td[1].xpath('.//a[starts-with(@href,"/agent/")]')[0];system=compact(a.text_content());raw=[compact(z.text_content()) for z in td[2].xpath('.//a')];urls=td[7].xpath('.//a/@href');url=urls[0] if urls else None
    r=self.oldmatch(t,row_url=url) if url else self.oldmatch(t,system=system,model_raw=raw)
    r.update(rank=int(compact(td[0].text_content())),system=system,agent=system,model_raw=raw,score=float(re.search(r'[\d.]+',td[4].text_content())[0]),verified='✓' in td[3].text_content(),row_url=url)
    ex={'cost_usd':float(re.search(r'[\d.,]+',td[5].text_content())[0].replace(',','')),'runs':int(compact(td[6].text_content())),'pareto_optimal':'Pareto optimal' in td[1].text_content()}
    man=re.search(r'([\d.]+)% w/ manual validation',td[4].text_content())
    if man:ex['accuracy_manual_validation']=float(man[1])

    for ix,prefix in [(4,'score'),(5,'cost_usd')]:
     bounds=re.search(r'\(-([\d.,]+)\s*/\+([\d.,]+)\)',td[ix].text_content())
     if bounds:ex[prefix+'_err_minus']=float(bounds[1].replace(',',''));ex[prefix+'_err_plus']=float(bounds[2].replace(',',''))
    r['score_extra']={k:v for k,v in ex.items() if v is not None};rows.append(r)
   self.save(t,html.tostring(tables[0],encoding='unicode')+'\n');return rows
  if tid.startswith('sec-bench-'):
   page=html.fromstring(self.get('https://sec-bench.github.io/'));table_id=html.fromstring((ROOT/t['snapshot']).read_text()).get('id');el=page.xpath('//table[@id="'+table_id+'"]')[0];rows=[]
   for tr in el.xpath('.//tbody/tr'):
    model_raw=compact(tr.xpath(".//*[contains(concat(' ',normalize-space(@class),' '),' model-name-text ')]")[0].text_content());agents=tr.xpath('.//span[@class="model-meta"]');agent=compact(agents[0].text_content()) if agents else None;system=model_raw+(' '+agent if agent else '')
    r=self.oldmatch(t,system=system);r.update(rank=int(tr.get('data-rank')),score=num(tr.get('data-resolved')),date=tr.get('data-date'),org=tr.get('data-org'));ex=r['score_extra'];ex['model_type']=tr.get('data-type')
    if tid.startswith('sec-bench-pro-'):
     for key,attr in [('solved_count','data-headline-count'),('completed','data-headline-completed'),('completed_solved_count','data-completed-count')]:ex[key]=tr.get(attr)
     ex['completed_score_pct']=num(tr.get('data-completed-score'));ex['backend']=tr.get('data-backend')
    else:r['verified']=bool(tr.xpath('.//*[contains(@class,"badge-verified")]'))
    rows.append(r)
   self.save(t,html.tostring(el,encoding='unicode')+'\n');return rows
  if tid.startswith('paperbench'):
   txt=self.get(t['fetched'][0]);section=txt.split('### PaperBench Code-Dev Results')[1] if tid.endswith('code-dev') else txt.split('### PaperBench Results')[1].split('###')[0];rows=[]
   for line in section.splitlines():
    c=[x.strip() for x in line.strip().strip('|').split('|')]
    if len(c)!=4 or not re.match(r'\d',c[1]):continue
    r=self.oldmatch(t,system=c[0]);vals=re.findall(r'[\d.]+',c[1]);r.update(score=float(vals[0]),date=c[3],score_extra={'score_std':float(vals[1]),'runs':int(c[2])});rows.append(r)
   self.save(t,txt);return rank(rows)
  if tid.startswith('mle-bench'):
   txt=self.get(t['fetched'][0]);tabs=[];active=[]
   for line in txt.splitlines()+['']:
    if line.startswith('|'):active.append(line)
    elif active:tabs.append(active);active=[]
   tab=tabs[1 if tid.endswith('additional') else 0];rows=[]
   for line in tab[2:]:
    c=[x.strip() for x in line.strip().strip('|').split('|')];assert len(c) in (10,11)
    system=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',c[0]).replace('**','').strip();system=re.sub(r'[*†]+$','',system).replace('<br>',' ').strip();score=float(re.search(r'\d+(?:\.\d+)?',c[5])[0]);r=self.oldmatch(t,system=system,score=score);r['date']=c[7]
    for ci,key in [(2,'low_lite'),(3,'medium'),(4,'high'),(5,'all')]:
     nums=re.findall(r'\d+(?:\.\d+)?',c[ci]);assert nums
     if key=='all':r['score']=float(nums[0])
     else:r['score_extra'][key+'_pct']=float(nums[0])
     if len(nums)>1:r['score_extra'][key+'_sem']=float(nums[1])
    r['score_extra']['running_time_hours']=float(c[6]);rows.append(r)
   self.save(t,txt);return rank(rows)
  if tid=='cybench':
   txt=self.get(t['fetched'][0]);rows=[]
   keys={'Count':'tasks_evaluated','Subtask-Guided % Solved':'subtask_guided_pct','Subtasks % Solved':'subtasks_pct','Flag Success Count':'flag_success_count','Subtask Challenge Count':'subtask_challenge_count','Subtask-Guided # Solved':'subtask_guided_solved','Sum of Subtask Run Scores':'sum_subtask_run_scores'}
   for a in csv.DictReader(io.StringIO(txt)):
    r=self.oldmatch(t,system=a['Model']);r['score']=float(a['End-to-End % Solved'])
    # Preserve existing column key names after verifying every existing number.
    for k,v in r['score_extra'].items():
     if isinstance(v,(float,int)) and not isinstance(v,bool) and not 'fst_' in k:assert any(num(z)==v for z in a.values() if z and re.fullmatch(r'[\d.,]+',z)),(k,v,a)
    rows.append(r)
   rows.sort(key=lambda r:(-r['score'],-r['score_extra'].get('subtask_guided_pct',0)))
   self.save(t,txt);return rank(rows)
  if tid.startswith('cve-bench'):
   txt=self.get(t['fetched'][1]);data=literal_at(txt,'var f=');rows=[];variation='oneDay' if tid.endswith('one-day') else 'zeroDay'
   for a in data['entries']:
    if a['variation']!=variation:continue
    r=self.oldmatch(t,system=a['label']);r.update(score=a['passAt1'],score_extra={'avg_cost_per_task_usd':a['avgCostPerTask']},date=a['date'],model_config='benchmark '+a['benchmarkVersion'],row_url=a['trajUrl'],org=a['modelOrg']);rows.append(r)
   self.save(t,json.dumps(data,ensure_ascii=False,indent=2)+'\n');return rank(rows)
  if tid.startswith('metr-time-horizon'):
   txt=self.get(t['fetched'][0]);data=yaml.safe_load(txt);olddata=yaml.safe_load((ROOT/t['snapshot']).read_text());assert data==olddata,'METR source changed; inspect display-name and scaffold mapping first'
   rows=[]
   for r0 in old:
    r=copy.deepcopy(r0);matches=[a for a in data['results'].values() if a['metrics']['p50_horizon_length']['estimate']==r['score'] and str(a['release_date'])==r['date']];assert len(matches)==1,(r['system'],len(matches));a=matches[0];m=a['metrics'];r['score']=m['p50_horizon_length']['estimate'];ex=r['score_extra']
    for k,path in {'p50_ci_low':('p50_horizon_length','ci_low'),'p50_ci_high':('p50_horizon_length','ci_high'),'p80_minutes':('p80_horizon_length','estimate'),'p80_ci_low':('p80_horizon_length','ci_low'),'p80_ci_high':('p80_horizon_length','ci_high'),'average_score':('average_score','estimate')}.items():
     if path[0] in m and path[1] in m[path[0]]:ex[k]=m[path[0]][path[1]]
    rows.append(r)
   self.save(t,txt);return rank(rows)
  if tid=='mind2web-2':
   txt=self.get(t['fetched'][0]);data=json.loads(txt);rows=[]
   for a in data['leaderboardData']:
    info=a['info']
    if info['name']=='Human':continue
    r=self.oldmatch(t,system=info['name']);ev=a['eval_set'];r['score']=num(ev['success_rate']);ex={'type':info['type']}
    for src,k in [('partial_completion','partial_completion'),('pass3','pass3'),('time','time_min'),('answer_length','answer_length')]:
     v=None if str(ev.get(src)).startswith('<') else num(ev.get(src))
     if str(ev.get(src)).startswith('<'):ex[k+'_text']=ev[src]
     if v is not None:ex[k]=v
    r.update(score_extra=ex,date=info['date']);rows.append(r)
   self.save(t,txt);return rank(rows)
  if tid=='cybergym-e2e':
   txt=self.get(t['fetched'][0]);data=json.loads(txt);rows=[]
   for a in data['results']:
    r=copy.deepcopy(next(r for r in old if r['model_raw']==[a['model']] and r['agent']==a['harness'] and r['score_extra']['task_set']==a['task_set'] and r['model_config']=='Budget: '+a['budget']));r['score']=a['s3'];r['score_extra']={k:a[v] for k,v in [('patch_only_pct','patch_only'),('s1_pct','s1'),('s2_pct','s2'),('s4_pct','s4'),('task_set','task_set')] if a[v] is not None};rows.append(r)
   self.save(t,txt);return rank(rows)
  if tid=='exploitgym':
   txt=self.get(t['fetched'][0]);data=json.loads(txt);olddata=json.loads((ROOT/t['snapshot']).read_text());assert data==olddata,'ExploitGym source changed; inspect nested versions first'
   numbers=[]
   def walk(v):
    if isinstance(v,dict):
     if v.get('hidden'):return
     if 'on_target' in v:numbers.append(v['on_target'])
     for z in v.values():walk(z)
    elif isinstance(v,list):
     for z in v:walk(z)
   walk(data);assert len(numbers)==len(old),(len(numbers),len(old));assert sorted(numbers)==sorted(r['score'] for r in old)
   self.save(t,txt);return old
  if tid=='browsecomp-plus':
   txt=self.get(t['fetched'][0]);data=json.loads(txt);csvtxt=self.get(t['fetched'][1]);rawcsv=list(csv.DictReader(io.StringIO(csvtxt)));rows=[]
   for a in data:
    system=a['LLM']+' + '+a['Retriever']
    rowdate=datetime.datetime.strptime(a['Evaluation Date'].replace('April','Apr').replace('June','Jun').replace('July','Jul').replace('Sept','Sep'),'%b %d, %Y').date().isoformat()
    # The same model/retriever can have several dates and scaffolds, while
    # scaffold descriptions can expand without changing the underlying run.
    matches=[r for r in old if r['system']==system and r['model_raw']==[a['LLM']] and r['date']==rowdate and r['score']==num(a['Accuracy (%)'])]
    r=copy.deepcopy(matches[0]) if len(matches)==1 else base()
    if len(matches)!=1:
     candidates=matches or [z for z in old if z['model_raw']==[a['LLM']]]
     ids={tuple(z['model_ids']) for z in candidates}
     configs={z['model_config'] for z in candidates}
     if candidates:
      assert len(ids)==1,'Ambiguous prior model normalization: '+a['LLM']
      r['model_ids']=list(next(iter(ids)))
      if len(configs)==1:r['model_config']=next(iter(configs))
     else:r['model_ids'],r['model_config']=model(a['LLM'])
    r.update(system=system,agent=a['Scaffold'] or 'Standard',model_raw=[a['LLM']],score=num(a['Accuracy (%)']),date=datetime.datetime.strptime(a['Evaluation Date'].replace('April','Apr').replace('June','Jun').replace('July','Jul').replace('Sept','Sep'),'%b %d, %Y').date().isoformat(),open_source=a['Open Weights?']=='Yes',org=a['Submitted By'],row_url=a['Submittor Link'] or a.get('LLM Link') or None)
    ex={'retriever':a['Retriever']}
    for src,k in [('Recall (%)','recall'),('Search Calls','search_calls'),('Calibration Error (%)','calibration_error'),('Model Size (B)','model_size_b'),('Accuracy (GPT-4.1 Judge)','accuracy_gpt41_judge')]:
     v=num(a.get(src))
     if v is not None:ex[k]=v
    # Dashboard replaces missing calibration error with 0; CSV is authoritative for missingness.
    cr=[z for z in rawcsv if z['LLM']==a['LLM'] and z['Retriever']==a['Retriever'] and z.get('Scaffold','')==a['Scaffold']]
    if len(cr)==1 and cr[0].get('Calibration Error (%)') in ('','-'):ex.pop('calibration_error',None)
    r['score_extra']=ex;rows.append(r)
   self.save(t,txt);self.save(t,csvtxt,'sources/browsecomp-plus/agent_results.csv');return rank(rows)
  if tid.startswith('cybergym-'):
   txt=self.get(t['fetched'][0]);data=json.loads(txt);focus='agent' if 'agent-focused' in tid else 'model';rows=[]
   def one(a,sub=False):
    agent=a['agent'].replace('\\(','(').replace('\\)',')');system=agent if focus=='agent' else a['model'];score=round(a['score_10']*100,4)
    matches=[r for r in old if r['agent']==agent and r['score']==score and r['date']==a.get('date')]
    if not matches and agent.startswith('VARAS-OneMind'):matches=[r for r in old if r['agent']=='VARAS-OneMind' and r['score']==score]
    r=copy.deepcopy(matches[0]) if len(matches)==1 else base()
    if not matches:
     raw=a['model'];cfg=None
     if raw.startswith('Multi-model ('):
      rawlist=raw[len('Multi-model ('):-1].split(', ');ids=[]
      for raw in rawlist:ids.extend(model(raw)[0])
      cfg='Multi-model'
     else:
      rawlist=[raw];ids,cfg=model(raw.split(' (finetuned from ')[0],a.get('source'))
      if ' (finetuned from ' in raw:cfg=raw.split(' (',1)[1].rstrip(')')
     r.update(model_raw=rawlist,model_ids=ids,model_config=cfg)

    if a['model'].startswith('XekRung-1.5-27B-Preview'):
     r['model_ids']=['xekrung-1.5-27b'];r['model_config']='preview; finetuned from Qwen3.8-27B'
    r.update(system=r['system'] if matches and focus=='model' else system,agent=agent,score=score,date=a.get('date'),org=a.get('source'),row_url=a.get('source_url'));ex={'trials':a['trials']}
    if a.get('score_x1') is not None:ex['score_x1_pct']=round(a['score_x1']*100,4)
    features=' '.join(a.get('features',[]))
    if 'dynamic' in features:ex['dynamic']=True
    if 'test-time mem.' in features:ex['test_time_memory']=True
    if focus=='agent' and score>90 and not sub:ex['lead_card_unranked']=True
    r['score_extra']=ex;r['rank']=None if sub or ex.get('lead_card_unranked') else 0;rows.append(r)
   parents=sorted([a for a in data['level1'] if a.get('focus')==focus and a.get('trials')==1],key=lambda a:-a['score_10'])
   nr=0
   for a in parents:
    one(a)
    if rows[-1]['rank'] is not None:nr+=1;rows[-1]['rank']=nr
    for sub in a.get('subRows',[]):one({**a,**sub,'subRows':[]},True)
   self.save(t,txt);return rows
  if tid=='ecommerce-bench':
   txt=self.get(t['fetched'][1]);data=json.loads(txt);rows=[]
   fields=['id','name','tier','family','hero','partial','partial_day','final_balance','final_balance_summary','bankrupt_count','terms','avg_rounds_to_deal','finance']
   trimmed={'source':t['fetched'][1]+' (models trimmed to leaderboard fields; curves/traces dropped)','data':{'bench':data['bench'],'num_days':data['num_days'],'models':[{k:a[k] for k in fields if k in a} for a in data['models']]}}
   for a in data['models']:
    r=self.oldmatch(t,system=a['name']);r['score']=a['final_balance'];r['score_extra'].update(final_balance_std=a['final_balance_summary']['std'],num_runs=a['final_balance_summary']['n'],bankrupt_runs=a['bankrupt_count'],cse_plus=a['terms']['CSE+'],pct_oracle=a['terms']['%Oracle']);rows.append(r)
   self.save(t,json.dumps(trimmed,ensure_ascii=False,indent=1)+'\n');return rank(rows)
  if tid=='vending-bench':
   page=self.get(t['source']);url=urllib.parse.urljoin(t['source'],re.findall(r'[^"\']*immutable/nodes/26\.[^"\']+\.js',page)[0]);txt=self.get(url);tsv=literal_at(txt,'const ct=');rows=[]
   for line in tsv.strip().splitlines():
    c=line.split('\t');r=self.oldmatch(t,system=c[0]);r['score']=num(c[2]);r['score_extra'].update({k:num(c[i]) for i,k in [(1,'net_worth_mean'),(3,'units_sold_mean'),(4,'units_sold_min'),(5,'days_until_sales_stop_mean'),(6,'days_until_sales_stop_pct')]});rows.append(r)
   t['fetched']=[t['source'],url];self.save(t,'# source: '+url+' (template literal ct)\n'+tsv+'\n');return rank(rows)
  if tid=='vending-bench-2':
   page=self.get(t['source']);url=urllib.parse.urljoin(t['source'],re.findall(r'[^"\']*immutable/nodes/27\.[^"\']+\.js',page)[0]);txt=self.get(url)
   runurl='https://andonlabs.com/_app/immutable/chunks/DVaUlUWR.js';datesurl='https://andonlabs.com/_app/immutable/chunks/D6mQEJpA.js'
   runs=literal_at(self.get(runurl),'vb2:');dates=literal_at(self.get(datesurl),'const ue=');costs=literal_at(txt,',ut=');rows=[]
   for name,a in runs.items():
    matches=[r for r in old if r['system']==name];r=copy.deepcopy(matches[0]) if len(matches)==1 else base()
    if not matches:r['model_ids'],r['model_config']=model(name,costs.get(name,{}).get('provider'))
    r.update(system=name,model_raw=[name],score=a['final_value'],date=dates.get(name),org=costs.get(name,{}).get('provider'));ex={'std_error':a['final_value_sem'],'num_runs':a['num_final_values'],'geomean_money_balance':a['final_value_geomean'],'geomean_num_runs':a['final_value_geomean_n']}
    if name in costs:ex['mean_cost_usd']=costs[name]['mean_cost']
    r['score_extra']={k:v for k,v in ex.items() if v is not None};rows.append(r)
   trimmed={name:{**{k:v for k,v in a.items() if k!='time_series'},'time_series_len':len(a['time_series'])} for name,a in runs.items()}
   snapshot={'source':{'runs':runurl+' (vb2; time_series removed)','release_dates':datesurl,'costs':url},'runs_vb2':trimmed,'release_dates':dates,'costs':costs}
   t['fetched']=[t['source'],url,runurl,datesurl];self.save(t,json.dumps(snapshot,ensure_ascii=False,indent=1)+'\n');t['notes_ja']=re.sub(r'New バッジは[^。]+。','',t['notes_ja']);t['notes_ja']=re.sub(r'\(Grok 4.6 など4件は日付なし\)',f'(日付が公表されていない{sum(r["date"] is None for r in rows)}件は null)',t['notes_ja']);return rank(rows)
  if tid.startswith('swe-marathon-'):
   page=self.get(t['source']);url=urllib.parse.urljoin(t['source'],re.findall(r'src="([^"]+\.js)"',page)[0]);txt=self.get(url);t['fetched']=[t['source'],url];rows=[]
   if tid.endswith('v1-0'):
    data=literal_at(txt,',ze=')
    for a in data:
     if a.get('ref'):continue
     r=self.oldmatch(t,model_raw=[a['name']],score=a['pass1'],rank=a['rank']);r.update(rank=a['rank'],score=a['pass1']);ex={'trials':a['nLoggedTrials'],'cost_trials':a['nCostTrials']}
     for k,v in [('partial_avg_pct','partialAvg'),('cost_avg_usd','costAvg'),('tokens_avg_m','tokAvg')]:
      if a[v] is not None:ex[k]=a[v]
     r['score_extra']={**r['score_extra'],**ex};rows.append(r)
    self.save(t,json.dumps({'source':url+' (v1.0 archive literal)','rows':data},ensure_ascii=False,separators=(',',':'))+'\n');return rows
   tasks=json.loads(literal_at(txt,'tasks:JSON.parse('));oldsource=json.loads((ROOT/t['snapshot']).read_text());taskids=oldsource['task_ids'];assert set(tasks)==set(taskids),'Task population changed'
   # Exact site display filter rt, dated bundle above. Never pool reasoning configurations.
   expected='return t||n||r||i||a?$e(e)===`max`:o?$e(e)===`xhigh`:!0';assert expected in txt,'Site display filter changed'
   def eligible(c):
    a,m=c['agent'],c['model'];eff=c.get('reasoningEffort') or 'max'
    maxonly=(a=='Codex' and re.fullmatch(r'GPT-5\.6-(?:sol|terra|luna)',m)) or (a=='Claude Code' and m in ['Claude Opus 5','Claude Opus 5.5','Claude Sonnet 5','GLM 5.3','GLM 5.3 Flash','Claude Fable 5.1']) or (a=='Codex' and m=='GPT-6 Astra')
    return eff=='max' if maxonly else eff=='xhigh' if a=='Muse Code' and m=='Muse Spark 1.3' else True
   grouped={};trim={}
   for task in taskids:
    trim[task]={'configs':[]}
    for c in tasks[task]['configs']:
     if not eligible(c):continue
     eff=c.get('reasoningEffort') or 'max';key=(c['agent'],c['model'],eff);g=grouped.setdefault(key,{'c':c,'trials':[]});g['trials']+=c['trials']
     trim[task]['configs'].append({**{k:c[k] for k in ['agent','model','reasoningEffort','displayLabel','n','binary'] if k in c},'trials':[{k:z[k] for k in ['id','reward','partial','costUsd','tokensRaw','startedAt'] if k in z} for z in c['trials']]})
   computed=[]
   for (agent,name,eff),g in grouped.items():
    trials=g['trials'];c=g['c'];score=100*sum(z['reward']>=1 for z in trials)/len(trials);partial=100*sum(z['partial'] for z in trials)/len(trials);cost=[z['costUsd'] for z in trials if z.get('costUsd') is not None];tok=[z['tokensRaw'] for z in trials if z.get('tokensRaw',0)>0]
    matches=[r for r in old if r['model_raw']==[name] and r['agent']==agent and ('reasoning_effort='+eff) in (r['model_config'] or '')];r=copy.deepcopy(matches[0]) if len(matches)==1 else base()
    if not matches:r['model_ids'],_=model(name)
    r.update(system=(c.get('displayLabel') or name+' ('+eff+')')+' / '+agent,agent=agent,model_raw=[name],model_config='reasoning_effort='+eff,score=score)
    ex={'partial_avg_pct':partial,'trials':len(trials),'cost_trials':len(cost)}
    if cost:ex['cost_avg_usd']=sum(cost)/len(cost)
    if tok:ex['tokens_avg_m']=sum(tok)/len(tok)/1e6
    if name=='Claude Fable 5':
     r['model_config']+='; Run with a fallback model.'
     # The source explicitly mixes an undisclosed fallback into this run.
     # Do not attribute its aggregate to one model or include it in the fit.
     r['model_ids']=[]

    # Avoid meaningless floating-point summation-order diffs for unchanged runs.
    if matches:
     for k,v in ex.items():
      prior=matches[0]['score_extra'].get(k)
      if isinstance(v,(int,float)) and isinstance(prior,(int,float)) and abs(v-prior)<1e-10:ex[k]=prior
    r['score_extra']=ex;rows.append(r);computed.append({'name':name,'scaffold':agent,'reasoningEffort':eff,'pass1':score,'partialAvg':partial,'nLoggedTrials':len(trials),'nCostTrials':len(cost),'lastStart':max(z['startedAt'] for z in trials)})
   rows.sort(key=lambda r:(-r['score'],-r['score_extra']['partial_avg_pct']))
   for i,r in enumerate(rows):r['rank']=i+1
   self.save(t,json.dumps({'source':url+' (embedded task data; site display filter and aggregate formulas)','task_ids':taskids,'tasks':trim,'computed_leaderboard':computed},ensure_ascii=False,separators=(',',':'))+'\n');last=max(a['lastStart'] for a in computed)[:10];t['notes_ja']=re.sub(r'試行開始時刻の最新は [0-9-]+', '試行開始時刻の最新は '+last,t['notes_ja']);return rows
  raise ValueError('No parser for '+tid)
 def run(self,ids=None):
  for p in sorted((ROOT/'data/tables').glob('*.json')):
   t=json.loads(p.read_text());tid=t['id']
   if t['category'] not in ['research','security','long-horizon'] or (ids and tid not in ids):continue
   t=json.loads(subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT));old=copy.deepcopy(t);self.used=[]
   try:
    rows=self.parse(t);assert rows,(tid,'empty result');t['rows']=rows;t['retrieved']=DATE;t['newest_row_date']=max([r['date'] for r in rows if r['date']],default=None)
    a={json.dumps(r,sort_keys=True,ensure_ascii=False) for r in old['rows']};b={json.dumps(r,sort_keys=True,ensure_ascii=False) for r in rows}
    changed=old['rows']!=rows
    if not changed:
     try:(ROOT/t['snapshot']).write_bytes(subprocess.check_output(['git','show','HEAD:'+t['snapshot']],cwd=ROOT))
     except subprocess.CalledProcessError:pass
    dump(pathlib.Path('data/tables')/p.name,t)
    out={'id':tid,'status':'refreshed_changed' if changed else 'refreshed_unchanged','rows_before':len(old['rows']),'rows_after':len(rows),'rows_changed_or_added':len(b-a),'rows_removed_or_changed':len(a-b),'sources':[self.idx[u] for u in dict.fromkeys(self.used)]}
   except Exception as e:out={'id':tid,'status':'preserved','rows_before':len(old['rows']),'reason':str(e),'sources':[self.idx[u] for u in dict.fromkeys(self.used)]}
   self.audit.append(out);print(tid,out['status'],out.get('rows_after'),out.get('reason',''))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--cache-index',required=True);ap.add_argument('--only',nargs='*');ap.add_argument('--audit',default='/tmp/abm-research-audit.json');args=ap.parse_args();rf=Refresh(json.loads(pathlib.Path(args.cache_index).read_text()));rf.run(args.only);pathlib.Path(args.audit).write_text(json.dumps({'retrieved':DATE,'tables':rf.audit},ensure_ascii=False,indent=2)+'\n');pathlib.Path('/tmp/abm-research-models.json').write_text(json.dumps(list(PROPOSALS.values()),ensure_ascii=False,indent=2)+'\n')
