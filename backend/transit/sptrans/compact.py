"""Small versioned GTFS point catalogue, independent of operational data."""
import gzip
import json
import threading
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from . import store, viewport

_lock = threading.Lock()
_cache = {}

def encode(rows, revision):
    previous_lat = previous_lon = 0
    packed = []
    for stop in sorted(rows, key=lambda s: (s['lat'], s['lon'], s['id'])):
        lat, lon = round(stop['lat'] * 100000), round(stop['lon'] * 100000)
        packed.append([str(stop['id']), lat-previous_lat, lon-previous_lon, stop['name']])
        previous_lat, previous_lon = lat, lon
    return json.dumps(dict(version=1, revision=revision, scale=100000, rows=packed), ensure_ascii=False, separators=(',', ':')).encode()

def accepts_gzip(header):
    values = {}
    for item in header.lower().split(','):
        parts = item.strip().split(';')
        try:
            values[parts[0]] = next((float(p.strip()[2:]) for p in parts[1:] if p.strip().startswith('q=')), 1)
        except ValueError:
            values[parts[0]] = 0
    return values.get('gzip', values.get('*', 0)) > 0

@require_GET
def catalogue(request):
    revision = viewport.revision()
    etag = '"stops-v1-' + revision + '"'
    headers = {'ETag': etag, 'Cache-Control': 'private, no-cache', 'Vary': 'Accept-Encoding'}
    if any(tag.strip().removeprefix('W/') in (etag, '*') for tag in request.headers.get('If-None-Match', '').split(',')):
        return HttpResponse(status=304, headers=headers)
    with _lock:
        if revision not in _cache:
            with store.connection() as db:
                raw = encode(store.in_bounds(db, -90, -180, 90, 180), revision)
            _cache.clear()
            _cache[revision] = (raw, gzip.compress(raw, compresslevel=9, mtime=0))
        raw, compressed = _cache[revision]
    if accepts_gzip(request.headers.get('Accept-Encoding', '')):
        headers['Content-Encoding'] = 'gzip'
        raw = compressed
    return HttpResponse(raw, content_type='application/json', headers=headers)
