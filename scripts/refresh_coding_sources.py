#!/usr/bin/env python3
"""Conservative coding-board refresh with source-level comparison and provenance.

Python 3 + lxml + PyYAML. Run from the repository root:
  python scripts/refresh_coding_sources.py --date YYYY-MM-DD --cache /tmp/coding-fetch

Fetches each primary artifact once, extracts complete comparable table data, and
keeps a table unchanged on any unsupported source/schema change. Existing model
normalization is reused, never guessed. Unknown models are reported for review.
The optional --offline flag replays a prior cache with index.json. Raw-response
hashes and per-table extracted snapshot hashes are persisted in provenance.json.
"""
import argparse, collections, concurrent.futures, copy, csv, datetime, hashlib
import io, json, pathlib, re, urllib.request
import yaml
from lxml import html

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load(path):
    return json.loads(path.read_text())

def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def rsc(raw):
    chunks = []
    for script in html.fromstring(raw).xpath('//script/text()'):
        m = re.search(r'self\.__next_f\.push\((\[.*\])\)', script, re.S)
        if m:
            a = json.loads(m.group(1))
            if len(a) > 1 and isinstance(a[1], str):
                chunks.append(a[1])
    assert chunks, 'No Next.js payload'
    return ''.join(chunks)

def field(text, key):
    start = text.index('"' + key + '":') + len(key) + 3
    return json.JSONDecoder().raw_decode(text[start:])[0]

def id_counts(value):
    if isinstance(value, dict):
        out = {k: (len(v) if k.endswith('_ids') and isinstance(v, list) else id_counts(v)) for k,v in value.items()}
        if any(k.endswith('_ids') for k in value):
            out['_note'] = 'id lists replaced by their lengths'
        return out
    return [id_counts(v) for v in value] if isinstance(value, list) else value

def live_counts(row):
    row = copy.deepcopy(row)
    for k,v in row.items():
        if isinstance(v, list):
            row[k] = {'_note': 'list of resolved instance ids replaced by its length' if k == 'resolved' else 'list replaced by its length', 'length': len(v)}
    return row

def comparable(value):
    if isinstance(value, dict):
        return {k:comparable(v) for k,v in value.items() if not k.startswith('_') and k not in ('source','note')}
    return [comparable(v) for v in value] if isinstance(value,list) else value

def source_jobs(tables):
    jobs = {}
    for t in tables:
        urls = t['fetched']
        if t['id'] == 'liveswebench':
            urls = [u for u in urls if u.endswith('.csv')]
        elif t['id'].startswith('deepswe-'):
            urls = [urls[0], 'https://deepswe.datacurve.ai/']
        elif t['id'].startswith('swe-bench-live-'):
            urls = urls[:2]
        else:
            urls = urls[:1]
        for u in urls:
            jobs.setdefault(u, []).append(t['id'])
    return jobs

def fetch(jobs, cache, date):
    cache.mkdir(parents=True,exist_ok=True)
    def one(item):
        description, ids = item
        url, data = description, None
        if ' (POST ' in url:
            url, body = url.split(' (POST ',1)
            data = body.removesuffix(')').encode()
        filename = sha(description.encode())[:16]
        out = {'url':url,'request_description':description,'tables':ids,'file':filename,'retrieved':date}
        try:
            req = urllib.request.Request(url,data=data,headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=90) as response:
                b = response.read()
                out.update(status=response.status,final_url=response.url,bytes=len(b),sha256=sha(b))
            (cache/filename).write_bytes(b)
        except Exception as exc:
            out['error'] = str(exc)
        return out
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        index = list(pool.map(one,jobs.items()))
    home=next((x for x in index if x['url']=='https://deepswe.datacurve.ai/' and x.get('status')==200),None)
    if home:
        tree=html.fromstring((cache/home['file']).read_text())
        modules=tree.xpath('//link[@rel="modulepreload"]/@href')
        assert modules, 'DeepSWE module preload missing'
        bundle=one(('https://deepswe.datacurve.ai'+modules[0],home['tables']))
        bundle['purpose']='frontend_pricing'
        index.append(bundle)
    dump(cache/'index.json',index)
    return index

