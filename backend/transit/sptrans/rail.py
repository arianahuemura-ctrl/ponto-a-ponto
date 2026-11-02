"""Rail timing and explicit station interchanges; see docs/rail-routing.md.

Engineering hypotheses are exposed as estimates. No real-time train claims.
"""
import math
from datetime import datetime, timedelta
from itertools import permutations
from .directions import distance

VERSION = 'rail-1'
RAIL_TYPES = ('1', '2')
# Explicit interchanges from the metropolitan network; similarly named stations
# elsewhere are never connected automatically. Lapa 7/8 is intentionally absent.
COMPLEXES = (
    ('18850','2600672'), ('18984','18860'), ('18989','18861'), ('19000','18869'),
    ('18872','18940','8010123'), ('6714561','18866'), ('6311287','18966'),
    ('614606','18985','18920','18986'), ('1010053','18987','1010054'),
    ('8210164','8210163','18944'), ('3608883','18890'), ('18927','3305856'),
    ('18856','9206549'), ('9206550','9206443'), ('18906','19041'),
    ('9505541','9505577'), ('4011343','18961'), ('18901','3515266'),
    ('18889','1814711'), ('18910','3407222'), ('3407190','3407226'),
    ('1506224','1506221'), ('18919','4814665'),
)


def mode(route_type):
    return {'1':'metro', '2':'rail'}.get(str(route_type), 'bus')


def motion(meters, acceleration, braking, speed_kmh):
    if not all(math.isfinite(v) and v > 0 for v in (meters, acceleration, braking, speed_kmh)):
        raise ValueError('Invalid rail motion parameters')
    peak = min(speed_kmh / 3.6, math.sqrt(2 * meters / (1 / acceleration + 1 / braking)))
    cruise_meters = max(0, meters - peak**2 / (2 * acceleration) - peak**2 / (2 * braking))
    return {'acceleration_seconds': peak / acceleration, 'cruise_seconds': cruise_meters / peak,
            'braking_seconds': peak / braking, 'peak_speed_kmh': peak * 3.6}


def prepare_timing(trip):
    """Separate implicit dwell inside GTFS totals; only raise physically short times."""
    from .geometry import leg_shape
    if trip['route_id'].startswith('METRÔ17'):
        trip['frequencies']=[(6*3600,22*3600,540,False)]
    tt = trip['times']
    if len(tt) < 2:
        return
    acceleration, braking, speed = (1.0, 1.2, 80) if str(trip['route_type']) == '1' else (.9, 1.1, 90)
    rebuilt = [tt[0]]
    segments = []
    for i in range(len(tt)-1):
        programmed = tt[i+1][1] - tt[i][2]
        explicit_dwell = tt[i+1][2] - tt[i+1][1]
        implicit = explicit_dwell == 0 and i+1 < len(tt)-1
        dwell = min(30, max(0, programmed / 3)) if implicit else max(0, explicit_dwell)
        shape = leg_shape(trip['trip_id'], i, i+1)
        meters = sum(distance(a, b) for a, b in zip(shape, shape[1:]))
        parts = motion(meters, acceleration, braking, speed) if meters > 0 else None
        minimum = sum(parts[k] for k in ('acceleration_seconds','cruise_seconds','braking_seconds')) if parts else 0
        running = max(programmed - (dwell if implicit else 0), minimum)
        arrived = rebuilt[-1][2] + running
        rebuilt.append((tt[i+1][0], arrived, arrived + dwell))
        segments.append({'running_seconds': running, 'dwell_seconds': dwell,
                         'motion': parts, 'operating_margin_seconds': max(0, running-minimum) if parts else None})
    trip['times'] = rebuilt
    trip['rail_segments'] = segments
    trip['rail_parameters'] = {'acceleration_m_s2':acceleration, 'service_braking_m_s2':braking,
                              'speed_ceiling_kmh':speed, 'assumed_implicit_dwell_seconds':30}


def timing_detail(trip, start, end):
    segments = trip.get('rail_segments', [])[start:end]
    if not segments:
        return {}
    totals = {key:sum(s['motion'][key] for s in segments if s['motion'])
              for key in ('acceleration_seconds','cruise_seconds','braking_seconds')}
    return {'method':'gtfs_with_kinematic_floor', 'estimated':True,
            'source':'GTFS SPTrans + hipóteses de engenharia; docs/rail-routing.md',
            'parameters':trip['rail_parameters'], 'motion_available':all(s['motion'] for s in segments),
            **totals, 'station_dwell_seconds':sum(s['dwell_seconds'] for s in segments[:-1]),
            'operating_margin_seconds':sum(s['operating_margin_seconds'] or 0 for s in segments),
            'running_seconds':sum(s['running_seconds'] for s in segments),
            'intermediate_stations':max(0,end-start-1)}


def internal_transfers(stops):
    paths = {}
    for group in COMPLEXES:
        for a,b in permutations(group,2):
            if a not in stops or b not in stops:
                continue
            paths[a,b] = {'available':True, 'internal_transfer':True, 'estimated':True,
                'origin':stops[a], 'destination':stops[b], 'distance_meters':0,
                'seconds':120, 'duration_minutes':2, 'geometry':[],
                'source':'Integração entre estações · tempo interno estimado'}
    return paths


def departure_allowed(trip, departure, tz, transferring=False):
    if str(trip.get('route_type','3')) not in RAIL_TYPES:
        return True
    if not math.isfinite(departure):return False
    at = datetime.fromtimestamp(departure, tz)
    seconds = at.hour*3600 + at.minute*60 + at.second
    code = trip['route_id']
    if code.startswith('METRÔ17'):
        return at.weekday()<6 and 6*3600 <= seconds < 22*3600
    # Conservative end-of-service boundary: no invented post-midnight connection.
    opening = (4*3600+40*60) if str(trip['route_type'])=='1' and code!='METRÔ L6' else 4*3600
    return opening <= seconds < 24*3600


def boarding_windows(trip, position, windows, tz):
    if str(trip.get('route_type','3')) not in RAIL_TYPES:return windows
    offset=trip['times'][position][2]-trip['times'][0][2]
    adjusted=[]
    for start,end,headway,exact in windows:
        first=datetime.fromtimestamp(start+offset,tz).replace(hour=0,minute=0,second=0,microsecond=0)
        last=datetime.fromtimestamp(end+offset,tz)
        while first<=last:
            is17=trip['route_id'].startswith('METRÔ17')
            opening=6*3600 if is17 else (4*3600+40*60 if trip['route_type']=='1' and trip['route_id']!='METRÔ L6' else 4*3600)
            closing=22*3600 if is17 else 24*3600
            low=max(start,first.timestamp()+opening-offset)
            high=min(end,first.timestamp()+closing-offset)
            if headway and exact:
                low=start+max(0,math.ceil((low-start)/headway))*headway
            if low<=high and low+offset<first.timestamp()+closing and (not is17 or first.weekday()<6):adjusted.append((low,high,headway,exact))
            first+=timedelta(days=1)
    return adjusted
