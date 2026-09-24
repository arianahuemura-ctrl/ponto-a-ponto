"""Dijkstra em eventos de chegada: viagens posteriores e trocas são examinadas.

Um estado distingue a viagem e o índice da parada. Arestas permitem continuar
no mesmo veículo ou embarcar em qualquer partida viável, com tempo mínimo de
troca. Custos são segundos não negativos. Nenhuma viagem é reduzida ao veículo
mais próximo da linha. O conjunto finito de horários delimita o planejamento.
"""

import heapq
from collections import defaultdict


def plan(
    trips,
    origin,
    destinations,
    departure,
    transfer_seconds=120,
    max_transfers=4,
    first_route=None,
):
    by_stop = defaultdict(list)
    trip_by_id = {t["id"]: t for t in trips}
    for trip in trips:
        for i, stop in enumerate(trip["stops"][:-1]):
            by_stop[stop].append((trip["times"][i], trip["id"], i))
    start = ("", -1, 0)
    best = {start: departure}
    previous = {}
    queue = [(departure, start)]
    winner, final_arrival = None, float("inf")
    while queue:
        at, state = heapq.heappop(queue)
        if best.get(state) != at:
            continue
        if at >= final_arrival:
            continue
        trip_id, index, boardings = state
        stop = trip_by_id[trip_id]["stops"][index] if trip_id else origin
        if stop in destinations:
            arrival = at + destinations[stop]
            if arrival < final_arrival:
                winner, final_arrival = state, arrival
        for depart, next_trip_id, next_index in by_stop[stop]:
            same_vehicle = next_trip_id == trip_id and next_index == index
            if trip_id == next_trip_id and not same_vehicle:
                continue
            count = boardings + (not same_vehicle)
            if count > max_transfers + 1:
                continue
            ready = at + (transfer_seconds if trip_id and not same_vehicle else 0)
            if depart < ready:
                continue
            trip = trip_by_id[next_trip_id]
            if not trip_id and first_route and trip["route_id"] != first_route:
                continue
            new_state = (next_trip_id, next_index + 1, count)
            arrival = trip["times"][next_index + 1]
            if arrival < best.get(new_state, float("inf")):
                best[new_state] = arrival
                previous[new_state] = (
                    state,
                    {
                        "trip_id": next_trip_id,
                        "route_id": trip["route_id"],
                        "from": stop,
                        "to": trip["stops"][next_index + 1],
                        "departure": depart,
                        "arrival": arrival,
                        "wait_seconds": depart - at,
                    },
                )
                heapq.heappush(queue, (arrival, new_state))
    if winner is None:
        return None
    edges, cursor = [], winner
    while cursor != start:
        cursor, edge = previous[cursor]
        edges.append(edge)
    edges.reverse()
    legs = []
    for edge in edges:
        if legs and legs[-1]["trip_id"] == edge["trip_id"]:
            legs[-1]["to"] = edge["to"]
            legs[-1]["arrival"] = edge["arrival"]
            legs[-1]["stops"].append(edge["to"])
        else:
            legs.append({**edge, "stops": [edge["from"], edge["to"]]})
    end_stop = trip_by_id[winner[0]]["stops"][winner[1]] if winner[0] else origin
    walk = destinations[end_stop]
    ride = sum(l["arrival"] - l["departure"] for l in legs)
    wait = sum(l["wait_seconds"] for l in legs)
    return {
        "departure": departure,
        "arrival": final_arrival,
        "duration_seconds": final_arrival - departure,
        "ride_seconds": ride,
        "wait_seconds": wait,
        "walk_seconds": walk,
        "transfers": max(0, len(legs) - 1),
        "legs": legs,
        "destination_stop": end_stop,
    }


def alternatives(trips, origin, destinations, departure, **options):
    first_routes = sorted({t["route_id"] for t in trips if origin in t["stops"][:-1]})
    answers = []
    for route in first_routes:
        answer = plan(
            trips, origin, destinations, departure, first_route=route, **options
        )
        if answer and answer["legs"]:
            answers.append(answer)
    if origin in destinations:
        answers.append(plan(trips, origin, destinations, departure, **options))
    unique = {
        tuple((l["trip_id"], l["from"], l["to"]) for l in a["legs"]): a for a in answers
    }
    return sorted(unique.values(), key=lambda a: (a["arrival"], a["transfers"]))[:5]
