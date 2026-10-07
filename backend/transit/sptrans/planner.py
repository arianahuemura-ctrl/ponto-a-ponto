"""Planejamento por rodadas de embarque; tempos GTFS são estimativas, não previsões."""
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from django.utils import timezone
from . import store
from .geometry import leg_shape
from .directions import distance

TRANSFER_SECONDS = 120
HORIZON_SECONDS = 6 * 3600


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
        for dy in range(-2,3):
            for dx in range(-2,3):
                for other in cells.get((y+dy,x+dx),[]):
                    if other==sid:continue
                    d=distance((s['lat'],s['lon']),(stops[other]['lat'],stops[other]['lon']))
                    if d<=200:near.append((other,d))
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
            # Unknown phase: average wait of half an interval, not an exact departure.
            candidate = max(ready, start) + headway/2
            if candidate >= end: continue
        best = min(best, candidate)
    return best


def journeys(db, origin, destination, max_transfers=2, now=None, transfer_paths=None):
    if not 0 <= max_transfers <= 3: raise ValueError('Limite de trocas inválido.')
    if origin == destination: return []
    now = now or timezone.localtime()
    path = store.database_path()
    stat = path.stat()
    stops, trips, by_stop = _network(str(path), stat.st_mtime_ns, stat.st_size)
    if origin not in stops or destination not in stops: raise ValueError('Ponto inválido.')
    neighbours=_nearby(str(path),stat.st_mtime_ns,stat.st_size) if transfer_paths is not None else {}
    start = now.timestamp()
    horizon = start + HORIZON_SECONDS
    midnight = now.replace(hour=0,minute=0,second=0,microsecond=0)
    active = {}
    windows = {}
    for identifier, trip in trips.items():
        if not trip['times']: continue
        entries = []
        # GTFS times may exceed 24:00; include previous service dates.
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
    # Labels from the previous round always represent fewer boardings. Never use a
    # newly discovered transfer to board again in the same round.
    previous = {origin: (start, ())}
    best = {origin: start}
    results = []
    for boarding in range(max_transfers+1):
        if boarding and transfer_paths is not None:
            expanded=dict(previous)
            for sid,(reached,chain) in previous.items():
                for other,gap in neighbours.get(sid,[]):
                    pair=(sid,other)
                    if pair in transfer_paths and transfer_paths[pair] is None:continue
                    path=transfer_paths.get(pair)
                    seconds=(path['distance_meters'] if path else gap)/(4000/3600)
                    arrival=reached+seconds
                    if arrival<expanded.get(other,(math.inf,))[0]:
                        expanded[other]=(arrival,chain+(('__walk__',sid,other,reached,arrival),))
            previous=expanded
        current = {}
        candidates = set().union(*(by_stop[s] for s in previous)) if previous else set()
        for identifier in sorted(candidates):
            trip = trips[identifier]
            onboard = None
            for index, (stop_id, arrival, departure) in enumerate(trip['times']):
                if onboard is not None:
                    boarded, departure_at_board, prefix = onboard
                    elapsed = arrival-trip['times'][boarded][2]
                    reached = departure_at_board+elapsed
                    if elapsed >= 0 and reached <= horizon and reached < best.get(stop_id,math.inf) and reached < current.get(stop_id,(math.inf,))[0]:
                        leg = (identifier,boarded,index,departure_at_board,reached)
                        current[stop_id] = (reached,prefix+(leg,))
                if stop_id not in previous: continue
                arrival_at_stop, prefix = previous[stop_id]
                ready = arrival_at_stop+(TRANSFER_SECONDS if prefix else 0)
                departure_at_stop = next_departure(trip,index,ready,windows[identifier])
                # Compare the departure's base time so downstream offsets are consistent.
                if departure_at_stop <= horizon and (onboard is None or departure_at_stop-departure < onboard[1]-trip['times'][onboard[0]][2]):
                    onboard = (index,departure_at_stop,prefix)
        if destination in current:
            reached, chain = current[destination]
            legs = []
            walks = []
            previous_arrival = start
            for identifier,a,b,depart,arrive in chain:
                if identifier=='__walk__':
                    foot=transfer_paths.get((a,b)) or {'origin':stops[a],'destination':stops[b],'distance_meters':(arrive-depart)*(4000/3600)}
                    walks.append({**foot,'accessType':'transfer','before_leg':len(legs)})
                    previous_arrival=arrive
                    continue
                trip = trips[identifier]
                legs.append({
                    'geometry':leg_shape(identifier,a,b),
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
            results.append({'transfers':len(legs)-1,'duration_minutes':round((reached-start)/60,1),
                            'arrival':datetime.fromtimestamp(reached,now.tzinfo).isoformat(),'legs':legs,'transfer_walks':walks,'estimated':True})
        for stop_id,label in current.items(): best[stop_id] = min(best.get(stop_id,math.inf),label[0])
        previous = current
        if not previous: break
    return sorted(results,key=lambda r:(r['duration_minutes'],r['transfers']))
