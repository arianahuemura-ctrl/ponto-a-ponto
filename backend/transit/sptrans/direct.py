"""Índices municipais diretos e reversos construídos percorrendo padrões dirigidos.

O índice reverso registra arestas de entrada: C <- B é a mesma aresta de ônibus B -> C.
Ele nunca cria um serviço C -> B. As consultas de transferência aqui são apenas estruturais.
"""
import json
import math
import os
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from django.utils import timezone
from . import graph, store

VERSION = 1


def database_path():
    return store.database_path().with_suffix('.direct.sqlite3')


@contextmanager
def connection(path=None):
    db=graph.readonly(path or database_path())
    try:
        meta=json.loads(db.execute('SELECT value FROM direct_meta WHERE id=1').fetchone()[0])
        if meta['version']!=VERSION or meta['source_gtfs']!=graph.fingerprint(store.database_path()):
            raise ValueError('Índice direto/reverso desatualizado. Execute build_sptrans_direct.')
        yield db
    finally:
        db.close()


def build(source=None,target=None,progress=None):
    """Banco separado e substituído atomicamente; todas as arestas diretas com ambos os índices.

    Reutiliza padrões e projeções validados, não a antiga tabela de todos os pares.
    Preserva todas as variantes, inclusive as que ficam fora das 16 exibidas.
    """
    source=Path(source or graph.graph_path()).resolve()
    target=Path(target or database_path()).resolve()
    if target in (source,store.database_path().resolve()):
        raise ValueError('O banco direto deve ser separado do GTFS e do grafo de origem.')
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='direct-build-',suffix='.sqlite3',dir=target.parent)
    os.close(fd)
    start=time.perf_counter()
    try:
        with graph.connection(source) as src, sqlite3.connect(temporary) as db:
            src.execute('BEGIN')  # Retrato consistente da fonte, mesmo se as correspondências operacionais mudarem.
            meta=json.loads(src.execute('SELECT value FROM graph_meta WHERE id=1').fetchone()[0])
            db.execute('PRAGMA cache_size=-131072')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA journal_mode=DELETE')
            for table in ('graph_stop','pattern','timetable','calendar','calendar_dates','ride_edge'):
                sql=src.execute("SELECT sql FROM sqlite_master WHERE name=? AND type='table'",(table,)).fetchone()[0]
                db.execute(sql)
                if table!='ride_edge':
                    rows=src.execute('SELECT * FROM '+table)
                    marks=','.join('?' for _ in rows.description)
                    db.executemany('INSERT INTO '+table+' VALUES ('+marks+')',rows)
            db.execute('CREATE TABLE direct_meta(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT NOT NULL)')
            total=unknown=self_excluded=patterns=0
            for pattern in src.execute('SELECT id,stops,projections FROM pattern ORDER BY id'):
                stops=json.loads(pattern['stops']);positions=json.loads(pattern['projections'])
                trips=[json.loads(r[0]) for r in src.execute('SELECT times FROM timetable WHERE pattern_id=?',(pattern['id'],))]
                if not trips:raise ValueError('Padrão sem programação.')
                if len(stops)!=len(positions) or any([t[0] for t in tt]!=stops for tt in trips):
                    raise ValueError('Sequência de paradas inconsistente no padrão.')
                edges=[]
                for i,origin in enumerate(stops):
                    for j in range(i+1,len(stops)):
                        destination=stops[j]
                        if origin==destination:
                            self_excluded+=1;continue
                        a,b=positions[i],positions[j]
                        distance=max(0,b['meters']-a['meters']) if a and b else None
                        duration=min(tt[j][1]-tt[i][2] for tt in trips)
                        if distance is not None and (not math.isfinite(distance) or distance<0):
                            raise ValueError('Distância projetada inválida.')
                        if not math.isfinite(duration) or duration<0:
                            raise ValueError('Programação inválida.')
                        unknown+=int(distance is None)
                        edges.append((origin,destination,pattern['id'],i,j,distance,duration))
                db.executemany('''INSERT INTO ride_edge(origin,destination,pattern_id,boarding_index,
                    alighting_index,distance_meters,min_ride_seconds) VALUES (?,?,?,?,?,?,?)''',edges)
                total+=len(edges);patterns+=1
                if progress and patterns%200==0:
                    progress(f'{patterns} padrões; {total} conexões direcionadas')
            edges_seconds=time.perf_counter()-start
            db.executescript('''
                CREATE INDEX direct_out ON ride_edge(origin,destination,distance_meters,id);
                CREATE INDEX direct_in ON ride_edge(destination,origin,distance_meters,id);
                CREATE INDEX timetable_pattern ON timetable(pattern_id);
                CREATE INDEX calendar_service ON calendar(service_id);
                CREATE INDEX exception_service ON calendar_dates(service_id,date);
                CREATE VIEW direct_forward AS SELECT id AS edge_id,origin AS search_from,
                    destination AS search_to,origin,destination,pattern_id,boarding_index,
                    alighting_index,distance_meters,min_ride_seconds FROM ride_edge;
                CREATE VIEW direct_reverse AS SELECT id AS edge_id,destination AS search_from,
                    origin AS search_to,origin,destination,pattern_id,boarding_index,
                    alighting_index,distance_meters,min_ride_seconds FROM ride_edge;
                CREATE VIEW direct_services AS SELECT e.*,p.route_id,p.code,p.direction,p.headsign
                    FROM ride_edge e JOIN pattern p ON p.id=e.pattern_id;
                CREATE VIEW single_transfer AS SELECT a.origin,b.destination,
                    a.destination AS transfer_stop,a.id AS first_edge,b.id AS second_edge,
                    a.distance_meters+b.distance_meters AS distance_meters
                    FROM ride_edge a JOIN ride_edge b ON a.destination=b.origin
                    WHERE a.pattern_id<>b.pattern_id AND a.origin<>b.destination
                    AND a.destination<>a.origin AND a.destination<>b.destination;
            ''')
            # Valide cardinalidade completa, sentido e restrições de identidade copiadas.
            bad=db.execute('SELECT COUNT(*) FROM ride_edge WHERE boarding_index>=alighting_index OR origin=destination').fetchone()[0]
            orphans=db.execute('''SELECT COUNT(*) FROM ride_edge e LEFT JOIN pattern p ON p.id=e.pattern_id
                LEFT JOIN graph_stop a ON a.id=e.origin LEFT JOIN graph_stop b ON b.id=e.destination
                WHERE p.id IS NULL OR a.id IS NULL OR b.id IS NULL''').fetchone()[0]
            unique_pairs=db.execute('SELECT COUNT(*) FROM (SELECT origin,destination FROM ride_edge GROUP BY origin,destination)').fetchone()[0]
            expected=src.execute('SELECT COUNT(*) FROM ride_edge').fetchone()[0]
            if bad or orphans or expected!=total:
                raise ValueError('Falha na validação das conexões diretas.')
            built={'version':VERSION,'built_at':timezone.now().isoformat(),'source_gtfs':meta['source'],
                'source_graph':str(source),'patterns':patterns,'stops':db.execute('SELECT COUNT(*) FROM graph_stop').fetchone()[0],
                'edges':total,'reverse_entries':total,'unique_pairs':unique_pairs,'unknown_distances':unknown,
                'same_stop_pairs_excluded':self_excluded,'skipped_source_trips':meta.get('skipped_trips',0),
                'skipped_source_trip_ids':meta.get('skipped_trip_ids'),
                'generation_seconds':edges_seconds,'total_build_seconds':time.perf_counter()-start,
                'forward_index':'direct_out','reverse_index':'direct_in','structural_only':True,
                'top_k_applied_at_build':False,'invalid_directions':bad,'orphan_edges':orphans}
            if graph.fingerprint(store.database_path())!=meta['source']:
                raise ValueError('GTFS mudou durante a construção; saída anterior preservada.')
            db.execute('INSERT INTO direct_meta VALUES (1,?)',(json.dumps(built,ensure_ascii=False),))
            db.execute('ANALYZE');db.commit()
            check_start=time.perf_counter()
            integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
            if integrity!='ok':raise ValueError('Integridade SQLite inválida.')
            built['integrity_check']=integrity
            built['integrity_seconds']=time.perf_counter()-check_start
            built['total_build_seconds']=time.perf_counter()-start
            built['sqlite_page_bytes']={r[0]:r[1] for r in db.execute('SELECT name,SUM(pgsize) FROM dbstat GROUP BY name')}
            db.execute('UPDATE direct_meta SET value=? WHERE id=1',(json.dumps(built,ensure_ascii=False),));db.commit()
        os.replace(temporary,target)
        return {**built,'database':str(target),'database_bytes':target.stat().st_size}
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def _validate_stop(db,sid):
    if not db.execute('SELECT 1 FROM graph_stop WHERE id=?',(sid,)).fetchone():
        raise ValueError('Ponto não cadastrado: '+str(sid))