class Refresh:
    def __init__(self, cache, date, tables, index):
        self.cache,self.date,self.tables = cache,date,tables
        self.sources = collections.defaultdict(list)
        for entry in index:
            for id in entry['tables']:
                self.sources[id].append(entry)
        self.byraw = collections.defaultdict(set)
        models = load(ROOT/'data/models.json')['models']
        self.registry = {m['id']:m for m in models}
        for t in tables:
            for r in t['rows']:
                if len(r['model_ids']) == 1:
                    for raw in r['model_raw']:
                        self.byraw[raw.lower()].add(r['model_ids'][0])
        for m in models:
            for raw in [m['id'],m['name'],*m.get('aliases',[])]:
                self.byraw[raw.lower()].add(m['id'])
        self.proposals = []

    def text(self,id,n=0):
        entry = self.sources[id][n]
        assert entry.get('status') == 200, entry.get('error','Fetch failed')
        raw = (self.cache/entry['file']).read_bytes()
        assert sha(raw) == entry['sha256'], 'Cached response hash mismatch'
        return raw.decode()

    def model_ids(self,raw):
        candidates = self.byraw.get(raw.lower(),set())
        assert len(candidates) == 1, f'Unresolved/ambiguous model: {raw}; {candidates}'
        return list(candidates)

    def project(self,t,old):
        id=t['id']; raw=self.text(id)
        if id.startswith('swe-bench-live-'):
            new=copy.deepcopy(old); subset=old['reports'][0]['set']
            new['reports']=[live_counts(json.loads(l)) for l in raw.splitlines() if l.strip() and json.loads(l)['set']==subset]
        elif id in {'swe-bench-full','swe-bench-lite','swe-bench-verified','swe-bench-bash-only','swe-bench-multilingual','swe-bench-multimodal'}:
            new=copy.deepcopy(old)
            board=next(b for b in json.loads(raw)['leaderboards'] if b['name']==old['leaderboard']['name'])
            if id=='swe-bench-bash-only':
                board['results']=[r for r in board['results'] if r.get('agent')=='mini-SWE-agent']
            for r in board['results']:
                r.pop('per_instance_details',None)
            new['leaderboard']=board
        elif id.startswith('multi-swe-bench'):
            new=copy.deepcopy(old); groups=id_counts(json.loads(raw))
            if 'group' in old:
                new['group']=next(g for g in groups if g['name']==old['group']['name'])
            else:
                new['groups']=groups
        elif id.startswith('swe-polybench'):
            new=copy.deepcopy(old)
            new['leaderboard']=next(b for b in json.loads(raw)['leaderboards'] if b['name']==old['leaderboard']['name'])
        elif id.startswith('aider-'):
            return raw, yaml.safe_load(raw)==yaml.safe_load(old)
        elif id.startswith('deepswe-') or id in {'gso','gso-opt10','cad-bench-v2'}:
            new=json.loads(raw)
        elif id.startswith('swe-bench-pro-'):
            new=copy.deepcopy(old)
            variants=field(rsc(raw),'variants')
            key=id.rsplit('-',1)[1]
            variant=next(v for v in variants if v['key']==key)
            assert ('Public' if key=='public' else 'Private') in variant['label']
            new['entries']=variant['entries']
            new['_source']=self.sources[id][0]['final_url']
            new['_note']='Entries extracted from the matching public/private variant in the unified Next.js RSC payload; variants remain separate tables.'
        elif id=='swe-rebench':
            new=copy.deepcopy(old); text=rsc(raw); dates=field(text,'dates')
            assert dates==old['dates'], 'Default benchmark time window changed; manual scope review required'
            items=field(text,'items'); key=old['window']['key']
            for r in items:
                r['rangeStats']={lang:{key:stats[key]} for lang,stats in r['rangeStats'].items() if key in stats}
            new['items']=items;new['dates']=dates
            new['problems_in_window']=[p for p in field(text,'problems') if old['window']['start']<=p['timestamp']<=old['window']['end']]
        elif id=='slopcodebench':
            new=copy.deepcopy(old);new['data']=field(rsc(raw),'data')
        elif id=='codeclash':
            new=json.JSONDecoder().raw_decode(raw.split('var fullLeaderboardData = ',1)[1])[0]
        elif id=='liveswebench':
            new=copy.deepcopy(old)
            for n,entry in enumerate(self.sources[id]):
                key=entry['url'].rsplit('/',1)[1].replace('.csv','_csv')
                new[key]=self.text(id,n)
        elif id=='swe-lancer-diamond':
            return raw,list(csv.DictReader(io.StringIO(raw)))==list(csv.DictReader(io.StringIO(old)))
        elif id.startswith('hal-') or id=='algotune' or id.startswith('commit0-'):
            # Exact HTML subtree extraction prevents overlooking appended rows.
            tree=html.fromstring(raw)
            if id.startswith('hal-'):
                selected=tree.xpath('//table'); assert len(selected)==1
                selected=selected[0]
            elif id=='algotune':
                selected=tree.xpath('//table[@id="model-summary-table"]')[0]
            else:
                heading=tree.xpath('//h2[@id="leaderboard-'+id.split('-')[1]+'"]')[0]
                selected=heading.xpath('following-sibling::table[1]')[0]
            old_tree=html.fromstring(old)
            old_table=(old_tree.xpath('.//h2[@id="leaderboard-'+id.split('-')[1]+'"]/following-sibling::table[1]')[0] if id.startswith('commit0-') else old_tree if old_tree.tag=='table' else old_tree.xpath('.//table')[0])
            def canon(el):return html.tostring(el,encoding='unicode',with_tail=False).strip()
            assert canon(selected)==canon(old_table), 'HTML table changed; review extraction before refresh'
            # Preserve source formatting when the complete extracted table matches.
            return old, True
        else:
            raise AssertionError('No projection handler')
        same=comparable(new)==comparable(old)
        if isinstance(new,dict) and '_retrieved' in new:
            new['_retrieved']=self.date
        return new,same

    def changed_rows(self,t,new):
        id=t['id']; oldrows=t['rows']; out=[]
        if id.startswith('swe-bench-live-'):
            bykey={(r['system'],r['date']):r for r in oldrows}
            for source in new['reports']:
                row=copy.deepcopy(bykey.get((source['name'],source['date'])))
                if row is None:
                    parts=source['name'].rsplit(' + ',1); assert len(parts)==2
                    agent,raw=parts
                    row={'rank':None,'system':source['name'],'agent':agent,'model_raw':[raw],'model_ids':self.model_ids(raw),'model_config':None,'score':None,'score_extra':{},'date':source['date'],'verified':source.get('verified'),'open_source':None,'org':None,'row_url':source.get('url')}
                count=source['resolved']; count=count['length'] if isinstance(count,dict) else count
                row['score']=round(count/source['total']*100,1)
                row['score_extra'].update(resolved_count=count,num_valid_inst=source['total'])
                out.append(row)
        elif id in {'gso','gso-opt10'}:
            setting='Opt@1' if id=='gso' else 'Opt@10'
            for source in new['models']:
                if source['setting']!=setting:continue
                key=(source['name'],source['scaffold'],source.get('reasoning_effort'),source['date'])
                row=next((copy.deepcopy(r) for r in oldrows if r['model_raw']==[key[0]] and r['agent']==key[1] and r['date']==key[3] and (('reasoning_effort='+key[2])==r['model_config'] if key[2] else not (r['model_config'] or '').startswith('reasoning_effort='))),None)
                if row is None:
                    row={'rank':None,'system':source['name']+(f" ({source['reasoning_effort']})" if source.get('reasoning_effort') else '')+' / '+source['scaffold'],'agent':source['scaffold'],'model_raw':[source['name']],'model_ids':self.model_ids(source['name']),'model_config':'reasoning_effort='+source['reasoning_effort'] if source.get('reasoning_effort') else None,'score':None,'score_extra':{},'date':source['date'],'verified':None,'open_source':None,'org':source.get('submission_org_name'),'row_url':None}
                row['score']=source['score'];row['score_extra']['score_hack_control']=source['score_hack_control'];out.append(row)
        elif id.startswith('deepswe-'):
            # Existing display-name mapping and provider-specific price rescaling
            # come from the site bundle. Preserve those rows when raw data did not
            # change; update only the directly published price corrections.
            previous=load(ROOT/t['snapshot'])['rows']
            assert len(previous)==len(new['rows']), 'DeepSWE row count changed; review display transforms'
            out=copy.deepcopy(oldrows)
            for before,source in zip(previous,new['rows']):
                assert before['config']==source['config'], 'DeepSWE configurations reordered'
                changed={k for k in set(before)|set(source) if before.get(k)!=source.get(k)}
                if not changed:continue
                assert changed <= {'mean_cost_usd','median_cost_usd','cost_basis'}, 'DeepSWE non-price data changed; review transforms'
                row=next(r for r in out if r['model_raw']==[source['model']] and r['agent']==source['harness'] and r['model_config']==('reasoning_effort='+source['reasoning_effort'] if source.get('reasoning_effort') else None))
                for key in ('mean_cost_usd','median_cost_usd','cost_basis'):
                    if key in source:row['score_extra'][key]=source[key]
        else:
            raise AssertionError('Comparable source data changed without an approved row extractor')
        if id.startswith('deepswe-'):return out
        out.sort(key=lambda r:r['score'] if r['score'] is not None else -1,reverse=True)
        for n,row in enumerate(out,1):row['rank']=n
        return out

    def verify_deepswe_prices(self,t,new):
        # Parse only the literal price table. Never execute fetched JavaScript.
        id=t['id'];entry=next(e for e in self.sources[id] if e.get('purpose')=='frontend_pricing')
        bundle=(self.cache/entry['file']).read_text()
        assert sha(bundle.encode())==entry['sha256']
        match=re.search(r'([A-Za-z0-9_$]+)=(\{"glm-5-3-flash":.*?\}),[A-Za-z0-9_$]+=/\(\^\|_\)cost_usd',bundle)
        assert match, 'DeepSWE price schema changed'
        literal=re.sub(r'([{,])([A-Za-z_][A-Za-z0-9_]*):',r'\1"\2":',match.group(2))
        prices=json.loads(re.sub(r':\.(\d)',r':0.\1',literal))
        assert '(t.input-t.cached)*e.input+t.cached*e.cached+t.output*e.output' in bundle, 'Price formula changed'
        norm=lambda text:re.sub(r'[._]','-',text.rsplit('/',1)[-1]).lower().removesuffix('-preview')
        version='v1.1' if id=='deepswe-v1-1' else 'v1'
        def effort(row):
            m=re.search(r'(?:^|; )reasoning_effort=([^;]+)',row['model_config'] or '')
            return m.group(1) if m else None
        for source in new['rows']:
            rows=[r for r in t['rows'] if len(r['model_raw'])==1 and norm(r['model_raw'][0])==norm(source['model']) and r['agent']==source['harness'] and effort(r)==source.get('reasoning_effort')]
            assert len(rows)==1, 'DeepSWE model/config mismatch: '+source['config']
            row=rows[0];factor=1.0;rate=prices.get(norm(source['model']))
            if rate and 'from' not in rate:rate=rate.get(version)
            if rate:
                for ik,ck,ok in [('n_input_tokens','n_cache_tokens','n_output_tokens'),('mean_input_tokens','mean_cache_tokens','mean_output_tokens'),('total_prompt_tokens','total_cached_tokens','total_completion_tokens'),('prompt_tokens','cached_tokens','completion_tokens')]:
                    if isinstance(source.get(ik),(int,float)) and isinstance(source.get(ok),(int,float)):
                        i,c,o=source[ik],source.get(ck) or 0,source[ok]
                        cost=lambda p:(i-c)*p['input']+c*p['cached']+o*p['output']
                        if cost(rate['from'])>0:factor=cost(rate['to'])/cost(rate['from'])
                        break
                else:
                    ratios=[rate['to'][k]/rate['from'][k] for k in ('input','cached','output')]
                    if max(ratios)-min(ratios)<1e-9:factor=ratios[0]
            assert abs(row['score']-source['pass_at_1']*100)<1e-10
            for key in ('mean_cost_usd','median_cost_usd'):
                if source.get(key) is not None:
                    value=source[key]*factor
                    # Avoid changing representation for equivalent floating point results.
                    if abs(row['score_extra'][key]-value)>1e-10:row['score_extra'][key]=value
            config=['reasoning_effort='+source['reasoning_effort']] if source.get('reasoning_effort') else []
            if abs(factor-1)>1e-12:config.append('cost rescaled by site x'+format(factor,'.6f').rstrip('0').rstrip('.')+' (raw mean_cost_usd='+str(source['mean_cost_usd'])+')')
            assert ((row['model_config'] or '').replace('hidden in default view','').strip('; ') or None)==('; '.join(config) or None), 'DeepSWE cost transform changed: '+source['model']+'; old='+str(row['model_config'])+'; new='+str('; '.join(config) or None)
        start=match.start();end=bundle.index('function P9(',match.end())
        (ROOT/t['snapshot']).parent.joinpath('frontend-pricing.js').write_text(bundle[start:end]+'\n')
        t['fetched']=[self.sources[id][0]['url'],'https://deepswe.datacurve.ai/',entry['url']]

    def run_one(self,t):
        id=t['id']; original=copy.deepcopy(t);path=ROOT/t['snapshot'];oldtext=path.read_bytes().decode()
        try:old=json.loads(oldtext)
        except json.JSONDecodeError:old=oldtext
        new,same=self.project(t,old)
        if not same:t['rows']=self.changed_rows(t,new)
        # Direct score validation for sources that publish unambiguous native rows.
        if id in {'swe-bench-full','swe-bench-lite','swe-bench-verified','swe-bench-bash-only','swe-bench-multilingual','swe-bench-multimodal'}:
            assert len(new['leaderboard']['results'])==len(t['rows'])
            for row in t['rows']:
                source=next(r for r in new['leaderboard']['results'] if r['name']==row['system'] and r['date']==row['date'] and r['resolved']==row['score'])
                assert row['score']==source['resolved']
                # No verification marker is unknown, not an explicit false.
                marker=source.get('checked')
                if marker is None or isinstance(marker,bool):row['verified']=marker
                elif isinstance(marker,str) and marker.lower().startswith('false'):
                    row['verified']=False
                    row['score_extra']['verification_note']=marker
                elif isinstance(marker,str) and marker.startswith(('https://','http://')):
                    row['verified']=True
                    row['score_extra']['verification_url']=marker
                else:raise AssertionError('Unrecognized SWE-bench verification marker: '+str(marker))
        if id.startswith('swe-bench-live-'):
            assert len(new['reports'])==len(t['rows'])
            for row in t['rows']:
                source=next(r for r in new['reports'] if r['name']==row['system'] and r['date']==row['date'])
                count=source['resolved'];count=count['length'] if isinstance(count,dict) else count
                assert row['score']==round(count/source['total']*100,1)
        if id.startswith('deepswe-'):
            self.verify_deepswe_prices(t,new)
            t['notes_ja']=re.sub(r'(データ生成日 \(generated_at\): )\d{4}-\d{2}-\d{2}',r'\g<1>'+new['generated_at'][:10],t['notes_ja'])
        if id=='gso':
            t['notes_ja']=t['notes_ja'].replace('metadata.last_updated は 2026-03-10 だが行の日付はそれより新しい。','') .strip()
        if id.startswith('swe-bench-pro-'):
            final=self.sources[id][0]['final_url']
            t['fetched']=list(dict.fromkeys([self.sources[id][0]['url'],final]))
        t['retrieved']=self.date
        dates=[r['date'] for r in t['rows'] if r.get('date')]
        t['newest_row_date']=max(dates) if dates else None
        assert all(not r.get('date') or r['date']<=self.date for r in t['rows'])
        assert all(mid in self.registry for r in t['rows'] for mid in r['model_ids'])
        indent=len(re.search(r'\n( +)"',oldtext).group(1)) if re.search(r'\n( +)"',oldtext) else None
        text=(oldtext if same else new if isinstance(new,str) else json.dumps(new,ensure_ascii=False,indent=indent)+'\n')
        path.write_text(text)
        dump(ROOT/f'data/tables/{id}.json',t)
        provenance={'retrieved':self.date,'table':id,'status':'comparable-source-extracted','source_data_changed':not same,'old_rows':len(original['rows']),'new_rows':len(t['rows']),'rows_changed':original['rows']!=t['rows'],'snapshot':t['snapshot'],'snapshot_sha256':sha(text.encode()),'sources':self.sources[id],'method':'Complete native JSON/YAML/CSV/HTML/RSC table projection compared against the prior snapshot; supported changed rows mechanically regenerated; other source changes fail closed.'}
        support=path.parent/'frontend-pricing.js'
        if id.startswith('deepswe-') and support.exists():
            provenance['supporting_snapshots']=[{'path':str(support.relative_to(ROOT)),'sha256':sha(support.read_bytes()),'description':'Current official frontend price literal and correction functions; parsed without executing fetched JavaScript.'}]
        dump(path.parent/'provenance.json',provenance)
        return provenance

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',required=True);parser.add_argument('--cache',type=pathlib.Path,required=True);parser.add_argument('--offline',action='store_true')
    args=parser.parse_args();datetime.date.fromisoformat(args.date)
    tables=[load(p) for p in sorted((ROOT/'data/tables').glob('*.json')) if load(p)['category']=='coding']
    index=load(args.cache/'index.json') if args.offline else fetch(source_jobs(tables),args.cache,args.date)
    worker=Refresh(args.cache,args.date,tables,index);results=[]
    for t in tables:
        try:
            entry=worker.run_one(t)
        except Exception as exc:
            entry={'table':t['id'],'status':'preserved-refresh-gap','error':type(exc).__name__+': '+str(exc),'retrieved_preserved':t['retrieved']}
        results.append(entry);print(json.dumps({k:v for k,v in entry.items() if k not in ('sources','method')},ensure_ascii=False),flush=True)
    dump(pathlib.Path('/tmp/abm-coding-audit.json'),{'date':args.date,'tables':results})
    dump(pathlib.Path('/tmp/abm-coding-model-additions.json'),worker.proposals)
    return 1 if any(e['status']=='preserved-refresh-gap' for e in results) else 0

if __name__=='__main__':
    raise SystemExit(main())
