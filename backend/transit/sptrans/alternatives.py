"""Alternativas porta a porta com acessos pedestres verificados nas duas extremidades."""
from datetime import timedelta
import hashlib
import json
import math
import time
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from . import store, planner, walking, directions, transfer_policy

WALK_LIMIT = walking.WALK_LIMIT
ENDPOINT_RADIUS_METERS = 200.0

def geographic_anchor(anchor):
    return anchor['id'].startswith('address-') or anchor['id']=='passenger-location' or anchor.get('useLocation',False)

def access_points(db, anchor, outgoing, budget=None, optimistic=False, endpoint_selection=False, include_rail=False):
    choices=[]; incomplete=False
    lat_margin=WALK_LIMIT/110000
    lon_margin=WALK_LIMIT/(110000*max(.01,math.cos(math.radians(anchor['lat']))))
    route_types="('1','2','3')" if include_rail else "('3')"
    rows=db.execute(f"SELECT s.* FROM stops s WHERE stop_lat BETWEEN ? AND ? AND stop_lon BETWEEN ? AND ? AND EXISTS (SELECT 1 FROM stop_times st JOIN trips t USING(trip_id) JOIN routes r USING(route_id) WHERE st.stop_id=s.stop_id AND r.route_type IN {route_types})",
                    (anchor['lat']-lat_margin,anchor['lat']+lat_margin,anchor['lon']-lon_margin,anchor['lon']+lon_margin))
    ranked=((directions.distance((anchor['lat'],anchor['lon']),(r['stop_lat'],r['stop_lon'])),r) for r in rows)
    ordered=sorted(((gap,row) for gap,row in ranked if gap<=WALK_LIMIT),key=lambda item:(item[0],item[1]['stop_id']))
    rail_stop_ids={r[0] for r in db.execute("SELECT DISTINCT st.stop_id FROM stop_times st JOIN trips t USING(trip_id) JOIN routes r USING(route_id) WHERE r.route_type IN ('1','2')")} if include_rail else set()
    if endpoint_selection:
        # Todas as paradas no raio; só busque as três mais próximas quando o raio estiver vazio.
        # A distância do percurso pedestre continua sendo validada antes de aceitar a viagem.
        nearby=[item for item in ordered if item[0]<=(WALK_LIMIT if item[1]['stop_id'] in rail_stop_ids else ENDPOINT_RADIUS_METERS)]
        ordered=nearby or ordered[:3]
    for gap,row in ordered:
        point=store.stop(row)
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
        key=(signature,journey.get('transfer_cost_units',3*max(0,len(journey['legs'])-1)))
        rank=lambda route:(route['duration_minutes'],route['walking_meters'],route['id'])
        if key not in groups or rank(journey)<rank(groups[key]):
            groups[key]=journey
    # Um ônibus adicional no final é dispensável quando uma rota já verificada com
    # os mesmos serviços anteriores chega antes e não exige mais caminhada.
    kept=[]
    for (signature,cost),route in groups.items():
        dominated=any(bool(prefix) and len(prefix)<len(signature) and signature[:len(prefix)]==prefix
                      and prefix_cost<=cost
                      and other['duration_minutes']<=route['duration_minutes']
                      and other['walking_meters']<=route['walking_meters']
                      for (prefix,prefix_cost),other in groups.items())
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


