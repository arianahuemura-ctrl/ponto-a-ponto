"""Diagnostic replay of successful queries not served by the staged reader.
Not an additional latency batch; identifies the source of the first visible route.
"""
import json,time,signal,multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor,as_completed
import sample_first_route as bench
from transit.sptrans import alternatives,staged_adapter,graph,store
from django.core.cache import cache
from datetime import datetime
from zoneinfo import ZoneInfo

def init():
 bench.init_worker()
 global SOURCES
 SOURCES={}
 def wrap(function,label):
  def run(*args,**kwargs):
   stream=function(*args,**kwargs)
   try:
    for event in stream:
     for journey in event['journeys']:SOURCES.setdefault(journey['id'],set()).add(label)
     yield event
   finally:stream.close()
  return run
 staged_adapter.progressive=wrap(staged_adapter.progressive,'staged')
 alternatives._bus_progressive=wrap(alternatives._bus_progressive,'legacy_connections')
 alternatives._raptor_progressive=wrap(alternatives._raptor_progressive,'raptor')

def run(task):
 SOURCES.clear();cache.clear();db=graph.readonly(store.database_path());stream=None;result={k:task[k] for k in ['origin','destination','group','hour']}
 signal.setitimer(signal.ITIMER_REAL,30)
 try:
  now=datetime(2026,11,3,task['hour'],tzinfo=ZoneInfo('America/Sao_Paulo'))
  stream=alternatives.progressive(db,bench.STOPS[task['origin']],bench.STOPS[task['destination']],4,now,refresh=True)
  for event in stream:
   if event['journeys']:
    first=event['journeys'][0]
    result.update(state='first_route',sources=sorted(SOURCES.get(first['id'],{'walk' if first.get('mode')=='walk' else 'unknown'})),cost=first.get('transfer_cost'),lines=[l['code'] for l in first.get('legs',[])],journey_id=first['id']);break
  else:result['state']='no_route_completed'
 except bench.ExternalRequired:result['state']='external_required'
 except bench.BudgetExceeded:result['state']='timeout_30s'
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  if stream is not None:stream.close()
  db.close()
 return result
if __name__=='__main__':
 rows=[json.loads(l) for l in (bench.OUT/'latency-results.jsonl').read_text().splitlines()]
 targets=[r for r in rows if r['flow']['state']=='first_route' and r['flow'].get('planner')!='walk' and r['prepared']['state']!='first_route']
 out=[]
 with ProcessPoolExecutor(max_workers=32,mp_context=mp.get_context('fork'),initializer=init) as pool:
  for f in as_completed([pool.submit(run,r) for r in targets]):out.append(f.result())
 (bench.OUT/'source-attribution.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 from collections import Counter
 print('targets',len(targets),'results',dict(Counter((r['state'],','.join(r.get('sources',[]))) for r in out)))
