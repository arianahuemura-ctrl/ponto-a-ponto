"""RAPTOR multicritério: rótulos distintos por custo e última linha embarcada."""
from collections import defaultdict
import math
import time
from django.utils import timezone
from . import planner, rail, store, transfer_policy


def journeys(db, origin, destination, ceiling, now, transfer_paths, context,
             access_times, end_times, known_transfers_only, include_rail, rail_only):
    if origin == destination and access_times is None:
        return []
    now = now or timezone.localtime()
    context = context if context is not None else {}
    deadline = min(context.setdefault('weighted_deadline', time.monotonic() + 30), time.monotonic() + 5)
    path = store.database_path(); stat = path.stat()
    stops, trips, by_stop = planner._network(str(path), stat.st_mtime_ns, stat.st_size, include_rail)
    if origin not in stops or destination not in stops:
        raise ValueError('Ponto inválido.')
    windows = planner._service_windows(db, trips, path, stat, now, include_rail, context)
    neighbours = planner._nearby(str(path), stat.st_mtime_ns, stat.st_size, include_rail) if transfer_paths is not None else {}
    feet = transfer_paths or {}
    access = dict(access_times) if access_times is not None else {origin: 0}
    ends = end_times if end_times is not None else {destination: 0}
    access_walks = {}
    for sid, seconds in list(access.items()):
        for other, _ in neighbours.get(sid, []):
            foot = feet.get((sid, other))
            if foot and foot.get('internal_transfer') and seconds + foot['seconds'] < access.get(other, math.inf):
                access[other] = seconds + foot['seconds']
                access_walks[other] = (sid, foot)
    start = now.timestamp(); horizon = start + planner.HORIZON_SECONDS
    # Key: stop, exact cost in thirds, last route. Label: arrival, chain.
    previous = {(sid, 0, None, True): (start + seconds, ()) for sid, seconds in access.items()}
    best = dict(previous)
    goals = {}
    units_limit = min(ceiling * 3, context.get('verified_cost_limit_units', ceiling * 3))
    max_boardings = units_limit + 1 if include_rail else units_limit // 3 + 1

    def rank(label):
        reached, chain = label
        walk = sum(leg[4] - leg[3] for leg in chain if leg[0] == '__walk__')
        first = next((leg for leg in chain if leg[0] != '__walk__'), None)
        if first:
            walk += access.get(trips[first[0]]['times'][first[1]][0], 0)
        return reached, walk

    def remember(sid, label, units):
        if sid not in ends or label[0] + ends[sid] > horizon:
            return
        signature = tuple((trips[l[0]]['route_id'], trips[l[0]]['direction_id']) for l in label[1] if l[0] != '__walk__')
        signature = signature, units
        score = (label[0] + ends[sid], rank(label)[1] + ends[sid])
        old = goals.get(signature)
        if old is None or score < old[0]:
            goals[signature] = (score, sid, label, units)

    def exhausted():
        if time.monotonic() >= deadline:
            context['weighted_search_limited'] = True
            return True
        return False

    for boarding in range(max_boardings):
        if exhausted(): break
        expanded = dict(previous)
        if boarding and transfer_paths is not None:
            for (sid, units, last_route, internal), (reached, chain) in previous.items():
                if exhausted(): break
                for other, gap in neighbours.get(sid, []):
                    pair = sid, other
                    if ((known_transfers_only and pair not in feet) or (pair in feet and feet[pair] is None)):
                        continue
                    foot = feet.get(pair)
                    seconds = foot.get('seconds', foot['distance_meters'] / planner.WALK_METERS_PER_SECOND) if foot else gap / planner.WALK_METERS_PER_SECOND
                    at = reached + seconds
                    candidate = (at, chain + (('__walk__', sid, other, reached, at),))
                    key = other, units, last_route, bool(foot and foot.get('internal_transfer'))
                    if at <= horizon and (key not in expanded or rank(candidate) < rank(expanded[key])):
                        expanded[key] = candidate
        by_origin = defaultdict(list)
        for (sid, units, last_route, internal), label in expanded.items():
            by_origin[sid].append((units, last_route, label))
        candidates = set().union(*(by_stop[s] for s in by_origin)) if by_origin else set()
        current = {}
        for identifier in sorted(candidates):
            if exhausted(): break
            trip = trips[identifier]
            if rail_only and trip['route_type'] not in rail.RAIL_TYPES: continue
            onboard = {}
            for index, (sid, arrival, departure) in enumerate(trip['times']):
                for units, (boarded, at_board, prefix) in list(onboard.items()):
                    elapsed = arrival - trip['times'][boarded][2]
                    reached = at_board + elapsed
                    if elapsed < 0 or reached > horizon: continue
                    candidate = (reached, prefix + ((identifier, boarded, index, at_board, reached),))
                    key = sid, units, trip['route_id'], True
                    dominated = any((sid, cheaper, trip['route_id'], True) in best
                                    and rank(best[sid, cheaper, trip['route_id'], True]) <= rank(candidate)
                                    for cheaper in range(units + 1))
                    if (not dominated
                            and (key not in current or rank(candidate) < rank(current[key]))):
                        current[key] = candidate
                        remember(sid, candidate, units)
                for units, last_route, (reached, prefix) in by_origin.get(sid, []):
                    if last_route == trip['route_id']: continue
                    previous_vehicle = next((leg for leg in reversed(prefix) if leg[0] != '__walk__'), None)
                    extra = 0
                    if previous_vehicle:
                        extra = 3
                        last_trip = trips[previous_vehicle[0]]
                        between = prefix[prefix.index(previous_vehicle) + 1:]
                        if (last_trip['route_type'] in rail.RAIL_TYPES and trip['route_type'] in rail.RAIL_TYPES
                                and all(feet.get((leg[1], leg[2]), {}).get('internal_transfer') for leg in between)):
                            extra = 1
                    cost = units + extra
                    if cost > units_limit: continue
                    ready = reached + (planner.TRANSFER_SECONDS if previous_vehicle else 0)
                    depart = planner.next_departure(trip, index, ready, rail.boarding_windows(trip, index, windows[identifier], now.tzinfo))
                    if depart > horizon or not rail.departure_allowed(trip, depart, now.tzinfo, bool(previous_vehicle)):
                        continue
                    old = onboard.get(cost)
                    score = (depart - departure, rank((reached, prefix))[1])
                    if old is None or score < (old[1] - trip['times'][old[0]][2], rank((old[1], old[2]))[1]):
                        onboard[cost] = index, depart, prefix
        if transfer_paths is not None:
            for (sid, units, _, _), (reached, chain) in current.items():
                if exhausted(): break
                for other, gap in neighbours.get(sid, []):
                    if other not in ends: continue
                    pair = sid, other
                    if ((known_transfers_only and pair not in feet) or (pair in feet and feet[pair] is None)):
                        continue
                    foot = feet.get(pair)
                    seconds = foot.get('seconds', foot['distance_meters'] / planner.WALK_METERS_PER_SECOND) if foot else gap / planner.WALK_METERS_PER_SECOND
                    remember(other, (reached + seconds, chain + (('__walk__', sid, other, reached, reached + seconds),)), units)
        best.update(current)
        previous = current
        if not previous: break
    # Preserve candidates at every cost so a fast but costly route cannot hide the minimum.
    buckets = defaultdict(list)
    for _, goal, (reached, chain), units in sorted(goals.values(), key=lambda value: value[0]):
        bucket = buckets[units]
        if len(bucket) >= 5:
            context['weighted_search_limited'] = True
            continue
        journey = planner._format_journey(goal, reached, chain, trips, stops, start, now, ends, access, access_walks, feet)
        journey = transfer_policy.annotate(journey)
        assert journey['transfer_cost_units'] == units
        bucket.append(journey)
    return sorted((j for bucket in buckets.values() for j in bucket), key=lambda j: (j['duration_minutes'], j['transfer_cost_units']))
