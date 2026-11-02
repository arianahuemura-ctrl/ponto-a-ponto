"""Piloto somente leitura: composição exata e RAPTOR sobre dois trajetos salvos.
Execute da raiz após find_materialized_composition.py. Não publica rotas.
"""
import os,sys,json,time,math
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from unittest.mock import patch
sys.path.insert(0,os.path.abspath('backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','mbm.settings')
import django;django.setup()
from transit.sptrans import staged_materialized as staged,graph,store,planner,rail,weighted_planner,transfer_policy
started=time.monotonic();candidate=json.load(open('artifacts/benchmarks/materialized-composition-candidate-20261101.json'))
p=graph.readonly(staged.database_path());db=graph.readonly(store.database_path());source=store.database_path();stat=source.stat()
stops,trips,_=planner._network(str(source),stat.st_mtime_ns,stat.st_size,True)
ids=dict(p.execute('select id,sid from stops'))
a,b,m=(candidate[k] for k in ['origin','destination','middle'])
for table in ['paths','expanded_paths','topup_paths','short_walk_paths']:
 assert p.execute(f'select 1 from {table} where origin=? and destination=?',(a,b)).fetchone() is None
left,right=candidate['left'],candidate['right'];edges=left['legs']+right['legs']
rides={e:dict(p.execute('select * from rides where id=?',(e,)).fetchone()) for e,w in edges}
patterns={edge['pattern']:json.loads(p.execute('select trips from patterns where id=?',(edge['pattern'],)).fetchone()[0]) for edge in rides.values()}
feet={};walkids={w for e,w in edges if w}|{w for w in [left['egress'],right['egress']] if w}
for wid in walkids:
 w=dict(p.execute('select * from walks where id=?',(wid,)).fetchone());oa,ob=ids[w['origin']],ids[w['destination']]
 feet[oa,ob]={'origin':stops[oa],'destination':stops[ob],'distance_meters':w['meters'],'seconds':w['seconds'],'internal_transfer':bool(w['internal']),'available':True}
near=defaultdict(list)
for (oa,ob),w in feet.items():near[oa].append((ob,w['distance_meters']))
# Restrict every trip to precisely the saved boarding/alighting span.
restricted={};by_stop=defaultdict(set)
for eid,edge in rides.items():
 for tid in patterns[edge['pattern']]:
  key=f'{tid}@{eid}';trip={**trips[tid]}
  # Keep absolute offsets from the original first stop for frequency windows.
  offset=trip['times'][edge['boarding']][2]-trip['times'][0][2]
  trip['frequencies']=[(x+offset,y+offset,h,e) for x,y,h,e in trip['frequencies']]
  trip['times']=trip['times'][edge['boarding']:edge['alighting']+1]
  restricted[key]=trip
  for sid,_,_ in trip['times']:by_stop[sid].add(key)
loaded=time.monotonic()-started
results=[]
for hour in [8,12,18]:
 now=datetime(2026,11,1,hour,tzinfo=ZoneInfo('America/Sao_Paulo'));t=time.monotonic()
 windows=planner._service_windows(db,trips,source,stat,now,True,{})
 reached=now.timestamp();chain=[];at=ids[a];valid=True
 for i,(eid,wid) in enumerate(edges):
  ws=([left['egress']] if i==len(left['legs']) and left['egress'] else [])+([wid] if wid else [])
  for w in ws:
   row=p.execute('select * from walks where id=?',(w,)).fetchone();oa,ob=ids[row['origin']],ids[row['destination']];assert at==oa
   chain.append(('__walk__',oa,ob,reached,reached+row['seconds']));reached+=row['seconds'];at=ob
  edge=rides[eid];assert at==ids[edge['origin']]
  choices=[]
  for tid in patterns[edge['pattern']]:
   trip=trips[tid];x,y=edge['boarding'],edge['alighting']
   dep=planner.next_departure(trip,x,reached+(planner.TRANSFER_SECONDS if i else 0),rail.boarding_windows(trip,x,windows[tid],now.tzinfo))
   if not rail.departure_allowed(trip,dep,now.tzinfo,i>0):continue
   arr=dep+trip['times'][y][1]-trip['times'][x][2]
   if math.isfinite(arr):choices.append((arr,dep,tid,x,y))
  if not choices:valid=False;break
  reached,dep,tid,x,y=min(choices);chain.append((tid,x,y,dep,reached));at=ids[edge['destination']]
 if right['egress']:raise AssertionError('Final egress not supported by this selected pilot')
 exact=None
 if valid and reached<=now.timestamp()+planner.HORIZON_SECONDS:
  assert at==ids[b]
  with patch.object(planner,'leg_shape',return_value=[]):
   exact=transfer_policy.annotate(planner._format_journey(ids[b],reached,chain,trips,stops,now.timestamp(),now,{ids[b]:0},{ids[a]:0},{},feet))
  assert exact['transfer_cost_units']<=24
 exact_seconds=time.monotonic()-t
 context={};t=time.monotonic()
 with patch.object(planner,'_network',return_value=(stops,restricted,by_stop)),patch.object(planner,'_nearby',return_value=near),patch.object(planner,'leg_shape',return_value=[]):
  found=weighted_planner.journeys(db,ids[a],ids[b],8,now,feet,context,None,None,True,True,False)
 elapsed=time.monotonic()-t
 if exact:
  assert found, 'RAPTOR não reproduziu a composição válida'
  best=min(found,key=lambda j:j['duration_minutes'])
  assert best['arrival']==exact['arrival']
  assert best['transfer_cost_units']==exact['transfer_cost_units']
  assert [(l['route_id'],l['origin']['id'],l['destination']['id']) for l in best['legs']]==[(l['route_id'],l['origin']['id'],l['destination']['id']) for l in exact['legs']]
  assert not context.get('weighted_search_limited',False)
 def compact(j):
  if j is None:return None
  return {k:j[k] for k in ['duration_minutes','arrival','transfers','transfer_cost','transfer_cost_units']}|{'legs':[{k:l[k] for k in ['code','mode','origin','destination','departure','arrival','wait_minutes','ride_minutes']} for l in j['legs']], 'walks':j['transfer_walks']}
 results.append({'departure':now.isoformat(),'exact_composition':compact(exact),'exact_seconds':exact_seconds,'raptor_seconds':elapsed,'raptor_search_limited':context.get('weighted_search_limited',False),'raptor_journeys':len(found),'raptor_best':compact(min(found,key=lambda j:j['duration_minutes'])) if found else None})
 print(json.dumps({'hour':hour,'exact':exact and exact['duration_minutes'],'raptor_count':len(found),'raptor_seconds':elapsed}),flush=True)
report={'candidate':candidate,'origin':stops[ids[a]],'destination':stops[ids[b]],'connection':stops[ids[m]],'network_load_seconds':loaded,'restricted_trips':len(restricted),'restricted_rides':len(rides),'results':results,'scope':'Read-only pilot. RAPTOR restricted to saved spans and their verified walks; timetable estimates, not real-time; no global completeness claim.'}
output='artifacts/benchmarks/materialized-raptor-composition-20261101.json';open(output,'w').write(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(output)
