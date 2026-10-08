"""Consulta indexada do GTFS original; não transforma frequências em partidas exatas."""
import csv
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.utils import timezone

TABLES = {
    'stops': ['stop_id', 'stop_name', 'stop_desc', 'stop_lat', 'stop_lon'],
    'routes': ['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type', 'route_color'],
    'trips': ['route_id', 'service_id', 'trip_id', 'trip_headsign', 'direction_id', 'shape_id'],
    'stop_times': ['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'],
    'frequencies': ['trip_id', 'start_time', 'end_time', 'headway_secs', 'exact_times'],
    'calendar': ['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_date', 'end_date'],
    'calendar_dates': ['service_id', 'date', 'exception_type'],
    'shapes': ['shape_id', 'shape_pt_lat', 'shape_pt_lon', 'shape_pt_sequence'],
}
NUMERIC = {'stop_lat', 'stop_lon', 'stop_sequence', 'headway_secs', 'shape_pt_lat', 'shape_pt_lon', 'shape_pt_sequence'}

def database_path():
    return Path(settings.SPTRANS_DATABASE)


def import_gtfs(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=destination.parent, suffix='.sqlite3')
    os.close(fd)
    counts = {}
    try:
        with sqlite3.connect(name) as db:
            for table, cols in TABLES.items():
                db.execute(f'CREATE TABLE {table} (' + ','.join(c + (' REAL' if c in NUMERIC else ' TEXT') for c in cols) + ')')
                path = source / (table + '.txt')
                if not path.exists() and table == 'calendar_dates':
                    counts[table] = 0
                    continue
                with path.open(encoding='utf-8-sig', newline='') as stream:
                    rows = csv.DictReader(stream)
                    db.executemany(f'INSERT INTO {table} VALUES (' + ','.join('?' for _ in cols) + ')',
                                   ([row.get(c, '') for c in cols] for row in rows))
                counts[table] = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            for table, columns in [('stops','stop_id'), ('stops','stop_lat,stop_lon'), ('routes','route_id'), ('trips','trip_id'), ('stop_times','stop_id,trip_id,stop_sequence'), ('stop_times','trip_id,stop_sequence'), ('frequencies','trip_id'), ('shapes','shape_id,shape_pt_sequence')]:
                db.execute(f'CREATE INDEX idx_{table}_{columns.replace(",", "_")} ON {table}({columns})')
            db.execute('CREATE TABLE metadata (value TEXT)')
            db.execute('INSERT INTO metadata VALUES (?)', (json.dumps({'imported_at': timezone.now().isoformat(), 'counts': counts}),))
            db.execute('ANALYZE')
        os.replace(name, destination)
    finally:
        if os.path.exists(name): os.unlink(name)
    return counts


