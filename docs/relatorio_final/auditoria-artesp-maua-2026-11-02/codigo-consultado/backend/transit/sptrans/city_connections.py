"""Conexões municipais fatoradas: trajetos dirigidos e junções materializadas de transferências.

Sem produto cartesiano de todas as paradas nem truncamento de padrões intermediários.
As visões expandem os percursos apenas na consulta. A estrutura não avalia horários.
"""
from contextlib import closing, nullcontext
from mbm import routing_config as config
import math
import heapq
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from django.utils import timezone
from . import direct, graph

VERSION = 2
PROGRESS_STEPS = 1000
QUOTAS = {1: config.ROUTES_DIRECT, 2: config.ROUTES_TWO_BUSES, 3: config.ROUTES_THREE_BUSES}


def database_path():
    return direct.store.database_path().with_suffix('.connections.sqlite3')


def build(source=None, graph_source=None, target=None, progress=None, walk_source=None):
    default_walk = direct.store.database_path().with_suffix('.walks.sqlite3')
    walk_source = walk_source or (default_walk if default_walk.exists() else None)
    source = Path(source or direct.database_path()).resolve()
    graph_source = Path(graph_source or graph.graph_path()).resolve()
    target = Path(target or database_path()).resolve()
    if target in (source, graph_source, Path(walk_source).resolve() if walk_source else None, direct.store.database_path().resolve()):
        raise ValueError('A saída deve ser um artefato separado.')
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='connections-build-', suffix='.sqlite3', dir=target.parent)
    os.close(fd)
    started = time.perf_counter()
    try:
        with direct.connection(source) as src, graph.connection(graph_source) as walking, (closing(graph.readonly(walk_source)) if walk_source else nullcontext()) as foot:
            src.execute('BEGIN')
            walking.execute('BEGIN')
            sm = json.loads(src.execute('SELECT value FROM direct_meta').fetchone()[0])
            wm = json.loads(walking.execute('SELECT value FROM graph_meta').fetchone()[0])
            foot_meta = None
            if foot is not None:
                foot.execute('BEGIN')
                foot_meta = json.loads(foot.execute('SELECT value FROM walk_meta').fetchone()[0])
                if foot_meta['source_gtfs'] != sm['source_gtfs'] or foot_meta['profile'] != 'foot':
                    raise ValueError('Artefato pedestre incompatível.')
            if sm['source_gtfs'] != wm['source']:
                raise ValueError('Fontes GTFS incompatíveis.')
            with sqlite3.connect(tmp) as db:
                src.backup(db)
                db.execute('PRAGMA cache_size=-131072')
                db.executescript("""
                    CREATE TABLE occurrence(pattern_id INTEGER, position INTEGER,
                        stop TEXT, last INTEGER, PRIMARY KEY(pattern_id,position));
                    CREATE INDEX occurrence_stop ON occurrence(stop);
                    CREATE INDEX occurrence_pattern_stop ON occurrence(pattern_id,stop,position);
                    CREATE TABLE walking_link(id INTEGER PRIMARY KEY, origin TEXT,
                        destination TEXT, distance_meters REAL NOT NULL CHECK(distance_meters>=0),
                        seconds REAL NOT NULL CHECK(seconds>=0), geometry TEXT, source TEXT,
                        checked_at TEXT, UNIQUE(origin,destination));
                    CREATE TABLE transfer(id INTEGER PRIMARY KEY,
                        incoming_pattern INTEGER, alighting_index INTEGER,
                        outgoing_pattern INTEGER, boarding_index INTEGER,
                        walk_id INTEGER REFERENCES walking_link(id),
                        UNIQUE(incoming_pattern,alighting_index,outgoing_pattern,boarding_index));
                """)
                for pid, raw in db.execute('SELECT id,stops FROM pattern').fetchall():
                    stops = json.loads(raw)
                    db.executemany('INSERT INTO occurrence VALUES (?,?,?,?)',
                        [(pid, i, stop, len(stops)-1) for i, stop in enumerate(stops)])
                db.executemany('''INSERT INTO walking_link(origin,destination,distance_meters,
                    seconds,geometry,source,checked_at) VALUES (?,?,?,?,?,?,?)''',
                    [(r['origin'], r['destination'], r['distance_meters'],
                      r['distance_meters']/(config.WALK_SPEED_KMH/3.6), r['geometry'], r['source'], r['checked_at'])
                     for r in (foot if foot is not None else walking).execute("SELECT * FROM walk_edge WHERE status='verified' AND origin<>destination")
                     if r['distance_meters'] is not None and math.isfinite(r['distance_meters']) and 0 <= r['distance_meters'] <= config.WALK_LIMIT_METERS])
                db.execute('''INSERT INTO transfer(incoming_pattern,alighting_index,
                    outgoing_pattern,boarding_index,walk_id)
                    SELECT a.pattern_id,a.position,b.pattern_id,b.position,NULL
                    FROM occurrence a JOIN occurrence b ON a.stop=b.stop
                    WHERE a.pattern_id<>b.pattern_id AND a.position>0 AND b.position<b.last''')
                same_stop = db.execute('SELECT count(*) FROM transfer').fetchone()[0]
                db.execute('''INSERT INTO transfer(incoming_pattern,alighting_index,
                    outgoing_pattern,boarding_index,walk_id)
                    SELECT a.pattern_id,a.position,b.pattern_id,b.position,w.id
                    FROM walking_link w JOIN occurrence a ON a.stop=w.origin
                    JOIN occurrence b ON b.stop=w.destination
                    WHERE a.pattern_id<>b.pattern_id AND a.position>0 AND b.position<b.last''')
                db.executescript('''
                    CREATE INDEX transfer_out ON transfer(incoming_pattern,alighting_index);
                    CREATE INDEX transfer_in ON transfer(outgoing_pattern,boarding_index);
                    CREATE INDEX transfer_meet ON transfer(outgoing_pattern,boarding_index,incoming_pattern,alighting_index);
                    CREATE TABLE connections_meta(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT);
                ''')
                db.executescript("""
                    CREATE INDEX ride_pattern_in ON ride_edge(pattern_id,alighting_index,boarding_index);
                    CREATE INDEX walking_out ON walking_link(origin,destination);
                    CREATE INDEX walking_in ON walking_link(destination,origin);
                    CREATE TABLE bus_walk_exit(pattern_id INTEGER,alighting_index INTEGER,
                        walk_id INTEGER REFERENCES walking_link(id),
                        PRIMARY KEY(pattern_id,alighting_index,walk_id));
                    INSERT INTO bus_walk_exit SELECT o.pattern_id,o.position,w.id
                        FROM occurrence o JOIN walking_link w ON w.origin=o.stop WHERE o.position>0;
                    CREATE INDEX bus_walk_exit_reverse ON bus_walk_exit(walk_id,pattern_id,alighting_index);
                    CREATE VIEW bus_walk_forward AS
                        SELECT e.id AS edge_id,w.id AS walk_id,e.origin,w.destination,
                            e.origin AS search_from,w.destination AS search_to,
                            e.pattern_id,e.boarding_index,e.alighting_index,
                            e.distance_meters AS bus_meters,w.distance_meters AS walk_meters,
                            w.seconds AS walk_seconds,e.distance_meters+w.distance_meters AS distance_meters
                        FROM ride_edge e JOIN bus_walk_exit x ON x.pattern_id=e.pattern_id
                            AND x.alighting_index=e.alighting_index
                        JOIN walking_link w ON w.id=x.walk_id
                        WHERE w.destination<>e.origin AND NOT EXISTS (
                            SELECT 1 FROM occurrence o WHERE o.pattern_id=e.pattern_id
                            AND o.stop=w.destination AND o.position>e.boarding_index);
                    CREATE VIEW bus_walk_reverse AS SELECT edge_id,walk_id,origin,destination,
                        destination AS search_from,origin AS search_to,pattern_id,boarding_index,
                        alighting_index,bus_meters,walk_meters,walk_seconds,distance_meters FROM bus_walk_forward;
                    CREATE VIEW one_bus AS
                        SELECT id AS edge_id,NULL AS walk_id,origin,destination,pattern_id,
                            boarding_index,alighting_index,distance_meters AS bus_meters,
                            0 AS walk_meters,0 AS walk_seconds,distance_meters FROM ride_edge
                        UNION ALL SELECT edge_id,walk_id,origin,destination,pattern_id,
                            boarding_index,alighting_index,bus_meters,walk_meters,walk_seconds,
                            distance_meters FROM bus_walk_forward;
                """)
                # Mesmo esquema entre categorias; distâncias somam os traçados e as caminhadas verificadas.
                for n in (1, 2, 3):
                    joins = 'ride_edge a'
                    if n >= 2:
                        joins += """ JOIN transfer t ON t.incoming_pattern=a.pattern_id
                          AND t.alighting_index=a.alighting_index
                          JOIN ride_edge b ON b.pattern_id=t.outgoing_pattern
                          AND b.boarding_index=t.boarding_index
                          LEFT JOIN walking_link w ON w.id=t.walk_id"""
                    if n == 3:
                        joins += """ JOIN transfer u ON u.incoming_pattern=b.pattern_id
                          AND u.alighting_index=b.alighting_index
                          JOIN ride_edge c ON c.pattern_id=u.outgoing_pattern
                          AND c.boarding_index=u.boarding_index
                          LEFT JOIN walking_link x ON x.id=u.walk_id"""
                    legs = list('abc'[:n]); last = legs[-1]
                    bus = '+'.join(f'{l}.distance_meters' for l in legs)
                    walk = '+'.join(f'coalesce({w}.distance_meters,0)' for w in 'wx'[:n-1]) or '0'
                    seconds = '+'.join(f'coalesce({w}.seconds,0)' for w in 'wx'[:n-1]) or '0'
                    condition = [f'{l}.distance_meters IS NOT NULL' for l in legs]
                    condition += [f'a.origin<>{last}.destination']
                    for prev,nxt,transfer in [('a','b','t'),('b','c','u')][:n-1]:
                        condition += [f"({transfer}.walk_id IS NULL OR ({nxt}.origin<>{prev}.origin AND NOT EXISTS (SELECT 1 FROM occurrence o WHERE o.pattern_id={prev}.pattern_id AND o.stop={nxt}.origin AND o.position>{prev}.boarding_index)))"]
                    for l in legs[:-1]:
                        condition += [f'{l}.destination<>{last}.destination']
                    for l in legs[1:]:
                        condition += [f'{l}.destination<>a.origin']
                    db.execute(f"""CREATE VIEW bus_end_{n} AS SELECT a.origin,
                        {last}.destination, {n} AS boardings, a.id AS edge1,
                        {'b.id' if n>=2 else 'NULL'} AS edge2,
                        {'c.id' if n==3 else 'NULL'} AS edge3,
                        {'t.walk_id' if n>=2 else 'NULL'} AS walk1,
                        {'u.walk_id' if n==3 else 'NULL'} AS walk2,
                        NULL AS final_walk,
                        ({bus}) AS bus_meters, ({walk}) AS walk_meters,
                        ({seconds}) AS walk_seconds, ({bus})+({walk}) AS distance_meters
                        FROM {joins} WHERE {' AND '.join(condition)}""")
                    db.execute(f"""CREATE VIEW conexoes_{n} AS SELECT * FROM bus_end_{n}
                        UNION ALL SELECT j.origin,w.destination,j.boardings,j.edge1,j.edge2,j.edge3,
                            j.walk1,j.walk2,w.id AS final_walk,j.bus_meters,
                            j.walk_meters+w.distance_meters,j.walk_seconds+w.seconds,
                            j.distance_meters+w.distance_meters
                        FROM walking_link w INDEXED BY walking_in
                        CROSS JOIN bus_walk_exit x INDEXED BY bus_walk_exit_reverse
                        CROSS JOIN ride_edge e INDEXED BY ride_pattern_in
                        CROSS JOIN bus_end_{n} j
                        WHERE x.walk_id=w.id AND e.pattern_id=x.pattern_id
                        AND e.alighting_index=x.alighting_index AND j.edge{n}=e.id
                        AND w.destination<>j.origin AND w.destination<>e.origin AND NOT EXISTS (
                            SELECT 1 FROM occurrence o WHERE o.pattern_id=e.pattern_id
                            AND o.stop=w.destination AND o.position>e.boarding_index)
                        AND NOT EXISTS (SELECT 1 FROM ride_edge earlier
                            WHERE earlier.id IN (j.edge1,j.edge2) AND earlier.id<>e.id
                            AND earlier.destination=w.destination)""")
                db.execute('CREATE VIEW conexoes AS SELECT * FROM conexoes_1 UNION ALL SELECT * FROM conexoes_2 UNION ALL SELECT * FROM conexoes_3')
                if progress:
                    progress('Conexões compartilhadas gravadas; validando índices e integridade.')
                db.execute('ANALYZE')
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Falha na integridade do artefato.')
                if db.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('Referência de caminhada inválida.')
                report = dict(version=VERSION, built_at=timezone.now().isoformat(), representation='factorized',
                    source_gtfs=sm['source_gtfs'], walk_revision=wm['revision'],
                    walking_speed_kmh=config.WALK_SPEED_KMH, max_walk_meters=config.WALK_LIMIT_METERS, quotas=QUOTAS,
                    walk_source=graph.fingerprint(walk_source) if walk_source else None,
                    walking_coverage=foot_meta,
                    bus_walk_exits=db.execute('SELECT count(*) FROM bus_walk_exit').fetchone()[0],
                    ride_edges=db.execute('SELECT count(*) FROM ride_edge').fetchone()[0],
                    patterns=db.execute('SELECT count(*) FROM pattern').fetchone()[0],
                    same_stop_transfers=same_stop,
                    transfers=db.execute('SELECT count(*) FROM transfer').fetchone()[0],
                    verified_walks=db.execute('SELECT count(*) FROM walking_link').fetchone()[0],
                    unknown_ride_distances=db.execute('SELECT count(*) FROM ride_edge WHERE distance_meters IS NULL').fetchone()[0],
                    structural_only=True, all_od_paths_materialized=False,
                    source=str(source), graph_source=str(graph_source))
                if graph.fingerprint(direct.store.database_path()) != sm['source_gtfs']:
                    raise ValueError('O GTFS mudou durante a geração; gere os artefatos novamente.')
                db.execute('INSERT INTO connections_meta VALUES (1,?)',(json.dumps(report),))
                db.commit()
        os.replace(tmp, target)
        report.update(seconds=time.perf_counter()-started, bytes=target.stat().st_size, database=str(target))
        return report
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _rank_three(db, origin, destination, limit, deadline):
    """Combina primeiro e último trajetos (com caminhada), ordenados por limite inferior não negativo.

    O ônibus intermediário e ambas as caminhadas têm custos não negativos. Quando o próximo
    par excede a K-ésima distância completa, nenhum par ainda não expandido melhora o top K.
    Os padrões e variantes das extremidades nunca são truncados nesta enumeração.
    """
    if origin == destination:return []
    first=db.execute("""SELECT id,distance_meters FROM ride_edge
        WHERE origin=? AND destination<>? AND distance_meters IS NOT NULL
        ORDER BY distance_meters,id""",(origin,destination)).fetchall()
    last=db.execute("""SELECT edge_id,walk_id,distance_meters,walk_meters,walk_seconds FROM one_bus
        WHERE destination=? AND distance_meters IS NOT NULL
        ORDER BY distance_meters,edge_id,walk_id""",(destination,)).fetchall()
    if not first or not last:return []
    queue=[(a['distance_meters']+last[0]['distance_meters'],i,0) for i,a in enumerate(first)]
    heapq.heapify(queue)
    best=[]
    rank=lambda r:(r['distance_meters'],r['edge1'],r['edge2'],r['edge3'],
                   -1 if r['final_walk'] is None else r['final_walk'])
    while queue:
        if time.perf_counter()>deadline:raise sqlite3.OperationalError('interrupted')
        lower,i,j=heapq.heappop(queue)
        if len(best)>=limit and lower>best[-1]['distance_meters']+1e-7:break
        a,c=first[i],last[j]
        rows=db.execute("""SELECT a.origin,? AS destination,3 AS boardings,
            a.id AS edge1,b.id AS edge2,c.id AS edge3,t.walk_id AS walk1,u.walk_id AS walk2,
            ? AS final_walk,a.distance_meters+b.distance_meters+c.distance_meters AS bus_meters,
            coalesce(w.distance_meters,0)+coalesce(x.distance_meters,0)+? AS walk_meters,
            coalesce(w.seconds,0)+coalesce(x.seconds,0)+? AS walk_seconds,
            (a.distance_meters+b.distance_meters+c.distance_meters)+
                (coalesce(w.distance_meters,0)+coalesce(x.distance_meters,0))+? AS distance_meters
            FROM ride_edge a CROSS JOIN ride_edge c
            CROSS JOIN transfer t INDEXED BY transfer_out
            CROSS JOIN transfer u INDEXED BY transfer_meet
            CROSS JOIN ride_edge b INDEXED BY ride_pattern_in
            LEFT JOIN walking_link w ON w.id=t.walk_id
            LEFT JOIN walking_link x ON x.id=u.walk_id
            WHERE a.id=? AND c.id=?
            AND t.incoming_pattern=a.pattern_id AND t.alighting_index=a.alighting_index
            AND u.outgoing_pattern=c.pattern_id AND u.boarding_index=c.boarding_index
            AND u.incoming_pattern=t.outgoing_pattern AND u.alighting_index>t.boarding_index
            AND b.pattern_id=t.outgoing_pattern AND b.boarding_index=t.boarding_index
            AND b.alighting_index=u.alighting_index AND b.distance_meters IS NOT NULL
            AND a.destination<>c.destination AND b.destination<>c.destination
            AND b.destination<>a.origin AND c.destination<>a.origin
            AND a.destination<>? AND b.destination<>?
            AND (t.walk_id IS NULL OR (b.origin<>a.origin AND NOT EXISTS (SELECT 1 FROM occurrence o
                WHERE o.pattern_id=a.pattern_id AND o.stop=b.origin AND o.position>a.boarding_index)))
            AND (u.walk_id IS NULL OR (c.origin<>b.origin AND NOT EXISTS (SELECT 1 FROM occurrence o
                WHERE o.pattern_id=b.pattern_id AND o.stop=c.origin AND o.position>b.boarding_index)))
            ORDER BY distance_meters,edge1,edge2,edge3,final_walk LIMIT ?""",
            (destination,c['walk_id'],c['walk_meters'],c['walk_seconds'],c['walk_meters'],
             a['id'],c['edge_id'],destination,destination,limit)).fetchall()
        best.extend(rows);best.sort(key=rank);del best[limit:]
        if j+1<len(last):
            heapq.heappush(queue,(a['distance_meters']+last[j+1]['distance_meters'],i,j+1))
    return best


