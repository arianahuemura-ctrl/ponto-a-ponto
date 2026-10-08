"""Listas exatas por distância preparadas offline; consultas online nunca compõem transferências.

Somente os trajetos finais TOP 16/8 são retidos por OD, sem truncar trechos intermediários.
Horários e previsões ao vivo permanecem em uma etapa separada de avaliação temporal.
"""
from contextlib import closing
import json
from mbm import routing_config as config
import math
from pathlib import Path
import shutil
import sqlite3
import time
from django.utils import timezone
from . import city_connections as structural, direct, graph

VERSION = 2


class MaterializationPending(ValueError):
    pass


def database_path(experimental=False):
    suffix='.materialized.heuristics.sqlite3' if experimental else '.materialized.sqlite3'
    return direct.store.database_path().with_suffix(suffix)


def _source_meta(source):
    with direct.connection(source) as db:
        meta=json.loads(db.execute('SELECT value FROM connections_meta WHERE id=1').fetchone()[0])
        if meta['version']!=structural.VERSION:
            raise ValueError('Componentes estruturais desatualizados.')
        if meta.get('walking_speed_kmh') != config.WALK_SPEED_KMH or meta.get('max_walk_meters') != config.WALK_LIMIT_METERS:
            raise ValueError('Configuração de caminhadas alterada; regenere os componentes.')
        if meta.get('walk_source'):
            with closing(graph.readonly(meta['walk_source'][0])) as foot:
                foot_meta=json.loads(foot.execute('SELECT value FROM walk_meta WHERE id=1').fetchone()[0])
                if foot_meta.get('configuration') != config.walking_signature():
                    raise ValueError('Configuração da rede pedestre alterada; regenere as caminhadas.')
            if graph.fingerprint(meta['walk_source'][0])!=meta['walk_source']:
                raise ValueError('Caminhadas desatualizadas.')
        elif Path(meta['graph_source']).exists():
            with graph.connection(meta['graph_source']) as g:
                revision=json.loads(g.execute('SELECT value FROM graph_meta').fetchone()[0])['revision']
            if revision!=meta['walk_revision']:
                raise ValueError('Caminhadas desatualizadas.')
    return meta


def _signature(source, experimental=False):
    meta=_source_meta(source)
    signature={'version':VERSION,'source':graph.fingerprint(source),'gtfs':meta['source_gtfs'],
            'quotas':{str(k):structural.QUOTAS[k] for k in (1,2)},
            'walk_speed_kmh':config.WALK_SPEED_KMH,'coverage':{'verified_walks':meta['verified_walks'],
            'unknown_ride_distances':meta['unknown_ride_distances']}}
    if experimental:signature['selection_policy']='coverage_then_midpoint_last_v1'
    return signature


def _read_meta(db):
    return json.loads(db.execute('SELECT value FROM materialization_meta WHERE id=1').fetchone()[0])


def _validate(meta):
    policy=meta['signature'].get('selection_policy')
    if policy not in (None,'coverage_then_midpoint_last_v1'):
        raise ValueError('Política de seleção desconhecida.')
    if meta['signature']!=_signature(meta['signature']['source'][0],experimental=policy is not None):
        raise ValueError('Conexões materializadas desatualizadas; use um novo artefato.')


def initialize(source=None, target=None, experimental=False):
    source=Path(source or structural.database_path()).resolve()
    target=Path(target or database_path(experimental)).resolve()
    if target in (source, direct.database_path().resolve(), graph.graph_path().resolve(),
                  direct.store.database_path().resolve()):
        raise ValueError('O consolidado deve ser separado das fontes.')
    sig=_signature(source,experimental)
    target.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(target) as db:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='materialization_meta'").fetchone()
        if exists:
            if _read_meta(db)['signature']!=sig:
                raise ValueError('Artefato incompatível; escolha nova saída para reconstruir.')
            return target
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone():
            raise ValueError('A saída já contém outro banco; não será sobrescrita.')
        db.executescript('''
            CREATE TABLE materialization_meta(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT NOT NULL);
            CREATE TABLE materialization_status(
                origin TEXT NOT NULL,destination TEXT NOT NULL,boardings INTEGER NOT NULL CHECK(boardings BETWEEN 1 AND 2),
                state TEXT NOT NULL CHECK(state IN ('ready','timeout')),path_count INTEGER NOT NULL,
                build_seconds REAL NOT NULL,updated_at TEXT NOT NULL,
                PRIMARY KEY(origin,destination,boardings)) WITHOUT ROWID;
            CREATE TABLE conexoes(
                origin TEXT NOT NULL,destination TEXT NOT NULL,boardings INTEGER NOT NULL CHECK(boardings BETWEEN 1 AND 2),
                rank INTEGER NOT NULL CHECK(rank>0),edge1 INTEGER NOT NULL,edge2 INTEGER,edge3 INTEGER,
                walk1 INTEGER,walk2 INTEGER,final_walk INTEGER,
                bus_meters REAL NOT NULL CHECK(bus_meters>=0),walk_meters REAL NOT NULL CHECK(walk_meters>=0),
                walk_seconds REAL NOT NULL CHECK(walk_seconds>=0),distance_meters REAL NOT NULL CHECK(distance_meters>=0),
                PRIMARY KEY(origin,destination,boardings,rank)) WITHOUT ROWID;
            CREATE INDEX conexoes_distancia ON conexoes(origin,destination,boardings,distance_meters,rank);
            CREATE INDEX conexoes_reversas ON conexoes(destination,origin,boardings,rank);
        ''')
        if experimental:
            db.execute('CREATE TABLE policy_decisions(origin TEXT,destination TEXT,boardings INTEGER,skipped INTEGER,sequences_checked INTEGER,sequences_pruned INTEGER,PRIMARY KEY(origin,destination,boardings)) WITHOUT ROWID')
        db.execute('INSERT INTO materialization_meta VALUES(1,?)',(json.dumps({
            'signature':sig,'created_at':timezone.now().isoformat(),'city_complete':False}),))
    return target


