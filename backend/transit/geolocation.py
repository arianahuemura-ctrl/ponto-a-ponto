"""Geocodificação local de endereços e escolha de segmentos por sequência dirigida.

Coordenadas retornadas são estimativas; não comprovam plataforma ou calçada.
"""

import heapq
import math
import re
import unicodedata
from collections import defaultdict
from difflib import get_close_matches, SequenceMatcher
from functools import lru_cache

VERSION = "osm-address-directed-v1.1"
LAT_SCALE = 111320.0
LON_SCALE = LAT_SCALE * math.cos(math.radians(-23.67))
MAX_PATH = 8000.0


def xy(point):
    return point[1] * LON_SCALE, point[0] * LAT_SCALE


def ll(point):
    return point[1] / LAT_SCALE, point[0] / LON_SCALE


def distance(a, b):
    x, y = xy(a)
    u, v = xy(b)
    return math.hypot(x - u, y - v)


def normalize(value):
    value = "".join(
        c
        for c in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(c)
    )
    words = re.sub(r"[^a-z0-9 ]", " ", value).split()
    expansions = {
        "r": "rua",
        "av": "avenida",
        "estr": "estrada",
        "rod": "rodovia",
        "pca": "praca",
        "pc": "praca",
        "dr": "doutor",
        "prof": "professor",
        "pres": "presidente",
        "pref": "prefeito",
        "ver": "vereador",
        "eng": "engenheiro",
    }
    return " ".join(expansions.get(w, w) for w in words)


def address_parts(value):
    # Número final antes da primeira vírgula ou após a vírgula da rua.
    match = re.match(r"^(.*?)(?:,\s*|\s+)(\d+)(?:\s*-\s*(\d+))?(?=\s*[-,]|$)", value)
    if match:
        street, low, high = match.groups()
        number = (int(low) + int(high)) / 2 if high else int(low)
    else:
        street, number = value.split(",")[0], None
    city = next(
        (c for c in ("santo andre", "ribeirao pires", "maua") if c in normalize(value)),
        None,
    )
    return {
        "street": normalize(street),
        "number": number,
        "city": city,
        "original": value,
    }


def project(point, a, b):
    x, y = xy(point)
    ax, ay = xy(a)
    bx, by = xy(b)
    length = (bx - ax) ** 2 + (by - ay) ** 2
    ratio = (
        max(0, min(1, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / length))
        if length
        else 0
    )
    projected = ll((ax + ratio * (bx - ax), ay + ratio * (by - ay)))
    return projected, ratio, distance(point, projected)


def heading(candidate):
    segment = candidate["segment"]
    ax, ay = xy(segment["a"])
    bx, by = xy(segment["b"])
    return (
        math.degrees(
            math.atan2(
                (bx - ax) * candidate["direction"], (by - ay) * candidate["direction"]
            )
        )
        % 360
    )


def heading_difference(a, b):
    return abs((heading(a) - heading(b) + 180) % 360 - 180)


def allowed_directions(tags):
    if (
        tags.get("bus") == "no"
        or tags.get("motor_vehicle") == "no"
        and tags.get("bus") not in ("yes", "designated")
    ):
        return ()
    if (
        tags.get("access") in ("private", "no")
        and tags.get("bus") not in ("yes", "designated")
        and tags.get("psv") not in ("yes", "designated")
    ):
        return ()
    # Regras condicionais não são avaliadas sem data/horário operacional.
    if any(
        k in tags
        for k in ("oneway:conditional", "oneway:bus:conditional", "access:conditional")
    ):
        return ()
    oneway = tags.get(
        "oneway:bus",
        tags.get(
            "oneway:psv",
            tags.get("oneway", "yes" if tags.get("junction") == "roundabout" else "no"),
        ),
    )
    return (
        (-1,) if oneway == "-1" else (1,) if oneway in ("yes", "1", "true") else (1, -1)
    )


