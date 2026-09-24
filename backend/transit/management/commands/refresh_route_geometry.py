"""Atualiza uma vez as geometrias viárias; o passageiro usa a cópia local."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from transit.network import dataset


class Command(BaseCommand):
    help = "Obtém trajetos pelas ruas via OSRM e salva geometrias locais do cenário."

    def add_arguments(self, parser):
        parser.add_argument(
            "--endpoint", default="https://router.project-osrm.org/route/v1/driving"
        )

    def handle(self, *args, **options):
        network = dataset()
        stops = {s["id"]: s for s in network["stops"]}
        routes = {}
        for route in network["routes"]:
            coords = ";".join(
                f"{stops[id]['lon']},{stops[id]['lat']}" for id in route["stops"]
            )
            url = (
                options["endpoint"].rstrip("/")
                + "/"
                + coords
                + "?"
                + urlencode(
                    {
                        "overview": "full",
                        "geometries": "geojson",
                        "steps": "true",
                        "continue_straight": "false",
                    }
                )
            )
            try:
                with urlopen(
                    Request(
                        url, headers={"User-Agent": "MauaBusMap/0.3 academic prototype"}
                    ),
                    timeout=60,
                ) as response:
                    data = json.load(response)
                if data.get("code") != "Ok":
                    raise ValueError(data.get("code"))
                result = data["routes"][0]
                segments = []
                for i, leg in enumerate(result["legs"]):
                    points = []
                    streets = []
                    for step in leg["steps"]:
                        for lon, lat in step["geometry"]["coordinates"]:
                            point = [lat, lon]
                            if not points or point != points[-1]:
                                points.append(point)
                        if step.get("name") and (
                            not streets or streets[-1] != step["name"]
                        ):
                            streets.append(step["name"])
                    if len(points) < 3:
                        raise ValueError("Geometria viária insuficiente")
                    segments.append(
                        {
                            "from": route["stops"][i],
                            "to": route["stops"][i + 1],
                            "points": points,
                            "streets": streets,
                            "distance_m": leg["distance"],
                        }
                    )
                routes[route["id"]] = {
                    "segments": segments,
                    "distance_m": result["distance"],
                    "waypoints": [
                        {
                            "lat": w["location"][1],
                            "lon": w["location"][0],
                            "snap_distance_m": w["distance"],
                        }
                        for w in data["waypoints"]
                    ],
                }
                self.stdout.write(
                    f"{route['id']}: {sum(len(s['points']) for s in segments)} pontos, {result['distance']:.0f} m"
                )
            except (OSError, ValueError, KeyError, IndexError) as exc:
                raise CommandError(
                    f"Falha ao obter {route['id']}; arquivo existente preservado: {exc}"
                ) from exc
            time.sleep(1)
        output = {
            "provider": "OSRM / OpenStreetMap",
            "endpoint": options["endpoint"],
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "profile": "driving",
            "note": "Trajetos viários calculados para o cenário simulado; não são itinerários oficiais de ônibus. Tempos continuam mockados.",
            "routes": routes,
        }
        path = Path(__file__).resolve().parents[2] / "data/route_geometry.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        temporary.replace(path)
        self.stdout.write(
            self.style.SUCCESS(
                "Geometrias salvas. Reinicie o Django para recarregar o cache."
            )
        )
