import hashlib
import json
from collections import Counter, defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from transit.geolocation import StreetIndex, VERSION, distance
from transit.models import GeolocationRun, StopEstimate, Route, Stop, SourceDocument


def publish_estimates(checksum, run):
    # Coalescer somente estimativas coerentes do mesmo ID, nunca IDs de provedores diferentes.
    by_stop = defaultdict(list)
    for estimate in (
        StopEstimate.objects.filter(
            status="estimated", run__source_hash=checksum, run__algorithm=VERSION
        )
        .filter(Q(run=run) | Q(run__summary__state="complete"))
        .select_related("stop")
    ):
        by_stop[estimate.stop_id].append(estimate)
    published = conflicts = 0
    with transaction.atomic():
        for stop in Stop.objects.filter(source="cittamobi"):
            if stop.data.get("geolocation", {}).get("status") == "validated":
                continue
            estimates = by_stop.get(stop.pk, [])
            existing = stop.data.get("geolocation", {})
            if not estimates:
                if str(existing.get("algorithm", "")).startswith(
                    "osm-address-directed-"
                ):
                    stop.lat = stop.lon = None
                    stop.data = {
                        **stop.data,
                        "geolocation": {
                            "status": "pending",
                            "algorithm": VERSION,
                            "run": run.pk,
                        },
                    }
                    stop.save(update_fields=["lat", "lon", "data"])
                continue
            points = [(e.lat, e.lon) for e in estimates]
            separation = max(
                (distance(a, b) for a in points for b in points), default=0
            )
            bearings = [
                e.evidence["bearing"] for e in estimates if "bearing" in e.evidence
            ]
            angular_disagreement = max(
                (abs((a - b + 180) % 360 - 180) for a in bearings for b in bearings),
                default=0,
            )
            if separation > 60 or angular_disagreement > 90:
                stop.lat = stop.lon = None
                state = "conflict"
                conflicts += 1
            else:
                chosen = min(
                    estimates,
                    key=lambda e: sum(
                        distance((e.lat, e.lon), point) for point in points
                    ),
                )
                stop.lat, stop.lon = chosen.lat, chosen.lon
                state = "estimated"
                published += 1
            stop.data = {
                **stop.data,
                "geolocation": {
                    "status": state,
                    "algorithm": VERSION,
                    "run": run.pk,
                    "source_hash": checksum,
                    "max_disagreement_m": round(separation, 2),
                    "max_heading_disagreement_deg": round(angular_disagreement, 2),
                    "route_estimates": len(estimates),
                    "confidence": "medium_or_low",
                    "approximate": True,
                },
            }
            stop.save(update_fields=["lat", "lon", "data"])
    return published, conflicts


class Command(BaseCommand):
    help = (
        "Estima posições das paradas por endereço OSM e sequência dirigida da variante."
    )

    def add_arguments(self, parser):
        parser.add_argument("--route", help="ID de uma variante, para diagnóstico")
        parser.add_argument(
            "--download",
            action="store_true",
            help="Atualiza o recorte de ruas/endereços antes do processamento",
        )

    def handle(self, *args, **options):
        self.run = None
        try:
            return self.process(*args, **options)
        except (Exception, KeyboardInterrupt) as exc:
            if self.run:
                self.run.summary = {
                    "state": "failed",
                    "error": str(exc) or "interrupted",
                }
                self.run.save(update_fields=["summary"])
            raise

    def process(self, *args, **options):
        folder = settings.BASE_DIR / "fonts"
        if options["download"]:
            import subprocess, sys

            subprocess.run(
                [sys.executable, str(folder / "download_geolocation.py")], check=True
            )
        source = folder / "geolocation_osm.json"
        if not source.exists():
            raise CommandError("Baixe o recorte com --download")
        body = source.read_bytes()
        checksum = hashlib.sha256(body).hexdigest()
        metadata = json.loads((folder / "geolocation_osm.meta.json").read_text())
        if metadata["sha256"] != checksum:
            raise CommandError("Checksum do recorte inválido")
        raw = json.loads(body)
        if raw.get("remark"):
            raise CommandError("Recorte Overpass incompleto")
        index = StreetIndex(raw["elements"])
        routes = (
            Route.objects.filter(source="cittamobi")
            .prefetch_related("sequence__stop")
            .order_by("pk")
        )
        if options["route"]:
            routes = routes.filter(pk=options["route"])
        if not routes.exists():
            raise CommandError("Nenhuma variante encontrada")
        run = GeolocationRun.objects.create(
            algorithm=VERSION, source_hash=checksum, summary={"state": "running"}
        )
        self.run = run
        SourceDocument.objects.update_or_create(
            pk="osm-geolocation-" + checksum[:40],
            defaults={
                "provider": "osm_geolocation",
                "url": metadata["url"],
                "kind": "geocoding_extract",
                "status": "ok",
                "metadata": metadata,
            },
        )
        cache = {}
        counts = Counter()
        reasons = Counter()
        all_results = []
        for n, route in enumerate(routes, 1):
            sequence = list(route.sequence.all())
            candidates = []
            notes = []
            for entry in sequence:
                address = entry.stop.data.get("address", entry.stop.name)
                if address not in cache:
                    cache[address] = index.candidates(address)
                options_for_stop, note = cache[address]
                candidates.append(options_for_stop)
                notes.append(note)
            resolved = index.resolve(candidates)
            entries = []
            for entry, note, result in zip(sequence, notes, resolved):
                result = result or {
                    "status": "pending",
                    "reason": note.get("reason", "no_directed_path"),
                }
                evidence = {
                    **note,
                    **result,
                    "algorithm": VERSION,
                    "source_hash": checksum,
                    "osm_timestamp": metadata.get("osm_timestamp"),
                    "source_address": entry.stop.data.get("address", entry.stop.name),
                }
                entries.append(
                    StopEstimate(
                        route=route,
                        stop_id=entry.stop_id,
                        position=entry.position,
                        run=run,
                        status=result["status"],
                        lat=result.get("lat"),
                        lon=result.get("lon"),
                        evidence=evidence,
                    )
                )
                counts[result["status"]] += 1
                reasons[result["reason"]] += 1
                all_results.append(
                    {
                        "route": route.pk,
                        "stop": entry.stop_id,
                        "position": entry.position,
                        **evidence,
                    }
                )
            with transaction.atomic():
                StopEstimate.objects.filter(route=route).delete()
                StopEstimate.objects.bulk_create(entries)
            self.stdout.write(
                f"{n}/{routes.count()} {route.code} {route.name}: {sum(e.status=='estimated' for e in entries)}/{len(entries)} estimadas"
            )
        published, conflicts = publish_estimates(checksum, run)
        run.summary = {
            "state": "complete",
            "occurrences": dict(counts),
            "reasons": dict(reasons),
            "published_stops": published,
            "conflicting_stops": conflicts,
            "addresses_consulted": len(cache),
            "osm_address_anchors": index.address_count,
            "route_filter": options["route"],
            "parameters": {
                "max_path_m": 8000,
                "max_projection_m": 100,
                "curb_offset_m": 3,
                "consensus_m": 60,
                "heading_conflict_deg": 90,
            },
        }
        run.save(update_fields=["summary"])
        output = folder / "geolocation_runs"
        output.mkdir(exist_ok=True)
        (output / f"run-{run.pk}.json").write_text(
            json.dumps(
                {
                    "id": run.pk,
                    "source": metadata,
                    "summary": run.summary,
                    "results": all_results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        self.stdout.write(json.dumps(run.summary, ensure_ascii=False, indent=2))