class StreetIndex:
    def __init__(self, elements):
        self.roads = defaultdict(list)
        self.anchors = defaultdict(list)
        self.graph = defaultdict(list)
        self.nodes = {}
        self.address_count = 0
        for element in elements:
            tags = element.get("tags", {})
            geometry = element.get("geometry", [])
            if tags.get("addr:street") and tags.get("addr:housenumber"):
                number = re.fullmatch(r"\d+", tags["addr:housenumber"])
                point = (element.get("lat"), element.get("lon"))
                if point[0] is None and geometry:
                    point = (
                        sum(g["lat"] for g in geometry) / len(geometry),
                        sum(g["lon"] for g in geometry) / len(geometry),
                    )
                if number and point[0] is not None:
                    self.anchors[normalize(tags["addr:street"])].append(
                        {
                            "number": int(number.group()),
                            "point": point,
                            "city": normalize(tags.get("addr:city", "")),
                            "osm_id": f"{element['type']}/{element['id']}",
                        }
                    )
                    self.address_count += 1
            if element["type"] != "way" or "highway" not in tags:
                continue
            directions = allowed_directions(tags)
            nodes = element.get("nodes", [])
            if len(nodes) != len(geometry):
                continue
            names = {
                normalize(name)
                for key in ("name", "alt_name", "short_name")
                for name in tags.get(key, "").split(";")
                if name
            }
            for i, (a, b) in enumerate(zip(geometry, geometry[1:])):
                u, v = nodes[i : i + 2]
                pa = (a["lat"], a["lon"])
                pb = (b["lat"], b["lon"])
                length = distance(pa, pb)
                if length < 0.1:
                    continue
                self.nodes[u] = pa
                self.nodes[v] = pb
                segment = {
                    "u": u,
                    "v": v,
                    "a": pa,
                    "b": pb,
                    "length": length,
                    "way": element["id"],
                    "directions": directions,
                    "name": tags.get("name", ""),
                }
                if 1 in directions:
                    self.graph[u].append((v, length))
                if -1 in directions:
                    self.graph[v].append((u, length))
                if directions:
                    for name in names:
                        self.roads[name].append(segment)
        self.names = sorted(self.roads)

    def candidates(self, address):
        parsed = address_parts(address)
        street = parsed["street"]
        match_type = "exact"
        if street not in self.roads:
            matches = get_close_matches(street, self.names, n=2, cutoff=0.9)
            if (
                not matches
                or len(matches) > 1
                and SequenceMatcher(None, street, matches[0]).ratio()
                - SequenceMatcher(None, street, matches[1]).ratio()
                < 0.05
            ):
                return [], {**parsed, "reason": "street_not_found_or_ambiguous"}
            street = matches[0]
            match_type = "fuzzy"
        segments = self.roads[street]
        anchors = [
            a
            for a in self.anchors[street]
            if not a["city"] or not parsed["city"] or a["city"] == parsed["city"]
        ]
        number = parsed["number"]
        targets = []
        if number is not None:
            targets = [
                (a["point"], "house_number", [a["osm_id"]])
                for a in anchors
                if a["number"] == number
            ]
            if not targets:
                # Bracketing only; no extrapolation beyond known numbers.
                lower = sorted(
                    (a for a in anchors if a["number"] < number),
                    key=lambda a: -a["number"],
                )
                upper = sorted(
                    (a for a in anchors if a["number"] > number),
                    key=lambda a: a["number"],
                )
                for a in lower[:2]:
                    for b in upper[:2]:
                        if (
                            distance(a["point"], b["point"]) > 500
                            or b["number"] - a["number"] > 1000
                        ):
                            continue
                        ratio = (number - a["number"]) / (b["number"] - a["number"])
                        point = tuple(
                            a["point"][i] + ratio * (b["point"][i] - a["point"][i])
                            for i in (0, 1)
                        )
                        targets.append(
                            (point, "number_interpolation", [a["osm_id"], b["osm_id"]])
                        )
        physical = []
        for point, method, anchor_ids in targets:
            for segment in segments:
                projected, ratio, gap = project(point, segment["a"], segment["b"])
                if gap <= 100:
                    physical.append(
                        {
                            "segment": segment,
                            "point": projected,
                            "ratio": ratio,
                            "gap": gap,
                            "method": method,
                            "anchors": anchor_ids,
                            "address_point": point,
                        }
                    )
        if physical:
            physical = sorted(physical, key=lambda c: c["gap"])[:4]
        else:
            # Street-only hypotheses. Never publish solely on this evidence.
            total = sum(s["length"] for s in segments)
            for fraction in (0.1, 0.3, 0.5, 0.7, 0.9):
                target = total * fraction
                for segment in segments:
                    if target <= segment["length"]:
                        ratio = target / segment["length"]
                        point = tuple(
                            segment["a"][i]
                            + ratio * (segment["b"][i] - segment["a"][i])
                            for i in (0, 1)
                        )
                        physical.append(
                            {
                                "segment": segment,
                                "point": point,
                                "ratio": ratio,
                                "gap": 0,
                                "method": "street_only",
                                "anchors": [],
                                "address_point": None,
                            }
                        )
                        break
                    target -= segment["length"]
        candidates = []
        for candidate in physical:
            for direction in candidate["segment"]["directions"]:
                candidates.append(
                    {
                        **candidate,
                        "direction": direction,
                        "unary": candidate["gap"] / 30
                        + (1 if match_type == "fuzzy" else 0),
                    }
                )
        return candidates, {
            **parsed,
            "matched_street": street,
            "match_type": match_type,
            "candidate_count": len(candidates),
        }

    @lru_cache(maxsize=100000)
    def path_distance(self, start, end):
        if start == end:
            return 0.0
        if distance(self.nodes[start], self.nodes[end]) > MAX_PATH:
            return math.inf
        # A* with Euclidean lower bound; directed topology enforces one-way roads.
        queue = [(0.0, 0.0, start)]
        best = {start: 0.0}
        while queue:
            _, cost, node = heapq.heappop(queue)
            if cost != best[node]:
                continue
            if node == end:
                return cost
            for neighbor, length in self.graph[node]:
                new = cost + length
                if new <= MAX_PATH and new < best.get(neighbor, math.inf):
                    best[neighbor] = new
                    heapq.heappush(
                        queue,
                        (
                            new + distance(self.nodes[neighbor], self.nodes[end]),
                            new,
                            neighbor,
                        ),
                    )
        return math.inf

    def transition(self, a, b):
        sa, sb = a["segment"], b["segment"]
        if (
            sa["u"] == sb["u"]
            and sa["v"] == sb["v"]
            and a["direction"] == b["direction"]
            and (b["ratio"] - a["ratio"]) * a["direction"] >= 0
        ):
            return abs(b["ratio"] - a["ratio"]) * sa["length"]
        end = sa["v"] if a["direction"] == 1 else sa["u"]
        start = sb["u"] if b["direction"] == 1 else sb["v"]
        tail = (1 - a["ratio"] if a["direction"] == 1 else a["ratio"]) * sa["length"]
        head = (b["ratio"] if b["direction"] == 1 else 1 - b["ratio"]) * sb["length"]
        return tail + self.path_distance(end, start) + head

    def resolve(self, lists):
        """Viterbi-like DP; unresolved streets split the sequence, never get skipped."""
        results = [None] * len(lists)
        start = 0
        while start < len(lists):
            if not lists[start]:
                start += 1
                continue
            end = start + 1
            while end < len(lists) and lists[end]:
                end += 1
            group = lists[start:end]
            forward = [[c["unary"] for c in group[0]]]
            parents = []
            matrices = []
            for previous, current in zip(group, group[1:]):
                matrix = [
                    [self.transition(a, b) / 150 for b in current] for a in previous
                ]
                matrices.append(matrix)
                costs = []
                ancestry = []
                for j, b in enumerate(current):
                    value, k = min(
                        (forward[-1][i] + matrix[i][j], i) for i in range(len(previous))
                    )
                    costs.append(value + b["unary"])
                    ancestry.append(k)
                forward.append(costs)
                parents.append(ancestry)
            if not any(math.isfinite(c) for c in forward[-1]):
                start = end
                continue
            backward = [[0.0] * len(group[-1])]
            for i in range(len(group) - 2, -1, -1):
                backward.append(
                    [
                        min(
                            matrices[i][j][k]
                            + group[i + 1][k]["unary"]
                            + backward[-1][k]
                            for k in range(len(group[i + 1]))
                        )
                        for j in range(len(group[i]))
                    ]
                )
            backward.reverse()
            chosen = min(range(len(group[-1])), key=lambda j: forward[-1][j])
            path = [chosen]
            for ancestry in reversed(parents):
                chosen = ancestry[chosen]
                path.append(chosen)
            path.reverse()
            for i, j in enumerate(path):
                candidate = group[i][j]
                total = forward[i][j] + backward[i][j]
                alternatives = [
                    forward[i][k] + backward[i][k]
                    for k, c in enumerate(group[i])
                    if distance(candidate["point"], c["point"]) > 40
                    or heading_difference(candidate, c) > 45
                ]
                margin = min(alternatives, default=total + 10) - total
                anchored = candidate["method"] != "street_only"
                neighbors = any(
                    c["method"] != "street_only"
                    for near in group[max(0, i - 2) : i]
                    for c in near
                ) and any(
                    c["method"] != "street_only"
                    for near in group[i + 1 : i + 3]
                    for c in near
                )
                # Missing direction or weak street-only evidence remains reviewable, unpublished.
                publish = margin >= 0.5 and (anchored or neighbors and margin >= 1.0)
                segment = candidate["segment"]
                ax, ay = xy(segment["a"])
                bx, by = xy(segment["b"])
                dx, dy = (bx - ax) * candidate["direction"], (by - ay) * candidate[
                    "direction"
                ]
                length = math.hypot(dx, dy)
                px, py = xy(candidate["point"])
                curb = ll((px + 3 * dy / length, py - 3 * dx / length))
                results[start + i] = {
                    "status": "estimated" if publish else "pending",
                    "lat": curb[0],
                    "lon": curb[1],
                    "method": candidate["method"],
                    "way_id": segment["way"],
                    "direction": candidate["direction"],
                    "bearing": math.degrees(math.atan2(dx, dy)) % 360,
                    "road_point": candidate["point"],
                    "address_point": candidate["address_point"],
                    "anchor_ids": candidate["anchors"],
                    "projection_distance_m": round(candidate["gap"], 2),
                    "margin": round(margin, 4) if math.isfinite(margin) else None,
                    "confidence": "medium" if anchored and publish else "low",
                    "reason": (
                        "address_and_directed_sequence"
                        if publish
                        else "ambiguous_direction_or_address"
                    ),
                    "curb_offset_m": 3,
                }
            start = end
        return results
