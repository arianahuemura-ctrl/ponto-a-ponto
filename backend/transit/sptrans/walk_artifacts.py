"""Distâncias pedestres offline com base OSRM foot local, nunca com perfil de automóvel.

O chamador informa a identidade da rede pedestre preparada. As distâncias incluem
os acessos entre parada e rede. A geometria é resolvida separadamente nessa rede;
nenhuma polilinha reta é apresentada como caminhada verificada.
"""
import concurrent.futures
import ipaddress
import json
from mbm import routing_config as config
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import urllib.parse
import urllib.request
from django.utils import timezone
from . import graph, store

VERSION = 1
SPEED_MPS = config.WALK_SPEED_KMH / 3.6
MAX_METERS = config.WALK_LIMIT_METERS


def database_path():
    return store.database_path().with_suffix('.walks.sqlite3')


def classify(air_meters, network_meters, offset_a, offset_b):
    if network_meters is None:
        return 'unreachable', None
    meters = float(network_meters) + offset_a + offset_b
    if not math.isfinite(meters) or meters < 0 or meters+2 < air_meters:
        return 'invalid_distance', None
    return ('verified' if meters <= MAX_METERS else 'over_limit'), meters


def build(base_url, network_id, source=None, target=None, workers=config.WALK_WORKERS, progress=None):
    parsed=urllib.parse.urlparse(base_url)
    # A geração municipal em massa não deve usar o serviço público de demonstração.
    if parsed.scheme not in ('http','https') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Informe a URL local do roteador pedestre.')
    try:
        local=parsed.hostname=='localhost' or ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        local=False
    if not local or not network_id.strip() or not 1<=workers<=16:
        raise ValueError('Requer roteador local, identificação da rede foot e 1–16 workers.')
    base_url=base_url.rstrip('/')
    source=Path(source or graph.graph_path()).resolve()
    target=Path(target or database_path()).resolve()
    if target in (source,store.database_path().resolve()):
        raise ValueError('A saída deve ser separada das fontes.')
    fd,tmp=tempfile.mkstemp(prefix='walks-',suffix='.sqlite3',dir=target.parent)
    os.close(fd)
    started=time.perf_counter()
    def request(path,params):
        url=base_url+'/'+path+'?'+urllib.parse.urlencode(params)
        with urllib.request.urlopen(url,timeout=config.WALK_REQUEST_SECONDS) as response:
            result=json.load(response)
        if result.get('code')!='Ok':
            raise ValueError('Resposta inválida do roteador local: '+str(result.get('code')))
        return result
    try:
        with graph.connection(source) as src, sqlite3.connect(tmp) as db:
            src.execute('BEGIN')
            meta=json.loads(src.execute('SELECT value FROM graph_meta').fetchone()[0])
            if meta['walk_radius']<MAX_METERS:
                raise ValueError(f'O grafo deve enumerar candidatos até pelo menos {MAX_METERS:g} m.')
            stops={r['id']:dict(r) for r in src.execute('SELECT * FROM graph_stop')}
            candidates={}
            for a,b,meters in src.execute('SELECT origin,destination,air_meters FROM walk_edge WHERE air_meters<=? AND origin<>destination', (MAX_METERS,)):
                candidates.setdefault(a,[]).append((b,meters))
            db.executescript('''CREATE TABLE walk_edge(origin TEXT,destination TEXT,air_meters REAL,
                distance_meters REAL,seconds REAL,geometry TEXT,source TEXT,checked_at TEXT,status TEXT,
                PRIMARY KEY(origin,destination));
                CREATE INDEX walk_in ON walk_edge(destination,origin);
                CREATE TABLE walk_meta(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT);
                CREATE TABLE stop_snap(id TEXT PRIMARY KEY,distance_meters REAL,lat REAL,lon REAL,hint TEXT);
            ''')
            def nearest(s):
                row=request(f"nearest/v1/foot/{s['lon']},{s['lat']}",{'number':1})['waypoints'][0]
                return s['id'],row
            snaps={}
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                for i,(sid,snap) in enumerate(pool.map(nearest,stops.values()),1):
                    snaps[sid]=snap
                    db.execute('INSERT INTO stop_snap VALUES (?,?,?,?,?)',
                        (sid,snap['distance'],snap['location'][1],snap['location'][0],snap['hint']))
                    if progress and i%2000==0:progress(f'{i}/{len(stops)} pontos localizados na rede pedestre')
            checked=timezone.now().isoformat()
            provenance='OSRM foot local / OpenStreetMap / '+network_id
            def routes(item):
                a,pairs=item
                rows=[]
                valid=[]
                for b,air in pairs:
                    if snaps[a]['distance']>config.WALK_SNAP_METERS or snaps[b]['distance']>config.WALK_SNAP_METERS:
                        rows.append((a,b,air,None,None,None,provenance,checked,'unsnappable'))
                    else:valid.append((b,air))
                for start in range(0,len(valid),config.WALK_BATCH_SIZE):
                    batch=valid[start:start+config.WALK_BATCH_SIZE];ids=[a]+[b for b,_ in batch]
                    coords=';'.join(f"{stops[s]['lon']},{stops[s]['lat']}" for s in ids)
                    data=request('table/v1/foot/'+coords,{'sources':'0',
                        'destinations':';'.join(map(str,range(1,len(ids)))),
                        'annotations':'distance','hints':';'.join(snaps[s]['hint'] for s in ids)})
                    distances=data['distances'][0]
                    if len(distances)!=len(batch):raise ValueError('Matriz incompleta.')
                    for (b,air),distance in zip(batch,distances):
                        status,meters=classify(air,distance,snaps[a]['distance'],snaps[b]['distance'])
                        rows.append((a,b,air,meters,meters/SPEED_MPS if meters is not None else None,
                            None,provenance,checked,status))
                return rows
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                for i,rows in enumerate(pool.map(routes,candidates.items()),1):
                    db.executemany('INSERT INTO walk_edge VALUES (?,?,?,?,?,?,?,?,?)',rows)
                    if i%1000==0:
                        db.commit()
                        if progress:progress(f'{i}/{len(candidates)} origens com caminhadas calculadas')
            counts=dict(db.execute('SELECT status,count(*) FROM walk_edge GROUP BY status'))
            report={'version':VERSION,'source_gtfs':meta['source'],'built_at':checked,
                'network_id':network_id,'router':base_url,'profile':'foot','max_meters':MAX_METERS,
                'speed_kmh':config.WALK_SPEED_KMH,'max_snap_meters':config.WALK_SNAP_METERS, 'configuration':config.walking_signature(),'geometry_materialized':False,
                'candidate_pairs':sum(map(len,candidates.values())), 'counts':counts,
                'stops':len(stops),'source_graph':str(source),'seconds':time.perf_counter()-started}
            if sum(counts.values())!=report['candidate_pairs']:raise ValueError('Pares perdidos na geração.')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Banco inválido.')
            if graph.fingerprint(store.database_path())!=meta['source']:raise ValueError('GTFS alterado durante a geração.')
            db.execute('INSERT INTO walk_meta VALUES (1,?)',(json.dumps(report),));db.commit()
        os.replace(tmp,target)
        report.update(bytes=target.stat().st_size,database=str(target),seconds=time.perf_counter()-started)
        return report
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
