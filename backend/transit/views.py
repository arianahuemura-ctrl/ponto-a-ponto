import math
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from . import services

STATES = set(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)


@require_GET
def health(request):
    return JsonResponse(
        {
            "status": "ok",
            "backend": "django",
            "source": "OpenStreetMap",
            "realtime": False,
        }
    )


@require_GET
def geocode(request):
    address = request.GET.get("address", "").strip()
    state = request.GET.get("state", "SP").upper()
    if not address or len(address) > 300 or state not in STATES:
        return JsonResponse(
            {"error": "Informe um endereço de até 300 caracteres e uma UF válida."},
            status=400,
        )
    try:
        result = services.geocode(address, state)
        if result is None:
            return JsonResponse(
                {
                    "error": f"Endereço não encontrado em {state}. Inclua cidade e número."
                },
                status=404,
            )
        return JsonResponse(result)
    except services.ProviderError as error:
        return JsonResponse({"error": str(error)}, status=502)


@require_GET
def nearby(request):
    try:
        lat, lon = float(request.GET["lat"]), float(request.GET["lon"])
        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
            and -90 <= lat <= 90
            and -180 <= lon <= 180
        ):
            raise ValueError
    except (KeyError, ValueError, TypeError):
        return JsonResponse({"error": "Latitude ou longitude inválida."}, status=400)
    try:
        return JsonResponse(services.nearby(lat, lon))
    except services.ProviderError as error:
        return JsonResponse({"error": str(error)}, status=502)


@require_GET
def index(request):
    path = settings.BASE_DIR / "frontend/dist/index.html"
    if not path.exists():
        return HttpResponse(
            "Compile o frontend: cd frontend && npm ci && npm run build",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    return FileResponse(path.open("rb"), content_type="text/html; charset=utf-8")
