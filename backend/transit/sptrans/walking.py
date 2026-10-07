"""Pedestrian routes via the FOSSGIS OSRM foot instance (never the car profile)."""
import json
import math
import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path
import time
from urllib.request import Request, urlopen
from urllib.error import URLError
from django.core.cache import cache
from .directions import distance

def reserve_request():
    """Share the public-provider rate limit between local Django workers."""
    folder = Path(tempfile.gettempdir()) / f"pap-routing-{getattr(os, 'getuid', lambda: 'local')()}"
    folder.mkdir(mode=0o700, exist_ok=True)
    try:
        with sqlite3.connect(folder / 'rate.sqlite3', timeout=0.2) as db:
            db.execute('CREATE TABLE IF NOT EXISTS rate (id INTEGER PRIMARY KEY, last REAL)')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT last FROM rate WHERE id=1').fetchone()
            now = time.time()
            if row and now-row[0]<1: return False
            db.execute('INSERT OR REPLACE INTO rate VALUES (1,?)',(now,))
        return True
    except sqlite3.Error:
        return False

MAX_DISTANCE = 5000
WALK_METERS_PER_MINUTE = 4000 / 60


def route(origin, destination, wait_for_slot=False):
    a,b = (origin['lat'],origin['lon']), (destination['lat'],destination['lon'])
    if origin['id'] == destination['id']:
        return {'available':False,'message':'Você já está no ponto de destino.'}
    if distance(a,b)>MAX_DISTANCE:
        return {'available':False,'message':'A consulta de caminhada direta atende destinos a até 5 km em linha reta.'}
    key = "pap.walk.v2:" + hashlib.sha256(f"{a}:{b}".encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None: return cached
    try:
        reserved=reserve_request()
        if not reserved and wait_for_slot:
            time.sleep(1.05)
            reserved=reserve_request()
        if not reserved:
            return {'available':False,'message':'Consulta de caminhada ocupada. Tente novamente em instantes.'}
        coordinates=f"{a[1]},{a[0]};{b[1]},{b[0]}"
        url=f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/{coordinates}?overview=full&geometries=geojson&steps=false"
        request=Request(url,headers={'User-Agent':'Ponto-a-Ponto/1.0 (UNIVESP academic pedestrian routing)','Accept':'application/json'})
        with urlopen(request,timeout=8) as response: data=json.load(response)
        if data.get('code')!='Ok' or not data.get('routes'): raise ValueError()
        result=data['routes'][0]
        waypoints=data['waypoints']
        if len(waypoints)!=2 or any(float(w['distance'])>30 for w in waypoints): raise ValueError()
        geometry=[[float(c[1]),float(c[0])] for c in result['geometry']['coordinates']]
        if len(geometry)<2 or any(not math.isfinite(v) for p in geometry for v in p): raise ValueError()
        access=distance(a,geometry[0])+distance(b,geometry[-1])
        meters=float(result['distance'])
        if not math.isfinite(meters) or meters<0 or (meters<5 and distance(a,b)>10): raise ValueError()
        # Same assumed walking speed for all options; snapped access is explicitly separate.
        result={'available':True,'mode':'walk','geometry':geometry,'distance_meters':round(meters+access),
                'duration_minutes':round((meters+access)/WALK_METERS_PER_MINUTE,1),'access_meters':round(access),
                'origin':origin,'destination':destination,'source':'OpenStreetMap / FOSSGIS OSRM a pé'}
        cache.set(key,result,86400)
        return result
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, IndexError):
        result={'available':False,'message':'Não foi possível obter um percurso a pé confiável. Tente novamente mais tarde.'}
        cache.set(key,result,30)
        return result
