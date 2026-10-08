"""Alternativas porta a porta com acessos pedestres verificados nas duas extremidades."""
from datetime import timedelta
import hashlib
import json
import math
import time
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from . import store, planner, walking, directions

WALK_LIMIT = walking.WALK_LIMIT

def geographic_anchor(anchor):
    return anchor['id'].startswith('address-') or anchor['id']=='passenger-location' or anchor.get('useLocation',False)

def access_points(db, anchor, outgoing, budget=None, optimistic=False, endpoint_selection=False):
    choices=[]; incomplete=False
    lat_margin=WALK_LIMIT/110000
    lon_margin=WALK_LIMIT/(110000*max(.01,math.cos(math.radians(anchor['lat']))))
    rows=db.execute("SELECT s.* FROM stops s WHERE stop_lat BETWEEN ? AND ? AND stop_lon BETWEEN ? AND ? AND EXISTS (SELECT 1 FROM stop_times st JOIN trips t USING(trip_id) JOIN routes r USING(route_id) WHERE st.stop_id=s.stop_id AND r.route_type='3')",
                    (anchor['lat']-lat_margin,anchor['lat']+lat_margin,anchor['lon']-lon_margin,anchor['lon']+lon_margin))
    ordered=sorted(rows,key=lambda r:(directions.distance((anchor['lat'],anchor['lon']),(r['stop_lat'],r['stop_lon'])),r['stop_id']))
    if endpoint_selection:
        # Preserve o ponto escolhido, mas permita caminhar até outro sentido.
        if not geographic_anchor(anchor):
            ordered.sort(key=lambda r:r['stop_id'] != anchor['id'])
        ordered=ordered[:3]
    for row in ordered:
        point=store.stop(row)
        gap=directions.distance((anchor['lat'],anchor['lon']),(point['lat'],point['lon']))
        if gap>WALK_LIMIT:continue
        if gap<0.01:
            choices.append((point,None));continue
        if optimistic:
            choices.append((point,{'pending':True,'origin':anchor if outgoing else point,'destination':point if outgoing else anchor,
                                   'distance_meters':gap,'accessType':'boarding' if outgoing else 'destination'}))
            continue
        if budget is not None:
            if budget['checks']>=64 or time.monotonic()>=budget['deadline']:
                budget['limited']=True;incomplete=True;continue
            budget['checks']+=1
        path=walking.route(anchor,point,wait_for_slot=True) if outgoing else walking.route(point,anchor,wait_for_slot=True)
        if not path.get('available'):
            incomplete=True;continue
        if path['distance_meters']<=WALK_LIMIT:
            choices.append((point,{**path,'accessType':'boarding' if outgoing else 'destination'}))
    return choices,incomplete

def distinct_routes(journeys):
    """Paradas próximas para a mesma sequência de linhas representam uma única escolha do passageiro."""
    groups={}
    for journey in journeys:
        signature=tuple((leg.get('route_id',leg['code']),leg.get('direction_id',leg['trip_id']),leg['headsign']) for leg in journey['legs'])
        rank=lambda route:(route['duration_minutes'],route['walking_meters'],route['id'])
        if signature not in groups or rank(journey)<rank(groups[signature]):
            groups[signature]=journey
    # Um ônibus adicional no final é dispensável quando uma rota já verificada com
    # os mesmos serviços anteriores chega antes e não exige mais caminhada.
    kept=[]
    for signature,route in groups.items():
        dominated=any(bool(prefix) and len(prefix)<len(signature) and signature[:len(prefix)]==prefix
                      and other['duration_minutes']<=route['duration_minutes']
                      and other['walking_meters']<=route['walking_meters']
                      for prefix,other in groups.items())
        if not dominated:kept.append(route)
    return sorted(kept,key=lambda r:(r['duration_minutes'],r['transfers'],r['walking_meters'],r['id']))


def earlier_alighting(db, journey, ends):
    """Verifica passagens anteriores do último ônibus sem alterar os trechos precedentes."""
    last=journey['legs'][-1]
    if 'boarding_index' not in last:return journey,None
    path=store.database_path();stat=path.stat()
    stops,trips,_=planner._network(str(path),stat.st_mtime_ns,stat.st_size)
    times=trips[last['trip_id']]['times']
    a,b=last['boarding_index'],last['alighting_index']
    candidates=[]
    for index in range(a+1,b+1):
        sid=times[index][0]
        if sid not in ends:continue
        point,walk=ends[sid]
        saved=(times[b][1]-times[index][1])/60
        minutes=walk['distance_meters']/walking.WALK_METERS_PER_MINUTE if walk else 0
        candidates.append((journey['duration_minutes']-saved+minutes,index,saved,point,walk))
    if not candidates:return journey,None
    _,index,saved,point,walk=min(candidates,key=lambda entry:(entry[0],entry[1]))
    if index==b:return journey,walk
    arrival=(timezone.datetime.fromisoformat(last['arrival'])-timedelta(minutes=saved)).isoformat()
    leg={**last,'destination':point,'alighting_index':index,'arrival':arrival,
         'ride_minutes':round(last['ride_minutes']-saved,1),
         'geometry':planner.leg_shape(last['trip_id'],a,index),
         'stops':[stops[t[0]] for t in times[a:index+1]]}
    return {**journey,'legs':[*journey['legs'][:-1],leg],'arrival':arrival,
            'duration_minutes':round(journey['duration_minutes']-saved,1)},walk


