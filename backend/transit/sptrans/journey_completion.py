"""Alternativa pedestre e revisão do último desembarque, sem alterar artefatos.

Caminhada direta: mode=walk, legs=[], walks=[percurso], sem embarque.
Os demais campos conservam o contrato de alternativas porta a porta.
"""
from datetime import datetime, timedelta
import hashlib
import json
import math
import time

from . import directions, planner, store, walking
from .materialized_adapter import Walks
from mbm import routing_config as config


def direct_walk(origin, destination, now):
    gap = directions.distance((origin['lat'], origin['lon']), (destination['lat'], destination['lon']))
    if gap < .01 or gap > walking.MAX_DISTANCE:
        return None
    path = walking.route({**origin, 'id': 'walking-origin'}, destination, wait_for_slot=True)
    meters = path.get('distance_meters', float('inf'))
    if not path.get('available') or not path.get('geometry') or not math.isfinite(meters) or not 0 <= meters <= walking.MAX_DISTANCE:
        return None
    seconds = meters / walking.WALK_METERS_PER_SECOND
    minutes = round(seconds / 60, 1)
    return {'id': 'walk-' + hashlib.sha256(json.dumps([origin, destination], sort_keys=True).encode()).hexdigest()[:20],
            'mode': 'walk', 'legs': [], 'transfers': 0, 'walks': [{**path, 'origin': origin,
            'destination': destination, 'accessType': 'destination', 'duration_minutes': minutes}],
            'duration_minutes': minutes, 'duration_seconds': seconds, 'walking_minutes': minutes,
            'walking_seconds': seconds, 'walking_meters': round(meters), 'distance_meters': round(meters),
            'arrival': (now + timedelta(seconds=seconds)).isoformat(), 'estimated': True}


