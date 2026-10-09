#!/usr/bin/env python3
"""Replay the reviewed Oct 9 coding refresh against the retained HTTP cache.
Run from root: python sources/audits/2026-10-09/refresh_coding.py --cache CACHE
Only coding data and source evidence are written. Unchanged data retains its date.
The fetch recipe is scripts/refresh_coding_sources.py: source_jobs + fetch.
"""
import argparse, copy, json, pathlib, re, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'scripts'))
import refresh_coding_sources as c
DATE='2026-10-09'
BASE='af0325ce49fdeb5200bd9730b195cc0537c63f05'
AUDIT=ROOT/'sources/audits'/DATE

def prior(path):
    return subprocess.check_output(['git','show',BASE+':'+str(path)],cwd=ROOT)

def decode(raw):
    try: return json.loads(raw)
    except json.JSONDecodeError: return raw.decode()

def source_ids(rows):
    return {(r['model'],r['createdAt']):r for r in rows}

class Reviewed(c.Refresh):
    def __init__(self,*args):
        super().__init__(*args)
        # Shared homepages may enter the grouped fetch index before v1's JSON.
        # Address the declared primary, never a source-list insertion position.
        for table in self.tables:
            if table['id'].startswith('deepswe-'):
                self.sources[table['id']].sort(key=lambda e:e['url']!=table['fetched'][0])

    def changed_rows(self,t,new):
        if not t['id'].startswith('swe-bench-pro-'):
            return super().changed_rows(t,new)
        review=c.load(AUDIT/'coding-rank-review.json')
        for proof in review['supporting_snapshots']:
            assert c.sha((ROOT/proof['path']).read_bytes())==proof['sha256']
        render=(AUDIT/'swe-bench-pro-rank-render.js').read_text()
        assert 'x=e.rank' in render and 'children:x' in render
        section=(AUDIT/'swe-bench-pro-entries-render.js').read_text()
        assert 'e.map(e=>(0,t.jsx)(o.LeaderboardScoreEntry,{entry:e,' in section
        old=decode(prior(t['snapshot']))
        before=source_ids(old['entries']);after=source_ids(new['entries'])
        assert before.keys()==after.keys(), 'SWE-bench Pro identities changed'
        assert len(before)==len(t['rows'])==len(after)
        rows=copy.deepcopy(t['rows'])
        for key,source in after.items():
            assert {k:v for k,v in before[key].items() if k!='rank'}=={k:v for k,v in source.items() if k!='rank'}, 'SWE-bench Pro change exceeds reviewed rank-only scope'
            row=next(r for r in rows if r['system']==source['model'] and r['date']==source['createdAt'][:10])
            assert row['score']==round(source['score'],2)
            assert row['score_extra']['ci_plus_minus']==source['confidenceInterval_upper']
            row['rank']=source['rank']
        return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cache',type=pathlib.Path,required=True)
    args=parser.parse_args();index=c.load(args.cache/'index.json')
    tables=[decode(prior(p.relative_to(ROOT))) for p in sorted((ROOT/'data/tables').glob('*.json')) if c.load(p)['category']=='coding']
    worker=Reviewed(args.cache,DATE,tables,index)
    results=[];changed=[]
    for table in tables:
        tid=table['id'];path=pathlib.Path('data/tables')/(tid+'.json');snapshot=pathlib.Path(table['snapshot']);provenance=snapshot.parent/'provenance.json'
        original=copy.deepcopy(table);oldbytes=prior(snapshot);old=decode(oldbytes)
        protected={path:prior(path),snapshot:oldbytes}
        for p in [provenance,snapshot.parent/'frontend-pricing.js']:
            if (ROOT/p).exists():
                try:protected[p]=prior(p)
                except subprocess.CalledProcessError:pass
        entry={'table':tid,'checked':DATE,'sources':worker.sources[tid],'rows_before':len(table['rows']),'retrieved_before':table['retrieved']}
        try:
            assert all(e.get('status')==200 for e in worker.sources[tid])
            new,same=worker.project(table,old)
            if not same:table['rows']=worker.changed_rows(table,new)
            if tid.startswith('deepswe-'):
                worker.verify_deepswe_prices(table,new)
            if tid.startswith('swe-bench-live-'):
                assert len(new['reports'])==len(table['rows'])
                for row in table['rows']:
                    source=next(r for r in new['reports'] if r['name']==row['system'] and r['date']==row['date'])
                    count=source['resolved'];count=count['length'] if isinstance(count,dict) else count
                    assert row['score']==round(count/source['total']*100,1)
            assert all(not r.get('date') or r['date']<=DATE for r in table['rows'])
            assert all(mid in worker.registry for r in table['rows'] for mid in r['model_ids'])
            row_changed=table['rows']!=original['rows']
            if row_changed:
                table['retrieved']=DATE
                table['newest_row_date']=max((r['date'] for r in table['rows'] if r.get('date')),default=None)
                if tid.startswith('swe-bench-pro-'):
                    table['notes_ja']=table['notes_ja'].replace('rank は信頼区間の上限基準(Rank (UB))。','rank は現行の公開データの rank を転記(フロントエンドもその値を表示)。ページには Rank (UB) の説明が残るが、現在の値はスコア順の連番。')
                c.dump(ROOT/path,table)
                if not same:
                    indent=len(re.search(rb'\n( +)"',oldbytes).group(1)) if re.search(rb'\n( +)"',oldbytes) else None
                    text=new if isinstance(new,str) else json.dumps(new,ensure_ascii=False,indent=indent)+'\n'
                    (ROOT/snapshot).write_text(text)
                else:(ROOT/snapshot).write_bytes(oldbytes)
                c.dump(ROOT/provenance,{'retrieved':DATE,'table':tid,'status':'comparable-source-extracted','source_data_changed':not same,'old_rows':len(original['rows']),'new_rows':len(table['rows']),'rows_changed':True,'snapshot':str(snapshot),'snapshot_sha256':c.sha((ROOT/snapshot).read_bytes()),'sources':worker.sources[tid],'method':'Reviewed complete source projection; existing normalization reused; SWE-bench Live native resolved/total and explicit dates, or SWE-bench Pro native rank-only updates with frontend direct-render evidence. Unchanged score/configuration fields preserved.'})
                if tid.startswith('swe-bench-pro-'):
                    proof=c.load(ROOT/provenance);proof['supporting_snapshots']=c.load(AUDIT/'coding-rank-review.json')['supporting_snapshots'];c.dump(ROOT/provenance,proof)
                changed.append(tid)
            else:
                for p,b in protected.items():(ROOT/p).write_bytes(b)
            entry.update(status='changed' if row_changed else 'unchanged',source_data_changed=not same,rows_changed=row_changed,rows_after=len(table['rows']),retrieved_after=table['retrieved'] if row_changed else original['retrieved'],snapshot=str(snapshot),snapshot_sha256=c.sha((ROOT/snapshot).read_bytes()))
        except Exception as exc:
            for p,b in protected.items():(ROOT/p).write_bytes(b)
            entry.update(status='preserved-gap',error=type(exc).__name__+': '+str(exc),rows_after=len(original['rows']),retrieved_after=original['retrieved'])
        results.append(entry)
    c.dump(AUDIT/'coding-fetch-index.json',index)
    c.dump(AUDIT/'coding-model-additions.json',worker.proposals)
    out={'date':DATE,'timezone':'Asia/Tokyo','base_commit':BASE,'category':'coding','method':'29 grouped HTTP responses; reviewed complete projections; unchanged good data and retrieval dates retained. DeepSWE declared-primary ordering reviewed. SWE-bench Pro rank-only source change checked against direct frontend rank rendering.','coverage':{'tables':len(results),'changed':sum(e['status']=='changed' for e in results),'unchanged':sum(e['status']=='unchanged' for e in results),'gaps':sum(e['status']=='preserved-gap' for e in results),'http_requests':len(index),'http_ok':sum(e.get('status')==200 for e in index),'supporting_http_requests':len(c.load(AUDIT/'coding-frontend-fetch-index.json')),'supporting_http_ok':sum(e.get('status')==200 for e in c.load(AUDIT/'coding-frontend-fetch-index.json')),'rows_before':sum(e['rows_before'] for e in results),'rows_after':sum(e['rows_after'] for e in results)},'changed_tables':changed,'tables':results}
    c.dump(AUDIT/'coding.json',out)
    print(json.dumps({k:v for k,v in out.items() if k!='tables'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
