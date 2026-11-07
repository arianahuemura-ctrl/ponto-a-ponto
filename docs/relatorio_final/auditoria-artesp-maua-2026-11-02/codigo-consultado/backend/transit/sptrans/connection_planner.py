"""Candidatos estruturais 16/8/4 -> estimativas temporais -> cinco melhores operacionais.

Sem reconstrução do grafo estático, HTTP implícito no pré-processamento ou credenciais salvas.
O único limite de poda é a caminhada obrigatória: o histórico não é um limite seguro.
"""
import json
from mbm import routing_config as config
import math
import sqlite3
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from . import graph, catalog, costs, realtime, tracking, planner
from .client import APIError

INTERMEDIATE_WAIT_SECONDS = config.INTERMEDIATE_WAIT_SECONDS
RESULT_LIMIT = config.RESULT_LIMIT
INITIAL_REFINEMENT = config.INITIAL_REFINEMENT


class Evaluator:
    def __init__(self,db,now,operational=True,provider=None):
        self.db=db;self.now=now;self.start=now.timestamp();self.horizon=self.start+planner.HORIZON_SECONDS
        self.costs=costs.Costs(db,now.tzinfo);self.edges={};self.schedules={};self.stops={}
        self.predictions={};self.operational=operational;self.provider=provider or realtime.add_predictions
        self.warnings=set();self.api_lookups=0;self.api_available=True
        self.api_deadline=time.monotonic()+float(getattr(settings,'SPTRANS_CONNECTION_API_BUDGET',20))

    def stop(self,sid):
        if sid not in self.stops:
            self.stops[sid]=dict(self.db.execute('SELECT * FROM graph_stop WHERE id=?',(sid,)).fetchone())
        return self.stops[sid]

    def edge(self,eid):
        if eid not in self.edges:
            self.edges[eid]=dict(self.db.execute('''SELECT e.*,p.route_id,p.code,p.direction,p.headsign
                FROM ride_edge e JOIN pattern p ON p.id=e.pattern_id WHERE e.id=?''',(eid,)).fetchone())
        return self.edges[eid]

    def schedule(self,edge):
        pid=edge['pattern_id']
        if pid not in self.schedules:
            schedules=[];midnight=self.now.replace(hour=0,minute=0,second=0,microsecond=0)
            for row in self.db.execute('SELECT * FROM timetable WHERE pattern_id=?',(pid,)):
                tt=json.loads(row['times']);freq=json.loads(row['frequencies']);windows=[]
                latest=max([t[2] for t in tt]+[f[1] for f in freq])
                for delta in range(-math.ceil(latest/86400),2):
                    day=midnight+timedelta(days=delta)
                    if not graph.store.service_active(self.db,row['service_id'],day.date()):continue
                    base=day.timestamp()
                    windows.extend((base+a,base+b,h,exact) for a,b,h,exact in freq)
                    if not freq:
                        t=base+tt[0][2];windows.append((t,t,0,True))
                if windows:schedules.append((row['trip_id'],tt,windows,any(not f[3] for f in freq)))
            self.schedules[pid]=schedules
        return self.schedules[pid]

    def predictions_for(self,edge):
        key=(edge['code'],edge['headsign'],edge['origin'])
        if key not in self.predictions:
            row={'code':edge['code'],'headsign':edge['headsign'],'arrivals':[]}
            if self.operational and self.api_available and time.monotonic()<self.api_deadline:
                self.api_lookups+=1
                try:self.provider(row,self.stop(edge['origin']))
                except APIError:
                    self.api_available=False
                    self.warnings.add('Olho Vivo indisponível; programação mantida.')
                except (ValueError,KeyError,TypeError):
                    self.warnings.add('Resposta operacional inválida; programação mantida.')
            elif self.operational:
                self.warnings.add('Consulta operacional limitada ou indisponível; programação mantida.')
            arrivals=tracking.reachable_arrivals(row.get('arrivals',[]),self.now)
            self.predictions[key]=arrivals
            if row.get('api_line') is not None and row.get('api_stop') is not None:
                self.db.execute('INSERT OR REPLACE INTO connection_operational_mappings VALUES (?,?,?,?,?)',
                    (edge['pattern_id'],edge['origin'],row['api_line'],row['api_stop'],self.now.isoformat()))
        return self.predictions[key]

    def choices(self,edge,ready,refine):
        scheduled=[]
        for tid,tt,windows,approx in self.schedule(edge):
            depart=planner.next_departure({'times':tt},edge['boarding_index'],ready,windows)
            if not math.isfinite(depart) or depart>self.horizon:continue
            duration,source=self.costs.ride(edge,tt,depart)
            scheduled.append({'trip_id':tid,'departure_s':depart,'arrival_s':depart+duration,
                              'frequency_estimate':approx,'timing_source':'programme','cost_detail':source,'tt':tt})
        arrivals=self.predictions_for(edge) if refine else []
        reachable=[a for a in arrivals if datetime.fromisoformat(a['arrival_at']).timestamp()>=ready]
        if reachable and self.schedule(edge):
            options=[]
            templates=scheduled or [{'trip_id':tid,'tt':tt,'departure_s':ready,'frequency_estimate':approx}
                for tid,tt,windows,approx in self.schedule(edge)]
            for a in reachable:
                depart=datetime.fromisoformat(a['arrival_at']).timestamp()
                # Uma previsão identifica linha/veículo, não uma viagem GTFS. Use um
                # modelo ativo para a duração restante, mantendo explicitamente a procedência.
                template=min(templates,key=lambda c:abs(c['departure_s']-depart))
                duration,source=self.costs.ride(edge,template['tt'],depart)
                options.append({**template,'departure_s':depart,'arrival_s':depart+duration,
                                'timing_source':'olho_vivo','prediction':a,'cost_detail':source})
            last=max(datetime.fromisoformat(a['arrival_at']).timestamp() for a in arrivals)
            options.extend(self._later_choices(edge,max(ready,last+1)))
            return [c for c in options if c['arrival_s']<=self.horizon]
        if arrivals:
            # Veículos já perdidos não podem reaparecer como estimativas programadas anteriores.
            # Mantenha somente partidas posteriores à última previsão observada e identifique a alternativa programada.
            last=max(datetime.fromisoformat(a['arrival_at']).timestamp() for a in arrivals)
            scheduled=self._later_choices(edge,max(ready,last+1))
        return [c for c in scheduled if c['arrival_s']<=self.horizon]

    def _later_choices(self,edge,ready):
        return self.choices(edge,ready,False)

    def preliminary(self,candidate,access=0,egress=0):
        clock=self.start+access;previous=None;coverage={'historical_segments':0,'scheduled_segments':0}
        for eid in json.loads(candidate['edge_ids']):
            edge=self.edge(eid)
            if previous:
                clock+=self.walk(previous,edge)['seconds']+INTERMEDIATE_WAIT_SECONDS
            valid=self.schedule(edge)
            if not valid:return math.inf
            # A validade temporal do serviço é conferida no refinamento. Não invente partidas.
            tt=valid[0][1]
            duration,source=self.costs.ride(edge,tt,clock)
            clock+=duration
            for k in coverage:coverage[k]+=source[k]
            previous=edge
        return clock+egress-self.start

    def walk(self,previous,edge):
        if previous['destination']==edge['origin']:
            return {'seconds':0,'distance_meters':0,'geometry':None}
        row=self.db.execute("SELECT * FROM walk_edge WHERE origin=? AND destination=? AND status='verified'",
                            (previous['destination'],edge['origin'])).fetchone()
        if row is None:raise ValueError('Conexão caminhável não verificada.')
        return dict(row)

    def evaluate(self,candidate,access=0,egress=0,ceiling=math.inf):
        edges=[self.edge(e) for e in json.loads(candidate['edge_ids'])]
        mandatory=access+egress+candidate['walk_seconds']+planner.TRANSFER_SECONDS*(len(edges)-1)
        if mandatory>ceiling:return None,'pruned'
        labels=[(self.start+access,[],[])];prefix_walk=0
        for index,edge in enumerate(edges):
            next_labels=[]
            walk=self.walk(edges[index-1],edge) if index else {'seconds':0,'distance_meters':0,'geometry':None}
            prefix_walk+=walk['seconds']
            remaining=egress+candidate['walk_seconds']-prefix_walk+planner.TRANSFER_SECONDS*(len(edges)-index-1)
            for reached,legs,walks in labels:
                ready=reached+walk['seconds']+(planner.TRANSFER_SECONDS if index else 0)
                if ready-self.start+remaining>ceiling:continue
                for choice in self.choices(edge,ready,True):
                    if choice['arrival_s']-self.start+remaining>ceiling:continue
                    leg={**edge,**{k:v for k,v in choice.items() if k!='tt'},
                         'wait_seconds':choice['departure_s']-ready,
                         'ride_seconds':choice['arrival_s']-choice['departure_s'],
                         'transfer_buffer_seconds':planner.TRANSFER_SECONDS if index else 0}
                    steps=walks+([{**walk,'before_leg':index}] if walk['distance_meters'] else [])
                    next_labels.append((choice['arrival_s'],legs+[leg],steps))
            if not next_labels:return None,'infeasible_or_pruned'
            # Preserve rótulos de chegada distintos: partidas posteriores podem ter comportamento diferente
            # com um perfil histórico não FIFO. Elimine apenas estados de chegada exatamente iguais.
            by_arrival={}
            for label in next_labels:by_arrival.setdefault(label[0],label)
            labels=list(by_arrival.values())
        reached,legs,walks=min(labels,key=lambda entry:entry[0])
        duration=reached+egress-self.start
        result={'id':candidate['id'],'transfers':candidate['boardings']-1,'duration_seconds':duration,
            'arrival':datetime.fromtimestamp(reached+egress,self.now.tzinfo).isoformat(),
            'access_seconds':access,'egress_seconds':egress,'legs':legs,'walks':walks,
            'walking_seconds':access+candidate['walk_seconds']+egress,
            'distance_meters':candidate['distance_meters'],'walk_meters':candidate['walk_meters'],
            'ride_seconds':sum(l['ride_seconds'] for l in legs),'wait_seconds':sum(l['wait_seconds'] for l in legs),
            'transfer_walk_seconds':candidate['walk_seconds'],
            'transfer_buffer_seconds':planner.TRANSFER_SECONDS*(len(legs)-1),
            'cost_source':'olho_vivo + historical/GTFS' if any(l['timing_source']=='olho_vivo' for l in legs) else 'historical/GTFS',
            'estimated':True}
        return result,'evaluated'


