"""Audit every graph-isolated endpoint against original GTFS and pedestrian data."""
import os,sys,json,csv,math,time
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2];os.chdir(ROOT);sys.path.insert(0,str(ROOT/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','mbm.settings')
import django;django.setup()
from transit.sptrans import staged_materialized as staged,graph,store,planner,directions
OUT=ROOT/'artifacts/benchmarks/coverage-audit-20261101';OUT.mkdir(exist_ok=True)
p=graph.readonly(staged.database_path());meta=json.loads(p.execute('select value from metadata where id=1').fetchone()[0]);ids=dict(p.execute('select id,sid from stops'));rev={s:i for i,s in ids.items()}
source=store.database_path();stat=source.stat();stops,trips,by_stop=planner._network(str(source),stat.st_mtime_ns,stat.st_size,True)
board=set(r[0] for r in p.execute('select distinct origin from rides'));alight=set(r[0] for r in p.execute('select distinct destination from rides'));starts=set(board);ends=set(alight)
for a,b,internal in p.execute('select origin,destination,internal from walks'):
 if internal and b in board:starts.add(a)
 if a in alight:ends.add(b)
no_start=set(ids)-starts;no_end=set(ids)-ends;affected=no_start|no_end;affected_sids={ids[i] for i in affected}
occ=defaultdict(list)
for tid,tr in trips.items():
 for pos,(sid,_,_) in enumerate(tr['times']):
  if sid in affected_sids:occ[sid].append({'trip_id':tid,'line':tr['route_short_name'],'direction':tr['direction_id'],'position':pos,'stops':len(tr['times']),'first':pos==0,'last':pos==len(tr['times'])-1})
walkdb=graph.readonly(meta['signature']['walks'][0]);outgoing=defaultdict(list);incoming=defaultdict(list)
qs=','.join('?'*len(affected_sids));args=sorted(affected_sids)
for row in walkdb.execute(f'select origin,destination,status,distance_meters,seconds,air_meters from walk_edge where origin in ({qs}) or destination in ({qs})',args+args):
 r=dict(row)
 if r['origin'] in affected_sids:outgoing[r['origin']].append(r)
 if r['destination'] in affected_sids:incoming[r['destination']].append(r)
records=[]
for i in sorted(affected):
 sid=ids[i];stop=stops[sid];rows=occ[sid];role='origin' if i in no_start else 'destination';peers=board if role=='origin' else alight
 candidates=outgoing[sid] if role=='origin' else incoming[sid]
 verified=[r for r in candidates if r['status']=='verified' and rev[r['destination'] if role=='origin' else r['origin']] in peers]
 nearest=sorted((directions.distance((stop['lat'],stop['lon']),(stops[ids[j]]['lat'],stops[ids[j]]['lon'])),j) for j in peers if j!=i)[:3]
 if not rows:cause='no_stop_times_in_supported_network'
 elif role=='origin' and all(r['last'] for r in rows):cause='last_stop_only'
 elif role=='destination' and all(r['first'] for r in rows):cause='first_stop_only'
 else:cause='other_requires_review'
 snap=walkdb.execute('select * from stop_snap where id=?',(sid,)).fetchone()
 records.append({'index':i,'stop':stop,'blocked_role':role,'cause':cause,'occurrences':rows,'pedestrian_statuses':dict(Counter(r['status'] for r in candidates)),
 'shortest_calculated_links':sorted([r for r in candidates if r['distance_meters'] is not None],key=lambda r:r['distance_meters'])[:3], 'verified_links_to_usable_network':len(verified),'nearest_verified_links':sorted(verified,key=lambda r:r['distance_meters'])[:3],
 'nearest_usable_stops':[{'air_meters':gap,'stop':stops[ids[j]]} for gap,j in nearest],
 'snap':dict(snap) if snap else None,'interpretation':('External initial walking exists but is excluded by materialization access policy' if role=='origin' and verified else 'No verified admissible endpoint connection in current graph; not proof of physical inaccessibility')})
configuration=meta['signature']['walk_configuration']
summary={'pedestrian_snap_limit_meters':configuration['max_snap_meters'],'materialized_walk_limit_meters':configuration['max_meters'], 'destination_causes':dict(Counter('snap_beyond_limit' if r['snap'] and r['snap']['distance_meters']>configuration['max_snap_meters'] else 'walk_beyond_limit' if r['shortest_calculated_links'] and r['shortest_calculated_links'][0]['distance_meters']>configuration['max_meters'] else 'other' for r in records if r['blocked_role']=='destination')),'points':len(records),'origins':len(no_start),'destinations':len(no_end),'causes':dict(Counter(r['cause'] for r in records)),
 'origins_with_verified_external_walk_to_boarding':sum(r['blocked_role']=='origin' and r['verified_links_to_usable_network']>0 for r in records),
 'scope':'Original local GTFS sequence positions, verified pedestrian graph and current endpoint rules; no inferred boarding prohibition'}
(OUT/'endpoint-audit.json').write_text(json.dumps({'summary':summary,'points':records},ensure_ascii=False,indent=2)+'\n')
with (OUT/'endpoint-audit.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['stop_id','name','role','cause','trip_occurrences','verified_links','nearest_usable_stop','air_meters','pedestrian_statuses'])
 for r in records:w.writerow([r['stop']['id'],r['stop']['name'],r['blocked_role'],r['cause'],len(r['occurrences']),r['verified_links_to_usable_network'],r['nearest_usable_stops'][0]['stop']['id'],round(r['nearest_usable_stops'][0]['air_meters'],2),json.dumps(r['pedestrian_statuses'])])
print(json.dumps(summary,ensure_ascii=False))
