"""Conexões de ônibus preparadas com o roteamento pedestre verificado da aplicação.

Todos os artefatos persistentes são somente leitura. A validação pedestre e as consultas
operacionais são locais à consulta; nenhuma conexão de ônibus é composta ou materializada aqui.
"""
from contextlib import closing
import hashlib
import json
import math
import sqlite3
import time

from . import direct, graph, materialized_connections as materialized
from . import connection_planner, store, walking


def prepare(db, origin, destination):
    from .alternatives import access_points
    try:
        with closing(graph.readonly(materialized.database_path())) as prepared:
            meta = materialized._read_meta(prepared)
            materialized._validate(meta)
            starts, _ = access_points(db, origin, True, optimistic=True,endpoint_selection=True)
            ends, _ = access_points(db, destination, False, optimistic=True,endpoint_selection=True)
            # Pequenos conjuntos temporários de consulta; nunca enumere o produto cartesiano municipal.
            prepared.execute('CREATE TEMP TABLE starts(id TEXT PRIMARY KEY)')
            prepared.execute('CREATE TEMP TABLE ends(id TEXT PRIMARY KEY)')
            prepared.executemany('INSERT INTO starts VALUES (?)', [(p['id'],) for p, _ in starts])
            prepared.executemany('INSERT INTO ends VALUES (?)', [(p['id'],) for p, _ in ends])
            rows = prepared.execute('''SELECT c.* FROM starts s CROSS JOIN conexoes c
                JOIN ends e ON e.id=c.destination WHERE c.origin=s.id AND c.boardings IN (1,2) AND
                EXISTS (SELECT 1 FROM materialization_status m WHERE m.origin=c.origin
                 AND m.destination=c.destination AND m.state='ready' AND m.boardings=c.boardings)
                ORDER BY c.distance_meters,c.origin,c.destination,c.boardings,c.rank''').fetchall()
            if not rows:
                return None
            with direct.connection(meta['signature']['source'][0]) as source:
                paths = [materialized._expand(row, source) for row in rows]
            return {'paths': paths, 'city_complete': meta.get('city_complete', False)}
    except (ValueError, sqlite3.Error, OSError):
        return None


class Walks:
    """Mesmo roteador, limite geométrico e velocidade de referência do SPTrans/RAPTOR."""
    def __init__(self, max_distance=None):
        self.max_distance = walking.WALK_LIMIT if max_distance is None else max_distance
        self.paths = {}
        self.checks = 0
        self.deadline = time.monotonic() + 30
        self.limited = False
        self.incomplete = False

    def route(self, origin, destination, kind):
        gap = graph.distance((origin['lat'], origin['lon']), (destination['lat'], destination['lon']))
        if gap < .01:
            return None
        if gap > self.max_distance:
            raise ValueError('Caminhada excede o limite.')
        key = (origin['lat'], origin['lon'], destination['lat'], destination['lon'])
        if key not in self.paths:
            if self.checks >= 64 or time.monotonic() >= self.deadline:
                self.limited = True
                raise ValueError('Limite de verificação de caminhada.')
            self.checks += 1
            a, b = origin, destination
            if a['id'] == b['id']:
                a = {**a, 'id': 'address-access'}
            self.paths[key] = walking.route(a, b, wait_for_slot=True)
        path = self.paths[key]
        if not path.get('available') or not path.get('geometry'):
            self.incomplete = True
            raise ValueError('Caminhada indisponível.')
        distance = path['distance_meters']
        if not math.isfinite(distance) or not 0 <= distance <= self.max_distance:
            raise ValueError('Caminhada excede o limite.')
        return {**path, 'origin': origin, 'destination': destination, 'accessType': kind,
                'seconds': distance / walking.WALK_METERS_PER_SECOND,
                'duration_minutes': distance / walking.WALK_METERS_PER_MINUTE}


