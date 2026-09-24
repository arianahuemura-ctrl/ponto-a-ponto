"""Rede demonstrável e horários determinísticos, independentes dos provedores externos."""

import json
import math
from functools import lru_cache
from pathlib import Path
from .geometry import road_data, point_on_segment


@lru_cache(maxsize=1)
def dataset():
    data = json.loads((Path(__file__).parent / "data/demo.json").read_text())
    for route in data["routes"]:
        route["segments"] = (
            road_data()["routes"].get(route["id"], {}).get("segments", [])
        )
    return data


def trips(network=None):
    network = network or dataset()
    result = []
    for route in network["routes"]:
        for start in range(
            network["service_start"] + route["offset"],
            network["service_end"],
            route["headway"],
        ):
            times = [start]
            for duration in route["durations"]:
                times.append(times[-1] + duration)
            result.append(
                {
                    "id": f"{route['id']}-{start}",
                    "route_id": route["id"],
                    "stops": route["stops"],
                    "times": times,
                }
            )
    return result


def distance(a, b):
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat, dlon = lat2 - lat1, math.radians(b["lon"] - a["lon"])
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


def destination_candidates(lat, lon, max_walk=500):
    target = {"lat": lat, "lon": lon}
    return {
        s["id"]: math.ceil(distance(s, target) / 1.3)
        for s in dataset()["stops"]
        if distance(s, target) <= max_walk
    }


def snapshot(at, origin=None, allowed_trips=None):
    network = dataset()
    stops = {s["id"]: s for s in network["stops"]}
    routes = {r["id"]: r for r in network["routes"]}
    arrivals, vehicles = [], []
    for trip in trips(network):
        if origin in trip["stops"]:
            index = trip["stops"].index(origin)
            when = trip["times"][index]
            if index < len(trip["stops"]) - 1 and at <= when <= at + 3600:
                arrivals.append(
                    {
                        "trip_id": trip["id"],
                        "route_id": trip["route_id"],
                        "arrival": when,
                        "wait_seconds": when - at,
                        "destination": stops[trip["stops"][-1]]["name"],
                    }
                )
        if allowed_trips is not None and trip["id"] not in allowed_trips:
            continue
        times = trip["times"]
        if not times[0] - 900 <= at < times[-1]:
            continue
        waiting = at < times[0]
        index = (
            0
            if waiting
            else next(i for i in range(len(times) - 1) if times[i] <= at < times[i + 1])
        )
        a, b = stops[trip["stops"][index]], stops[trip["stops"][index + 1]]
        fraction = (
            0 if waiting else (at - times[index]) / (times[index + 1] - times[index])
        )
        segments = routes[trip["route_id"]].get("segments", [])
        if index >= len(segments):
            continue
        lat, lon = point_on_segment(segments[index], fraction)
        vehicles.append(
            {
                "id": trip["id"],
                "route_id": trip["route_id"],
                "lat": lat,
                "lon": lon,
                "next_stop": a["id"] if waiting else b["id"],
                "waiting_to_depart": waiting,
                "color": routes[trip["route_id"]]["color"],
            }
        )
    arrivals.sort(key=lambda x: (x["arrival"], x["trip_id"]))
    grouped = []
    for route_id in dict.fromkeys(a["route_id"] for a in arrivals):
        upcoming = [a for a in arrivals if a["route_id"] == route_id][:3]
        grouped.append({"route_id": route_id, "arrivals": upcoming})
    # Ao selecionar a parada, acompanhe o próximo veículo de cada linha que se aproxima.
    nearest = {g["arrivals"][0]["trip_id"] for g in grouped}
    for vehicle in vehicles:
        vehicle["approaching_origin"] = vehicle["id"] in nearest
    return {"at": at, "mode": "simulation", "vehicles": vehicles, "lines": grouped}