def _compact(origin,destination,n,rank,path):
    edges=[];walks=[None,None];final=None;pending=None
    for leg in path['trechos']:
        if leg['modo']=='caminhada':pending=leg['percurso_id']
        else:
            if edges:walks[len(edges)-1]=pending
            edges.append(leg['aresta_id']);pending=None
    final=pending
    if len(edges)!=n:raise ValueError('Número de ônibus inconsistente.')
    return (origin,destination,n,rank,*(edges+[None]*(3-n)),*walks,final,
            path['distancia_onibus_m'],path['distancia_caminhada_m'],path['caminhada_s'],path['distancia_m'])


def materialize(pairs, source=None, target=None, seconds=config.ROUTE_SECONDS, progress=None, min_free_bytes=config.MIN_FREE_GIB*1024**3, experimental=False):
    """Retoma por OD/categoria. Uma lista que excedeu o prazo nunca é publicada como pronta."""
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('Prazo offline inválido.')
    target=initialize(source,target,experimental)
    started=time.perf_counter();built=skipped=timed_out=0
    with sqlite3.connect(target) as db:
        meta=_read_meta(db);source=meta['signature']['source'][0]
        shared={}
        previous_origin=None
        for origin,destination in pairs:
            origin,destination=str(origin),str(destination)
            if origin!=previous_origin:
                shared.clear()
                previous_origin=origin
            for n in (1,2):
                old=db.execute('SELECT state FROM materialization_status WHERE origin=? AND destination=? AND boardings=?',
                               (origin,destination,n)).fetchone()
                if old and old[0]=='ready':skipped+=1;continue
                if shutil.disk_usage(target.parent).free<min_free_bytes:
                    raise OSError('Espaço livre insuficiente; geração preservada para retomada.')
                before=time.perf_counter()
                result=structural.structural_query(origin,destination,path=source,seconds=seconds,categories=(n,),offline=True,shared=shared,experimental=experimental)
                category=result['categories'][n]
                if graph.fingerprint(source)!=meta['signature']['source']:
                    raise ValueError('A fonte mudou durante a geração.')
                with db:
                    db.execute('DELETE FROM conexoes WHERE origin=? AND destination=? AND boardings=?',(origin,destination,n))
                    if category['complete']:
                        db.executemany('INSERT INTO conexoes VALUES ('+','.join('?'*14)+')',
                            [_compact(origin,destination,n,i+1,p) for i,p in enumerate(result['trajetos'])])
                        built+=1
                    else:timed_out+=1
                    if experimental:
                        stats=result.get('convergence_stats',{})
                        db.execute('INSERT OR REPLACE INTO policy_decisions VALUES(?,?,?,?,?,?)',
                            (origin,destination,n,int(category.get('policy_skipped',False)),stats.get('sequences_checked',0),stats.get('sequences_pruned',0)))
                    db.execute('INSERT OR REPLACE INTO materialization_status VALUES(?,?,?,?,?,?,?)',
                        (origin,destination,n,'ready' if category['complete'] else 'timeout',
                         len(result['trajetos']),time.perf_counter()-before,timezone.now().isoformat()))
                if progress:progress(f'{origin} -> {destination}: {n} ônibus, {category["count"]} trajetos, '
                                     f'{"excluído pela política" if category.get("policy_skipped") else "pronto" if category["complete"] else "PENDENTE"}, {time.perf_counter()-before:.3f}s')
        count=db.execute('SELECT count(*) FROM conexoes').fetchone()[0]
        ready=db.execute("SELECT count(*) FROM (SELECT origin,destination FROM materialization_status WHERE state='ready' GROUP BY origin,destination HAVING count(*)=2)").fetchone()[0]
    return {'selection_policy':meta['signature'].get('selection_policy','reference'),'database':str(target),'built_categories':built,'skipped_categories':skipped,
            'timed_out_categories':timed_out,'ready_pairs':ready,'stored_paths':count,
            'seconds':time.perf_counter()-started,'bytes':target.stat().st_size}


