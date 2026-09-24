from django.db.models import Count, Q, F
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Route, Stop, SourceDocument, StopEstimate


@require_GET
def catalogue(request):
    query = request.GET.get("q", "").strip()[:200]
    routes = (
        Route.objects.filter(simulated=False)
        .filter(Q(name__icontains=query) | Q(code__icontains=query))
        .annotate(stop_count=Count("sequence"))
        .order_by("source", "code", "name")
    )
    return JsonResponse(
        {
            "routes": [
                dict(
                    id=r.pk,
                    code=r.code,
                    name=r.name,
                    source=r.source,
                    stop_count=r.stop_count,
                    source_url=r.data.get("source_url", ""),
                    routable=r.routable,
                )
                for r in routes
            ],
            "counts": dict(
                stops=Stop.objects.exclude(source="demo").count(),
                located_stops=Stop.objects.exclude(source="demo")
                .filter(lat__isnull=False)
                .count(),
                variants=Route.objects.filter(simulated=False).count(),
            ),
            "sources": [
                dict(
                    provider=d.provider,
                    url=d.url,
                    kind=d.kind,
                    status=d.status,
                    retrieved_at=d.metadata.get("retrieved_at"),
                    error=d.metadata.get("error", ""),
                )
                for d in SourceDocument.objects.exclude(
                    kind__in=["itinerary_pdf", "official_itinerary", "official_pdf"]
                ).exclude(url__contains="/linha/")
            ],
        }
    )


@require_GET
def route_detail(request, route_id):
    route = Route.objects.filter(pk=route_id).first()
    if route is None:
        return JsonResponse({"error": "Linha não encontrada"}, status=404)
    # Somente a execução publicada para a parada; diagnósticos ficam na auditoria.
    estimates = {
        e.position: e
        for e in StopEstimate.objects.filter(
            route=route,
            run__summary__state="complete",
            run_id=F("stop__data__geolocation__run"),
        ).select_related("stop", "run")
        if not e.run.summary.get("route_filter")
        and e.evidence.get("source_address") == e.stop.data.get("address", e.stop.name)
    }
    return JsonResponse(
        {
            "id": route.pk,
            "code": route.code,
            "name": route.name,
            "source": route.source,
            "source_url": route.data.get("source_url", ""),
            "schedule": route.data.get("schedule", {}),
            "street_itinerary": route.data.get("street_itinerary", ""),
            "routable": route.routable,
            "stops": [
                dict(
                    id=e.stop_id,
                    name=e.stop.name,
                    lat=e.stop.lat,
                    lon=e.stop.lon,
                    position=e.position,
                    geolocation=e.stop.data.get("geolocation", {}),
                    route_estimate=(
                        {
                            "status": estimates[e.position].status,
                            "lat": estimates[e.position].lat,
                            "lon": estimates[e.position].lon,
                            "evidence": estimates[e.position].evidence,
                        }
                        if e.position in estimates and estimates[e.position].stop_id == e.stop_id
                        else None
                    ),
                )
                for e in route.sequence.select_related("stop").all()
            ],
        }
    )