def rank_origin(db, origin, boardings, limit, shared):
    """Expanda uma origem uma vez; preserve TOP por destino sem podar intermediários.

    Os JOINs das views cruzam ocorrências de chegada e partida nos pontos
    de transferência, incluindo as ligações pedestres verificadas.
    O SQLite pode usar disco para ordenar; só os resultados finais ficam em RAM.
    """
    key = ('origin_rank', origin, boardings, limit)
    if key not in shared:
        ranked = {}
        # Copie a expansão de ônibus desta origem uma única vez. A extensão
        # pedestre reutiliza essa tabela em vez de repetir a junção de ônibus.
        table = f'origin_bus_{boardings}'
        db.execute(f'DROP TABLE IF EXISTS temp.{table}')
        db.execute(f'CREATE TEMP TABLE {table} AS SELECT * FROM bus_end_{boardings} WHERE origin=?', (origin,))
        db.execute(f'CREATE INDEX temp.{table}_last ON {table}(edge{boardings})')
        definition = db.execute("SELECT sql FROM sqlite_master WHERE name=?", (f'conexoes_{boardings}',)).fetchone()[0]
        query = definition.split(' AS ', 1)[1].replace(f'bus_end_{boardings}', f'temp.{table}')
        # Comece pelos desembarques já expandidos, não pela rede pedestre inteira.
        begin = query.index('FROM walking_link')
        end = query.index('AND w.destination<>j.origin', begin)
        query = query[:begin] + (f'FROM temp.{table} j CROSS JOIN ride_edge e '
            f'CROSS JOIN walking_link w INDEXED BY walking_out '
            f'WHERE e.id=j.edge{boardings} AND w.origin=e.destination ') + query[end:]
        rows = db.execute(f"""SELECT * FROM (
            SELECT c.*, ROW_NUMBER() OVER (
                PARTITION BY destination
                ORDER BY distance_meters,edge1,edge2,edge3,final_walk
            ) AS destination_rank
            FROM ({query}) c WHERE origin=?
        ) WHERE destination_rank<=? ORDER BY destination,destination_rank""", (origin, limit))
        for row in rows:
            ranked.setdefault(row['destination'], []).append(dict(row))
        # Não publique resultados parciais caso a consulta seja interrompida.
        shared[key] = ranked
    return shared[key]


