"""Paired rerun of the original 3264 scenarios; no public provider load."""
import json,time,signal,multiprocessing as mp,threading
from concurrent.futures import ProcessPoolExecutor,as_completed,ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import sample_first_route as base
from transit.sptrans import alternatives,staged_adapter,store,graph,planner,walking,concurrent_sources
from transit.sptrans.journey_completion import has_short_bus_leg,normalize_walks
from django.core.cache import cache
OUT=base.ROOT/'artifacts/benchmarks/async-comparison-20261101';OUT.mkdir(exist_ok=True)

def init():
 global POINTS,ATTEMPTS,LOCK
 source=store.database_path();st=source.stat();POINTS,_,_=planner._network(str(source),st.st_mtime_ns,st.st_size,True)
 ATTEMPTS=[];LOCK=threading.Lock()
 def external(*args,**kwargs):
  with LOCK:ATTEMPTS.append(time.monotonic())
  raise base.ExternalRequired()
 walking.route=external
 import socket
 socket.socket.connect=external
 def timeout(*args):raise base.BudgetExceeded()
 signal.signal(signal.SIGALRM,timeout)

def measure(task):
 ATTEMPTS.clear();cache.clear();a,b=POINTS[task['origin']],POINTS[task['destination']]
 now=datetime(2026,11,3,task['hour'],tzinfo=ZoneInfo('America/Sao_Paulo'))
 result={k:task[k] for k in ['group','hour','origin','destination','batch']};result['departure']=now.isoformat()
 def run(prepared=False):
  ATTEMPTS.clear();db=graph.readonly(store.database_path());stream=None;events=0;last={};start=time.monotonic()
  signal.setitimer(signal.ITIMER_REAL,30)
  try:
   stream=staged_adapter.progressive(db,a,b,4,now) if prepared else alternatives.progressive(db,a,b,4,now,refresh=True)
   for event in stream:
    events+=1;last=event;journeys=event['journeys']
    if prepared:journeys=[normalize_walks(j) for j in journeys if not has_short_bus_leg(j)]
    if journeys:
     answer={'state':'first_route','first_route_seconds':time.monotonic()-start,'planner':event.get('planner'),'cost':journeys[0].get('transfer_cost'),'duration_minutes':journeys[0].get('duration_minutes')};break
   else:answer={'state':'external_required' if ATTEMPTS else 'no_route_completed','search_limited':last.get('search_limited',False)}
  except base.ExternalRequired:answer={'state':'external_required'}
  except base.BudgetExceeded:answer={'state':'timeout_30s'}
  except Exception as e:answer={'state':'error','error':type(e).__name__+': '+str(e)}
  finally:
   signal.setitimer(signal.ITIMER_REAL,0)
   if stream is not None:stream.close()
   db.close()
  answer.update(elapsed_seconds=time.monotonic()-start,events=events,external_attempts_before_return=len(ATTEMPTS),failed_sources=last.get('failed_sources',[]),busy_sources=last.get('busy_sources',[]))
  return answer
 result['flow']=run()
 # Drain cancelled producers OUTSIDE first-route timing, so one sample cannot
 # contaminate the next one's cache, external-call accounting or CPU workload.
 t=time.monotonic()
 concurrent_sources.PREPARED.shutdown(wait=True,cancel_futures=True)
 concurrent_sources.BACKGROUND.shutdown(wait=True,cancel_futures=True)
 result['producer_drain_seconds']=time.monotonic()-t
 concurrent_sources.PREPARED=ThreadPoolExecutor(max_workers=4,thread_name_prefix='pap-prepared')
 concurrent_sources.BACKGROUND=ThreadPoolExecutor(max_workers=8,thread_name_prefix='pap-routing')
 result['prepared']=run(True)
 return result

def main():
 old=[json.loads(l) for l in (base.OUT/'latency-results.jsonl').read_text().splitlines()]
 key=lambda r:(r['group'],r['hour'],r['origin'],r['destination'])
 target=OUT/'latency-results.jsonl';done={key(r):r for r in [json.loads(l) for l in target.read_text().splitlines()]} if target.exists() else {}
 order=list(json.loads((base.OUT/'sample-pairs.json').read_text()))
 tasks=sorted(old,key=lambda r:(r['batch'],order.index(r['group']),[8,14,2].index(r['hour']),r['origin'],r['destination']))
 start=time.monotonic()
 with ProcessPoolExecutor(max_workers=32,mp_context=mp.get_context('fork'),initializer=init) as pool,target.open('a',buffering=1) as output:
  pending={pool.submit(measure,t):t for t in tasks if key(t) not in done}
  for future in as_completed(pending):
   row=future.result();done[key(row)]=row;output.write(json.dumps(row,ensure_ascii=False)+'\n')
   if len(done)%32==0:print('completed',len(done),'seconds',round(time.monotonic()-start,1),flush=True)
 assert set(done)=={key(r) for r in old}
 (OUT/'run.json').write_text(json.dumps({'queries':len(done),'workers':32,'wall_seconds_this_run':time.monotonic()-start,'scope':'Paired original scenarios; local flow, external attempts blocked and tracked across threads; producer drain excluded from first-route timing'},indent=2)+'\n')
 print('DONE',len(done),flush=True)
if __name__=='__main__':main()