def _raptor_progressive(db, origin, destination, max_transfers=2, now=None, *, refresh=False, include_rail=False, weighted_transfers=False):
    now=now or timezone.localtime()
    stat=store.database_path().stat()
    key='pap.alternatives.v24:'+str(weighted_transfers)+':'+str(include_rail)+':'+hashlib.sha256(json.dumps([origin,destination,max_transfers,int(now.timestamp()//30),stat.st_mtime_ns,stat.st_size],sort_keys=True).encode()).hexdigest()
    cached=None if refresh else cache.get(key)
    if cached is not None and not cached.get("search_limited"):
        yield {**cached,"complete":True}
        return
    # Retorne o itinerário entre as paradas selecionadas antes de consultar percursos pedestres.
    initial=list(cached["journeys"]) if cached else []
    context={}
    transfer_paths={}
    if include_rail:
        from . import rail
        network=planner._network(str(store.database_path()),stat.st_mtime_ns,stat.st_size,True)
        transfer_paths.update(rail.internal_transfers(network[0]))
    if not geographic_anchor(origin) and not geographic_anchor(destination):
        for trip in planner.journeys(db,origin['id'],destination['id'],max_transfers,now=now,context=context,preserve_alternatives=True,include_rail=include_rail,
                transfer_paths=transfer_paths if include_rail else None,known_transfers_only=include_rail,weighted_transfers=weighted_transfers):
            fingerprint='|'.join(f"{leg['trip_id']}:{leg['origin']['id']}:{leg['destination']['id']}" for leg in trip['legs'])
            walks=trip.get('transfer_walks',[]) if include_rail else []
            initial.append({**trip,'id':fingerprint,'walking_minutes':sum(w['duration_minutes'] for w in walks),
                'walking_meters':sum(w['distance_meters'] for w in walks),'walks':walks})
    def tighten_cost_limit(journeys):
        from .journey_completion import has_short_bus_leg
        journeys=[j for j in journeys if not has_short_bus_leg(j)]
        if weighted_transfers and journeys:
            context['verified_cost_limit_units']=min(3*max_transfers,
                min(transfer_policy.annotate(j)['transfer_cost_units'] for j in journeys)+3)
    tighten_cost_limit(initial)
    yield {'journeys':distinct_routes(initial),'walking_incomplete':False,'complete':False}
    budget={'checks':0,'deadline':time.monotonic()+30,'limited':False}
    starts,missing_start=access_points(db,origin,True,optimistic=True,endpoint_selection=True,include_rail=include_rail)
    ends,missing_end=access_points(db,destination,False,optimistic=True,endpoint_selection=True,include_rail=include_rail)
    found={j['id']:j for j in initial}
    starts_by_id={point['id']:(point,foot) for point,foot in starts}
    ends_by_id={point['id']:(point,foot) for point,foot in ends}
    access_times={sid:(foot['distance_meters']/walking.WALK_METERS_PER_SECOND if foot else 0) for sid,(_,foot) in starts_by_id.items()}
    end_times={sid:(foot['distance_meters']/walking.WALK_METERS_PER_SECOND if foot else 0) for sid,(_,foot) in ends_by_id.items()}
    incomplete=missing_start or missing_end
    limited=budget['limited']
    checked=0
    deadline=budget['deadline']
    def remember(trips):
        for trip in trips:
            walks=trip['transfer_walks']
            if any((w['origin']['id'],w['destination']['id']) not in transfer_paths for w in walks):continue
            first,last=trip['legs'][0],trip['legs'][-1]
            access=starts_by_id[trip.get('access_stop_id',first['origin']['id'])][1]
            egress=ends_by_id[trip.get('goal_stop_id',last['destination']['id'])][1]
            if any(p and p.get('pending') for p in (access,egress)):continue
            paths=[p for p in [access,*[{**w,'accessType':'destination'} if w.get('before_leg')==len(trip['legs']) else w for w in walks],egress] if p]
            meters=sum(p['distance_meters'] for p in paths)
            fingerprint='|'.join(f"{l['trip_id']}:{l['origin']['id']}:{l['destination']['id']}" for l in trip['legs'])
            found[fingerprint]={**trip,'id':fingerprint,'walking_meters':round(meters),
                                'walking_minutes':round(meters/walking.WALK_METERS_PER_MINUTE,1),'walks':paths}
        tighten_cost_limit(list(found.values()))
    if starts and ends:
        options=dict(max_transfers=max_transfers,now=now,preserve_alternatives=True,transfer_paths=transfer_paths,context=context,
                     access_times=access_times,end_times=end_times,include_rail=include_rail,weighted_transfers=weighted_transfers)
        if include_rail:
            # Garanta uma comparação ferroviária antes de explorar os muitos
            # acessos de ônibus. Só publique após verificar os acessos externos.
            rail_starts={sid:seconds for sid,seconds in access_times.items() if network[0][sid].get('mode') in ('metro','rail')}
            rail_ends={sid:seconds for sid,seconds in end_times.items() if network[0][sid].get('mode') in ('metro','rail')}
            if rail_starts and rail_ends:
                rail_options={**options,'access_times':rail_starts,'end_times':rail_ends,'known_transfers_only':True,'rail_only':True}
                for _ in range(6):
                    if not rail_starts or not rail_ends:break
                    candidates=planner.journeys(db,starts[0][0]['id'],ends[0][0]['id'],**rail_options)
                    candidate=next((j for j in candidates if
                        (starts_by_id[j.get('access_stop_id',j['legs'][0]['origin']['id'])][1] or {}).get('pending') or
                        (ends_by_id[j.get('goal_stop_id',j['legs'][-1]['destination']['id'])][1] or {}).get('pending')),None)
                    if candidate is None:
                        remember(candidates)
                        break
                    for sid,mapping,times,rail_times in ((candidate.get('access_stop_id',candidate['legs'][0]['origin']['id']),starts_by_id,access_times,rail_starts),
                            (candidate.get('goal_stop_id',candidate['legs'][-1]['destination']['id']),ends_by_id,end_times,rail_ends)):
                        point,foot=mapping[sid]
                        if not foot or not foot.get('pending'):continue
                        if time.monotonic()>=deadline:limited=True;break
                        foot=walking.route(foot['origin'],foot['destination'],wait_for_slot=True)
                        checked+=1;budget['checks']+=1
                        if foot.get('available') and foot['distance_meters']<=WALK_LIMIT:
                            mapping[sid]=(point,{**foot,'accessType':'boarding' if mapping is starts_by_id else 'destination'})
                            times[sid]=rail_times[sid]=foot['distance_meters']/walking.WALK_METERS_PER_SECOND
                        else:
                            incomplete=True;times.pop(sid,None);rail_times.pop(sid,None)
                    if rail_starts and rail_ends:
                        verified_starts={sid:seconds for sid,seconds in rail_starts.items() if not (starts_by_id[sid][1] or {}).get('pending')}
                        verified_ends={sid:seconds for sid,seconds in rail_ends.items() if not (ends_by_id[sid][1] or {}).get('pending')}
                        if verified_starts and verified_ends:
                            remember(planner.journeys(db,starts[0][0]['id'],ends[0][0]['id'],**{**rail_options,'access_times':verified_starts,'end_times':verified_ends}))
                    yield {'journeys':distinct_routes(found.values()),'walking_incomplete':incomplete,'complete':False}
        # Uma busca limitada com múltiplas origens/destinos, em vez de consultar cada par.
        for iteration in range(12):
            if not access_times or not end_times:break
            trips=planner.journeys(db,starts[0][0]['id'],ends[0][0]['id'],**options)
            remember(trips)
            yield {'journeys':distinct_routes(found.values()),'walking_incomplete':incomplete,'complete':False}
            pending={}
            for trip in trips:
                for kind,sid,mapping in [('start',trip.get('access_stop_id',trip['legs'][0]['origin']['id']),starts_by_id),('end',trip.get('goal_stop_id',trip['legs'][-1]['destination']['id']),ends_by_id)]:
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
    limited = limited or bool(context.get('weighted_search_limited'))
    result={'journeys':distinct_routes(found.values()),'walking_incomplete':incomplete,
            'search_limited':limited,'optimal_within_limits':not limited and not incomplete,
            'search_limits':{'max_boardings':(3*max_transfers+1 if weighted_transfers and include_rail else max_transfers+1),'max_validation_rounds':12,'max_transfer_walk_checks':32,'max_walk_checks':64,'soft_time_limit_seconds':30}}
    cached_journeys,policy=transfer_policy.select(result['journeys'],max_transfers)
    cache.set(key,{**result,'journeys':cached_journeys,'transfer_policy':policy},30)
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


def _multimodal_progressive(db, origin, destination, max_transfers, now, **kwargs):
    if db is None:
        yield from _bus_progressive(db,origin,destination,min(max_transfers,2),now,**kwargs)
        return
    enabled=bool(db is not None and db.execute("SELECT 1 FROM routes WHERE route_type IN ('1','2') LIMIT 1").fetchone())
    from . import staged_adapter, concurrent_sources
    include_walk = kwargs.pop('_include_walk', False)
    # Connections and generators are constructed inside their owning thread.
    def prepared():
        with store.connection() as connection:
            yield from staged_adapter.progressive(connection,origin,destination,max_transfers,now)
    def bus():
        with store.connection() as connection:
            yield from _bus_progressive(connection,origin,destination,min(max_transfers,1),now,
                                        **{**kwargs,'allow_raptor':False})
    def rail_source():
        with store.connection() as connection:
            yield from _raptor_progressive(connection,origin,destination,max_transfers,now,
                refresh=kwargs.get('refresh',False),include_rail=enabled,weighted_transfers=True)
    def foot_source():
        from .journey_completion import direct_walk
        foot=direct_walk(origin,destination,now)
        yield {'journeys':[foot] if foot else [],'complete':True,
               'materialized':bool(foot and foot.get('materialized'))}
    factories={'prepared':prepared,'bus':bus}
    from . import supplementary
    legacy = supplementary.configured_path()
    if legacy is not None:
        factories['legacy_prepared'] = lambda: supplementary.progressive(
            legacy, origin, destination, max_transfers, now)
    if kwargs.get('allow_raptor') is not False:factories['rail']=rail_source
    if include_walk:factories['walk']=foot_source
    found={};states={};metadata={}
    stream=concurrent_sources.merge(factories)
    try:
        for name,result,finished in stream:
            if result is not None:
                states[name]={**states.get(name,{}),**result}
                found.update((j['id'],j) for j in result['journeys'])
                for key,value in result.items():
                    if key.startswith('materialization_') and name != 'legacy_prepared':metadata[key]=value
            failures={key:sorted({source for state in states.values() for source in state.get(key,[])})
                      for key in ('failed_sources','busy_sources','timed_out_sources')}
            yield {**metadata,**{k:v for k,v in failures.items() if v},
                   'journeys':distinct_routes(found.values()),'planner':'multimodal',
                   'complete':finished,
                   'optimal_within_limits':finished and all(s.get('optimal_within_limits',True)
                       and not s.get('walking_incomplete') and not s.get('search_limited') for s in states.values()),
                   'search_limited':any(s.get('search_limited') for s in states.values()),
                   'walking_incomplete':any(s.get('walking_incomplete') for s in states.values())}
    finally:
        stream.close()


def progressive(db, origin, destination, max_transfers=4, now=None, *, refresh=False):
    from .journey_completion import Completion, direct_walk, has_short_bus_leg, normalize_walks
    now = now or timezone.localtime()
    foot = direct_walk(origin, destination, now) if db is None else direct_walk(origin, destination, now, materialized_only=True)
    if foot:
        # Publique o percurso já validado antes da preparação dos índices de ônibus.
        # Ainda não é uma conclusão: alternativas mais rápidas podem aparecer depois.
        yield {'journeys': [foot], 'walking_incomplete': False, 'complete': False,
               'planner': 'walk', 'planner_fallback': None, 'materialized': bool(foot.get('materialized'))}
    # A revisão do desembarque examina a própria viagem, além dos pontos usados na busca inicial.
    completion = Completion(db, destination, origin=origin)
    for result in _multimodal_progressive(db, origin, destination, max_transfers, now, refresh=refresh,
                                   allow_raptor=foot is None or foot['walking_meters'] >= 1000,
                                   **({'_include_walk':foot is None} if db is not None else {})):
        # As rotas recebidas já têm horários e caminhadas verificados. A revisão
        # opcional de embarque/desembarque não deve atrasar os resultados parciais.
        walking_options=[j for j in result['journeys'] if j.get('mode')=='walk']
        if walking_options:foot=min(walking_options,key=lambda j:j['duration_minutes'])
        journeys = [normalize_walks(journey) for journey in result['journeys'] if journey.get('mode')!='walk']
        if result['complete']:
            journeys = [normalize_walks(completion.improve(journey)) if all(l.get('mode','bus')=='bus' for l in journey['legs']) else journey for journey in journeys]
        journeys = [journey for journey in journeys if not has_short_bus_leg(journey)]
        # A caminhada validada domina o ônibus quando chega antes e exige
        # no máximo a mesma distância a pé, sem nenhum embarque.
        if foot:
            journeys = [journey for journey in journeys if not (
                foot['duration_minutes'] <= journey['duration_minutes']
                and foot['walking_meters'] <= journey['walking_meters'])]
        if journeys:
            journeys=distinct_routes(journeys)
        journeys, policy = transfer_policy.select(journeys + ([foot] if foot else []), max_transfers)
        yield {**result, 'transfer_policy': policy, 'journeys': sorted(journeys,key=lambda j:j['duration_minutes'])}


def alternatives(db, origin, destination, max_transfers=4, now=None):
    result=None
    for result in progressive(db,origin,destination,max_transfers,now):pass
    return result