def structural_query(origin, destination, path=None, seconds=30, quotas=None, categories=(1,2,3), offline=False, shared=None, experimental=False):
    if seconds <= 0:
        raise ValueError('O prazo deve ser positivo.')
    quotas = QUOTAS if quotas is None else quotas
    if set(quotas) != {1,2,3} or any(not isinstance(q,int) or not 1<=q<=10000 for q in quotas.values()):
        raise ValueError('Quotas inválidas.')
    result = dict(origem=origin, destino=destination, trajetos=[], categories={},
                  structural_only=True, temporal_feasibility_checked=False)
    with direct.connection(path or database_path()) as db:
        meta = json.loads(db.execute('SELECT value FROM connections_meta').fetchone()[0])
        if meta['version'] != VERSION:
            raise ValueError('Artefato de conexões desatualizado.')
        # Recuse ligações pedestres desatualizadas enquanto o grafo de origem estiver disponível.
        if meta.get('walk_source') and graph.fingerprint(meta['walk_source'][0]) != meta['walk_source']:
            raise ValueError('Artefato pedestre desatualizado; reconstrua as conexões.')
        if not meta.get('walk_source') and Path(meta['graph_source']).exists():
            with graph.connection(meta['graph_source']) as source:
                revision=json.loads(source.execute('SELECT value FROM graph_meta').fetchone()[0])['revision']
            if revision != meta['walk_revision']:
                raise ValueError('Caminhadas desatualizadas; execute build_sptrans_city_connections.')
        allows=None
        if experimental:
            from .experimental_pruning import convergence_filter
            allows=convergence_filter(db,destination)
            db.create_function('pap_converges',1,allows)
            result['experimental_policy']='coverage_then_midpoint_last'
            result['convergence_stats']=allows.stats
        for n, limit in sorted(quotas.items()):
            if n not in categories: continue
            start = time.perf_counter()
            db.set_progress_handler(lambda: int(time.perf_counter()-start > seconds), PROGRESS_STEPS)
            try:
                skipped=False
                if experimental and n==3:
                    skipped=any(db.execute(f'SELECT 1 FROM conexoes_{k} WHERE origin=? AND destination=? LIMIT 1',
                                           (origin,destination)).fetchone() for k in (1,2))
                if skipped:
                    rows=[]
                elif n == 3:
                    if offline or experimental:
                        from .offline_three import rank_three
                        rows = rank_three(db,origin,destination,limit,start+seconds,shared=None if experimental else shared,allows=allows)
                    else:
                        rows = _rank_three(db,origin,destination,limit,start+seconds)
                elif offline and shared is not None and not experimental:
                    failure_key = ('origin_rank_timeout', origin, n, limit)
                    ranked = None
                    if not shared.get(failure_key):
                        try:
                            ranked = rank_origin(db, origin, n, limit, shared)
                        except sqlite3.OperationalError as error:
                            if 'interrupted' not in str(error): raise
                            shared[failure_key] = True
                    if ranked is None:
                        # Uma origem muito grande não deve repetir a expansão em cada destino.
                        deadline = time.perf_counter() + seconds
                        db.set_progress_handler(lambda: int(time.perf_counter() > deadline), PROGRESS_STEPS)
                        rows = db.execute(f'''SELECT * FROM conexoes_{n} WHERE origin=? AND destination=?
                            ORDER BY distance_meters,edge1,edge2,edge3,final_walk LIMIT ?''',
                            (origin,destination,limit)).fetchall()
                    else:
                        rows = ranked.get(destination, [])
                else:
                    restriction=(' AND '+ ' AND '.join(f'pap_converges(edge{i})' for i in range(1,n+1))) if experimental else ''
                    rows = db.execute(f'''SELECT * FROM conexoes_{n} WHERE origin=? AND destination=?{restriction}
                        ORDER BY distance_meters,edge1,edge2,edge3,final_walk LIMIT ?''', (origin,destination,limit)).fetchall()
                complete = True
            except sqlite3.OperationalError as error:
                if 'interrupted' not in str(error):
                    raise
                rows=[]; complete=False
            finally:
                db.set_progress_handler(None,0)
            result['categories'][n] = dict(complete=complete, count=len(rows), seconds=time.perf_counter()-start)
            if experimental:
                result['categories'][n]['policy_skipped']=bool(complete and skipped)
            for row in rows:
                legs=[]
                for i in range(1,n+1):
                    if i>1 and row[f'walk{i-1}'] is not None:
                        w=dict(db.execute('SELECT * FROM walking_link WHERE id=?',(row[f'walk{i-1}'],)).fetchone())
                        legs.append(dict(modo='caminhada', origem=w['origin'], destino=w['destination'],
                            distancia_m=w['distance_meters'], tempo_s=w['seconds'], percurso_id=w['id']))
                    e=dict(db.execute('SELECT * FROM direct_services WHERE id=?',(row[f'edge{i}'],)).fetchone())
                    legs.append(dict(modo='onibus', aresta_id=e['id'], padrao_id=e['pattern_id'],
                        linha=e['code'], route_id=e['route_id'], sentido=e['direction'], letreiro=e['headsign'],
                        origem=e['origin'], destino=e['destination'], distancia_m=e['distance_meters'],
                        embarque_indice=e['boarding_index'], desembarque_indice=e['alighting_index']))
                if row['final_walk'] is not None:
                    w=dict(db.execute('SELECT * FROM walking_link WHERE id=?',(row['final_walk'],)).fetchone())
                    legs.append(dict(modo='caminhada',origem=w['origin'],destino=w['destination'],
                        distancia_m=w['distance_meters'],tempo_s=w['seconds'],percurso_id=w['id']))
                result['trajetos'].append(dict(embarques=n, baldeacoes=n-1, trechos=legs,
                    distancia_m=row['distance_meters'], distancia_onibus_m=row['bus_meters'],
                    distancia_caminhada_m=row['walk_meters'], caminhada_s=row['walk_seconds']))
        result['complete']=all(c['complete'] for c in result['categories'].values())
        result['coverage']=dict(verified_walks=meta['verified_walks'],unknown_ride_distances=meta['unknown_ride_distances'])
    return result


def query(origin, destination, path=None, seconds=30, quotas=None):
    """Lê conexões físicas pré-calculadas; nunca compõe baldeações aqui."""
    from . import materialized_connections
    return materialized_connections.query(origin, destination, path=path, quotas=quotas)
