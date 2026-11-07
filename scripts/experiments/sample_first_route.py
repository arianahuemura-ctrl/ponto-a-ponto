"""Adaptive 32-process first-journey benchmark. See docs/coverage-audit-contract.md."""
import os,sys,json,time,random,signal,math,multiprocessing as mp
from pathlib import Path
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2];os.chdir(ROOT);sys.path.insert(0,str(ROOT/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','mbm.settings')
import django;django.setup()
from django.core.cache import cache
from transit.sptrans import staged_materialized as staged,graph,store,planner,alternatives,staged_adapter,walking,directions
from transit.sptrans.journey_completion import has_short_bus_leg,normalize_walks
OUT=ROOT/'artifacts/benchmarks/coverage-audit-20261101';OUT.mkdir(exist_ok=True)
class BudgetExceeded(BaseException):pass
class ExternalRequired(BaseException):pass

def prepare_samples():
 target=OUT/'sample-pairs.json'
 existing=json.loads(target.read_text()) if target.exists() else None
 if existing and all(len(v)>=128 for v in existing.values()):return existing
 source=store.database_path();stat=source.stat();stops,_,_=planner._network(str(source),stat.st_mtime_ns,stat.st_size,True)
 p=graph.readonly(staged.database_path());ids=dict(p.execute('select id,sid from stops'));rev={v:k for k,v in ids.items()}
 audit=json.loads((OUT/'endpoint-audit.json').read_text())['points'];no_start={r['index'] for r in audit if r['blocked_role']=='origin'};no_end={r['index'] for r in audit if r['blocked_role']=='destination'}
 rand=random.Random(20261101);groups=defaultdict(list);seen=set();target_n=128
 def add(group,a,b):
  if a==b or (group,a,b) in seen:return
  seen.add((group,a,b));groups[group].append({'origin':ids[a],'destination':ids[b],'group':group,'air_meters':directions.distance((stops[ids[a]]['lat'],stops[ids[a]]['lon']),(stops[ids[b]]['lat'],stops[ids[b]]['lon']))})
 def lookup(a,b):
  for t in ['topup_paths','expanded_paths','paths']:
   r=p.execute(f'select data from {t} where origin=? and destination=?',(a,b)).fetchone()
   if r:return staged.decode(r[0])
  return []
 for r in audit:
  i=r['index'];peers=[k for k in ids if k not in no_start|no_end and directions.distance((stops[ids[i]]['lat'],stops[ids[i]]['lon']),(stops[ids[k]]['lat'],stops[ids[k]]['lon']))>6000]
  j=rand.choice(peers);add('blocked_origin' if i in no_start else 'blocked_destination',i if i in no_start else j,j if i in no_start else i)
  # Explicitly examine the closest usable stop, without pretending the walk is verified.
  for neighbour in r['nearest_usable_stops']:
   near=rev[neighbour['stop']['id']]
   add('endpoint_near',i if i in no_start else near,near if i in no_start else i)
 for group,points in [('blocked_origin',sorted(no_start)),('blocked_destination',sorted(no_end))]:
  while len(groups[group])<target_n:
   i=rand.choice(points);j=rand.randrange(len(ids))
   if j in no_start|no_end:continue
   gap=directions.distance((stops[ids[i]]['lat'],stops[ids[i]]['lon']),(stops[ids[j]]['lat'],stops[ids[j]]['lon']))
   if gap>6000:add(group,i if group=='blocked_origin' else j,j if group=='blocked_origin' else i)
 for a,b in p.execute('select origin,destination from short_walk_paths order by origin,destination'):
  if len(groups['short_walk'])<target_n:add('short_walk',a,b)
 # Include missing pairs with usable endpoints, sampled across origins.
 order=list(ids);rand.shuffle(order)
 for a in order:
  if len(groups['missing_connected_endpoints'])>=target_n:break
  if a in no_start:continue
  present=set()
  for table in ['paths','expanded_paths','topup_paths','short_walk_paths']:
   present.update(r[0] for r in p.execute(f'select destination from {table} where origin=?',(a,)))
  missing=list(set(ids)-present-no_end-{a});rand.shuffle(missing)
  for b in missing[:4]:
   if directions.distance((stops[ids[a]]['lat'],stops[ids[a]]['lon']),(stops[ids[b]]['lat'],stops[ids[b]]['lon']))>6000:add('missing_connected_endpoints',a,b)
   if len(groups['missing_connected_endpoints'])>=target_n:break
 pattern_rail=dict(p.execute('select id,rail from patterns'));ridepatterns={}
 required=['bus_direct','bus_one_transfer','bus_multiple_transfers','rail_or_mixed','near_materialized']
 tries=0
 while any(len(groups[g])<target_n for g in required):
  tries+=1
  if tries>200000:raise RuntimeError('Insufficient samples')
  a,b=rand.sample(list(ids),2)
  if a in no_start or b in no_end:continue
  routes=lookup(a,b)
  if not routes:continue
  gap=directions.distance((stops[ids[a]]['lat'],stops[ids[a]]['lon']),(stops[ids[b]]['lat'],stops[ids[b]]['lon']))
  if gap<=5000:group='near_materialized'
  else:
   r=routes[0];rail=False
   for e,w in r['legs']:
    if e not in ridepatterns:ridepatterns[e]=p.execute('select pattern from rides where id=?',(e,)).fetchone()[0]
    rail=rail or bool(pattern_rail[ridepatterns[e]])
   group='rail_or_mixed' if rail else 'bus_direct' if r['units']==0 else 'bus_one_transfer' if r['units']==3 else 'bus_multiple_transfers'
  if len(groups[group])<target_n:add(group,a,b)
 p.close();result=dict(groups)
 if existing:
  for group,rows in result.items():
   prior=existing.get(group,[]);seen_pairs={(r['origin'],r['destination']) for r in prior}
   result[group]=prior+[r for r in rows if (r['origin'],r['destination']) not in seen_pairs]
 target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result

def init_worker():
 global STOPS,EXTERNAL
 source=store.database_path();stat=source.stat();STOPS,_,_=planner._network(str(source),stat.st_mtime_ns,stat.st_size,True)
 EXTERNAL=[]
 def unavailable(a,b,**kwargs):
  EXTERNAL.append({'origin':a['id'],'destination':b['id']});raise ExternalRequired()
 walking.route=unavailable
 def timeout(*args):raise BudgetExceeded()
 signal.signal(signal.SIGALRM,timeout)
 # Fail closed if another code path tries to use a network socket.
 import socket
 def no_network(*args,**kwargs):raise ExternalRequired()
 socket.socket.connect=no_network

def measure(task):
 global EXTERNAL
 origin,destination=STOPS[task['origin']],STOPS[task['destination']];now=datetime(2026,11,3,task['hour'],tzinfo=ZoneInfo('America/Sao_Paulo'))
 result={**task,'departure':now.isoformat(),'pid':os.getpid()};cache.clear()
 def run(prepared=False):
  EXTERNAL.clear();t=time.monotonic();stream=None;db=graph.readonly(store.database_path());events=0;last={};answer={}
  signal.setitimer(signal.ITIMER_REAL,30)
  try:
   stream=staged_adapter.progressive(db,origin,destination,4,now) if prepared else alternatives.progressive(db,origin,destination,4,now,refresh=True)
   for event in stream:
    events+=1;last=event
    journeys=event['journeys']
    if prepared:journeys=[normalize_walks(j) for j in journeys if not has_short_bus_leg(j)]
    if journeys:
     answer={'state':'first_route','first_route_seconds':time.monotonic()-t,'planner':event.get('planner'),'routes_at_first_event':len(journeys),'cost':journeys[0].get('transfer_cost'),'duration_minutes':journeys[0].get('duration_minutes')};break
   else:answer={'state':'no_route_completed','search_limited':last.get('search_limited',False),'walking_incomplete':last.get('walking_incomplete',False)}
  except ExternalRequired:answer={'state':'external_required','external_calls':list(EXTERNAL)}
  except BudgetExceeded:answer={'state':'timeout_30s'}
  except Exception as e:answer={'state':'error','error':type(e).__name__+': '+str(e)}
  finally:
   signal.setitimer(signal.ITIMER_REAL,0)
   if stream is not None:stream.close()
   db.close()
  answer.update(elapsed_seconds=time.monotonic()-t,events=events)
  return answer
 result['flow']=run()
 # Independent prepared-reader measurement isolates routing from external dependencies.
 result['prepared']=run(True)
 return result

def quantile(values,q):
 s=sorted(values);return s[round((len(s)-1)*q)] if s else None

def summarize(rows):
 states=Counter(r['flow']['state'] for r in rows);times=[r['flow']['elapsed_seconds'] for r in rows];p10,median,p90=(quantile(times,q) for q in [.1,.5,.9]);stable=len(states)==1 and p90-p10<=max(.05,.2*median)
 return {'n':len(rows),'states':dict(states),'p10_seconds':p10,'median_seconds':median,'p90_seconds':p90,'max_seconds':max(times),'stable_batch':stable,'all_first_routes_within_30s':all(r['flow']['state']=='first_route' and r['flow']['first_route_seconds']<=30 for r in rows),'prepared_states':dict(Counter(r['prepared']['state'] for r in rows))}

def main():
 groups=prepare_samples();hours=[8,14,2];tasks=[]
 # Mandatory endpoint audit measurements include all 59 near endpoint cases.
 for group in groups:
  for hour in hours:
   for row in groups[group][:32]:tasks.append({**row,'hour':hour,'batch':0})
 donefile=OUT/'latency-results.jsonl';previous=[json.loads(l) for l in donefile.read_text().splitlines()] if donefile.exists() else []
 key=lambda r:(r['group'],r['hour'],r['origin'],r['destination'])
 done={key(r):r for r in previous};started=time.monotonic()
 old_summary=OUT/'latency-summary.json'
 previous_wall=json.loads(old_summary.read_text()).get('wall_seconds_total',json.loads(old_summary.read_text()).get('wall_seconds_this_run',0)) if old_summary.exists() else 0
 with ProcessPoolExecutor(max_workers=32,mp_context=mp.get_context('fork'),initializer=init_worker) as pool,donefile.open('a',buffering=1) as output:
  for batch in range(4):
   if batch:
    tasks=[]
    for group in groups:
     for hour in hours:
      prev=[r for r in done.values() if r['group']==group and r['hour']==hour and r['batch']==batch-1]
      if prev and not summarize(prev)['stable_batch']:
       for row in groups[group][32*batch:32*(batch+1)]:tasks.append({**row,'hour':hour,'batch':batch})
   futures={pool.submit(measure,t):t for t in tasks if key(t) not in done}
   for f in as_completed(futures):
    r=f.result();done[key(r)]=r;output.write(json.dumps(r,ensure_ascii=False)+'\n')
    if len(done)%32==0:print('completed',len(done),'elapsed',round(time.monotonic()-started,1),flush=True)
   print('batch',batch,'complete',flush=True)
  mandatory=[{**row,'hour':hour,'batch':-1} for group in ['blocked_origin','endpoint_near'] for row in groups[group][:59] for hour in hours]
  futures=[pool.submit(measure,t) for t in mandatory if key(t) not in done]
  for f in as_completed(futures):
   r=f.result();done[key(r)]=r;output.write(json.dumps(r,ensure_ascii=False)+'\n')
 allrows=list(done.values());summaries=[]
 for group in groups:
  for hour in hours:
   rows=[r for r in allrows if r['group']==group and r['hour']==hour];summaries.append({'group':group,'hour':hour,**summarize(rows),'batches':[{'batch':b,**summarize([r for r in rows if r['batch']==b])} for b in sorted({r['batch'] for r in rows})]})
 report={'workers':32,'queries':len(allrows),'wall_seconds_this_run':time.monotonic()-started,'wall_seconds_total':previous_wall+time.monotonic()-started,'max_batches':4,'groups':summaries,'scope':'Local application flow, loaded GTFS, no outbound pedestrian requests; external_required is censored, not failure or measured first-route latency.'}
 (OUT/'latency-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('DONE',len(allrows),flush=True)
if __name__=='__main__':main()