def _raptor_progressive(db, origin, destination, max_transfers=2, now=None, *, refresh=False):
    now=now or timezone.localtime()
    stat=store.database_path().stat()
    key='pap.alternatives.v18:'+hashlib.sha256(json.dumps([origin,destination,max_transfers,int(now.timestamp()//30),stat.st_mtime_ns,stat.st_size],sort_keys=True).encode()).hexdigest()
    cached=None if refresh else cache.get(key)
    if cached is not None and not cached.get("search_limited"):
        yield {**cached,"complete":True}
        return
    # Retorne o itinerário entre as paradas selecionadas antes de consultar percursos pedestres.
    initial=list(cached["journeys"]) if cached else []
    context={}
    if not geographic_anchor(origin) and not geographic_anchor(destination):
        for trip in planner.journeys(db,origin['id'],destination['id'],max_transfers,now=now,context=context,preserve_alternatives=True):
            fingerprint='|'.join(f"{leg['trip_id']}:{leg['origin']['id']}:{leg['destination']['id']}" for leg in trip['legs'])
            initial.append({**trip,'id':fingerprint,'walking_minutes':0,'walking_meters':0,'walks':[]})
    yield {'journeys':distinct_routes(initial),'walking_incomplete':False,'complete':False}
    budget={'checks':0,'deadline':time.monotonic()+30,'limited':False}
    starts,missing_start=access_points(db,origin,True,optimistic=True,endpoint_selection=True)
    ends,missing_end=access_points(db,destination,False,optimistic=True,endpoint_selection=True)
    found={j['id']:j for j in initial}
    starts_by_id={point['id']:(point,foot) for point,foot in starts}
    ends_by_id={point['id']:(point,foot) for point,foot in ends}
    access_times={sid:(foot['distance_meters']/walking.WALK_METERS_PER_SECOND if foot else 0) for sid,(_,foot) in starts_by_id.items()}
    end_times={sid:(foot['distance_meters']/walking.WALK_METERS_PER_SECOND if foot else 0) for sid,(_,foot) in ends_by_id.items()}
    transfer_paths={}
    incomplete=missing_start or missing_end
    limited=budget['limited']
    checked=0
    deadline=budget['deadline']
    def remember(trips):
        for trip in trips:
            walks=trip['transfer_walks']
            if any((w['origin']['id'],w['destination']['id']) not in transfer_paths for w in walks):continue
            first,last=trip['legs'][0],trip['legs'][-1]
            access=starts_by_id[first['origin']['id']][1]
            egress=ends_by_id[trip.get('goal_stop_id',last['destination']['id'])][1]
            if any(p and p.get('pending') for p in (access,egress)):continue
            paths=[p for p in [access,*[{**w,'accessType':'destination'} if w.get('before_leg')==len(trip['legs']) else w for w in walks],egress] if p]
            meters=sum(p['distance_meters'] for p in paths)
            fingerprint='|'.join(f"{l['trip_id']}:{l['origin']['id']}:{l['destination']['id']}" for l in trip['legs'])
            found[fingerprint]={**trip,'id':fingerprint,'walking_meters':round(meters),
                                'walking_minutes':round(meters/walking.WALK_METERS_PER_MINUTE,1),'walks':paths}
    if starts and ends:
        options=dict(max_transfers=max_transfers,now=now,preserve_alternatives=True,transfer_paths=transfer_paths,context=context,
                     access_times=access_times,end_times=end_times)
        # Uma busca limitada com múltiplas origens/destinos, em vez de consultar cada par.
        for iteration in range(12):
            if not access_times or not end_times:break
            trips=planner.journeys(db,starts[0][0]['id'],ends[0][0]['id'],**options)
            remember(trips)
            yield {'journeys':distinct_routes(found.values()),'walking_incomplete':incomplete,'complete':False}
            pending={}
            for trip in trips:
                for kind,sid,mapping in [('start',trip['legs'][0]['origin']['id'],starts_by_id),('end',trip.get('goal_stop_id',trip['legs'][-1]['destination']['id']),ends_by_id)]:
                    foot=mapping[sid][1]
                    if foot and foot.get('pending'):pending[(kind,sid)]=(foot['origin'],foot['destination'])
                for w in trip['transfer_walks']:
                    pair=(w['origin']['id'],w['destination']['id'])
                    if pair not in transfer_paths:pending[('transfer',pair)]=(w['origin'],w['destination'])
            if not pending:break
            for (kind,identifier),(a,b) in pending.items():
                if checked>=32 or budget['checks']>=64 or time.monotonic()>=deadline:
                    limited=True;break
                foot=walking.route(a,b,wait_for_slot=True);checked+=1;budget['checks']+=1
                if not foot.get('available'):incomplete=True
                valid=foot.get('available') and foot['distance_meters']<=WALK_LIMIT
                if kind=='transfer':transfer_paths[identifier]=foot if valid else None
                else:
                    mapping,times=(starts_by_id,access_times) if kind=='start' else (ends_by_id,end_times)
                    if valid:
                        mapping[identifier]=(mapping[identifier][0],{**foot,'accessType':'boarding' if kind=='start' else 'destination'})
                        times[identifier]=foot['distance_meters']/walking.WALK_METERS_PER_SECOND
                    else:times.pop(identifier,None)
            if limited:break
        else:limited=True
        if limited:
            # Nunca exiba percursos cujas conexões pedestres ainda não foram verificadas.
            for times,mapping in ((access_times,starts_by_id),(end_times,ends_by_id)):
                for sid in list(times):
                    if mapping[sid][1] and mapping[sid][1].get('pending'):times.pop(sid)
            if access_times and end_times:remember(planner.journeys(db,starts[0][0]['id'],ends[0][0]['id'],known_transfers_only=True,**options))
    result={'journeys':distinct_routes(found.values()),'walking_incomplete':incomplete,
            'search_limited':limited,'optimal_within_limits':not limited and not incomplete,
            'search_limits':{'max_boardings':max_transfers+1,'max_validation_rounds':12,'max_transfer_walk_checks':32,'max_walk_checks':64,'soft_time_limit_seconds':30}}
    cache.set(key,result,30)
    yield {**result,'complete':True}

def _bus_progressive(db, origin, destination, max_transfers=2, now=None, *, refresh=False, allow_raptor=True):
    now=now or timezone.localtime()
    selected=getattr(settings,'SPTRANS_PLANNER','raptor')
    fallback_reason = None
    if selected=='connections' and max_transfers<=2:
        from . import connection_adapter
        context=connection_adapter.prepare(db,origin,destination)
        fallback_reason = (context or {}).get('unavailable_reason')
        if context and not fallback_reason:
            found=False
            for result in connection_adapter.progressive(db,origin,destination,min(max_transfers,1),now,context):
                found=bool(result['journeys'])
                # Um resultado final vazio do novo mecanismo não deve encerrar o fluxo HTTP
                # antes de o RAPTOR tentar sua busca mais abrangente.
                if not result['complete'] or found:
                    yield result
            if found:
                return
    if not allow_raptor:
        yield {'journeys': [], 'complete': True, 'planner': 'connections' if selected == 'connections' else 'walk', 'planner_fallback': None}
        return
    for result in _raptor_progressive(db,origin,destination,max_transfers,now,refresh=refresh):
        yield {**result,'planner':'raptor','planner_fallback':
            (fallback_reason or 'Conexões de até dois ônibus indisponíveis ou sem rotas válidas; usando o planejador por rodadas, inclusive para três ônibus.') if selected=='connections' else None}


def progressive(db, origin, destination, max_transfers=2, now=None, *, refresh=False):
    from .journey_completion import Completion, direct_walk, has_short_bus_leg, normalize_walks
    now = now or timezone.localtime()
    foot = direct_walk(origin, destination, now)
    # A revisão do desembarque examina a própria viagem, além dos pontos usados na busca inicial.
    completion = Completion(db, destination, origin=origin)
    for result in _bus_progressive(db, origin, destination, max_transfers, now, refresh=refresh,
                                   allow_raptor=foot is None or foot['walking_meters'] >= 1000):
        journeys = [normalize_walks(completion.improve(normalize_walks(journey))) for journey in result['journeys']]
        journeys = [journey for journey in journeys if not has_short_bus_leg(journey)]
        # A caminhada validada domina o ônibus quando chega antes e exige
        # no máximo a mesma distância a pé, sem nenhum embarque.
        if foot:
            journeys = [journey for journey in journeys if not (
                foot['duration_minutes'] <= journey['duration_minutes']
                and foot['walking_meters'] <= journey['walking_meters'])]
        if journeys:
            minimum=min(j['transfers'] for j in journeys)
            journeys=distinct_routes(j for j in journeys if j['transfers']==minimum)
            if result.get('planner')=='raptor':journeys=journeys[:3]
        yield {**result, 'journeys': sorted(journeys + ([foot] if foot else []),key=lambda j:j['duration_minutes'])}


def alternatives(db, origin, destination, max_transfers=2, now=None):
    result=None
    for result in progressive(db,origin,destination,max_transfers,now):pass
    return result
