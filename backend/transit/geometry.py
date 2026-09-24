"""Geometrias viárias locais, sem inventar retas quando um trecho não existe."""

import bisect
import json
import math
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def road_data():
    return json.loads((Path(__file__).parent / "data/route_geometry.json").read_text())


def segments_for(route_id, stop_ids):
    from .models import RouteStop
    segments = [entry.segment for entry in RouteStop.objects.filter(route_id=route_id) if entry.segment]
    result = []
    for a, b in zip(stop_ids, stop_ids[1:]):
        segment = next((s for s in segments if s["from"] == a and s["to"] == b), None)
        if segment is not None:
            result.append(segment)
    return result


def point_on_segment(segment, fraction):
    points = segment["points"]
    distances = [0.0]
    for a, b in zip(points, points[1:]):
        dy = (b[0] - a[0]) * 111320
        dx = (b[1] - a[1]) * 111320 * math.cos(math.radians((b[0] + a[0]) / 2))
        distances.append(distances[-1] + math.hypot(dx, dy))
    target = max(0, min(1, fraction)) * distances[-1]
    index = min(len(points) - 2, max(0, bisect.bisect_right(distances, target) - 1))
    length = distances[index + 1] - distances[index]
    ratio = (target - distances[index]) / length if length else 0
    a, b = points[index], points[index + 1]
    return [a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio]
