"""Catálogo persistente de conexões ordenadas por distância, independente do horário da consulta."""
import hashlib
import json
import math
import sqlite3
import time
from django.utils import timezone
from . import graph

QUOTAS = {1: 16, 2: 8, 3: 4}
CATALOG_VERSION = 1


def install(path=None):
    """Adiciona artefatos derivados sem reconstruir o GTFS nem perder caminhadas verificadas."""
    path = path or graph.graph_path()
    with graph.connection(path):
        pass
    with sqlite3.connect(path, timeout=30) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS connection_pairs (
            origin TEXT, destination TEXT, revision INTEGER, version INTEGER,
            complete INTEGER, built_at TEXT, stats TEXT,
            PRIMARY KEY(origin,destination));
        CREATE TABLE IF NOT EXISTS connections (
            id TEXT PRIMARY KEY, origin TEXT, destination TEXT, boardings INTEGER,
            rank INTEGER, distance_meters REAL NOT NULL, bus_meters REAL NOT NULL,
            walk_meters REAL NOT NULL, walk_seconds REAL NOT NULL, edge_ids TEXT NOT NULL,
            UNIQUE(origin,destination,boardings,rank));
        CREATE INDEX IF NOT EXISTS connections_lookup
            ON connections(origin,destination,boardings,distance_meters,id);
        CREATE TABLE IF NOT EXISTS historical_profiles (
            pattern_id INTEGER, segment_index INTEGER, day_type TEXT,
            start_second INTEGER, end_second INTEGER, speed_kmh REAL,
            source TEXT NOT NULL, samples INTEGER NOT NULL,
            PRIMARY KEY(pattern_id,segment_index,day_type,start_second));
        CREATE TABLE IF NOT EXISTS historical_days (date TEXT PRIMARY KEY, day_type TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS connection_operational_mappings (
            pattern_id INTEGER, stop_id TEXT, api_line INTEGER, api_stop INTEGER,
            checked_at TEXT NOT NULL, PRIMARY KEY(pattern_id,stop_id));
        CREATE TABLE IF NOT EXISTS connection_segments (
            pattern_id INTEGER, segment_index INTEGER, origin TEXT, destination TEXT,
            distance_meters REAL, PRIMARY KEY(pattern_id,segment_index));
        ''')
        for n in QUOTAS:
            rs = [f'r{i}' for i in range(n)]
            ids = [f'{r}.id AS edge{i}' for i,r in enumerate(rs)]
            ids += [f'NULL AS edge{i}' for i in range(n,3)]
            joins = ['ride_edge r0']
            conditions = [f'{r}.distance_meters IS NOT NULL' for r in rs]
            for i in range(1,n):
                joins += [f'JOIN transfer_link w{i} ON w{i}.origin=r{i-1}.destination',
                          f'JOIN ride_edge r{i} ON r{i}.origin=w{i}.destination']
                conditions += [f'r{i}.pattern_id<>r{i-1}.pattern_id',
                               f'r{i}.origin<>r0.origin', f'r{i-1}.destination<>r{n-1}.destination']
            conditions += [f'r0.origin<>r{n-1}.destination']
            bus = '+'.join(f'{r}.distance_meters' for r in rs)
            walk = '+'.join(f'w{i}.distance_meters' for i in range(1,n)) or '0.0'
            seconds = '+'.join(f'w{i}.seconds' for i in range(1,n)) or '0.0'
            db.execute(f'''CREATE VIEW IF NOT EXISTS connection_variants_{n} AS
                SELECT r0.origin,r{n-1}.destination,{n} AS boardings,{','.join(ids)},
                    ({bus}) AS bus_meters,({walk}) AS walk_meters,({seconds}) AS walk_seconds,
                    ({bus})+({walk}) AS distance_meters
                FROM {' '.join(joins)} WHERE {' AND '.join(conditions)}''')
        db.execute('CREATE VIEW IF NOT EXISTS connection_variants AS '+
                   ' UNION ALL '.join(f'SELECT * FROM connection_variants_{n}' for n in QUOTAS))
        db.execute('CREATE VIEW IF NOT EXISTS conexoes AS SELECT * FROM connections')
        if not db.execute('SELECT 1 FROM connection_segments LIMIT 1').fetchone():
            for pid, stops, positions in db.execute('SELECT id,stops,projections FROM pattern').fetchall():
                stops, positions = json.loads(stops), json.loads(positions)
                db.executemany('INSERT INTO connection_segments VALUES (?,?,?,?,?)',
                    ((pid,i,a,b,max(0,positions[i+1]['meters']-positions[i]['meters'])
                      if positions[i] and positions[i+1] else None)
                     for i,(a,b) in enumerate(zip(stops,stops[1:]))))
        db.execute('PRAGMA user_version=2')
    return path


def revision(db):
    return json.loads(db.execute('SELECT value FROM graph_meta WHERE id=1').fetchone()[0])['revision']


def build_pair(db, origin, destination, seconds=60, force=False):
    """Materializa as menores distâncias exatas no grafo verificado ou indica incompletude.

    ORDER BY precede LIMIT. Ordenações canceladas não publicam um falso subconjunto top-K.
    Cada categoria tem seu próprio limite; categorias que falharem podem ser retomadas.
    """
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Tempo de construção deve ser positivo.')
    for sid in (origin,destination):
        if not db.execute('SELECT 1 FROM graph_stop WHERE id=?',(sid,)).fetchone():
            raise ValueError('Ponto não cadastrado no grafo: '+str(sid))
    rev = revision(db)
    previous = db.execute('SELECT * FROM connection_pairs WHERE origin=? AND destination=?',
                          (origin,destination)).fetchone()
    if previous and previous['revision']==rev and previous['version']==CATALOG_VERSION and previous['complete'] and not force:
        return json.loads(previous['stats'])
    selected=[]; stats={}; complete=True
    for boardings,limit in QUOTAS.items():
        start=time.monotonic(); deadline=start+seconds; done=True; rows=[]
        db.set_progress_handler(lambda: int(time.monotonic()>=deadline),1000)
        try:
            if origin!=destination:
                rows=db.execute(f'''SELECT * FROM connection_variants_{boardings}
                    WHERE origin=? AND destination=?
                    ORDER BY distance_meters,edge0,edge1,edge2 LIMIT ?''',
                    (origin,destination,limit)).fetchall()
        except sqlite3.OperationalError as error:
            if str(error)!='interrupted': raise
            done=False
        finally:
            db.set_progress_handler(None,0)
        complete &= done
        stats[str(boardings)]={'count':len(rows),'quota':limit,'complete':done,
                               'build_seconds':time.monotonic()-start}
        for rank,row in enumerate(rows,1):
            edges=[row[f'edge{i}'] for i in range(boardings)]
            key=json.dumps([origin,destination,edges],separators=(',',':'))
            sid=hashlib.sha256(key.encode()).hexdigest()[:24]
            selected.append((sid,origin,destination,boardings,rank,row['distance_meters'],
                             row['bus_meters'],row['walk_meters'],row['walk_seconds'],json.dumps(edges)))
    db.execute('DELETE FROM connections WHERE origin=? AND destination=?',(origin,destination))
    db.executemany('INSERT INTO connections VALUES (?,?,?,?,?,?,?,?,?,?)',selected)
    result={'origin':origin,'destination':destination,'complete':complete,'categories':stats,
            'candidate_count':len(selected),'revision':rev,'selection':'distance_bus_plus_walk'}
    db.execute('INSERT OR REPLACE INTO connection_pairs VALUES (?,?,?,?,?,?,?)',
        (origin,destination,rev,CATALOG_VERSION,int(complete),timezone.now().isoformat(),json.dumps(result)))
    return result


def candidates(db, origin, destination):
    pair=db.execute('SELECT * FROM connection_pairs WHERE origin=? AND destination=?',(origin,destination)).fetchone()
    if not pair or pair['revision']!=revision(db) or pair['version']!=CATALOG_VERSION:
        raise ValueError('Catálogo ausente/desatualizado. Execute build_sptrans_connections para este par.')
    return [dict(r) for r in db.execute('SELECT * FROM connections WHERE origin=? AND destination=? ORDER BY boardings,rank',
                                       (origin,destination))],json.loads(pair['stats'])


def describe(db, candidate):
    """Representação estrutural pública, com identificação das linhas e caminhadas pré-calculadas."""
    legs=[]; previous=None
    for eid in json.loads(candidate['edge_ids']):
        edge=dict(db.execute('''SELECT e.*,p.route_id,p.code,p.direction,p.headsign
            FROM ride_edge e JOIN pattern p ON p.id=e.pattern_id WHERE e.id=?''',(eid,)).fetchone())
        if previous and previous['destination']!=edge['origin']:
            walk=dict(db.execute("SELECT * FROM walk_edge WHERE origin=? AND destination=? AND status='verified'",
                                 (previous['destination'],edge['origin'])).fetchone())
            legs.append({'modo':'caminhada','origem':walk['origin'],'destino':walk['destination'],
                         'distancia_m':walk['distance_meters'],'tempo_caminhada_s':walk['seconds'],
                         'geometry':json.loads(walk['geometry'])})
        mapping=db.execute('SELECT * FROM connection_operational_mappings WHERE pattern_id=? AND stop_id=?',
                           (edge['pattern_id'],edge['origin'])).fetchone()
        legs.append({'modo':'onibus','conexao_direta_id':eid,'origem':edge['origin'],'destino':edge['destination'],
            'distancia_m':edge['distance_meters'],
            'segmentos':[f"{edge['pattern_id']}:{i}" for i in range(edge['boarding_index'],edge['alighting_index'])],
            'servicos':[{'linha':edge['code'],'gtfs_route_id':edge['route_id'],'padrao_id':edge['pattern_id'],
                         'sentido_gtfs':edge['direction'],'destino_letreiro':edge['headsign'],
                         'indice_embarque':edge['boarding_index'],'indice_desembarque':edge['alighting_index'],
                         'olho_vivo':dict(mapping) if mapping else None}]})
        previous=edge
    return {'id':candidate['id'],'origem':candidate['origin'],'destino':candidate['destination'],
        'embarques':candidate['boardings'],'baldeacoes':candidate['boardings']-1,'trechos':legs,
        'distancia_total_m':candidate['distance_meters'],'distancia_onibus_m':candidate['bus_meters'],
        'distancia_caminhada_m':candidate['walk_meters'],'tempo_caminhada_s':candidate['walk_seconds']}
