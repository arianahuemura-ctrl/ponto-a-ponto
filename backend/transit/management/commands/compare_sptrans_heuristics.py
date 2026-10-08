"""Experimento somente leitura; não publica candidatos no banco municipal."""
import json
import time
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import city_connections, graph, materialized_adapter


def temporal(paths,db,now):
    engine=materialized_adapter.Evaluator(db,now,operational=False)
    durations=[]
    for i,path in enumerate(paths):
        buses=[x for x in path['trechos'] if x['modo']=='onibus']
        walks=[x for x in path['trechos'][:-1] if x['modo']=='caminhada']
        ids=[]
        for leg in buses:
            row=db.execute('SELECT id FROM ride_edge WHERE pattern_id=? AND boarding_index=? AND alighting_index=?',
                           (leg['padrao_id'],leg['embarque_indice'],leg['desembarque_indice'])).fetchone()
            if row is None:raise ValueError('Índice temporal incompatível')
            ids.append(row[0])
        for w in walks:
            engine.walks[w['origem'],w['destino']]={'seconds':w['tempo_s'],'distance_meters':w['distancia_m'],'geometry':None}
        last=path['trechos'][-1]
        egress=last['tempo_s'] if last['modo']=='caminhada' else 0
        candidate={'id':str(i),'edge_ids':json.dumps(ids),'boardings':len(ids),
                   'walk_seconds':sum(w['tempo_s'] for w in walks),'walk_meters':sum(w['distancia_m'] for w in walks),
                   'distance_meters':path['distancia_m']}
        result,_=engine.evaluate(candidate,egress=egress)
        if result:durations.append(result['duration_seconds'])
    return {'valid':len(durations),'best_seconds':min(durations) if durations else None}


class Command(BaseCommand):
    help='Compara preparação padrão e heurísticas experimentais sem alterar artefatos ou consultar APIs.'
    def add_arguments(self,p):
        p.add_argument('--pairs-file',required=True)
        p.add_argument('--source')
        p.add_argument('--graph')
        p.add_argument('--at',required=True,help='Instante ISO com fuso, igual nos dois modos.')
        p.add_argument('--seconds',type=float,default=60)
    def handle(self,*args,**o):
        now=datetime.fromisoformat(o['at'])
        if now.utcoffset() is None:raise CommandError('--at requer fuso horário')
        with open(o['pairs_file']) as f:pairs=json.load(f)
        results=[]
        with graph.connection(o['graph']) as index:
            for i,(a,b) in enumerate(pairs):
                row={'origin':a,'destination':b}; paths={}
                for mode in (['reference','experimental'] if i%2==0 else ['experimental','reference']):
                    started=time.perf_counter()
                    result=city_connections.structural_query(a,b,path=o['source'],seconds=o['seconds'],offline=True,experimental=mode=='experimental')
                    elapsed=time.perf_counter()-started
                    paths[mode]=result['trajetos']
                    row[mode]={'seconds':elapsed,'complete':result['complete'],'categories':result['categories'],
                               'convergence':result.get('convergence_stats'),'candidates':len(result['trajetos']),**temporal(result['trajetos'],index,now)}
                signature=lambda p:json.dumps(p,sort_keys=True)
                row['reference_candidates_removed']=len(set(map(signature,paths['reference']))-set(map(signature,paths['experimental'])))
                row['lost_structural_connection']=bool(paths['reference']) and not paths['experimental']
                results.append(row)
        self.stdout.write(json.dumps({'at':now.isoformat(),'operational':False,'initial_walk':False,
            'note':'Amostra exploratória, uma execução por modo, caches do SO não reiniciados. Custo temporal GTFS; não mede previsão operacional.',
            'results':results},ensure_ascii=False,indent=2))
