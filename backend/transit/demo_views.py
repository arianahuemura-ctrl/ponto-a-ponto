import io
import json
import math
from urllib.parse import urlencode

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

from .network import dataset, destination_candidates, snapshot, trips
from .planner import alternatives
from .runtime import status
from .geometry import segments_for
from django.views.decorators.cache import never_cache


def error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def time_param(request):
    value = int(request.GET.get("at", dataset()["default_time"]))
    if not 0 <= value < 86400:
        raise ValueError("Horário fora do dia de demonstração.")
    return status()["at"]


def stop_param(value):
    if value not in {s["id"] for s in dataset()["stops"]}:
        raise ValueError("Parada não encontrada no recorte de demonstração.")
    return value


@require_GET
@never_cache
@ensure_csrf_cookie
def network(request):
    state = status()
    return JsonResponse(
        {
            **dataset(),
            "routes": dataset()["routes"] if state["enabled"] else [],
            **state,
        }
    )


@require_GET
def stop(request, stop_id):
    try:
        stop_param(stop_id)
    except ValueError as exc:
        return error(str(exc), 404)
    network = dataset()
    return JsonResponse(
        {
            "stop": next(s for s in network["stops"] if s["id"] == stop_id),
            "routes": [r for r in network["routes"] if stop_id in r["stops"]]
            if status()["enabled"]
            else [],
            "mode": "simulation",
        }
    )


@require_GET
@never_cache
def board(request):
    try:
        at = time_param(request)
        origin = (
            stop_param(request.GET["origin"]) if request.GET.get("origin") else None
        )
    except (ValueError, KeyError):
        return error("Horário ou parada inválidos.")
    state = status()
    if not state["enabled"]:
        return JsonResponse(
            {
                **state,
                "lines": [],
                "vehicles": [],
                "message": "Previsões indisponíveis no momento.",
            }
        )
    return JsonResponse({**snapshot(at, origin), **state})


@require_GET
@never_cache
def journey(request):
    state = status()
    if not state["enabled"]:
        return JsonResponse(
            {
                **state,
                "itineraries": [],
                "message": "Previsões indisponíveis no momento.",
            }
        )
    try:
        origin = stop_param(request.GET["origin"])
        departure = time_param(request)
        limit = int(request.GET.get("max_transfers", 4))
        if not 0 <= limit <= 4:
            raise ValueError
        if request.GET.get("destination"):
            destinations = {stop_param(request.GET["destination"]): 0}
        else:
            lat, lon = float(request.GET["lat"]), float(request.GET["lon"])
            if not (
                math.isfinite(lat)
                and math.isfinite(lon)
                and -90 <= lat <= 90
                and -180 <= lon <= 180
            ):
                raise ValueError
            destinations = destination_candidates(lat, lon)
    except (ValueError, KeyError, TypeError):
        return error("Informe origem, destino, horário e limite de trocas válidos.")
    if not destinations:
        return JsonResponse(
            {
                "itineraries": [],
                "mode": "simulation",
                "message": "Nenhuma parada do recorte a até 500 m do destino. Escolha outro local.",
            }
        )
    result = alternatives(
        trips(),
        origin,
        destinations,
        departure,
        transfer_seconds=dataset()["transfer_seconds"],
        max_transfers=limit,
    )
    for itinerary in result:
        for leg in itinerary["legs"]:
            leg["segments"] = segments_for(leg["route_id"], leg["stops"])
    return JsonResponse(
        {
            "at": departure,
            "itineraries": result,
            "mode": "simulation",
            "message": ""
            if result
            else "Não há conexão nos horários simulados. Tente outro horário ou permita baldeações.",
        }
    )


@require_GET
def qr(request, stop_id):
    try:
        stop_param(stop_id)
    except ValueError as exc:
        return error(str(exc), 404)
    base = settings.PUBLIC_BASE_URL or request.build_absolute_uri("/").rstrip("/")
    url = base.rstrip("/") + "/?" + urlencode({"stop": stop_id})
    image = qrcode.make(
        url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=4
    )
    buffer = io.BytesIO()
    image.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type="image/svg+xml")
    response["Content-Disposition"] = 'inline; filename="parada-qr.svg"'
    return response


@require_http_methods(["GET", "POST"])
@ensure_csrf_cookie
def evaluation(request):
    from .models import Evaluation

    if request.method == "GET":
        return JsonResponse(
            {
                "questions": [
                    "O QR Code identifica a origem sem conhecimento prévio?",
                    "Os próximos ônibus e a comparação entre linhas estão claros?",
                    "O destino e as baldeações são fáceis de entender?",
                    "Quais fontes operacionais poderiam substituir a simulação?",
                    "Os favoritos ajudam nos deslocamentos cotidianos?",
                ]
            }
        )
    try:
        payload = json.loads(request.body)
        notes = payload.get("notes", "")
        scenario = payload.get("scenario", "")
        if (
            not isinstance(notes, str)
            or not 1 <= len(notes.strip()) <= 5000
            or not isinstance(scenario, str)
            or len(scenario) > 200
        ):
            raise ValueError
        entry = Evaluation.objects.create(notes=notes.strip(), scenario=scenario)
    except (ValueError, TypeError, AttributeError):
        return error("Informe observações de até 5.000 caracteres.")
    return JsonResponse({"saved": True, "id": entry.pk}, status=201)
