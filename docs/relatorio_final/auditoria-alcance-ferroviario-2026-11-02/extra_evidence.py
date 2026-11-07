# Reuse the read-only/no-network setup, without repeating the query loop.
from pathlib import Path
p=Path('/tmp/pap-alcance-ferroviario-20261102')
s=(p/'query.py').read_text().split('now=datetime.now')[0];exec(compile(s,'readonly-setup','exec'))
import csv
from django.test import RequestFactory
from transit.sptrans import views
observed=datetime.now(ZoneInfo('America/Sao_Paulo'));t=time.monotonic();r=views.board(RequestFactory().get('/api/sptrans/board/',{'origin':'18935','destination':'18859','max_transfers':'4','route_only':'1'}));body=json.loads(r.content);(P/'endpoint-response.json').write_text(json.dumps(body,ensure_ascii=False,indent=2));(P/'endpoint-query.json').write_text(json.dumps({'started_at':observed.isoformat(),'finished_at':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),'request':'/api/sptrans/board/?origin=18935&destination=18859&max_transfers=4&route_only=1','execution':'Django view via RequestFactory; no HTTP transport/middleware, actual clock; all SQLite connections read-only; network blocked','status':r.status_code,'seconds':time.monotonic()-t},ensure_ascii=False,indent=2));print('endpoint',r.status_code,body.keys(),flush=True)
print('journeys',len(body.get('journeys',[])),flush=True)
# Match station, route, service and timetable records in preserved feed to the imported DB.
source=R/'fonts/sptrans_gtfs';match={};hashes={}
for name in ['agency','stops','routes','trips','calendar','frequencies','stop_times','shapes']:
 f=source/(name+'.txt');hashes[f.name]=hashlib.file_digest(f.open('rb'),'sha256').hexdigest()
 with f.open(encoding='utf-8-sig',newline='') as st:
  rows=list(csv.DictReader(st))
 if name=='agency':chosen=rows
 elif name=='stops':chosen=[r for r in rows if r['stop_id'] in ['18935','18937']]
 elif name=='routes':chosen=[r for r in rows if r['route_id']=='CPTM L10']
 elif name=='calendar':chosen=[r for r in rows if r['service_id']=='USD']
 elif name=='shapes':chosen=[r for r in rows if r['shape_id'] in ['17852','17853']]
 else:chosen=[r for r in rows if r.get('route_id')=='CPTM L10' or r.get('trip_id') in ['CPTM L10-0','CPTM L10-1']]
 with store.connection() as db:
  if name=='agency':match[name]={'rows':chosen,'comparison':'agency.txt not imported by store.TABLES'};continue
  columns=store.TABLES[name];sql='SELECT '+','.join(columns)+' FROM '+name
  # Compare selected source rows with imported records using membership normalized to declared types.
  normalized=lambda r:tuple(float(r[c]) if c in store.NUMERIC else str(r.get(c,'')) for c in columns)
  imported={tuple(r) for r in db.execute(sql)};assert all(normalized(r) in imported for r in chosen)
 match[name]={'selected_rows':len(chosen),'all_selected_rows_match_imported_db':True}
(P/'feed-provenance.json').write_text(json.dumps({'source':str(source),'raw_files_sha256':hashes,'matching':match,'import_metadata':json.loads((P/'database-inspection.json').read_text())['metadata'],'limit':'Import metadata records counts and import time, not the original download URL or a signed release manifest. agency_url carries versao=051026.'},ensure_ascii=False,indent=2));print('FEED MATCHED',flush=True)