def _edge(db,eid):
    row=db.execute('SELECT * FROM direct_services WHERE id=?',(eid,)).fetchone()
    return {**dict(row),'walking_meters':0,'walking_seconds':0}


def lookup(stop,reverse=False,other=None,limit=100,path=None):
    """Destinos de saída ou origens de entrada, preservando o sentido real do ônibus."""
    if not isinstance(limit,int) or not 1<=limit<=10000:raise ValueError('Limite entre 1 e 10000.')
    with connection(path) as db:
        _validate_stop(db,stop)
        if other is not None:_validate_stop(db,other)
        column,opposite=('destination','origin') if reverse else ('origin','destination')
        index='direct_in' if reverse else 'direct_out'
        where=f'{column}=?';params=[stop]
        if other is not None:where+=f' AND {opposite}=?';params.append(other)
        # Geometrias desconhecidas continuam alcançáveis, mas ficam após as distâncias conhecidas.
        ids=db.execute(f'''SELECT id FROM ride_edge INDEXED BY {index} WHERE {where}
            ORDER BY distance_meters IS NULL,distance_meters,id LIMIT ?''',params+[limit+1]).fetchall()
        return {'search_from':stop,'reverse':reverse,'structural_only':True,
                'has_more':len(ids)>limit,'connections':[_edge(db,r[0]) for r in ids[:limit]]}


