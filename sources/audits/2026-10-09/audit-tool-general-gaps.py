"""Recheck relevant gaps from retained 2026-10-09 public-source responses only."""
import csv,hashlib,io,json,pathlib,os
DATE='2026-10-09';ROOT=pathlib.Path('.');OUT=ROOT/'sources/audits'/DATE;CACHE=pathlib.Path(os.environ.get('ABM_TOOL_GAPS_CACHE','/tmp/abm-tool-gaps-20261009'))
INDEX=json.loads((CACHE/'index.json').read_text());IX={r['url']:r for r in INDEX};OLD={r['url']:r for r in json.loads((ROOT/'sources/audit-2026-10-05/tool-general-gaps.json').read_text())['requests']}
IDS=['terminal-bench-1-0','terminal-bench-challenges','harbor-index','livemcpbench','gaia-validation','galileo-agent-leaderboard-v2','crmarena'];AUD=[]
def raw(u):
 r=IX[u];p=pathlib.Path(r['file']);p=p if p.is_absolute()else CACHE/p;b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==r['sha256'];return b
def text(u):return raw(u).decode()
def obj(u):return json.loads(raw(u))
def save(p,o):pathlib.Path(p).write_text(json.dumps(o,ensure_ascii=False,indent=1)+'\n')
primary={r['url']:r for r in json.loads((pathlib.Path(os.environ.get('ABM_TOOL_CACHE','/tmp/abm-tool-20261009'))/'index.json').read_text())};home=primary['https://www.tbench.ai/']['sha256']
for id in IDS:
 p=ROOT/f'data/gaps/{id}.json';gap=json.loads(p.read_text());evidence={}
 if id=='terminal-bench-1-0':
  for u in gap['tried'][:3]:assert IX[u]['sha256']==home
  evidence={'old_board_urls_match_current_homepage':True,'current_homepage_sha256':home};reason='旧1.0の3つのボードURLを再取得し、いずれも現行トップページと同一のHTMLであることをSHA-256で確認した。独立した旧1.0提出結果表は取り出せず、過去値から補完しない。'
 elif id=='terminal-bench-challenges':
  assert IX[gap['tried'][0]]['sha256']==home;assert IX[gap['tried'][1]]['sha256']==OLD[gap['tried'][1]]['sha256'];evidence={'board_url_matches_current_homepage':True,'announcement_unchanged_since':'2026-10-05'};reason='指定ボードURLは現行トップページと同一のHTML。公式のチャレンジ告知記事も前回と同一で、今回取得した一次資料から独立した提出結果表を機械抽出できなかった。'
 elif id=='harbor-index':
  posts=[u for u in gap['tried']if'(POST'in u];counts={u:len(obj(u)['rows'])for u in posts};assert all(v==0 for v in counts.values());assert IX['https://harbor-index.org/']['sha256']==OLD['https://harbor-index.org/']['sha256'];evidence={'api_row_counts':counts,'announcement_site_unchanged_since':'2026-10-05'};reason='公式Harbor HubリーダーボードAPIの1.0/1.4を再取得し、どちらもrowsは0件。harbor-index.orgも前回と同一の告知ページで、独立した公開ボード表は確認できなかった。'
 elif id=='livemcpbench':
  u=next(u for u in gap['tried']if'format=csv'in u);rows=list(csv.DictReader(io.StringIO(text(u))));dates=sorted({r['Date']for r in rows});assert len(rows)==13 and dates==['8/2025'];evidence={'csv_rows':len(rows),'csv_dates':dates,'csv_unchanged_since_previous':IX[u]['sha256']==OLD[u]['sha256']};reason='公式ページと公開スプレッドシートCSVを再取得。13行すべての日付は引き続き8/2025で、CSVは前回と同一。更新停止表を除く既存方針を維持。'
 elif id=='gaia-validation':
  app,parquet=gap['tried'];s=text(app);assert '#with gr.Tab("Results: Validation"):'in s;assert IX[parquet]['sha256']==OLD[parquet]['sha256'];evidence={'validation_tab_commented_out':True,'validation_parquet_identical_to_2026_10_05':True,'previously_verified_rows':96};reason='公式app.pyのvalidationタブは引き続きコメントアウト。公開validation Parquetは前回96件を確認したデータとSHA-256が一致する。現行ボードに表示されない表は既存の採録方針に従い取り込まない。'
 elif id=='galileo-agent-leaderboard-v2':
  space,commits,dataset=gap['tried'];cs=obj(commits);assert IX[commits]['sha256']==OLD[commits]['sha256'];ds=obj(dataset);assert ds['lastModified']=='2025-07-16T14:50:47.000Z';evidence={'latest_space_commit':{'date':cs[0]['date'],'title':cs[0]['title']},'commit_history_unchanged_since':'2026-10-05','v2_dataset_last_modified':ds['lastModified'],'v2_dataset_revision':ds['sha']};reason='公式HF Spaceとコミット一覧を再取得。履歴は前回と同一で、最後の結果追加は2025-08-13、最新2026-06-11の更新は依存ライブラリ。v2データセットの最終更新も2025-07-16のまま。更新停止表を除く既存方針を維持。'
 elif id=='crmarena':
  space,commits,csvurl=gap['tried'];meta=obj(space);rows=list(csv.DictReader(io.StringIO(text(csvurl))));assert meta['lastModified']=='2025-02-06T20:01:53.000Z';assert len(rows)==24;assert IX[csvurl]['sha256']==OLD[csvurl]['sha256'];evidence={'last_modified':meta['lastModified'],'csv_rows':len(rows),'csv_identical_to_2026_10_05':True};reason='公式HF Spaceの最終更新は2025-02-06のまま。CSVも前回と同一で、初代CRMArenaの24モデル・足場設定×9タスク種別、CRMArena-Proの結果は無い。更新停止表を除く既存方針を維持。'
 gap.update(retrieved=DATE,reason_ja=reason);save(p,gap);AUD.append({'id':id,'status':'still-gap','evidence':evidence,'reason_ja':reason,'requests':[{k:v for k,v in IX[u].items()if k!='file'}for u in gap['tried']]})
save(OUT/'tool-general-gaps.json',{'retrieved':DATE,'gaps':AUD,'note':'All 22 gap-source requests had complete successful responses already retained before cancellation surfaced on the separate main collector polling call. This recipe performs no network calls.'})
