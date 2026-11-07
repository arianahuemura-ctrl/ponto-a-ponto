"""Diagnóstico local: executar pelo manage.py shell, sem expor credenciais."""
import json
import time
from pathlib import Path
from collections import defaultdict
from unittest.mock import patch
from contextlib import ExitStack
from django.test import RequestFactory
from transit.sptrans import views, walking, planner, materialized_adapter, connection_planner, client, store

results=[]
for geographic in (False,True):
    times=defaultdict(float);counts=defaultdict(int);errors=defaultdict(int);stack=[]
    def measured(name,fn):
        def call(*args,**kwargs):
            start=time.perf_counter();frame=[0];stack.append(frame)
            try:return fn(*args,**kwargs)
            except Exception:
                errors[name]+=1;raise
            finally:
                elapsed=time.perf_counter()-start;stack.pop()
                times[name]+=elapsed-frame[0];counts[name]+=1
                if stack:stack[-1][0]+=elapsed
        return call
    params={'origin':'260016857','destination':'610006081','max_transfers':2,'refresh':1}
    if geographic:
        with store.connection() as db:
            for prefix,sid in [('from',params['origin']),('to',params['destination'])]:
                point=store.get_stop(db,sid);params[prefix+'_lat']=point['lat'];params[prefix+'_lon']=point['lon']
    with ExitStack() as scope:
        for obj,method,label in [(walking,'route','caminhadas'),(planner,'journeys','raptor'),(materialized_adapter,'prepare','leitura_conexoes'),(connection_planner.Evaluator,'evaluate','avaliacao_temporal'),(client.OlhoVivo,'_request','rede_sptrans')]:
            scope.enter_context(patch.object(obj,method,measured(label,getattr(obj,method))))
        start=time.perf_counter();first=None;last={};chunks=0
        for chunk in views.stream_board(RequestFactory().get('/api/sptrans/board',params)).streaming_content:
            last=json.loads(chunk);chunks+=1
            if first is None and last.get('journeys'):first=time.perf_counter()-start
        total=time.perf_counter()-start
    result={'geographic':geographic,'query':params,'total_s':total,'first_s':first,'exclusive_s':dict(times),'calls':dict(counts),'errors':dict(errors),'other_s':total-sum(times.values()),'planner':last.get('planner'),'routes':len(last.get('journeys',[])),'limited':last.get('search_limited'),'fallback':last.get('planner_fallback'),'warning':last.get('warning'),'chunks':chunks}
    results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
Path('/tmp/pap-planner-diagnosis.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
