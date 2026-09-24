"""Importação transacional: IDs estáveis por fonte, ordem e proveniência preservadas."""

import hashlib
import json
import math
from django.db import transaction
from .models import (
    Stop,
    Route,
    RouteStop,
    SourceDocument,
    NetworkMetadata,
    StopEstimate,
)


def validate_stop(s):
    lat, lon = s.get("lat"), s.get("lon")
    if (lat is None) != (lon is None):
        raise ValueError(f"Coordenadas incompletas: {s['id']}")
    if lat is not None and not (
        math.isfinite(lat)
        and math.isfinite(lon)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    ):
        raise ValueError(f"Coordenadas inválidas: {s['id']}")


@transaction.atomic
def import_network(payload, source="demo", simulated=False):
    for key in ("stops", "routes"):
        ids = [item["id"] for item in payload.get(key, [])]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Identificadores duplicados em {key}")
    for s in payload.get("stops", []):
        validate_stop(s)
        s = dict(s)
        previous = Stop.objects.filter(pk=s["id"]).first()
        if previous and previous.data.get("geolocation"):
            previous_address = previous.data.get("address", previous.name)
            incoming_address = s.get("address", s["name"])
            if previous_address == incoming_address and s.get("lat") is None:
                s["lat"], s["lon"] = previous.lat, previous.lon
                s["geolocation"] = previous.data["geolocation"]
            elif previous_address != incoming_address:
                StopEstimate.objects.filter(stop=previous).delete()
        Stop.objects.update_or_create(
            pk=s["id"],
            defaults=dict(
                name=s["name"],
                lat=s.get("lat"),
                lon=s.get("lon"),
                source=s.get("source", source),
                data=s,
            ),
        )
    for r in payload.get("routes", []):
        ids = r.get("stops", [])
        if set(ids) - set(Stop.objects.filter(pk__in=ids).values_list("pk", flat=True)):
            raise ValueError(f"Parada ausente na linha {r['id']}")
        durations = r.get("durations", [])
        if durations and (
            len(durations) != len(ids) - 1
            or any(type(d) is not int or d <= 0 for d in durations)
        ):
            raise ValueError(f"Durações inválidas: {r['id']}")
        routable = bool(
            len(ids) >= 2
            and durations
            and not Stop.objects.filter(pk__in=ids, lat__isnull=True).exists()
        )
        if routable and (type(r.get("headway")) is not int or r["headway"] <= 0):
            raise ValueError("Intervalo inválido")
        route, _ = Route.objects.update_or_create(
            pk=r["id"],
            defaults=dict(
                name=r["name"],
                code=r.get("code", ""),
                source=r.get("source", source),
                simulated=simulated,
                routable=routable,
                data=r,
            ),
        )
        old_ids = list(route.sequence.values_list("stop_id", flat=True))
        if old_ids and old_ids != ids:
            StopEstimate.objects.filter(route=route).delete()
            for affected in Stop.objects.filter(
                pk__in=set(old_ids + ids), source="cittamobi"
            ):
                if affected.data.get("geolocation", {}).get(
                    "status"
                ) != "validated" and affected.data.get("geolocation"):
                    affected.lat = affected.lon = None
                    affected.data = {
                        **affected.data,
                        "geolocation": {
                            "status": "pending",
                            "reason": "route_sequence_changed",
                        },
                    }
                    affected.save(update_fields=["lat", "lon", "data"])
        route.sequence.all().delete()
        segments = r.get("segments", [])
        RouteStop.objects.bulk_create(
            [
                RouteStop(
                    route=route,
                    stop_id=sid,
                    position=i,
                    duration=durations[i] if i < len(durations) else None,
                    segment=segments[i] if i < len(segments) else {},
                )
                for i, sid in enumerate(ids)
            ]
        )
    return dict(
        stops=len(payload.get("stops", [])), routes=len(payload.get("routes", []))
    )