def progressive(origin,destination,now=None,path=None,access_seconds=0,egress_seconds=0,
                operational=True,provider=None,max_transfers=2):
    """Lê candidatos persistidos; refina dez primeiro e depois todos os demais não podados."""
    now=now or timezone.localtime()
    if timezone.is_naive(now):raise ValueError('Informe data e hora com fuso.')
    now=timezone.localtime(now)
    if any(not math.isfinite(x) or x<0 for x in (access_seconds,egress_seconds)):
        raise ValueError('Caminhada inválida.')
    path=path or graph.graph_path()
    with graph.connection(path):pass
    with sqlite3.connect(path,timeout=30) as db:
        db.row_factory=sqlite3.Row
        candidates,meta=catalog.candidates(db,origin,destination)
        candidates=[c for c in candidates if c['boardings']<=max_transfers+1]
        engine=Evaluator(db,now,operational,provider)
        candidates.sort(key=lambda c:(engine.preliminary(c,access_seconds,egress_seconds),c['distance_meters'],c['id']))
        best=[];counts={'evaluated':0,'pruned':0,'infeasible_or_pruned':0};total=len(candidates)
        base={'candidate_count':total,'catalog':meta,'queried_at':now.isoformat(),'optimal_globally':False,
              'selection_heuristic':'distance_16_8_4','initial_refinement':INITIAL_REFINEMENT,
              'walking_coverage':json.loads(db.execute('SELECT value FROM graph_meta').fetchone()[0]).get('walk_status_counts',{})}
        yield {**base,'journeys':[],'complete':False,'processed':0}
        # O limite do lote é informativo, não um corte inseguro no décimo candidato.
        for index,candidate in enumerate(candidates):
            ceiling=best[-1]['duration_seconds'] if len(best)==RESULT_LIMIT else math.inf
            result,state=engine.evaluate(candidate,access_seconds,egress_seconds,ceiling)
            counts[state]+=1
            if result:
                best.append(result);best.sort(key=lambda r:(r['duration_seconds'],r['transfers'],r['walking_seconds'],r['id']))
                best=best[:RESULT_LIMIT]
            db.commit()  # Apenas cache de correspondências, nunca a topologia do grafo.
            yield {**base,'journeys':best[:],'complete':False,'processed':index+1,'counts':dict(counts),
                   'refinement_round':1 if index<INITIAL_REFINEMENT else 2,
                   'api_lookups':engine.api_lookups,'warnings':sorted(engine.warnings)}
        yield {**base,'journeys':best,'complete':True,'processed':total,'counts':counts,
               'api_lookups':engine.api_lookups,'warnings':sorted(engine.warnings)}


def query(*args,**kwargs):
    result=None
    for result in progressive(*args,**kwargs):pass
    return result
