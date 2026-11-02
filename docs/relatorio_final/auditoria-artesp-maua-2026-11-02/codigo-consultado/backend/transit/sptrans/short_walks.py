"""Caminhadas diretas verificadas de até 300 m, ocupando uma vaga por par."""
from contextlib import closing
import json
import math
from pathlib import Path
import shutil
import sqlite3
import time
from django.utils import timezone
from . import graph, staged_materialized as staged, store

MAX_METERS = 300
VERSION = 1


def signature(meta):
    return {'version': VERSION, 'base': meta['signature'],
            'transport': meta.get('topup_signature'), 'max_meters': MAX_METERS,
            'max_routes': 5, 'only_vacancies': True,
            **({'stages': meta.get('complete_stages', [])} if not meta.get('topup_signature') else {})}


def valid(meta):
    return (meta.get('short_walk_complete') is True
            and meta.get('short_walk_signature') == signature(meta)
            and meta['signature'] == staged.signature(meta['signature']['walks'][0]))


def build(path=None, min_free_gib=20):
    path = Path(path or staged.database_path()); started = time.monotonic()
    if not math.isfinite(min_free_gib) or min_free_gib < 0:
        raise ValueError('Reserva de disco inválida.')
    with closing(sqlite3.connect(path, timeout=30)) as db:
        meta = json.loads(db.execute('SELECT value FROM metadata WHERE id=1').fetchone()[0])
        if meta['signature'] != staged.signature(meta['signature']['walks'][0]):
            raise ValueError('Fontes da materialização foram alteradas.')
        if meta.get('topup_complete_units') != 12 and 0 not in meta.get('complete_stages', []):
            raise ValueError('Conclua primeiro pelo menos a etapa de custo zero.')
        if meta.get('short_walk_signature', signature(meta)) != signature(meta):
            raise ValueError('A assinatura das caminhadas curtas mudou.')
        before = path.stat().st_size
        if not meta.get('short_walk_complete'):
            ids = dict(db.execute('SELECT sid,id FROM stops'))
            with closing(graph.readonly(store.database_path())) as source:
                points = {r['stop_id']: (r['stop_lat'], r['stop_lon']) for r in source.execute('SELECT stop_id,stop_lat,stop_lon FROM stops')}
            records = []; skipped_full = 0; verified = 0
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            with closing(graph.readonly(Path(meta['signature']['walks'][0]))) as feet:
                for row in feet.execute("SELECT * FROM walk_edge WHERE status='verified' AND distance_meters BETWEEN 0 AND ? AND origin<>destination", (MAX_METERS,)):
                    a, b = row['origin'], row['destination']
                    if a not in ids or b not in ids: continue
                    verified += 1
                    pair = ids[a], ids[b]; count = 0
                    for table in ('topup_paths', 'expanded_paths', 'paths'):
                        if table not in tables: continue
                        previous = db.execute(f'SELECT substr(data,1,1) FROM {table} WHERE origin=? AND destination=?', pair).fetchone()
                        if previous:
                            count = previous[0][0]; break
                    if not 0 <= count <= 5: raise ValueError('Quantidade de rotas inválida.')
                    if count == 5:
                        skipped_full += 1; continue
                    meters, seconds = row['distance_meters'], row['seconds']
                    if not all(math.isfinite(v) and v >= 0 for v in (meters, seconds)):
                        raise ValueError('Caminhada sem distância/tempo válidos.')
                    records.append((*pair, meters, seconds, row['source'], count, *points[a], *points[b]))
            if meta['signature'] != staged.signature(meta['signature']['walks'][0]):
                raise ValueError('Fontes alteradas durante a preparação.')
            if shutil.disk_usage(path.parent).free - len(records)*1024 < min_free_gib*1024**3:
                raise OSError('Reserva de disco atingida.')
            with db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('''CREATE TABLE IF NOT EXISTS short_walk_paths(
                    origin INTEGER, destination INTEGER,
                    meters REAL NOT NULL CHECK(meters>=0 AND meters<=300),
                    seconds REAL NOT NULL CHECK(seconds>=0), source TEXT NOT NULL,
                    previous_routes INTEGER NOT NULL CHECK(previous_routes>=0 AND previous_routes<5),
                    origin_lat REAL, origin_lon REAL, destination_lat REAL, destination_lon REAL,
                    PRIMARY KEY(origin,destination)) WITHOUT ROWID''')
                db.executemany('INSERT INTO short_walk_paths VALUES(?,?,?,?,?,?,?,?,?,?)', records)
                if db.execute("PRAGMA quick_check('short_walk_paths')").fetchone()[0] != 'ok':
                    raise ValueError('Falha de integridade das caminhadas.')
                meta.update(short_walk_signature=signature(meta), short_walk_complete=True,
                            short_walk_completed_at=timezone.now().isoformat(),
                            short_walk_verified_candidates=verified, short_walk_skipped_full=skipped_full)
                db.execute('UPDATE metadata SET value=? WHERE id=1', (json.dumps(meta),))
        counts = dict(db.execute('SELECT previous_routes,count(*) FROM short_walk_paths GROUP BY previous_routes'))
    return {'complete': True, 'max_meters': MAX_METERS, 'only_vacancies': True,
            'walking_routes': sum(counts.values()), 'new_pairs': counts.get(0, 0),
            'pairs_newly_full': counts.get(4, 0), 'by_previous_route_count': counts,
            'verified_candidates': meta['short_walk_verified_candidates'],
            'skipped_full_pairs': meta['short_walk_skipped_full'],
            'database_bytes': path.stat().st_size, 'added_bytes_this_run': path.stat().st_size-before,
            'free_bytes': shutil.disk_usage(path.parent).free,
            'seconds': time.monotonic()-started, 'integrity': 'ok', 'geometry': 'on_selection'}


def route(origin, destination):
    """Somente IDs e coordenadas do catálogo; nunca reaproveite para outro endereço."""
    path = staged.database_path()
    if not path.exists(): return None
    try:
        with closing(graph.readonly(path)) as db:
            meta = json.loads(db.execute('SELECT value FROM metadata WHERE id=1').fetchone()[0])
            if not valid(meta): return None
            row = db.execute('''SELECT w.* FROM short_walk_paths w
                JOIN stops a ON a.id=w.origin JOIN stops b ON b.id=w.destination
                WHERE a.sid=? AND b.sid=?''', (origin['id'], destination['id'])).fetchone()
            if row is None: return None
            for prefix, point in (('origin', origin), ('destination', destination)):
                if any(not math.isfinite(point[k]) or abs(point[k]-row[prefix+'_'+k]) > 1e-7 for k in ('lat', 'lon')):
                    return None
            return {'available': True, 'mode': 'walk', 'materialized': True,
                    'geometry': [], 'geometry_pending': True, 'distance_meters': row['meters'],
                    'seconds': row['seconds'], 'duration_minutes': row['seconds']/60,
                    'origin': origin, 'destination': destination, 'source': row['source']+' · materializado',
                    'max_meters': MAX_METERS}
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        return None