def import_demo(root):
    payload = json.loads((root / "backend/transit/data/demo.json").read_text())
    geometry = json.loads(
        (root / "backend/transit/data/route_geometry.json").read_text()
    )
    for route in payload["routes"]:
        route["segments"] = geometry["routes"].get(route["id"], {}).get("segments", [])
    payload["default_origin"] = payload["stops"][0]["id"]
    result = import_network(payload, simulated=True)
    NetworkMetadata.objects.update_or_create(
        name="default",
        defaults={
            "data": {k: v for k, v in payload.items() if k not in ("stops", "routes")}
        },
    )
    return result


@transaction.atomic
def import_collected(folder):
    payload = json.loads((folder / "collected.json").read_text())
    for d in payload["documents"]:
        content = ""
        if d.get("status") == "ok" and d.get("path"):
            path = (folder / d["path"]).resolve()
            if not path.is_relative_to(folder.resolve()):
                raise ValueError("Caminho externo ao diretório de fontes")
            body = path.read_bytes()
            if hashlib.sha256(body).hexdigest() != d["sha256"]:
                raise ValueError(f"Checksum inválido: {path}")
            if "pdf" in d.get("content_type", ""):
                import subprocess

                try:
                    extraction = subprocess.run(
                        ["pdftotext", "-layout", str(path), "-"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=True,
                    )
                    content = extraction.stdout
                except (OSError, subprocess.SubprocessError) as exc:
                    d = {**d, "text_extraction_error": str(exc)}
            else:
                from fonts.collect import clean, decode
                import re

                content = clean(
                    re.sub(
                        r"<(script|style)\b[^>]*>.*?</\1>",
                        "",
                        decode(body),
                        flags=re.S | re.I,
                    )
                )
        SourceDocument.objects.update_or_create(
            pk=d["id"],
            defaults=dict(
                provider=d["provider"],
                url=d["url"],
                kind=d["kind"],
                status=d["status"],
                metadata=d,
                content=content,
            ),
        )
    return import_network(payload, source="external")


@transaction.atomic
def import_osm(path):
    raw = json.loads(path.read_text())
    elements = raw["elements"]
    stops = []
    for e in elements:
        tags = e.get("tags", {})
        if (
            e["type"] == "relation"
            or tags.get("train") == "yes"
            or tags.get("bus") == "no"
        ):
            continue
        if not (
            tags.get("highway") == "bus_stop"
            or tags.get("amenity") == "bus_station"
            or tags.get("public_transport") in ("platform", "stop_position")
        ):
            continue
        coord = e if "lat" in e else e.get("center", {})
        sid = f"{e['type']}:{e['id']}"
        stops.append(
            dict(
                id=sid,
                name=tags.get("name", tags.get("ref", "Parada OSM " + str(e["id"]))),
                lat=coord.get("lat"),
                lon=coord.get("lon"),
                source="osm",
                osm_url=f"https://www.openstreetmap.org/{e['type']}/{e['id']}",
                tags=tags,
            )
        )
    routes = []
    for e in elements:
        tags = e.get("tags", {})
        if e["type"] != "relation" or tags.get("route") != "bus":
            continue
        # O recorte não contém todos os membros: não inventar uma sequência completa.
        routes.append(
            dict(
                id=f"osm:relation:{e['id']}",
                name=tags.get("name", "Linha OSM"),
                code=tags.get("ref", ""),
                source="osm",
                stops=[],
                members=e.get("members", []),
                tags=tags,
                source_url=f"https://www.openstreetmap.org/relation/{e['id']}",
                incomplete=True,
            )
        )
    result = import_network(dict(stops=stops, routes=routes), "osm")
    SourceDocument.objects.update_or_create(
        pk="osm-snapshot",
        defaults=dict(
            provider="osm",
            url="https://www.openstreetmap.org/copyright",
            kind="geographic",
            status="ok",
            metadata={
                "timestamp": raw.get("osm3s", {}),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "path": str(path),
                "license": "ODbL",
            },
        ),
    )
    return result
