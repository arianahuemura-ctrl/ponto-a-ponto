"""Recorta traçados GTFS pela ordem das paradas da viagem, incluindo trechos curvos."""
import math
from functools import lru_cache
from . import store
from .directions import distance

@lru_cache(maxsize=256)
def trip_geometry(path, modified, size, trip_id):
    with store.connection() as db:
        row=db.execute('SELECT shape_id FROM trips WHERE trip_id=?',(trip_id,)).fetchone()
        shape=[tuple(p) for p in db.execute('SELECT shape_pt_lat,shape_pt_lon FROM shapes WHERE shape_id=? ORDER BY shape_pt_sequence',(row[0],))] if row else []
        stops=list(db.execute('SELECT s.stop_lat,s.stop_lon FROM stop_times st JOIN stops s USING(stop_id) WHERE trip_id=? ORDER BY stop_sequence',(trip_id,)))
    if len(shape)<2:return shape,[]
    positions=[];previous=0
    for point in stops:
        scale=math.cos(math.radians(point[0]));candidates=[]
        for i in range(int(previous),len(shape)-1):
            a,b=shape[i],shape[i+1]
            dx,dy=(b[1]-a[1])*scale,b[0]-a[0]
            norm=dx*dx+dy*dy
            if not norm:continue
            t=max(0,min(1,((point[1]-a[1])*scale*dx+(point[0]-a[0])*dy)/norm))
            if i+t<previous:continue
            projected=(a[0]+t*dy,a[1]+t*(b[1]-a[1]))
            gap=distance(point,projected)
            candidates.append((gap,i+t,projected))
        if not candidates:
            positions.append(None);continue
        minimum=min(c[0] for c in candidates)
        if minimum>150:
            positions.append(None);continue
        # Prefira a primeira passagem por coordenadas repetidas: pequenas diferenças no GPS
        # não devem saltar para o trecho de retorno de um itinerário circular.
        best=min((c for c in candidates if c[0]<=minimum+5),key=lambda c:c[1])
        previous=best[1];positions.append((previous,best[2]))
    return shape,positions

def leg_shape(trip_id,start,end):
    path=store.database_path();stat=path.stat()
    shape,positions=trip_geometry(str(path),stat.st_mtime_ns,stat.st_size,trip_id)
    if not positions or end>=len(positions) or positions[start] is None or positions[end] is None:return []
    a,first=positions[start];b,last=positions[end]
    if b<=a:return []
    return [first]+shape[math.floor(a)+1:math.ceil(b)]+[last]
