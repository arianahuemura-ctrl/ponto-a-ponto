"""Select an upstream vehicle without confusing the return side of a route."""
import math
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from . import store
from .geometry import trip_geometry
from .directions import distance


def select_approach(shape, boarding, vehicles, arrivals=(), require_prediction=False):
    if len(shape)<2 or boarding is None:
        return None
    end, endpoint=boarding
    candidates=[]
    for vehicle in vehicles:
        if require_prediction and str(vehicle['id']) not in {str(a['vehicle']) for a in arrivals}: continue
        point=(vehicle['lat'],vehicle['lon'])
        scale=math.cos(math.radians(point[0]))
        projections=[]
        for i,(a,b) in enumerate(zip(shape,shape[1:])):
            dx,dy=(b[1]-a[1])*scale,b[0]-a[0]
            norm=dx*dx+dy*dy
            if not norm: continue
            t=max(0,min(1,((point[1]-a[1])*scale*dx+(point[0]-a[0])*dy)/norm))
            projected=(a[0]+t*dy,a[1]+t*(b[1]-a[1]))
            projections.append((distance(point,projected),i+t,projected))
        if not projections: continue
        gap,pos,projected=min(projections)
        if gap>100 or pos>end: continue
        # A single GPS sample cannot disambiguate a repeated passage after boarding.
        if any(g<=gap+10 and p>end+0.01 for g,p,_ in projections): continue
        geometry=[projected]+shape[math.floor(pos)+1:math.ceil(end)]+[endpoint]
        meters=sum(distance(a,b) for a,b in zip(geometry,geometry[1:]))
        candidates.append((meters,vehicle,geometry))
    if not candidates: return None
    predicted={str(a['vehicle']):i for i,a in enumerate(arrivals)}
    # Prefer the next arrival confirmed for this stop; otherwise label an estimate.
    candidates.sort(key=lambda c:(0,predicted[str(c[1]['id'])]) if str(c[1]['id']) in predicted else (1,c[0]))
    meters,vehicle,geometry=candidates[0]
    confirmed=str(vehicle['id']) in predicted
    return {'vehicle':vehicle,'geometry':geometry,'distance_meters':round(meters),
            'selection':'prediction' if confirmed else 'upstream',
            'label':'Próximo ônibus previsto no embarque' if confirmed else 'Ônibus se aproximando · identificação estimada pelo trajeto'}


def approaching(trip_id,boarding_index,vehicles,arrivals=(),require_prediction=False):
    path=store.database_path(); stat=path.stat()
    shape,positions=trip_geometry(str(path),stat.st_mtime_ns,stat.st_size,trip_id)
    if boarding_index>=len(positions): return None
    return select_approach(shape,positions[boarding_index],vehicles,arrivals,require_prediction)


def reachable_arrivals(arrivals, now, wait_seconds=0):
    """Compare exact arrival times with access time, before rounding for display."""
    ready=now+timedelta(seconds=wait_seconds)
    results=[]
    for arrival in arrivals:
        try:
            observed=parse_datetime(arrival.get('observed_at',''))
            if not observed or timezone.is_naive(observed) or not -60<=(now-observed).total_seconds()<=300: continue
            h,m=map(int,arrival['time'].split(':'))
            base=timezone.localtime(observed)
            expected=base.replace(hour=h,minute=m,second=0,microsecond=0)
            if (expected-base).total_seconds() < -43200: expected+=timedelta(days=1)
            if (expected-base).total_seconds() > 43200: expected-=timedelta(days=1)
            # With no access walk, retain the current minute as "0 min".
            if wait_seconds==0 and expected<=now<expected+timedelta(minutes=1): pass
            elif expected<ready: continue
            if expected>now+timedelta(hours=6): continue
            results.append({**arrival,'arrival_at':expected.isoformat()})
        except (ValueError,TypeError,KeyError): continue
    return sorted(results,key=lambda a:a['arrival_at'])
