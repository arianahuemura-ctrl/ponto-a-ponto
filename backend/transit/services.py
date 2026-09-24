"""Consultas a provedores OSM, com cache e URLs controladas pelo servidor."""

import json
import threading
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
_lock = threading.Lock()
_last_geocode = 0.0


class ProviderError(Exception):
    pass


def request_json(url, data=None):
    headers = {"User-Agent": settings.OSM_USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        with urlopen(Request(url, data=data, headers=headers), timeout=100) as response:
            return json.load(response)
    except (URLError, TimeoutError, OSError, ValueError) as error:
        raise ProviderError(
            "O provedor de mapas está indisponível. Tente novamente."
        ) from error


def geocode(address, state):
    global _last_geocode
    params = urlencode(
        {
            "q": f"{address}, {state}, Brasil",
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "br",
        }
    )
    import hashlib

    key = "geocode:" + hashlib.sha256(params.encode()).hexdigest()
    with _lock:
        cached = cache.get(key)
        if cached is not None:
            return cached
        time.sleep(max(0, 1.1 - (time.monotonic() - _last_geocode)))
        try:
            data = request_json("https://nominatim.openstreetmap.org/search?" + params)
        finally:
            _last_geocode = time.monotonic()
        if not isinstance(data, list):
            raise ProviderError("Resposta inválida do serviço de endereços.")
        if not data:
            return None
        try:
            result = {
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
                "label": data[0]["display_name"],
            }
        except (KeyError, TypeError, ValueError) as error:
            raise ProviderError("Resposta inválida do serviço de endereços.") from error
        cache.set(key, result, 86400)
        return result


def nearby_query(lat, lon):
    around = f"(around:1000,{lat},{lon})"
    return f"""[out:json][timeout:90];
(
 node{around}["highway"="bus_stop"];
 node{around}["public_transport"="platform"]["bus"!="no"];
 node{around}["public_transport"="stop_position"]["bus"!="no"];
 way{around}["public_transport"="platform"]["bus"!="no"];
)->.nearbyStops;
rel{around}["type"="route"]["route"="bus"]->.routes;
(.nearbyStops;.routes;);
out body geom;"""


def nearby(lat, lon):
    key = f"nearby:{lat:.5f}:{lon:.5f}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    payload = urlencode({"data": nearby_query(lat, lon)}).encode()
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            data = request_json(endpoint, payload)
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("elements"), list)
                or data.get("remark")
            ):
                raise ProviderError("Resposta incompleta do Overpass.")
            cache.set(key, data, 300)
            return data
        except ProviderError:
            continue
    raise ProviderError(
        "Não foi possível consultar os pontos e linhas no OSM. Tente novamente."
    )
