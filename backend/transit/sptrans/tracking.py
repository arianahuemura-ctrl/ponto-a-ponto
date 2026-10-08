"""Seleciona um veículo antes do embarque sem confundir o trecho de retorno da rota."""
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
        # Uma única amostra GPS não distingue uma passagem repetida após o embarque.
        if any(g<=gap+10 and p>end+0.01 for g,p,_ in projections): continue
        geometry=[projected]+shape[math.floor(pos)+1:math.ceil(end)]+[endpoint]
        meters=sum(distance(a,b) for a,b in zip(geometry,geometry[1:]))
        candidates.append((meters,vehicle,geometry))
    if not candidates: return None
    predicted={str(a['vehicle']):i for i,a in enumerate(arrivals)}
    # Prefira a próxima chegada confirmada para a parada; caso contrário, identifique a estimativa.
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
    """Compara horários exatos de chegada com o tempo de acesso antes de arredondar para exibição."""
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
            # Sem caminhada de acesso, mantenha o minuto atual como "0 min".
            if wait_seconds==0 and expected<=now<expected+timedelta(minutes=1): pass
            elif expected<ready: continue
            if expected>now+timedelta(hours=6): continue
            results.append({**arrival,'arrival_at':expected.isoformat()})
        except (ValueError,TypeError,KeyError): continue
    return sorted(results,key=lambda a:a['arrival_at'])


def select_passed(shape, boarding, vehicles, limit_meters=500):
    """Veículos até 500 m após o embarque, medidos sobre a geometria dirigida.

    A projeção reversa reutiliza a proteção contra trajetos sobrepostos. Esses
    marcadores não representam oportunidades de embarque nem desenham rastro.
    """
    if len(shape)<2 or boarding is None:return []
    end,endpoint=boarding
    reverse=list(reversed(shape));anchor=(len(shape)-1-end,endpoint)
    found={}
    for vehicle in vehicles:
        if not all(isinstance(vehicle.get(k),(int,float)) and math.isfinite(vehicle[k]) for k in ('lat','lon')):continue
        candidate=select_approach(reverse,anchor,[vehicle])
        if candidate is None:continue
        # Compare a distância sem arredondar para não aceitar veículos além do limite.
        meters=sum(distance(a,b) for a,b in zip(candidate['geometry'],candidate['geometry'][1:]))
        if not 0<meters<=limit_meters:continue
        found[str(vehicle['id'])]={'vehicle':vehicle,'geometry':[],
            'distance_meters':round(meters),'selection':'passed',
            'label':f'Já passou do embarque · {round(meters)} m após o ponto'}
    return sorted(found.values(),key=lambda v:(v['distance_meters'],str(v['vehicle']['id'])))


def passed(trip_id,boarding_index,vehicles):
    path=store.database_path();stat=path.stat()
    shape,positions=trip_geometry(str(path),stat.st_mtime_ns,stat.st_size,trip_id)
    if not 0<=boarding_index<len(positions):return []
    return select_passed(shape,positions[boarding_index],vehicles)
