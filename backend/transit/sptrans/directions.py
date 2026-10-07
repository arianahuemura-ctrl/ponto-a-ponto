"""Local GTFS tangents with explicit approximate stop-sequence fallback."""
import math


def bearing(a, b):
    lat1, lat2 = map(math.radians, (a[0], b[0]))
    delta = math.radians(b[1] - a[1])
    return (math.degrees(math.atan2(math.sin(delta) * math.cos(lat2),
            math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta))) + 360) % 360


def distance(a, b):
    lat1, lat2 = map(math.radians, (a[0], b[0]))
    x = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(math.radians(b[1]-a[1])/2)**2
    return 12742000 * math.asin(math.sqrt(min(1, x)))


def tangent(shape, point):
    candidates = []
    scale = math.cos(math.radians(point[0]))
    for a, b in zip(shape, shape[1:]):
        dx, dy = (b[1]-a[1])*scale, b[0]-a[0]
        norm = dx*dx + dy*dy
        if norm == 0: continue
        t = max(0, min(1, ((point[1]-a[1])*scale*dx + (point[0]-a[0])*dy)/norm))
        projected = (a[0]+t*dy, a[1]+t*(b[1]-a[1]))
        gap = distance(point, projected)
        if gap <= 35: candidates.append((gap, bearing(a,b)))
    if not candidates: return None
    candidates.sort()
    heading = candidates[0][1]
    # At loops/crossings, do not pick one of two opposite directions arbitrarily.
    if any(abs((angle-heading+180)%360-180)>75 for gap,angle in candidates if gap<=candidates[0][0]+5): return None
    return round(heading)


def enrich(db, stops):
    shapes = {}
    for stop in stops:
        stop['directions'] = []
        rows = db.execute("""SELECT DISTINCT t.shape_id,t.trip_headsign,r.route_short_name,
            (SELECT n.stop_id FROM stop_times n WHERE n.trip_id=st.trip_id
             AND n.stop_sequence>st.stop_sequence ORDER BY n.stop_sequence LIMIT 1) AS next_id,
            (SELECT n.stop_id FROM stop_times n WHERE n.trip_id=st.trip_id
             AND n.stop_sequence<st.stop_sequence ORDER BY n.stop_sequence DESC LIMIT 1) AS previous_id
            FROM stop_times st JOIN trips t USING(trip_id) JOIN routes r USING(route_id)
            WHERE st.stop_id=? AND r.route_type='3'""", (stop['id'],))
        for row in rows:
            shape_id = row['shape_id']
            if shape_id not in shapes:
                shapes[shape_id] = [(float(s[0]),float(s[1])) for s in db.execute(
                    'SELECT shape_pt_lat,shape_pt_lon FROM shapes WHERE shape_id=? ORDER BY shape_pt_sequence',(shape_id,))]
            point = (stop['lat'],stop['lon'])
            heading = tangent(shapes[shape_id], point)
            kind = 'departure' if row['next_id'] else 'arrival'
            source = 'shape'
            if heading is None:
                neighbor_id = row['next_id'] or row['previous_id']
                neighbor = db.execute('SELECT stop_lat,stop_lon FROM stops WHERE stop_id=?',(neighbor_id,)).fetchone()
                if neighbor:
                    other = (float(neighbor[0]),float(neighbor[1]))
                    if distance(point,other)>=3:
                        heading = round(bearing(point,other) if kind=='departure' else bearing(other,point))
                        source = 'stop_sequence'
            if heading is not None:
                item = {'bearing':heading,'code':row['route_short_name'],'headsign':row['trip_headsign'],
                        'source':source,'approximate':source!='shape','kind':kind}
                if item not in stop['directions']: stop['directions'].append(item)
        stop['direction_status'] = 'available' if stop['directions'] else 'unavailable'
    return stops
