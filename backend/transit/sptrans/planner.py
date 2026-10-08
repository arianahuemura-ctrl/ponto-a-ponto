"""Planejamento por rodadas de embarque; tempos GTFS são estimativas, não previsões."""
from mbm import routing_config as config
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from django.utils import timezone
from . import store
from .geometry import leg_shape
from .directions import distance
from .walking import WALK_LIMIT, WALK_METERS_PER_SECOND

TRANSFER_SECONDS = config.TRANSFER_SECONDS
HORIZON_SECONDS = config.HORIZON_SECONDS


@lru_cache(maxsize=2)
def _network(path, modified, size):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        stops = {r['stop_id']: store.stop(r) for r in db.execute('SELECT * FROM stops')}
        trips = {r['trip_id']: dict(r) for r in db.execute('''SELECT t.*, r.route_short_name, r.route_color
            FROM trips t JOIN routes r USING(route_id) WHERE r.route_type='3' ''')}
        times = defaultdict(list)
        for row in db.execute('SELECT * FROM stop_times ORDER BY trip_id,stop_sequence'):
            if row['trip_id'] in trips:
                times[row['trip_id']].append((row['stop_id'], store.seconds(row['arrival_time']), store.seconds(row['departure_time'])))
        frequencies = defaultdict(list)
        for r in db.execute('SELECT * FROM frequencies'):
            frequencies[r['trip_id']].append((store.seconds(r['start_time']), store.seconds(r['end_time']), float(r['headway_secs']), r['exact_times']=='1'))
        by_stop = defaultdict(set)
        for identifier, trip in trips.items():
            trip['times'] = times[identifier]
            trip['frequencies'] = frequencies[identifier]
            for stop_id, _, _ in times[identifier]: by_stop[stop_id].add(identifier)
        return stops, trips, by_stop
    finally:
        db.close()


@lru_cache(maxsize=2)
def _nearby(path, modified, size):
    stops, _, by_stop = _network(path, modified, size)
    cells=defaultdict(list)
    for sid,s in stops.items():
        if sid in by_stop:cells[(math.floor(s['lat']/.002),math.floor(s['lon']/.002))].append(sid)
    edges={}
    for sid,s in stops.items():
        if sid not in by_stop:continue
        y,x=math.floor(s['lat']/.002),math.floor(s['lon']/.002)
        near=[]
        for dy in range(-3,4):
            for dx in range(-3,4):
                for other in cells.get((y+dy,x+dx),[]):
                    if other==sid:continue
                    d=distance((s['lat'],s['lon']),(stops[other]['lat'],stops[other]['lon']))
                    if d<=WALK_LIMIT:near.append((other,d))
        edges[sid]=near
    return edges


def next_departure(trip, position, ready, windows):
    offset = trip['times'][position][2] - trip['times'][0][2]
    best = math.inf
    for start, end, headway, exact in windows:
        start += offset
        end += offset
        if not headway:
            candidate = start if start >= ready else math.inf
        elif exact:
            candidate = start + max(0, math.ceil((ready-start)/headway))*headway
            if candidate >= end: continue
        else:
            # Fase desconhecida: espera média de meio intervalo, não uma partida exata.
            candidate = max(ready, start) + headway/2
            if candidate >= end: continue
        best = min(best, candidate)
    return best