class Evaluator(connection_planner.Evaluator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.walks = {}

    def walk(self, previous, edge):
        if previous['destination'] == edge['origin']:
            return {'seconds': 0, 'distance_meters': 0, 'geometry': None}
        return self.walks[(previous['destination'], edge['origin'])]


def progressive(db, origin, destination, max_transfers, now, context):
    from .alternatives import distinct_routes
    from .connection_adapter import journey
    best = []
    walks = Walks()
    base = {'planner': 'connections', 'materialized': True, 'complete': False,
            'optimal_within_limits': False, 'optimal_globally': False,
            'selection_heuristic': 'distance_16_8', 'queried_at': now.isoformat(),
            'materialization_city_complete': context['city_complete']}
    yield {**base, 'journeys': [], 'walking_incomplete': False, 'search_limited': False}
    try:
        with graph.connection() as index:
            # O avaliador pode guardar correspondências do Olho Vivo, mas nunca em um artefato estático.
            index.execute('CREATE TEMP TABLE connection_operational_mappings '
                          '(pattern_id,stop_id,api_line,api_stop,updated_at)')
            engine = Evaluator(index, now)
            api_remaining = max(0, engine.api_deadline - time.monotonic())
            candidates = {}
            for path in context['paths']:
                buses = [leg for leg in path['trechos'] if leg['modo'] == 'onibus']
                if len(buses) > max_transfers + 1:
                    continue
                ids = []
                for leg in buses:
                    row = index.execute('''SELECT id FROM ride_edge WHERE origin=? AND destination=?
                        AND pattern_id=? AND boarding_index=? AND alighting_index=?''',
                        (leg['origem'], leg['destino'], leg['padrao_id'], leg['embarque_indice'],
                         leg['desembarque_indice'])).fetchone()
                    if row is None:
                        raise ValueError('Aresta materializada incompatível com o índice temporal.')
                    ids.append(row[0])
                signature = tuple(ids)
                if signature in candidates:
                    continue
                # A caminhada final armazenada é substituída por desembarque -> destino real,
                # não somada a esse trecho. Assim há uma única caminhada final sujeita ao limite.
                middle = [leg for leg in path['trechos'][:-1] if leg['modo'] == 'caminhada']
                for leg in middle:
                    engine.walks[(leg['origem'], leg['destino'])] = {
                        'seconds': leg['distancia_m'] / walking.WALK_METERS_PER_SECOND,
                        'distance_meters': leg['distancia_m']}
                candidate = {'id': 'connections-' + hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:20],
                             'edge_ids': json.dumps(ids), 'boardings': len(ids),
                             'walk_seconds': sum(w['distancia_m'] for w in middle) / walking.WALK_METERS_PER_SECOND,
                             'walk_meters': sum(w['distancia_m'] for w in middle),
                             'distance_meters': path['distancia_onibus_m'] + sum(w['distancia_m'] for w in middle)}
                start = store.get_stop(db, buses[0]['origem'])
                end = store.get_stop(db, buses[-1]['destino'])
                # Distância em linha reta é apenas um critério preliminar de ordenação, nunca uma caminhada publicada.
                a = graph.distance((origin['lat'], origin['lon']), (start['lat'], start['lon'])) / walking.WALK_METERS_PER_SECOND
                b = graph.distance((end['lat'], end['lon']), (destination['lat'], destination['lon'])) / walking.WALK_METERS_PER_SECOND
                candidates[signature] = (engine.preliminary(candidate, a, b), candidate, start, end, middle)
            ranked = sorted(candidates.values(), key=lambda item: (item[0], item[1]['id']))
            base['candidate_count'] = len(ranked)
            for _, candidate, start, end, middle in ranked:
                if walks.limited:
                    break
                try:
                    access = walks.route(origin, start, 'boarding')
                    egress = walks.route(end, destination, 'destination')
                    transfers = []
                    for leg in middle:
                        foot = walks.route(store.get_stop(db, leg['origem']), store.get_stop(db, leg['destino']), 'transfer')
                        foot = foot or {'seconds': 0, 'distance_meters': 0, 'geometry': []}
                        engine.walks[(leg['origem'], leg['destino'])] = {
                            **foot, 'origin': leg['origem'], 'destination': leg['destino']}
                        transfers.append(foot)
                except ValueError:
                    continue
                candidate['distance_meters'] += sum(w['distance_meters'] for w in transfers) - candidate['walk_meters']
                candidate['walk_meters'] = sum(w['distance_meters'] for w in transfers)
                candidate['walk_seconds'] = sum(w['seconds'] for w in transfers)
                # A consulta de caminhadas não deve consumir o limite de consultas operacionais.
                before = time.monotonic()
                engine.api_deadline = before + api_remaining
                result, _ = engine.evaluate(candidate, access['seconds'] if access else 0,
                                            egress['seconds'] if egress else 0)
                elapsed = time.monotonic() - before
                # Mantenha um limite compartilhado para a API; exclua o tempo de obtenção das geometrias pedestres.
                api_remaining = max(0, api_remaining - elapsed)
                if not result:
                    continue
                item = journey(db, result)
                endpoints = [p for p in (access, egress) if p]
                item['walks'] = ([access] if access else []) + item['walks'] + ([egress] if egress else [])
                item['walking_meters'] = round(result['walk_meters'] + sum(p['distance_meters'] for p in endpoints))
                item['distance_meters'] += sum(p['distance_meters'] for p in endpoints)
                best = distinct_routes([*best, item])
                yield {**base, 'journeys': best[:], 'walking_incomplete': walks.incomplete,
                       'search_limited': walks.limited}
    except (ValueError, sqlite3.Error, OSError):
        base['artifact_unavailable'] = True
    yield {**base, 'journeys': best, 'complete': True, 'walking_incomplete': walks.incomplete,
           'search_limited': walks.limited}
