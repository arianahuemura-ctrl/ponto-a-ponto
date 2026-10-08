"""Cache GTFS local ao processo, sensível à revisão, com paginação a partir do centro."""
import hashlib
import json
import math
import threading
from collections import OrderedDict
from . import store, directions

_lock = threading.RLock()
_snapshots = OrderedDict()


def revision():
    path=store.database_path().resolve()
    stat=path.stat()
    return hashlib.sha256(f'{path}:{stat.st_ino}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()[:24]


def page(db, south, west, north, east, lat, lon, offset=0, limit=None):
    version=revision()
    with _lock:
        snapshot=_snapshots.get(version)
        if snapshot is None:
            # Carregue uma vez por banco importado, não a cada movimento ou lote.
            snapshot={'stops':store.in_bounds(db,-90,-180,90,180),
                      'metadata':json.loads(db.execute('SELECT value FROM metadata').fetchone()[0]),'enriched':{}}
            _snapshots[version]=snapshot
            while len(_snapshots)>2: _snapshots.popitem(last=False)
        _snapshots.move_to_end(version)
        points=[s for s in snapshot['stops'] if south<=s['lat']<=north and west<=s['lon']<=east]
        scale=math.cos(math.radians(lat))**2
        points.sort(key=lambda s:((s['lat']-lat)**2+(s['lon']-lon)**2*scale,s['id']))
        total=len(points)
        selected=points[offset:offset+limit if limit else None]
        missing=[dict(s) for s in selected if s['id'] not in snapshot['enriched']]
        if missing:
            directions.enrich(db,missing)
            snapshot['enriched'].update((s['id'],s) for s in missing)
        return {'stops':[snapshot['enriched'][s['id']] for s in selected],
                'revision':version,'metadata':snapshot['metadata'],'limit':limit,'total':total,
                'next_offset':offset+len(selected) if limit and offset+len(selected)<total else None}
