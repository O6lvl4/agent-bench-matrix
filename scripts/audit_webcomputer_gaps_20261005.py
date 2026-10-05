#!/usr/bin/env python3
"""Record read-only public-source rechecks for the web/computer-use gaps."""
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1];P=pathlib.Path('/tmp/abm-webcomputer-fetch');ix=json.loads((P/'index.json').read_text());date='2026-10-05'
checks={
'computer-agent-arena':(['https://arena.xlang.ai/leaderboard','https://arena.xlang.ai/'],'現行の leaderboard URL は HTTP 404、サイトのルートは HTTP 403。公開リーダーボードを再取得できなかったため既存の欠測扱いを維持。旧リポジトリの固定 CSV を現行値として代用しない。'),
'webvoyager':(['https://raw.githubusercontent.com/MinorJerry/WebVoyager/main/README.md'],'公式 README を再取得。実装・タスク・評価方法はあるが、継続更新の公式リーダーボードへのリンクやモデル別の現行結果データは確認できない。'),
'browsecomp':(['https://openai.com/index/browsecomp/','https://raw.githubusercontent.com/openai/simple-evals/main/README.md','https://www.kaggle.com/api/i/benchmarks.BenchmarkService/GetBenchmarkLeaderboard'],'simple-evals の公式 README は2025年7月に新モデル・結果の更新を終了したと引き続き明記。OpenAI 紹介ページは今回 HTTP 403 で再取得できない。Kaggle の公開 API は取得成功し、別表 browsecomp-kaggle の全42行を照合済み。ブラウジング用ツール付きエージェントの公式ボードと同一視しない。'),
'browsecomp-zh':(['https://raw.githubusercontent.com/PALIN2018/BrowseComp-ZH/main/README.md'],'公式 README を再取得。Model Performance Overview は論文の固定結果表で、継続更新される公開リーダーボードは確認できない。論文の固定表を現行ボードとして取り込まない。'),
'windows-agent-arena':(['https://microsoft.github.io/WindowsAgentArena/'],'公式サイトを再取得。研究紹介・論文時点の結果はあるが、継続更新のモデル別リーダーボードや結果データは確認できない。'),
'screensuite':(['https://raw.githubusercontent.com/huggingface/screensuite/main/README.md'],'公式 README を再取得。評価ツール群と対象データセットの一覧はあるが、公開の公式リーダーボードや保守中のモデル別結果データへの案内は確認できない。'),
'hud-osworld-verified':(['https://www.hud.ai/leaderboards','https://www.hud.ai/'],'旧リーダーボード URL は今回 HTTP 404（前回の429ボット検査とは異なる）。公式トップページは取得できたが、OSWorld-Verified の現行ボードや結果データへのリンクは見つからず、既存の欠測扱いを維持。'),
'macosworld':(['https://macos-world.github.io/'],'公式サイトを再取得。主なベンチマーク成績は images/results.png の画像で示され、機械可読な公開リーダーボードは確認できない。画像の値を転記しない。'),
'st-webagentbench':(['https://huggingface.co/api/spaces/ST-WebAgentBench/st-webagentbench-leaderboard','https://st-webagentbench-st-webagentbench-leaderboard.hf.space/config','https://huggingface.co/spaces/ST-WebAgentBench/st-webagentbench-leaderboard/raw/main/app.py','https://huggingface.co/api/datasets/ST-WebAgentBench/st-webagentbench-data'],'HF Space API は引き続き RUNTIME_ERROR。実行中ボードの config は HTTP 503。公式 app.py が結果を同期する ST-WebAgentBench/st-webagentbench-data の API は HTTP 401 で、認証無しの結果抽出はできない。')}
audit=[]
for id,(urls,reason) in checks.items():
 p=ROOT/'data/gaps'/f'{id}.json';d=json.loads(p.read_text());d.update(tried=urls,reason_ja=reason,retrieved=date);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 a={'id':id,'retrieved':date,'status':'gap-rechecked','reason_ja':reason,'sources':[]}
 for u in urls:
  q=ix[u];r={'url':u,'http_status':q.get('status') or int(re.search(r'HTTP Error (\d+)',q.get('error',''))[1]) if q.get('status') or 'HTTP Error' in q.get('error','') else None,'error':q.get('error')}
  if 'path' in q:r.update(bytes=q['bytes'],sha256=hashlib.sha256(pathlib.Path(q['path']).read_bytes()).hexdigest())
  a['sources'].append(r)
 audit.append(a)
q=ROOT/'sources/gaps';q.mkdir(exist_ok=True);(q/'webcomputer-audit-2026-10-05.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
pathlib.Path('/tmp/abm-webcomputer-gap-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('Rechecked',len(audit),'gaps')
