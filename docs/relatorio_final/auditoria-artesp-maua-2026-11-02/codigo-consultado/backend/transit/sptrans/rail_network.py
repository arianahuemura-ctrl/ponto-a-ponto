"""Traçados ferroviários de contexto, independentes do planejamento de viagem."""
from collections import OrderedDict
import threading
from . import viewport, rail

_cache = OrderedDict()
_lock = threading.RLock()


def catalogue(db):
    revision = viewport.revision()
    with _lock:
        if revision in _cache:
            _cache.move_to_end(revision)
            return _cache[revision]
        lines = {}
        shapes = {}
        seen = {}
        for row in db.execute('''SELECT DISTINCT r.route_id,r.route_short_name,r.route_long_name,
                r.route_type,r.route_color,t.shape_id FROM routes r JOIN trips t USING(route_id)
                WHERE r.route_type IN ('1','2') ORDER BY r.route_id,t.shape_id'''):
            shape_id = row['shape_id']
            if shape_id not in shapes:
                shapes[shape_id] = [list(p) for p in db.execute('''SELECT shape_pt_lat,shape_pt_lon
                    FROM shapes WHERE shape_id=? ORDER BY shape_pt_sequence''', (shape_id,))]
            geometry = shapes[shape_id]
            if len(geometry) < 2:
                continue
            route_id = row['route_id']
            key = tuple(map(tuple, geometry))
            key = min(key, key[::-1])
            if key in seen.setdefault(route_id, set()):
                continue
            seen[route_id].add(key)
            line = lines.setdefault(route_id, {
                'route_id': route_id, 'code': row['route_short_name'], 'name': row['route_long_name'],
                'mode': rail.mode(row['route_type']),
                'color': '#' + row['route_color'] if row['route_color'] else None, 'geometries': [],
            })
            line['geometries'].append(geometry)
        result = {'revision': revision, 'lines': list(lines.values())}
        _cache[revision] = result
        while len(_cache) > 2:
            _cache.popitem(last=False)
        return result