class Completion:
    def __init__(self, db, destination, allowed_stops=None):
        self.db, self.destination = db, destination
        self.allowed_stops = allowed_stops
        self.walks = Walks(max_distance=config.FINAL_WALK_LIMIT_METERS)
        self.cache = {}
        self.remaining_seconds = 30

    def improve(self, journey):
        if not journey.get('legs'):
            return journey
        key = json.dumps(journey, sort_keys=True)
        if key not in self.cache:
            started = time.monotonic()
            self.walks.deadline = started + self.remaining_seconds
            self.cache[key] = self._finish_before_transfer(self._improve(journey))
            self.remaining_seconds = max(0, self.remaining_seconds - (time.monotonic() - started))
        return self.cache[key]

    def _finish_before_transfer(self, journey):
        if len(journey['legs'])<2:return journey
        best = journey
        original_arrival = datetime.fromisoformat(journey['arrival'])
        for index, leg in enumerate(journey['legs'][:-1]):
            try:
                foot = self.walks.route(leg['destination'], self.destination, 'destination')
            except ValueError:
                continue
            seconds = foot['seconds'] if foot else 0
            arrival = datetime.fromisoformat(leg['arrival']) + timedelta(seconds=seconds)
            retained = [w for w in journey.get('walks', []) if
                        w.get('accessType') == 'boarding' or
                        (w.get('accessType') == 'transfer' and w.get('before_leg', 999) <= index)]
            walks = retained + ([foot] if foot else [])
            meters = sum(w['distance_meters'] for w in walks)
            # Só elimine a continuação quando o término a pé chegar antes (ou no mesmo instante).
            if arrival > datetime.fromisoformat(best['arrival']):
                continue
            if arrival == datetime.fromisoformat(best['arrival']) and index >= best['transfers']:
                continue
            delta = (arrival - original_arrival).total_seconds()
            legs = journey['legs'][:index+1]
            best = {**journey, 'id': journey['id'] + ':finish-' + str(index),
                    'legs': legs, 'transfers': index, 'walks': walks,
                    'transfer_walks': [w for w in retained if w.get('accessType') == 'transfer'],
                    'arrival': arrival.isoformat(),
                    'duration_minutes': round(journey['duration_minutes'] + delta/60, 1),
                    'walking_meters': round(meters),
                    'walking_minutes': round(meters/walking.WALK_METERS_PER_MINUTE, 1)}
            if 'duration_seconds' in best:best['duration_seconds'] += delta
            if 'walking_seconds' in best:best['walking_seconds'] = meters/walking.WALK_METERS_PER_SECOND
            if 'ride_seconds' in best:best['ride_seconds'] = sum((datetime.fromisoformat(l['arrival'])-datetime.fromisoformat(l['departure'])).total_seconds() for l in legs)
            if 'egress_seconds' in best:best['egress_seconds'] = seconds
            if 'boardings' in best:best['boardings'] = len(legs)
            best.pop('distance_meters', None)
        return best

    def _improve(self, journey):
        last = journey['legs'][-1]
        if 'boarding_index' not in last or 'alighting_index' not in last:
            return journey
        a, b = last['boarding_index'], last['alighting_index']
        rows = self.db.execute('SELECT * FROM stop_times WHERE trip_id=? ORDER BY stop_sequence', (last['trip_id'],)).fetchall()
        if not 0 <= a < b < len(rows):
            return journey
        start = store.seconds(rows[a]['departure_time'])
        end = store.seconds(rows[b]['arrival_time'])
        if end <= start:
            return journey
        arrival = datetime.fromisoformat(last['arrival'])
        departure = datetime.fromisoformat(last['departure'])
        ride = (arrival - departure).total_seconds()
        old_walk = [w for w in journey.get('walks', []) if w.get('accessType') == 'destination']
        old_meters = sum(w['distance_meters'] for w in old_walk)
        old_seconds = old_meters / walking.WALK_METERS_PER_SECOND
        best = (arrival + timedelta(seconds=old_seconds), old_meters, b, None, arrival)
        # Verifique primeiro as paradas mais próximas do destino; o orçamento é compartilhado.
        candidates = []
        for index in range(a + 1, b):
            row = rows[index]
            if self.allowed_stops is not None and row['stop_id'] not in self.allowed_stops:
                continue
            if 'drop_off_type' in row.keys() and str(row['drop_off_type']) == '1':
                continue
            point = store.get_stop(self.db, row['stop_id'])
            gap = directions.distance((point['lat'], point['lon']), (self.destination['lat'], self.destination['lon']))
            if gap <= walking.WALK_LIMIT:
                candidates.append((gap, index, point))
        for _, index, point in sorted(candidates):
            try:
                foot = self.walks.route(point, self.destination, 'destination')
            except ValueError:
                continue
            # Preserve o tempo do trecho calculado; distribua-o pelos offsets GTFS
            # da mesma viagem, inclusive horários superiores a 24 horas.
            fraction = (store.seconds(rows[index]['arrival_time']) - start) / (end - start)
            if not 0 <= fraction <= 1:
                continue
            at = departure + timedelta(seconds=ride * fraction)
            seconds = foot['seconds'] if foot else 0
            meters = foot['distance_meters'] if foot else 0
            option = (at + timedelta(seconds=seconds), meters, index, foot, at)
            if option[:3] < best[:3]:
                best = option
        final, meters, index, foot, at = best
        if index == b:
            return journey
        saved = (arrival - at).total_seconds()
        delta = -saved + meters / walking.WALK_METERS_PER_SECOND - old_seconds
        leg = {**last, 'destination': store.get_stop(self.db, rows[index]['stop_id']),
               'alighting_index': index, 'arrival': at.isoformat(), 'ride_minutes': round((ride-saved)/60, 1),
               'geometry': planner.leg_shape(last['trip_id'], a, index),
               'stops': [store.get_stop(self.db, row['stop_id']) for row in rows[a:index+1]]}
        if 'ride_seconds' in leg:
            leg['ride_seconds'] = ride - saved
        walks = [w for w in journey.get('walks', []) if w.get('accessType') != 'destination'] + ([foot] if foot else [])
        walking_meters = journey['walking_meters'] - old_meters + meters
        result = {**journey, 'id': journey['id'] + ':alight-' + str(index), 'legs': [*journey['legs'][:-1], leg],
                  'walks': walks, 'arrival': final.isoformat(),
                  'duration_minutes': round(journey['duration_minutes'] + delta/60, 1),
                  'walking_meters': round(walking_meters), 'walking_minutes': round(walking_meters/walking.WALK_METERS_PER_MINUTE, 1)}
        for field, change in [('duration_seconds', delta), ('ride_seconds', -saved),
                              ('walking_seconds', meters/walking.WALK_METERS_PER_SECOND-old_seconds),
                              ('egress_seconds', meters/walking.WALK_METERS_PER_SECOND-old_seconds)]:
            if field in result:
                result[field] += change
        # A distância total anterior não corresponde mais ao desembarque revisado.
        result.pop('distance_meters', None)
        return result


def has_short_bus_leg(journey):
    """Meça o percurso de ônibus, nunca apenas a distância entre os extremos."""
    for leg in journey.get('legs', []):
        geometry = leg.get('geometry') or []
        if len(geometry) < 2:
            continue
        meters = sum(directions.distance(a, b) for a, b in zip(geometry, geometry[1:]))
        if meters < config.MIN_BUS_RIDE_METERS:
            return True
    return False


def normalize_walks(journey):
    """Classifique pelo primeiro embarque e pelo último desembarque, não pelo tipo de ponto."""
    legs = journey.get('legs', [])
    paths = []
    for original in journey.get('walks', []):
        path = dict(original)
        before = path.get('before_leg')
        if before is not None:
            path['accessType'] = 'boarding' if before == 0 else 'destination' if before >= len(legs) else 'transfer'
        elif legs and path.get('origin', {}).get('id') != legs[0]['origin']['id'] and path.get('destination', {}).get('id') == legs[0]['origin']['id']:
            path['accessType'] = 'boarding'
        # Distância verificada é a referência; não deixe um tempo ausente virar zero na interface.
        if 'distance_meters' in path:
            path['seconds'] = path['distance_meters'] / walking.WALK_METERS_PER_SECOND
            path['duration_minutes'] = path['seconds'] / 60
        paths.append(path)
    return {**journey, 'walks': paths,
            'transfer_walks': [p for p in paths if p.get('accessType') == 'transfer']}