@contextmanager
def connection():
    if not database_path().exists():
        raise ValueError('Importe o GTFS com: python backend/manage.py import_sptrans')
    db = sqlite3.connect(database_path().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try: yield db
    finally: db.close()


def stop(row):
    return {'id': row['stop_id'], 'name': row['stop_name'], 'address': row['stop_desc'] or row['stop_name'], 'lat': float(row['stop_lat']), 'lon': float(row['stop_lon']), 'code': row['stop_id']}


def get_stop(db, identifier):
    row = db.execute('SELECT * FROM stops WHERE stop_id=?', (identifier,)).fetchone()
    if row is None: raise ValueError('Ponto não encontrado no GTFS de São Paulo.')
    return stop(row)


def search(db, query='', lat=-23.5505, lon=-46.6333):
    # Somente paradas atendidas por ônibus. A ordenação espacial evita carregar 22 mil marcadores.
    rows = db.execute('''SELECT s.* FROM stops s WHERE (s.stop_name LIKE ? OR s.stop_id=?)
        AND EXISTS (SELECT 1 FROM stop_times st JOIN trips t USING(trip_id) JOIN routes r USING(route_id)
        WHERE st.stop_id=s.stop_id AND r.route_type='3')
        ORDER BY (s.stop_lat-?)*(s.stop_lat-?)+(s.stop_lon-?)*(s.stop_lon-?)*0.84 LIMIT 80''',
        ('%'+query+'%',query,lat,lat,lon,lon)).fetchall()
    return [stop(row) for row in rows]


def seconds(value):
    h,m,s=map(int,value.split(':'))
    return h*3600+m*60+s


def service_active(db, service_id, day):
    date = day.strftime('%Y%m%d')
    exception = db.execute('SELECT exception_type FROM calendar_dates WHERE service_id=? AND date=?', (service_id,date)).fetchone()
    if exception: return exception[0]=='1'
    row = db.execute('SELECT * FROM calendar WHERE service_id=?', (service_id,)).fetchone()
    return bool(row and row['start_date']<=date<=row['end_date'] and row[['monday','tuesday','wednesday','thursday','friday','saturday','sunday'][day.weekday()]]=='1')


def programme(db, trip, now):
    first = db.execute('SELECT departure_time FROM stop_times WHERE trip_id=? ORDER BY stop_sequence LIMIT 1', (trip['trip_id'],)).fetchone()
    offset = seconds(trip['departure_time'])-seconds(first[0])
    frequencies=db.execute('SELECT * FROM frequencies WHERE trip_id=?', (trip['trip_id'],)).fetchall()
    result=[]
    # Inclua o dia anterior para partidas após a meia-noite e o seguinte para a próxima faixa.
    for delta in [-1,0,1]:
        day=now.date()+timedelta(days=delta)
        if not service_active(db,trip['service_id'],day): continue
        midnight=now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=delta)
        for f in frequencies:
            start=midnight+timedelta(seconds=seconds(f['start_time'])+offset)
            end=midnight+timedelta(seconds=seconds(f['end_time'])+offset)
            if end<=now: continue
            result.append({'start':start.isoformat(),'end':end.isoformat(),'interval_minutes':round(float(f['headway_secs'])/60,1),'kind':'frequency'})
        if not frequencies:
            departure=midnight+timedelta(seconds=seconds(trip['departure_time']))
            if departure>=now:
                result.append({'start':departure.isoformat(),'end':departure.isoformat(),'kind':'scheduled'})
    return sorted(result,key=lambda x:x['start'])[:3]


def alternatives(db, origin, destination, now=None):
    now=now or timezone.localtime()
    params=[origin]
    clause=''
    if destination:
        clause='AND EXISTS (SELECT 1 FROM stop_times d WHERE d.trip_id=t.trip_id AND d.stop_id=? AND d.stop_sequence>o.stop_sequence)'
        params.append(destination)
    rows=db.execute('''SELECT t.*,r.route_short_name,r.route_long_name,r.route_color,o.departure_time,o.stop_sequence
        FROM stop_times o JOIN trips t USING(trip_id) JOIN routes r USING(route_id)
        WHERE o.stop_id=? AND r.route_type='3' '''+clause+' ORDER BY r.route_short_name,t.direction_id,o.stop_sequence',params).fetchall()
    result=[]
    seen=set()
    for row in rows:
        # Serviços distintos permanecem representados por suas faixas de horários ativas.
        windows=programme(db,row,now)
        key=(row['route_id'],row['direction_id'],row['trip_headsign'])
        if key in seen: continue
        if not windows: continue
        seen.add(key)
        result.append({'trip_id':row['trip_id'],'route_id':row['route_id'],'code':row['route_short_name'],'name':row['route_long_name'],'headsign':row['trip_headsign'],'direction':row['direction_id'],'color':'#'+(row['route_color'] or '005cec'),'programme':windows,'arrivals':[]})
    return result


def in_bounds(db, south, west, north, east):
    rows=db.execute("""SELECT s.* FROM stops s
        WHERE s.stop_lat BETWEEN ? AND ? AND s.stop_lon BETWEEN ? AND ?
        AND EXISTS (SELECT 1 FROM stop_times st JOIN trips t USING(trip_id) JOIN routes r USING(route_id)
                    WHERE st.stop_id=s.stop_id AND r.route_type='3')
        ORDER BY s.stop_id""",(south,north,west,east))
    return [stop(row) for row in rows]