def _expand(row, source):
    legs=[]
    def foot(wid):
        w=source.execute('SELECT * FROM walking_link WHERE id=?',(wid,)).fetchone()
        return dict(modo='caminhada',origem=w['origin'],destino=w['destination'],
                    distancia_m=w['distance_meters'],tempo_s=w['seconds'],percurso_id=w['id'])
    for i in range(1,row['boardings']+1):
        if i>1 and row[f'walk{i-1}'] is not None:legs.append(foot(row[f'walk{i-1}']))
        e=source.execute('SELECT * FROM direct_services WHERE id=?',(row[f'edge{i}'],)).fetchone()
        legs.append(dict(modo='onibus',aresta_id=e['id'],padrao_id=e['pattern_id'],linha=e['code'],
            route_id=e['route_id'],sentido=e['direction'],letreiro=e['headsign'],origem=e['origin'],
            destino=e['destination'],distancia_m=e['distance_meters'],embarque_indice=e['boarding_index'],
            desembarque_indice=e['alighting_index']))
    if row['final_walk'] is not None:legs.append(foot(row['final_walk']))
    return dict(embarques=row['boardings'],baldeacoes=row['boardings']-1,trechos=legs,
                distancia_m=row['distance_meters'],distancia_onibus_m=row['bus_meters'],
                distancia_caminhada_m=row['walk_meters'],caminhada_s=row['walk_seconds'])


def query(origin,destination,path=None,quotas=None):
    quotas={n:structural.QUOTAS[n] for n in (1,2)} if quotas is None else quotas
    if set(quotas)!={1,2} or any(not isinstance(v,int) or not 1<=v<=structural.QUOTAS[n] for n,v in quotas.items()):
        raise ValueError('Consulta materializada limitada a um ou dois ônibus (16/8); três ônibus usam o planejador por rodadas.')
    path=Path(path or database_path())
    if not path.exists():raise MaterializationPending('Artefato não gerado. Execute materialize_sptrans_connections.')
    result=dict(origem=origin,destino=destination,trajetos=[],categories={},structural_only=True,
                temporal_feasibility_checked=False,materialized=True)
    with closing(graph.readonly(path)) as db:
        meta=_read_meta(db);_validate(meta)
        if meta['signature'].get('selection_policy'):
            result['selection_policy']=meta['signature']['selection_policy']
            result['policy_decisions']=[dict(r) for r in db.execute('SELECT boardings,skipped,sequences_checked,sequences_pruned FROM policy_decisions WHERE origin=? AND destination=?',(origin,destination))]
        status={r['boardings']:r['state'] for r in db.execute(
            'SELECT boardings,state FROM materialization_status WHERE origin=? AND destination=?',(origin,destination))}
        if any(status.get(n)!='ready' for n in quotas):
            raise MaterializationPending('Par ainda não materializado por completo; não será composto durante a consulta.')
        with direct.connection(meta['signature']['source'][0]) as src:
            for n,k in sorted(quotas.items()):
                started=time.perf_counter()
                rows=db.execute('''SELECT * FROM conexoes WHERE origin=? AND destination=? AND boardings=?
                    ORDER BY distance_meters,rank LIMIT ?''',(origin,destination,n,k)).fetchall()
                result['trajetos'].extend(_expand(row,src) for row in rows)
                result['categories'][n]=dict(complete=True,count=len(rows),seconds=time.perf_counter()-started)
    result['complete']=True;result['coverage']=meta['signature']['coverage']
    return result


def city_pairs(source=None,origins=None):
    """Descobre candidatos OD por padrões dirigidos, nunca pelo produto cartesiano de todas as paradas.

    A alcançabilidade é um superconjunto (ignora exclusões de percursos); o pré-processamento
    exato pode armazenar um resultado vazio concluído. Nunca omite um OD estruturalmente viável.
    """
    source=source or structural.database_path()
    with direct.connection(source) as db:
        patterns=[json.loads(r[0]) for r in db.execute('SELECT stops FROM pattern')]
        walks={}
        for a,b in db.execute('SELECT origin,destination FROM walking_link'):
            walks.setdefault(a,set()).add(b)
        starts=sorted({s for p in patterns for s in p[:-1]}) if origins is None else origins
        for origin in starts:
            frontier={origin};reached=set()
            for _ in range(2):
                bus=set()
                for stops in patterns:
                    boarding=False
                    for stop in stops:
                        if boarding:bus.add(stop)
                        if stop in frontier:boarding=True
                frontier=set(bus)
                for stop in bus:frontier.update(walks.get(stop,()))
                reached.update(frontier)
            for destination in sorted(reached-{origin}):yield origin,destination
