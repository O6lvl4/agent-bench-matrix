#!/usr/bin/env python3
"""Check fetched Sakana report v2 Table 1 and arXiv's latest-version metadata.
Never writes measured tables. Update only after exact comparable numeric checks.
Usage: python scripts/audit_research_claims.py --html /tmp/v2.html --abstract /tmp/abs.html --date YYYY-MM-DD
Obtain inputs with curl -L from the URLs in the claim and its source fields.
"""
import argparse,datetime,hashlib,json,pathlib,re
from lxml import html
ROOT=pathlib.Path(__file__).resolve().parents[1]
def compact(s):return ' '.join(s.split())
def key(s):
 s=re.sub(r'\\+tau\^\{3\}','',s);return ''.join(s.split()).replace('³','3')
def extract(table):
 trs=table.xpath('.//tr');headers=[compact(c.text_content()) for c in trs[0].xpath('./td|./th')];result={}
 for tr in trs[1:]:
  cells=tr.xpath('./td|./th');benchmark=compact(cells[0].text_content());values={}
  assert len(cells)==len(headers)
  for name,cell in zip(headers[1:],cells[1:]):
   text=compact(cell.text_content())
   if not name:assert not text;continue
   if re.fullmatch(r'-?\d+(?:\.\d+)?',text):values[name]=float(text)
   elif text not in ['','-','—']:raise ValueError('Unexpected nonnumeric table cell: '+text)
  result[benchmark]=values
 return result
ap=argparse.ArgumentParser();ap.add_argument('--html',required=True);ap.add_argument('--abstract',required=True);ap.add_argument('--date',required=True);args=ap.parse_args();datetime.date.fromisoformat(args.date)
p=ROOT/'data/claims/sakana-fugu-report.json';claim=json.loads(p.read_text());source=pathlib.Path(args.html).read_bytes();abstract=pathlib.Path(args.abstract).read_bytes();doc=html.fromstring(source.decode("utf-8"));absdoc=html.fromstring(abstract.decode("utf-8"));tables=doc.xpath('//table[@id="S4.T1.7"]');assert len(tables)==1
fresh=extract(tables[0]);stored_html=extract(html.fromstring((ROOT/claim['snapshot']).read_text()));stored_json=json.loads((ROOT/'sources/claims/sakana-fugu-report/table1.json').read_text())['rows']
normalize=lambda data:{key(k):v for k,v in data.items()}
assert normalize(fresh)==normalize(stored_html),'Report differs from stored HTML table: preserve claims and review new values'
assert normalize(fresh)==normalize(stored_json),'Report differs from stored JSON extraction'
figure_diffs=[]
for f in claim['figures']:
 current=normalize(fresh)[key(f['benchmark_raw'])][f['model_raw']]
 if current!=f['value']:figure_diffs.append({'benchmark':f['benchmark_raw'],'model':f['model_raw'],'stored':f['value'],'source':current})
assert not figure_diffs,figure_diffs
abs_text=compact(absdoc.text_content());latest=re.search(r'\(this version, (v\d+)\)',abs_text);assert latest,'Missing latest-version declaration';assert latest[1]=='v2','A newer report exists: fetch exact new version before updating'
links=sorted(set(absdoc.xpath('//a[contains(@href,"2606.21228v")]/@href')))
version_history=absdoc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," submission-history ")]');history=compact(version_history[0].text_content()) if version_history else abs_text[abs_text.index('Submission history'):abs_text.index('Full-text links:')]
setup=doc.xpath('//*[@id="S4.SS1.SSS1"]');assert len(setup)==1
out=ROOT/'sources/claims/sakana-fugu-report';(out/('abstract-'+args.date+'.html')).write_bytes(abstract);(out/('setup-'+args.date+'.txt')).write_text('Source: '+claim['fetched'][0]+'\n\n'+compact(setup[0].text_content())+'\n')
report={'id':claim['id'],'retrieved':args.date,'status':'comparable_unchanged','table_id':'S4.T1.7','latest_report_version':latest[1],'submission_history':history,'version_links':links,'table_rows':len(fresh),'numeric_cells_checked':sum(map(len,fresh.values())),'claim_figures_checked':len(claim['figures']),'numeric_differences':figure_diffs,'layer':'vendor_claims_only','measured_tables_modified':False,'sources':[{'url':claim['fetched'][0],'bytes':len(source),'sha256':hashlib.sha256(source).hexdigest()},{'url':claim['source'],'bytes':len(abstract),'sha256':hashlib.sha256(abstract).hexdigest()}],'preserved_snapshots':[claim['snapshot'],'sources/claims/sakana-fugu-report/table1.json'],'extracted_rows':fresh}
(out/('audit-'+args.date+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');pathlib.Path('/tmp/abm-research-claims-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
# Keep the original claim JSON formatting, figures, mappings, and historical notes.
s=p.read_text();s=s.replace('"retrieved": "'+claim['retrieved']+'"','"retrieved": "'+args.date+'"',1);p.write_text(s)
print(json.dumps({k:v for k,v in report.items() if k!='extracted_rows'},ensure_ascii=False,indent=2))
