"""Índices persistentes dirigidos de ônibus/caminhada. Previsões operacionais não são armazenadas aqui."""
import json
import math
import os
import sqlite3
import tempfile
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from django.utils import timezone
from . import store, walking
from .directions import distance
from .planner import next_departure, TRANSFER_SECONDS, HORIZON_SECONDS

VERSION = 1


def graph_path():
    return store.database_path().with_suffix('.routing.sqlite3')


def fingerprint(path):
    p = Path(path).resolve()
    s = p.stat()
    return [str(p), s.st_size, s.st_mtime_ns]


def readonly(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


@contextmanager
def connection(path=None, source=None):
    db = readonly(path or graph_path())
    try:
        meta = json.loads(db.execute('SELECT value FROM graph_meta WHERE id=1').fetchone()[0])
        if meta['version'] != VERSION or meta['walking_speed_kmh'] != walking.WALK_SPEED_KMH or meta['source'] != fingerprint(source or store.database_path()):
            raise ValueError('Índice desatualizado: execute build_sptrans_graph novamente.')
        yield db
    finally:
        db.close()


def projected_positions(shape, points):
    """Projeção monotônica no traçado detalhado; distâncias seguem sua polilinha.

    Paradas ausentes ou fora do traçado ficam desconhecidas. Nunca substitua distância viária por linha reta.
    """
    if len(shape) < 2:
        return [None] * len(points)
    cumulative = [0.0]
    for a, b in zip(shape, shape[1:]):
        cumulative.append(cumulative[-1] + distance(a, b))
    previous = 0.0
    positions = []
    for point in points:
        scale = math.cos(math.radians(point[0]))
        candidates = []
        for i in range(int(previous), len(shape) - 1):
            a, b = shape[i:i+2]
            dx, dy = (b[1]-a[1])*scale, b[0]-a[0]
            norm = dx*dx + dy*dy
            if not norm:
                continue
            t = max(0, min(1, ((point[1]-a[1])*scale*dx+(point[0]-a[0])*dy)/norm))
            if i+t < previous:
                continue
            q = (a[0]+t*dy, a[1]+t*(b[1]-a[1]))
            # Métrica local simples para ordenação; verifique geodesicamente a projeção final.
            gap = math.hypot((point[1]-q[1])*scale, point[0]-q[0])*111195
            candidates.append((gap, i+t, q, cumulative[i]+t*(cumulative[i+1]-cumulative[i])))
        if not candidates:
            positions.append(None)
            continue
        minimum = min(c[0] for c in candidates)
        best = min((c for c in candidates if c[0] <= minimum+5), key=lambda c:c[1])
        if distance(point, best[2]) > 150:
            positions.append(None)
            continue
        previous = best[1]
        positions.append({'position': previous, 'point': best[2], 'meters': best[3]})
    return positions


def schema(db):
    db.executescript('''
    CREATE TABLE graph_meta(id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
    CREATE TABLE graph_stop(id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL);
    CREATE TABLE pattern(id INTEGER PRIMARY KEY, route_id TEXT, code TEXT, direction TEXT,
      headsign TEXT, shape_id TEXT, stops TEXT, geometry TEXT, projections TEXT);
    CREATE TABLE timetable(trip_id TEXT PRIMARY KEY, pattern_id INTEGER, service_id TEXT,
      times TEXT, frequencies TEXT);
    CREATE INDEX timetable_pattern ON timetable(pattern_id);
    CREATE TABLE ride_edge(id INTEGER PRIMARY KEY, origin TEXT, destination TEXT,
      pattern_id INTEGER, boarding_index INTEGER, alighting_index INTEGER,
      distance_meters REAL, min_ride_seconds REAL CHECK(min_ride_seconds>=0),
      UNIQUE(pattern_id,boarding_index,alighting_index));
    CREATE INDEX ride_out ON ride_edge(origin,destination);
    CREATE INDEX ride_in ON ride_edge(destination,origin);
    CREATE TABLE walk_edge(origin TEXT, destination TEXT, air_meters REAL,
      distance_meters REAL, seconds REAL, geometry TEXT, source TEXT, checked_at TEXT,
      status TEXT NOT NULL CHECK(status IN ('pending','verified','unavailable','over_limit')),
      PRIMARY KEY(origin,destination));
    CREATE INDEX walk_in ON walk_edge(destination,origin);
    CREATE INDEX walk_status ON walk_edge(status,origin,destination);
    CREATE TABLE candidate_cache(origin TEXT, destination TEXT, transfers INTEGER,
      revision INTEGER, complete INTEGER, candidates TEXT,
      PRIMARY KEY(origin,destination,transfers));
    CREATE VIEW transfer_link AS
      SELECT id AS origin,id AS destination,0.0 AS distance_meters,0.0 AS seconds FROM graph_stop
      UNION ALL
      SELECT origin,destination,distance_meters,seconds FROM walk_edge WHERE status='verified';
    CREATE VIEW direct_adjacency AS
      SELECT origin,destination,pattern_id,boarding_index,alighting_index,distance_meters,
        min_ride_seconds FROM ride_edge;
    CREATE VIEW walk_adjacency AS
      SELECT origin,destination,distance_meters,seconds FROM walk_edge WHERE status='verified';
    ''')
    # Produtos relacionais indexados, não um produto cartesiano global materializado.
    for transfers in range(3):
        edges = [f'r{i}' for i in range(transfers+1)]
        ids = [f'{r}.id AS edge{i}' for i,r in enumerate(edges)]
        ids += [f'NULL AS edge{i}' for i in range(transfers+1,3)]
        joins = ['ride_edge r0']
        for i in range(transfers):
            joins += [f'JOIN transfer_link w{i} ON w{i}.origin=r{i}.destination',
                      f'JOIN ride_edge r{i+1} ON r{i+1}.origin=w{i}.destination AND r{i+1}.pattern_id<>r{i}.pattern_id']
        cost = '+'.join([f'{r}.min_ride_seconds' for r in edges]+[f'w{i}.seconds+{TRANSFER_SECONDS}' for i in range(transfers)])
        db.execute(f'''CREATE VIEW routes_{transfers} AS SELECT r0.origin,{edges[-1]}.destination,
            {transfers} AS transfers,{','.join(ids)},({cost}) AS lower_bound_seconds
            FROM {' '.join(joins)}''')


def build(source=None, target=None, walk_radius=walking.WALK_LIMIT, progress=None):
    """Reconstrução completa atômica, sem requisições externas. O índice anterior resiste a falhas."""
    source = Path(source or store.database_path()).resolve()
    target = Path(target or graph_path()).resolve()
    if source == target:
        raise ValueError('O índice deve ser separado do GTFS de origem.')
    if not math.isfinite(walk_radius) or not 0 < walk_radius <= walking.MAX_DISTANCE:
        raise ValueError('Raio de caminhada inválido.')
    signature = fingerprint(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=target.parent, suffix='.sqlite3')
    os.close(fd)
    src = readonly(source)
    try:
        with sqlite3.connect(name) as db:
            schema(db)
            stops = {r['stop_id']: store.stop(r) for r in src.execute('''SELECT s.* FROM stops s
                WHERE EXISTS (SELECT 1 FROM stop_times st JOIN trips t USING(trip_id)
                JOIN routes r USING(route_id) WHERE st.stop_id=s.stop_id AND r.route_type='3')''')}
            db.executemany('INSERT INTO graph_stop VALUES (?,?,?,?)',
                ((s['id'],s['name'],s['lat'],s['lon']) for s in stops.values()))
            for table in ('calendar','calendar_dates'):
                cols = store.TABLES[table]
                db.execute(f'CREATE TABLE {table} ('+','.join(c+' TEXT' for c in cols)+')')
                db.executemany(f'INSERT INTO {table} VALUES ('+','.join('?' for _ in cols)+')',src.execute('SELECT * FROM '+table))
            db.execute('CREATE INDEX calendar_service ON calendar(service_id)')
            db.execute('CREATE INDEX exception_service ON calendar_dates(service_id,date)')
            patterns = {}
            times = defaultdict(list)
            for r in src.execute('SELECT * FROM stop_times ORDER BY trip_id,stop_sequence'):
                times[r['trip_id']].append(r)
            freqs = defaultdict(list)
            for r in src.execute('SELECT * FROM frequencies'):
                freqs[r['trip_id']].append([store.seconds(r['start_time']),store.seconds(r['end_time']),float(r['headway_secs']),r['exact_times']=='1'])
            skipped = []
            for trip in src.execute("SELECT t.*,r.route_short_name FROM trips t JOIN routes r USING(route_id) WHERE r.route_type='3'"):
                rows = times[trip['trip_id']]
                try:
                    tt = [(r['stop_id'],store.seconds(r['arrival_time']),store.seconds(r['departure_time'])) for r in rows]
                    if len(tt)<2 or any(a<0 or d<a for _,a,d in tt) or any(b[1]<a[2] for a,b in zip(tt,tt[1:])):
                        raise ValueError()
                    if any(not math.isfinite(f[2]) or f[2]<=0 or f[1]<=f[0] for f in freqs[trip['trip_id']]):
                        raise ValueError()
                except (ValueError,TypeError):
                    skipped.append(trip['trip_id'])
                    continue
                ids = [t[0] for t in tt]
                key = (trip['route_id'],trip['direction_id'],trip['trip_headsign'],trip['shape_id'],tuple(ids))
                if key not in patterns:
                    pid = len(patterns)+1
                    shape = [tuple(r) for r in src.execute('SELECT shape_pt_lat,shape_pt_lon FROM shapes WHERE shape_id=? ORDER BY shape_pt_sequence',(trip['shape_id'],))]
                    positions = projected_positions(shape,[(stops[s]['lat'],stops[s]['lon']) for s in ids])
                    patterns[key] = (pid,positions)
                    db.execute('INSERT INTO pattern VALUES (?,?,?,?,?,?,?,?,?)',
                        (pid,trip['route_id'],trip['route_short_name'],trip['direction_id'],trip['trip_headsign'],trip['shape_id'],json.dumps(ids),json.dumps(shape),json.dumps(positions)))
                    if progress and pid % 100 == 0:
                        progress(f'{pid} padrões de itinerário indexados')
                pid, positions = patterns[key]
                db.execute('INSERT INTO timetable VALUES (?,?,?,?,?)',(trip['trip_id'],pid,trip['service_id'],json.dumps(tt),json.dumps(freqs[trip['trip_id']])))
                def edges():
                    for i,a in enumerate(tt):
                        for j in range(i+1,len(tt)):
                            if a[0] == tt[j][0]:
                                continue
                            pa,pb = positions[i],positions[j]
                            meters = max(0,pb['meters']-pa['meters']) if pa and pb else None
                            yield a[0],tt[j][0],pid,i,j,meters,tt[j][1]-a[2]
                db.executemany('''INSERT INTO ride_edge(origin,destination,pattern_id,boarding_index,alighting_index,distance_meters,min_ride_seconds)
                    VALUES (?,?,?,?,?,?,?) ON CONFLICT(pattern_id,boarding_index,alighting_index)
                    DO UPDATE SET min_ride_seconds=MIN(min_ride_seconds,excluded.min_ride_seconds)''',edges())
            # A grade espacial gera candidatos dirigidos. Distância em linha reta nunca vale como caminhada.
            cells = defaultdict(list)
            step = walk_radius/111195
            for sid,s in stops.items():
                cells[(math.floor(s['lat']/step),math.floor(s['lon']/step))].append(sid)
            def candidates():
                for sid,s in stops.items():
                    y,x = math.floor(s['lat']/step),math.floor(s['lon']/step)
                    span = math.ceil(1/max(.01,math.cos(math.radians(s['lat']))))+1
                    for dy in range(-2,3):
                        for dx in range(-span,span+1):
                            for other in cells.get((y+dy,x+dx),[]):
                                if other==sid:
                                    continue
                                o=stops[other];gap=distance((s['lat'],s['lon']),(o['lat'],o['lon']))
                                if gap<=walk_radius:
                                    yield sid,other,gap,'pending'
            db.executemany('INSERT INTO walk_edge(origin,destination,air_meters,status) VALUES (?,?,?,?)',candidates())
            counts = {t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('graph_stop','pattern','timetable','ride_edge','walk_edge')}
            meta = {'version':VERSION,'source':signature,'built_at':timezone.now().isoformat(),'walk_radius':walk_radius,
                    'walking_speed_kmh':walking.WALK_SPEED_KMH,'revision':0,'counts':counts,'walk_status_counts':{'pending':counts['walk_edge']},'skipped_trips':len(skipped),'skipped_trip_ids':skipped}
            db.execute('INSERT INTO graph_meta VALUES (1,?)',(json.dumps(meta),))
            db.execute('ANALYZE')
            if fingerprint(source)!=signature:
                raise ValueError('GTFS mudou durante a construção; índice anterior preservado.')
        os.replace(name,target)
        return meta
    finally:
        src.close()
        if os.path.exists(name):
            os.unlink(name)


def put_walk(db, origin, destination, result):
    """Persiste apenas percursos detalhados, verificados e dirigidos; erros impedem o uso do trecho."""
    row=db.execute('SELECT * FROM walk_edge WHERE origin=? AND destination=?',(origin,destination)).fetchone()
    if row is None:
        raise ValueError('Par não cadastrado entre os candidatos de caminhada.')
    meta=json.loads(db.execute('SELECT value FROM graph_meta').fetchone()[0])
    coverage=meta.get('walk_status_counts') or dict(db.execute('SELECT status,COUNT(*) FROM walk_edge GROUP BY status'))
    status='unavailable';meters=seconds=geometry=None
    if result.get('available'):
        meters=float(result['distance_meters']);geometry=result['geometry']
        if not math.isfinite(meters) or meters<0 or len(geometry)<2 or any(len(p)!=2 or any(not math.isfinite(float(v)) for v in p) for p in geometry):
            raise ValueError('Percurso a pé inválido.')
        polyline_meters=sum(distance(a,b) for a,b in zip(geometry,geometry[1:]))
        if meters+max(2,polyline_meters*.01)<polyline_meters:
            raise ValueError('Distância incompatível com a geometria da caminhada.')
        ends=[db.execute('SELECT lat,lon FROM graph_stop WHERE id=?',(sid,)).fetchone() for sid in (origin,destination)]
        if distance(ends[0],geometry[0])>40 or distance(ends[1],geometry[-1])>40 or meters+2<row['air_meters']:
            raise ValueError('Percurso a pé não corresponde aos pontos informados.')
        seconds=meters/walking.WALK_METERS_PER_SECOND
        status='verified' if meters<=meta['walk_radius'] else 'over_limit'
    db.execute('''UPDATE walk_edge SET distance_meters=?,seconds=?,geometry=?,source=?,checked_at=?,status=?
        WHERE origin=? AND destination=?''',(meters,seconds,json.dumps(geometry) if geometry else None,result.get('source',''),timezone.now().isoformat(),status,origin,destination))
    coverage[row['status']]=coverage.get(row['status'],0)-1
    coverage[status]=coverage.get(status,0)+1
    meta['walk_status_counts']=coverage
    meta['revision']+=1
    db.execute('UPDATE graph_meta SET value=? WHERE id=1',(json.dumps(meta),))
    db.execute('DELETE FROM candidate_cache')
    return status


def verify_walks(path=None, limit=0, origins=None, resolver=None):
    """Enriquecimento limitado e retomável pelo roteador pedestre existente, sem processamento em massa por padrão."""
    if not isinstance(limit,int) or limit<0:
        raise ValueError('Limite inválido.')
    path=path or graph_path()
    with connection(path):
        pass
    resolver=resolver or (lambda a,b: walking.route(a,b,wait_for_slot=True))
    with sqlite3.connect(path) as db:
        db.row_factory=sqlite3.Row
        params=[];where="status='pending'"
        if origins:
            where+=' AND origin IN ('+','.join('?' for _ in origins)+')';params.extend(origins)
        pairs=db.execute('SELECT origin,destination FROM walk_edge WHERE '+where+' ORDER BY air_meters LIMIT ?',[*params,limit]).fetchall()
        summary=defaultdict(int)
        for pair in pairs:
            points=[]
            for sid in pair:
                s=db.execute('SELECT * FROM graph_stop WHERE id=?',(sid,)).fetchone()
                points.append(dict(s))
            result=resolver(*points)
            summary[put_walk(db,*pair,result)]+=1
            db.commit()
        return dict(summary)


def materialize(db, origin, destination, transfers, max_candidates=10000, seconds=5):
    """Armazena um produto relacional limitado para este par, sem truncamento silencioso."""
    if transfers not in (0,1,2) or max_candidates<1 or not math.isfinite(seconds) or seconds<=0:
        raise ValueError('Limites inválidos.')
    if origin == destination:
        return [],True
    meta=json.loads(db.execute('SELECT value FROM graph_meta').fetchone()[0]);revision=meta['revision']
    cache=db.execute('SELECT * FROM candidate_cache WHERE origin=? AND destination=? AND transfers=? AND revision=?',
                     (origin,destination,transfers,revision)).fetchone()
    if cache and cache['complete']:
        return json.loads(cache['candidates']),True
    cutoff=time.monotonic()+seconds;rows=[];complete=True
    db.set_progress_handler(lambda: int(time.monotonic()>cutoff),10000)
    try:
        cursor=db.execute(f'SELECT edge0,edge1,edge2,lower_bound_seconds FROM routes_{transfers} WHERE origin=? AND destination=? LIMIT ?',
                          (origin,destination,max_candidates+1))
        for r in cursor:
            rows.append(list(r))
        if len(rows)>max_candidates:
            rows=rows[:max_candidates];complete=False
    except sqlite3.OperationalError as e:
        if str(e)!='interrupted':
            raise
        complete=False
    finally:
        db.set_progress_handler(None,0)
    db.execute('INSERT OR REPLACE INTO candidate_cache VALUES (?,?,?,?,?,?)',
               (origin,destination,transfers,revision,int(complete),json.dumps(rows)))
    return rows,complete


def query(origin, destination, now=None, transfers=(0,1,2), path=None, access_seconds=0,
          egress_seconds=0, max_candidates=10000, query_seconds=5):
    """Melhor viagem programada por quantidade exata de trocas, com completude explícita.

    A espera depende da chegada a cada parada. Frequências sem fase exata usam metade
    do intervalo, como no planejador existente, e são identificadas como estimativas.
    """
    now=now or timezone.localtime()
    if timezone.is_naive(now):
        raise ValueError('Informe data e hora com fuso horário.')
    now=timezone.localtime(now)
    if any(not math.isfinite(x) or x<0 for x in (access_seconds,egress_seconds)):
        raise ValueError('Tempos de acesso/saída inválidos.')
    transfers=tuple(transfers)
    if not transfers or any(t not in (0,1,2) for t in transfers):
        raise ValueError('Consulte 0, 1 ou 2 baldeações.')
    path=path or graph_path()
    with connection(path):
        pass
    with sqlite3.connect(path) as db:
        db.row_factory=sqlite3.Row
        for sid in (origin,destination):
            if db.execute('SELECT 1 FROM graph_stop WHERE id=?',(sid,)).fetchone() is None:
                raise ValueError('Ponto não cadastrado.')
        start=now.timestamp();horizon=start+HORIZON_SECONDS
        midnight=now.replace(hour=0,minute=0,second=0,microsecond=0)
        schedules={};active={};edge_cache={};walk_cache={}
        def edge(eid):
            if eid not in edge_cache:
                edge_cache[eid]=dict(db.execute('SELECT e.*,p.code,p.direction FROM ride_edge e JOIN pattern p ON p.id=e.pattern_id WHERE e.id=?',(eid,)).fetchone())
            return edge_cache[eid]
        def departure(e, ready):
            pid=e['pattern_id']
            if pid not in schedules:
                schedules[pid]=[]
                for row in db.execute('SELECT * FROM timetable WHERE pattern_id=?',(pid,)):
                    tt=json.loads(row['times']);freq=json.loads(row['frequencies']);entries=[]
                    latest=max([t[2] for t in tt]+[f[1] for f in freq])
                    for delta in range(-math.ceil(latest/86400),2):
                        day=midnight+timedelta(days=delta);key=(row['service_id'],day.date())
                        if key not in active:
                            active[key]=store.service_active(db,*key)
                        if not active[key]:
                            continue
                        base=day.timestamp()
                        entries.extend((base+a,base+b,h,exact) for a,b,h,exact in freq)
                        if not freq:
                            t=base+tt[0][2];entries.append((t,t,0,True))
                    schedules[pid].append((row['trip_id'],tt,entries,any(not f[3] for f in freq)))
            best=None
            for tid,tt,windows,estimated in schedules[pid]:
                depart=next_departure({'times':tt},e['boarding_index'],ready,windows)
                arrive=depart+tt[e['alighting_index']][1]-tt[e['boarding_index']][2]
                if arrive<=horizon and (best is None or arrive<best[1]):
                    best=(depart,arrive,tid,estimated)
            return best
        result=[];complete=True;examined=0;counts={}
        for count in transfers:
            rows,done=materialize(db,origin,destination,count,max_candidates,query_seconds)
            complete &= done;counts[str(count)]={'candidates':len(rows),'complete':done}
            best=None
            for *eids,lower in sorted(rows,key=lambda r:r[-1]):
                if best and access_seconds+egress_seconds+lower>=best['duration_seconds']:
                    continue
                reached=start+access_seconds;legs=[];walks=[];valid=True;estimated=False
                for eid in [e for e in eids if e is not None]:
                    e=edge(eid);walk_seconds=0
                    if legs:
                        a,b=legs[-1]['destination'],e['origin']
                        if a!=b:
                            key=(a,b)
                            if key not in walk_cache:
                                walk_cache[key]=dict(db.execute("SELECT * FROM walk_edge WHERE origin=? AND destination=? AND status='verified'",key).fetchone())
                            w=walk_cache[key];walk_seconds=w['seconds']
                            walks.append({'origin':a,'destination':b,'distance_meters':w['distance_meters'],'seconds':walk_seconds})
                        reached+=walk_seconds+TRANSFER_SECONDS
                    choice=departure(e,reached)
                    if choice is None:
                        valid=False;break
                    depart,arrive,tid,approx=choice;estimated |= approx
                    legs.append({**e,'trip_id':tid,'departure':timezone.datetime.fromtimestamp(depart,now.tzinfo).isoformat(),
                        'arrival':timezone.datetime.fromtimestamp(arrive,now.tzinfo).isoformat(),'wait_seconds':depart-reached,
                        'ride_seconds':arrive-depart,'frequency_estimate':approx,'transfer_buffer_seconds':TRANSFER_SECONDS if len(legs) else 0})
                    reached=arrive
                examined+=1
                if valid and legs:
                    total=reached+egress_seconds-start
                    if best is None or total<best['duration_seconds']:
                        best={'transfers':count,'duration_seconds':total,'arrival':timezone.datetime.fromtimestamp(reached+egress_seconds,now.tzinfo).isoformat(),
                              'access_seconds':access_seconds,'egress_seconds':egress_seconds,'legs':legs,'walks':walks,
                              'ride_seconds':sum(l['ride_seconds'] for l in legs),
                              'wait_seconds':sum(l['wait_seconds'] for l in legs),
                              'transfer_walk_seconds':sum(w['seconds'] for w in walks),
                              'transfer_buffer_seconds':count*TRANSFER_SECONDS,
                              'frequency_estimate':estimated,'cost_source':'GTFS + caminhada verificada; sem previsão operacional'}
            if best:
                result.append(best)
        meta=json.loads(db.execute('SELECT value FROM graph_meta').fetchone()[0])
        coverage=meta.get('walk_status_counts')
        if coverage is None:
            coverage=dict(db.execute('SELECT status,COUNT(*) FROM walk_edge GROUP BY status'))
            meta['walk_status_counts']=coverage
            db.execute('UPDATE graph_meta SET value=? WHERE id=1',(json.dumps(meta),))
        pending=coverage.get('pending',0)+coverage.get('unavailable',0)
        return {'journeys':sorted(result,key=lambda r:r['duration_seconds']),'candidate_search_complete':complete,
                'complete_for_verified_graph':complete,'walk_pairs_not_verified':pending,'walk_coverage':coverage,'evaluated_candidates':examined,'counts':counts}
