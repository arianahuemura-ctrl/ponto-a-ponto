"""Read-only geographic and timetable census. Requires shapely and pyproj."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
import sqlite3

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DATA = ROOT / 'artifacts/transport/artesp-20261102'
db = sqlite3.connect((DATA / 'network.sqlite3').as_uri() + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
db.execute('PRAGMA query_only=ON')
boundary = shape(json.loads((OUT / 'maua-ibge-2024.geojson').read_text())['geometry'])
projection = Transformer.from_crs(4674, 31983, always_xy=True).transform
metric_boundary = transform(projection, boundary).boundary
all_stops = {r['stop_id']: dict(r) for r in db.execute('SELECT * FROM stops')}
inside = {sid: r for sid, r in all_stops.items()
          if boundary.covers(Point(r['stop_lon'], r['stop_lat']))}
local = {sid: r for sid, r in inside.items() if sid.startswith('artesp:')}
marks = ','.join('?' for _ in local)
trips = {r['trip_id']: dict(r) for r in db.execute(
    f'SELECT * FROM trips WHERE trip_id IN (SELECT DISTINCT trip_id FROM stop_times WHERE stop_id IN ({marks}))',
    list(local))}
routes = {r['route_id']: dict(r) for r in db.execute('SELECT * FROM routes')}
calendars = {r['service_id']: dict(r) for r in db.execute('SELECT * FROM calendar')}
exceptions = {(r['service_id'], r['date']): r['exception_type']
              for r in db.execute('SELECT * FROM calendar_dates')}
times = defaultdict(list)
# A join by local route fetches the full stop sequence, including outside Mauá.
route_ids = sorted({t['route_id'] for t in trips.values()})
for r in db.execute('SELECT s.* FROM stop_times s JOIN trips t USING(trip_id) WHERE t.route_id IN (' +
                    ','.join('?' for _ in route_ids) + ') ORDER BY s.trip_id,s.stop_sequence', route_ids):
    if r['trip_id'] in trips:
        times[r['trip_id']].append(dict(r))

def seconds(value):
    h, m, s = map(int, value.split(':'))
    if h < 0 or not 0 <= m < 60 or not 0 <= s < 60:
        raise ValueError(value)
    return h * 3600 + m * 60 + s

def active(trip, day):
    sid = trip['service_id']; stamp = day.strftime('%Y%m%d')
    exception = exceptions.get((sid, stamp))
    if exception is not None:
        return exception == '1'
    c = calendars.get(sid)
    return bool(c and c['start_date'] <= stamp <= c['end_date'] and
                c[('monday','tuesday','wednesday','thursday','friday','saturday','sunday')[day.weekday()]] == '1')

valid = {}; invalid = {}; events = {}; used_stops = set()
for tid, t in trips.items():
    seq = times[tid]
    try:
        if len({x['stop_id'] for x in seq}) < 2:
            raise ValueError('fewer than two distinct stops')
        previous = -1
        for x in seq:
            x['arrival_seconds'] = seconds(x['arrival_time'])
            x['departure_seconds'] = seconds(x['departure_time'])
            if not previous <= x['arrival_seconds'] <= x['departure_seconds']:
                raise ValueError('non-monotonic times')
            previous = x['departure_seconds']
        e = [(x, i < len(seq)-1, i > 0) for i, x in enumerate(seq) if x['stop_id'] in local]
        if not e:
            raise ValueError('no local event')
        valid[tid] = t; events[tid] = e
        used_stops.update(x['stop_id'] for x, board, alight in e if board or alight)
    except (ValueError, TypeError) as error:
        invalid[tid] = str(error)

days = {'weekday': date(2026,11,3), 'saturday': date(2026,11,7), 'sunday': date(2026,11,8)}
daily = {}; per_route = {rid: {'route_id': rid, 'name': routes[rid]['route_long_name']} for rid in route_ids}
for label, day in days.items():
    selected = {tid: t for tid, t in valid.items() if active(t, day)}
    boarding = {x['stop_id'] for tid in selected for x, b, a in events[tid] if b}
    alighting = {x['stop_id'] for tid in selected for x, b, a in events[tid] if a}
    counts = Counter(t['route_id'] for t in selected.values())
    daily[label] = {'date': day.isoformat(), 'trips': len(selected),
                   'routes': len(counts), 'boarding_stops': len(boarding),
                   'alighting_stops': len(alighting), 'served_stops': len(boarding | alighting),
                   'trips_with_boarding': sum(any(b for x,b,a in events[tid]) for tid in selected),
                   'trips_with_alighting': sum(any(a for x,b,a in events[tid]) for tid in selected)}
    for rid in route_ids:
        per_route[rid][label] = counts[rid]
    # Civil-day windows include previous service dates for GTFS times >24:00.
    windows = {}
    for name, start, end in [('madrugada_00_04',0,4), ('pico_07_09',7,9),
                             ('entrepico_12_14',12,14), ('pico_17_19',17,19)]:
        departures = set(); served = set(); lines = set()
        for tid, t in valid.items():
            for delta in (-2,-1,0):
                if not active(t, day + timedelta(days=delta)):
                    continue
                for x, b, a in events[tid]:
                    tm = delta*86400 + x['departure_seconds']
                    if b and start*3600 <= tm < end*3600:
                        departures.add((tid,delta)); served.add(x['stop_id']); lines.add(t['route_id'])
        windows[name] = {'distinct_trip_occurrences': len(departures), 'boarding_stops': len(served), 'routes': len(lines)}
    daily[label]['civil_day_boarding_windows'] = windows

stop_routes = defaultdict(set); stop_trips = defaultdict(set)
for tid,t in valid.items():
    for x,b,a in events[tid]:
        if b or a:
            stop_routes[x['stop_id']].add(t['route_id']);stop_trips[x['stop_id']].add(tid)
stop_rows = []
for sid,s in local.items():
    point = transform(projection, Point(s['stop_lon'],s['stop_lat']))
    stop_rows.append({**s, 'boundary_distance_m': round(point.distance(metric_boundary),2),
                      'routes': '|'.join(sorted(stop_routes[sid])), 'valid_trip_templates': len(stop_trips[sid])})
near_boundary = []
for sid,s in all_stops.items():
    if not sid.startswith('artesp:') or not (-46.51<s['stop_lon']<-46.37 and -23.73<s['stop_lat']<-23.60):
        continue
    distance = transform(projection,Point(s['stop_lon'],s['stop_lat'])).distance(metric_boundary)
    if distance <= 20:
        near_boundary.append({'stop_id':sid,'name':s['stop_name'],'inside':sid in local,'distance_m':round(distance,2)})

with sqlite3.connect((DATA/'network.staged.sqlite3').as_uri()+'?mode=ro',uri=True) as prepared:
    lookup = dict(prepared.execute('SELECT sid,id FROM stops'))
    materialized = []
    for sid in local:
        row = prepared.execute('SELECT pairs,paths FROM progress WHERE stage=1 AND origin=?',(lookup[sid],)).fetchone()
        materialized.append({'stop_id':sid,'destinations':row[0] if row else 0,'transport_alternatives':row[1] if row else 0})

def save_csv(name, rows):
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

save_csv('stops.csv',stop_rows)
save_csv('routes.csv',list(per_route.values()))
save_csv('materialized-origins.csv',materialized)
save_csv('trips.csv',[{'trip_id':tid,'route_id':t['route_id'],'service_id':t['service_id'],
                     'direction_id':t['direction_id'],'first_local_time':min(x['departure_time'] for x,b,a in events[tid]),
                     'local_stop_calls':len(events[tid])} for tid,t in valid.items()])
report = {
    'boundary_source':'https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/UFs/SP/SP_Municipios_2024.zip',
    'boundary_code':'3529401','boundary_crs':'SIRGAS 2000 EPSG:4674',
    'boundary_geojson_sha256':hashlib.sha256((OUT/'maua-ibge-2024.geojson').read_bytes()).hexdigest(),
    'feed_version':'20261007','feed_calendar':'2026-01-01/2026-12-31',
    'artesp_stop_ids_inside':len(local),
    'artesp_distinct_coordinates_inside':len({(s['stop_lat'],s['stop_lon']) for s in local.values()}),
    'served_artesp_stop_ids':len(used_stops),'unused_artesp_stop_ids':sorted(set(local)-used_stops),
    'routes':len(per_route),'trip_templates':len(trips),'valid_trip_templates':len(valid),'invalid_trips':invalid,
    'daily':daily,'by_route':list(per_route.values()),
    'rail_stations_already_present':[s for sid,s in inside.items() if not sid.startswith('artesp:')],
    'stops_with_materialized_origin':sum(r['destinations']>0 for r in materialized),
    'near_boundary_20m':near_boundary,
    'definition':'Distinct GTFS trips with a valid full stop sequence and at least one boarding/alighting event inside the IBGE polygon. Each trip is counted once per service date, irrespective of local stop calls.',
    'limitations':['Scheduled availability, not observed operations or realtime predictions.',
                   'No ARTESP holiday exceptions; ordinary weekday, Saturday and Sunday samples only.',
                   'Stop IDs are directional catalog records, not deduplicated physical boarding locations.',
                   'Boundary and stop coordinate uncertainty affects points very near municipal borders.',
                   'Does not include complete municipal Suzantur services.',
                   'Public activation is tracked separately in artesp-activation-20261102.json; this census alone does not establish deployment.',
                   'Rail uses frequency templates and is listed separately, not added to bus trip counts.']
}
(OUT/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
