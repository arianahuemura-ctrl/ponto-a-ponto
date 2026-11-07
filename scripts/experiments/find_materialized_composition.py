import os,sys,time,json,random
sys.path.insert(0,os.path.abspath('backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','mbm.settings')
import django;django.setup()
from transit.sptrans import staged_materialized as s,graph,planner,store,rail
from django.utils import timezone
from datetime import datetime
from zoneinfo import ZoneInfo
source=store.database_path();stat=source.stat();_,trips,_=planner._network(str(source),stat.st_mtime_ns,stat.st_size,True)
source_db=graph.readonly(source);now=datetime(2026,11,1,8,tzinfo=ZoneInfo('America/Sao_Paulo'));today=now.date();windows=planner._service_windows(source_db,trips,source,stat,now,True,{})
p=graph.readonly(s.database_path());ids=dict(p.execute('select id,sid from stops'));r=random.Random(42)
board=set(x[0] for x in p.execute('select distinct origin from rides'));end=set(x[0] for x in p.execute('select distinct destination from rides'))
def lookup(a,b):
 for table in ['topup_paths','expanded_paths','paths']:
  row=p.execute(f'select data from {table} where origin=? and destination=?',(a,b)).fetchone()
  if row:return s.decode(row[0])
 return []
t=time.monotonic();best=None
for a in r.sample(sorted(board),100):
 present=set()
 for table in ['paths','expanded_paths','topup_paths','short_walk_paths']:
  present.update(x[0] for x in p.execute(f'select destination from {table} where origin=?',(a,)))
 missing=sorted(end-present-{a});r.shuffle(missing)
 for b in missing[:20]:
  mids=r.sample(sorted(present & board-{a,b}),min(2000,len(present & board-{a,b})))
  for m in mids:
   left,right=lookup(a,m),lookup(m,b)
   for l in left:
    for rr in right:
     if l['units']+rr['units']+3>24:continue
     if l['egress'] and rr['legs'][0][1]:continue
     routes=l['legs']+rr['legs'];services=[p.execute('select service from patterns where id=(select pattern from rides where id=?)',(e,)).fetchone()[0] for e,w in routes]
     if len(services)!=len(set(services)):continue
     variants=[json.loads(p.execute('select trips from patterns where id=(select pattern from rides where id=?)',(e,)).fetchone()[0]) for e,w in routes]
     routeids=[trips[v[0]]['route_id'] for v in variants]
     if len(routeids)!=len(set(routeids)):continue
     if any(min(planner.next_departure(trips[tid],p.execute('select boarding from rides where id=?',(e,)).fetchone()[0],now.timestamp(),windows[tid])-now.timestamp() for tid in v)>3600 for (e,w),v in zip(routes,variants)):continue
     if not all(any(store.service_active(source_db,trips[tid]['service_id'],today) for tid in v) for v in variants):continue
     result=dict(origin=a,destination=b,middle=m,ids={str(k):ids[k] for k in [a,b,m]},left=l,right=rr,search_seconds=time.monotonic()-t)
     score=sum(p.execute('select seconds from rides where id=?',(e,)).fetchone()[0] for e,w in routes)+sum(p.execute('select seconds from walks where id=?',(w,)).fetchone()[0] for w in [*[w for e,w in routes],l['egress'],rr['egress']] if w)
     if best is None or score<best[0]:best=(score,result)
  if best:
   best[1]['search_seconds']=time.monotonic()-t
   open('artifacts/benchmarks/materialized-composition-candidate-20261101.json','w').write(json.dumps(best[1]));print(json.dumps(best));sys.exit()
print('NONE')