def transfers(origin,destination,limit=8,seconds=5,path=None):
    """Combina saída A->B com entrada B->C. Não afirma viabilidade de horários."""
    if not isinstance(limit,int) or not 1<=limit<=1000:raise ValueError('Limite entre 1 e 1000.')
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Tempo de consulta deve ser positivo.')
    with connection(path) as db:
        _validate_stop(db,origin);_validate_stop(db,destination)
        if origin==destination:
            return {'origin':origin,'destination':destination,'structural_only':True,'complete':True,'candidates':[]}
        deadline=time.monotonic()+seconds
        db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
        rows=[];complete=True
        try:
            rows=db.execute('''SELECT a.id AS first_edge,b.id AS second_edge,
                a.destination AS transfer_stop,a.distance_meters+b.distance_meters AS distance_meters
                FROM ride_edge a INDEXED BY direct_out JOIN ride_edge b INDEXED BY direct_in
                ON b.origin=a.destination
                WHERE a.origin=? AND b.destination=? AND a.pattern_id<>b.pattern_id
                    AND a.destination NOT IN (?,?)
                    AND a.distance_meters IS NOT NULL AND b.distance_meters IS NOT NULL
                ORDER BY distance_meters,a.id,b.id LIMIT ?''',(origin,destination,origin,destination,limit+1)).fetchall()
        except sqlite3.OperationalError as error:
            if str(error)!='interrupted':raise
            complete=False
        finally:db.set_progress_handler(None,0)
        candidates=[{'transfer_stop':r['transfer_stop'],'distance_meters':r['distance_meters'],
                     'legs':[_edge(db,r['first_edge']),_edge(db,r['second_edge'])]} for r in rows[:limit]]
        return {'origin':origin,'destination':destination,'structural_only':True,'complete':complete,
                'has_more':len(rows)>limit,'candidates':candidates,
                'scope':'Transferência no mesmo ponto; horários e caminhada entre pontos não avaliados.'}