def journeys(db, origin, destination, max_transfers=2, now=None, transfer_paths=None, context=None, access_times=None, end_times=None, known_transfers_only=False, preserve_alternatives=False):
    if not 0 <= max_transfers <= 3: raise ValueError('Limite de trocas inválido.')
    if origin == destination and access_times is None: return []
    now = now or timezone.localtime()
    path = store.database_path()
    stat = path.stat()
    stops, trips, by_stop = _network(str(path), stat.st_mtime_ns, stat.st_size)
    if origin not in stops or destination not in stops: raise ValueError('Ponto inválido.')
    neighbours=_nearby(str(path),stat.st_mtime_ns,stat.st_size) if transfer_paths is not None else {}
    start = now.timestamp()
    horizon = start + HORIZON_SECONDS
    midnight = now.replace(hour=0,minute=0,second=0,microsecond=0)
    context=context if context is not None else {}
    window_key=(str(path),stat.st_mtime_ns,stat.st_size,midnight.isoformat())
    windows=context.get(window_key)
    if windows is None:
        active = {}
        windows = {}
        for identifier, trip in trips.items():
            if not trip['times']: continue
            entries = []
            # Horários GTFS podem exceder 24:00; inclua datas de serviço anteriores.
            latest = max([t[2] for t in trip['times']] + [f[1] for f in trip['frequencies']])
            for delta in range(-math.ceil(latest/86400), 2):
                day = midnight + timedelta(days=delta)
                key = (trip['service_id'], day.date())
                if key not in active: active[key] = store.service_active(db,*key)
                if not active[key]: continue
                base = day.timestamp()
                if trip['frequencies']:
                    entries.extend((base+a,base+b,h,e) for a,b,h,e in trip['frequencies'] if h>0)
                else:
                    departure = base + trip['times'][0][2]
                    entries.append((departure,departure,0,True))
            windows[identifier] = entries
        context[window_key]=windows
    # Rótulos da rodada anterior sempre representam menos embarques. Nunca use uma
    # transferência recém-descoberta para embarcar novamente na mesma rodada.
    multi_goal=end_times is not None
    access_times=access_times if access_times is not None else {origin:0}
    end_times=end_times if end_times is not None else {destination:0}
    previous = {sid:(start+seconds,()) for sid,seconds in access_times.items()}
    def walking_seconds(chain, sid):
        if not chain:
            return access_times.get(sid, 0)
        first = next((leg for leg in chain if leg[0] != '__walk__'), None)
        access = access_times.get(trips[first[0]]['times'][first[1]][0], 0) if first else access_times.get(sid, 0)
        return access + sum(leg[4]-leg[3] for leg in chain if leg[0]=='__walk__')
    def label_rank(label, sid):
        return (label[0], walking_seconds(label[1], sid))
    best = {sid:label_rank(label,sid) for sid,label in previous.items()}
    results = []
    # Válido apenas nesta busca origem/destino, não entre pares alternativos.
    # Tempos não negativos de viagem e caminhada não melhoram um limite já alcançado.
    arrival_bound = math.inf
    for boarding in range(max_transfers+1):
        if boarding and transfer_paths is not None:
            expanded=dict(previous)
            for sid,(reached,chain) in previous.items():
                if reached+TRANSFER_SECONDS>arrival_bound:continue
                for other,gap in neighbours.get(sid,[]):
                    pair=(sid,other)
                    if (known_transfers_only and pair not in transfer_paths) or (pair in transfer_paths and transfer_paths[pair] is None):continue
                    path=transfer_paths.get(pair)
                    seconds=(path['distance_meters'] if path else gap)/WALK_METERS_PER_SECOND
                    arrival=reached+seconds
                    candidate=(arrival,chain+(('__walk__',sid,other,reached,arrival),))
                    if arrival+TRANSFER_SECONDS<=arrival_bound and label_rank(candidate,other)<label_rank(expanded.get(other,(math.inf,())),other):
                        expanded[other]=candidate
            previous=expanded
        current = {}
        goal_labels = {}
        previous={sid:label for sid,label in previous.items() if label[0]+(TRANSFER_SECONDS if label[1] else 0)<=arrival_bound}
        if not previous:break
        candidates = set().union(*(by_stop[s] for s in previous)) if previous else set()
        for identifier in sorted(candidates):
            trip = trips[identifier]
            onboard = None
            for index, (stop_id, arrival, departure) in enumerate(trip['times']):
                if onboard is not None:
                    boarded, departure_at_board, prefix = onboard
                    elapsed = arrival-trip['times'][boarded][2]
                    reached = departure_at_board+elapsed
                    leg = (identifier,boarded,index,departure_at_board,reached)
                    candidate = (reached,prefix+(leg,))
                    if preserve_alternatives and elapsed >= 0 and reached <= horizon and stop_id in end_times:
                        signature=tuple((trips[part[0]]['route_id'],trips[part[0]]['direction_id']) for part in candidate[1] if part[0]!='__walk__')
                        old=goal_labels.get(signature)
                        score=(reached+end_times[stop_id],walking_seconds(candidate[1],stop_id)+end_times[stop_id])
                        if old is None or score<old[0]:goal_labels[signature]=(score,stop_id,candidate)
                    rank = label_rank(candidate,stop_id)
                    if elapsed >= 0 and reached <= horizon and reached <= arrival_bound and rank < best.get(stop_id,(math.inf,math.inf)) and rank < label_rank(current.get(stop_id,(math.inf,())),stop_id):
                        current[stop_id] = candidate
                        if stop_id in end_times and not preserve_alternatives:arrival_bound=min(arrival_bound,reached+end_times[stop_id])
                if stop_id not in previous: continue
                arrival_at_stop, prefix = previous[stop_id]
                ready = arrival_at_stop+(TRANSFER_SECONDS if prefix else 0)
                if ready>arrival_bound:continue
                departure_at_stop = next_departure(trip,index,ready,windows[identifier])
                # Compare o horário-base da partida para manter consistentes os deslocamentos temporais seguintes.
                if departure_at_stop <= horizon and departure_at_stop <= arrival_bound and (onboard is None or (departure_at_stop-departure,walking_seconds(prefix,stop_id)) < (onboard[1]-trip['times'][onboard[0]][2],walking_seconds(onboard[2],trip['times'][onboard[0]][0]))):
                    onboard = (index,departure_at_stop,prefix)
        # Termine a rodada a pé quando o destino já é alcançável, sem outro embarque.
        if transfer_paths is not None:
            for sid,(reached,chain) in list(current.items()):
                for other,gap in neighbours.get(sid,[]):
                    if other not in end_times:continue
                    pair=(sid,other)
                    if (known_transfers_only and pair not in transfer_paths) or (pair in transfer_paths and transfer_paths[pair] is None):continue
                    foot=transfer_paths.get(pair)
                    seconds=(foot['distance_meters'] if foot else gap)/WALK_METERS_PER_SECOND
                    at=reached+seconds
                    if at+end_times[other]>horizon:continue
                    candidate=(at,chain+(('__walk__',sid,other,reached,at),))
                    if label_rank(candidate,other)<label_rank(current.get(other,(math.inf,())),other):
                        current[other]=candidate
                    if preserve_alternatives:
                        signature=tuple((trips[part[0]]['route_id'],trips[part[0]]['direction_id']) for part in chain if part[0]!='__walk__')
                        score=(at+end_times[other],walking_seconds(candidate[1],other)+end_times[other])
                        old=goal_labels.get(signature)
                        if old is None or score<old[0]:goal_labels[signature]=(score,other,candidate)
        goals=sorted(end_times.keys() & current.keys(),key=lambda sid:(current[sid][0]+end_times[sid],walking_seconds(current[sid][1],sid)+end_times[sid],sid))
        selected_goals = [(goal,current[goal]) for goal in (goals[:1] if multi_goal else goals)]
        if preserve_alternatives:
            selected_goals=[(goal,label) for _,goal,label in sorted(goal_labels.values(),key=lambda item:item[0])[:3]]
        for goal,(reached,chain) in selected_goals:
            legs = []
            walks = []
            previous_arrival = start
            for identifier,a,b,depart,arrive in chain:
                if identifier=='__walk__':
                    foot=transfer_paths.get((a,b)) or {'origin':stops[a],'destination':stops[b],'distance_meters':(arrive-depart)*WALK_METERS_PER_SECOND}
                    walks.append({**foot,'accessType':'boarding' if not legs else 'transfer','before_leg':len(legs),
                                  'duration_minutes':(arrive-depart)/60})
                    previous_arrival=arrive
                    continue
                trip = trips[identifier]
                if not legs:previous_arrival=start+access_times.get(trip['times'][a][0],0)
                legs.append({
                    'geometry':leg_shape(identifier,a,b),'boarding_index':a,'alighting_index':b,
                    'trip_id':identifier,'route_id':trip['route_id'],'direction_id':trip['direction_id'],'code':trip['route_short_name'],'headsign':trip['trip_headsign'],
                    'color':'#'+(trip['route_color'] or '005cec'),
                    'origin':stops[trip['times'][a][0]],'destination':stops[trip['times'][b][0]],
                    'departure':datetime.fromtimestamp(depart,now.tzinfo).isoformat(),
                    'arrival':datetime.fromtimestamp(arrive,now.tzinfo).isoformat(),
                    'wait_minutes':round((depart-previous_arrival)/60,1),
                    'ride_minutes':round((arrive-depart)/60,1),
                    'stops':[stops[t[0]] for t in trip['times'][a:b+1]],
                })
                previous_arrival = arrive
            results.append({'transfers':len(legs)-1,'duration_minutes':round((reached+end_times[goal]-start)/60,1),
                            'arrival':datetime.fromtimestamp(reached+end_times[goal],now.tzinfo).isoformat(),'legs':legs,'transfer_walks':walks,'goal_stop_id':goal,'estimated':True})
        for stop_id,label in current.items(): best[stop_id] = min(best.get(stop_id,(math.inf,math.inf)),label_rank(label,stop_id))
        previous = current
        if not previous: break
    return sorted(results,key=lambda r:(r['duration_minutes'],r['transfers']))
