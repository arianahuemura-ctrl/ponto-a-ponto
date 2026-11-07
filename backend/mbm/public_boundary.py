"""Restrições aplicadas somente ao processo público, antes dos arquivos estáticos."""
import json
from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect, JsonResponse


def public_payload(value):
    if isinstance(value, dict):
        return {key: ("Planejador alternativo utilizado; diagnóstico disponível apenas no servidor."
                      if key in {"planner_fallback", "unavailable_reason"} and item
                      else public_payload(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [public_payload(item) for item in value]
    return value


def public_chunks(chunks, event_stream=False):
    def encode(line):
        if event_stream:
            line = line.removeprefix(b"data: ")
        data = json.dumps(public_payload(json.loads(line))).encode()
        return b"data: " + data + b"\n\n" if event_stream else data + b"\n"
    pending = b""
    for chunk in chunks:
        pending += chunk
        while b"\n" in pending:
            line, pending = pending.split(b"\n", 1)
            if line.strip():
                yield encode(line)
    if pending.strip():
        yield encode(pending)


class PublicBoundary:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()  # Valida ALLOWED_HOSTS inclusive para assets.
        if settings.PUBLIC_HOST and host.split(":")[0] == settings.PUBLIC_HOST and not request.is_secure():
            return HttpResponsePermanentRedirect("https://" + settings.PUBLIC_HOST + request.get_full_path())
        if request.path.rstrip("/") == "/admin" or request.path.startswith("/admin/") or request.path.rstrip("/") in {"/api/demo/evaluation", "/explorar"}:
            return HttpResponse(status=404)
        # Escritas públicas limitadas aos canais voluntários; cada endpoint mantém
        # validação, limites e proteção CSRF próprios.
        public_posts = {"/api/usability/", "/api/research/feedback/", "/api/research/requests/"}
        if request.method not in {"GET", "HEAD"} and not (request.method == "POST" and request.path in public_posts):
            return HttpResponse(status=405, headers={"Allow": "GET, HEAD"})
        response = self.get_response(request)
        response['X-Frame-Options']='DENY'
        response['Content-Security-Policy']="frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        response['Content-Security-Policy-Report-Only']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://tile.openstreetmap.org; connect-src 'self'; font-src 'self' data:; frame-ancestors 'none'"
        if response.status_code >= 500 and request.path.startswith("/api/"):
            return JsonResponse({"error": "Serviço temporariamente indisponível."}, status=response.status_code)
        if response.streaming and response.get("Content-Type", "").startswith(("application/x-ndjson", "text/event-stream")):
            response.streaming_content = public_chunks(response.streaming_content,
                event_stream=response["Content-Type"].startswith("text/event-stream"))
        elif not response.streaming and response.get("Content-Type", "").startswith("application/json") and not response.get("Content-Encoding"):
            response.content = json.dumps(public_payload(json.loads(response.content)))
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        return response
