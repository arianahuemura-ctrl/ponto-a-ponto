import os,sys,json,time,hashlib,subprocess,sqlite3
from pathlib import Path
from datetime import datetime
R=Path('/home/avale/Projetos/maua_bus_map');P=R/'artifacts/transport/artesp-20261102';O=Path(__file__).parent
os.environ['DJANGO_SETTINGS_MODULE']='mbm.settings';os.environ['SPTRANS_DATABASE']=str(P/'network.sqlite3');os.environ['SPTRANS_LEGACY_DATABASE']=str(R/'sptrans.sqlite3');sys.path.insert(0,str(R/'backend'))
import django
django.setup()
from transit.sptrans import store,staged_adapter
files=['backend/transit/sptrans/'+s+'.py' for s in ['store','staged_adapter','planner','rail','rail_network','transfer_policy','supplementary']]
report={'executed_at':datetime.now().astimezone().isoformat(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'source_sha256':{f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in files},'method':'Production staged_adapter.progressive, real imported read-only databases, exact stop IDs, explicit service datetime, max weighted cost 1. No mock timetables. Local process timings are not mobile latency.','queries':[]}
dbstats={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in [P/'network.sqlite3',P/'network.staged.sqlite3',P/'network.staged-walks.sqlite3']}
pairs=[('metropolitana','artesp:48804','artesp:5776'),('onibus_metro','artesp:64476','18859'),('onibus_trem','artesp:7700','1010053'),('ferroviaria','18935','18859')]
with store.connection() as db:
 for day in ['2026-11-03','2026-11-07','2026-11-08']:
  for label,a,b in pairs:
   now=datetime.fromisoformat(day+'T08:00:00-03:00');start=time.monotonic();first=None;events=[]
   origin,destination=store.get_stop(db,a),store.get_stop(db,b)
   for row in staged_adapter.progressive(db,origin,destination,1,now):
    if row['journeys'] and first is None:first=time.monotonic()-start
    events.append({'elapsed_seconds':time.monotonic()-start,'journeys':len(row['journeys']),'complete':row.get('complete')})
   item={'scenario':label,'query_at':now.isoformat(),'origin':origin,'destination':destination,'first_route_seconds':first,'elapsed_seconds':time.monotonic()-start,'events':events,'result':row}
   report['queries'].append(item)
   print(label,now.date(),'first',first,'routes',[(j['duration_minutes'],[l['route_id'] for l in j['legs']]) for j in row['journeys']],flush=True)
 for label,a,b,when in [('madrugada','artesp:64476','18859','2026-11-03T02:00:00-03:00'),('fora_vigencia','artesp:64476','18859','2027-01-02T08:00:00-03:00')]:
  now=datetime.fromisoformat(when);start=time.monotonic();first=None
  origin,destination=store.get_stop(db,a),store.get_stop(db,b)
  for row in staged_adapter.progressive(db,origin,destination,1,now):
   if row['journeys'] and first is None:first=time.monotonic()-start
  report['queries'].append({'scenario':label,'query_at':when,'origin':origin,'destination':destination,'first_route_seconds':first,'elapsed_seconds':time.monotonic()-start,'result':row})
  print(label,[(j['duration_minutes'],[l['route_id'] for l in j['legs']]) for j in row['journeys']],flush=True)
 with sqlite3.connect((P/'network.staged.sqlite3').as_uri()+'?mode=ro',uri=True) as prepared:
  prepared.row_factory=sqlite3.Row
  row=prepared.execute('SELECT w.* FROM walks w JOIN stops a ON a.id=w.origin JOIN stops b ON b.id=w.destination WHERE a.sid=? AND b.sid=?',('artesp:93038','18934')).fetchone()
  report['station_access']={'origin':store.get_stop(db,'artesp:93038'),'destination':store.get_stop(db,'18934'),'verified_materialized_walk':dict(row),'interpretation':'Pedestrian connection in verified transfer graph, not proof of step-free access, station opening or full public-interface walking query.'}
report['transport_databases_unmodified']=all([Path(p).stat().st_size,Path(p).stat().st_mtime_ns]==s for p,s in dbstats.items())
assert report['transport_databases_unmodified']
(O/'planning-queries.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
