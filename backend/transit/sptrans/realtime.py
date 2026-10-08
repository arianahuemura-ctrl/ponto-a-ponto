import math
import re
import unicodedata
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .client import client, APIError


def normalized(value):
    return re.sub(r'[^A-Z0-9]', '', unicodedata.normalize('NFKD',value.upper()).encode('ascii','ignore').decode())


def line_mapping(row):
    lines=client.get('Linha/Buscar',{'termosBusca':row['code']},86400)
    matches=[]
    for line in lines:
        code=f"{line['lt']}-{str(line['tl']).zfill(2)}"
        terminal=line['tp'] if line['sl']==1 else line['ts']
        if code==row['code'] and normalized(terminal)==normalized(row['headsign']):
            matches.append(line)
    # Não deduza o sentido Olho Vivo a partir de direction_id GTFS: as convenções podem diferir.
    return matches[0] if len(matches)==1 else None


def stop_mapping(origin, line):
    stops=client.get('Parada/BuscarParadasPorLinha',{'codigoLinha':line['cl']},86400)
    def distance(s):
        return math.hypot((float(s['py'])-origin['lat'])*111320,(float(s['px'])-origin['lon'])*102000)
    candidates=[s for s in stops if distance(s)<=15]
    exact=[s for s in candidates if str(s['cp'])==origin['id']]
    return exact[0] if len(exact)==1 else candidates[0] if len(candidates)==1 else None


def add_predictions(row, origin, ttl=30):
    line=line_mapping(row)
    if not line:
        row['realtime_status']='Sentido sem correspondência inequívoca na API.'
        return
    row['api_line']=line['cl']
    # O catálogo linha/parada é incompleto: Previsao aceita IDs GTFS de paradas
    # que BuscarParadasPorLinha não enumera. Valide a identidade e as coordenadas
    # da parada retornada antes de aceitar a consulta direta.
    payload=None
    if str(origin['id']).isdigit() and 'lat' in origin and 'lon' in origin:
        direct=client.get('Previsao',{'codigoParada':int(origin['id']),'codigoLinha':line['cl']},ttl)
        point=(direct or {}).get('p') or {}
        try:
            gap=math.hypot((float(point['py'])-origin['lat'])*111320,(float(point['px'])-origin['lon'])*102000)
            if str(point.get('cp'))==str(origin['id']) and gap<=15:
                payload=direct
                row['api_stop']=point['cp']
        except (KeyError,ValueError,TypeError): pass
    if payload is None:
        point=stop_mapping(origin,line)
        if not point:
            row['realtime_status']='Ponto sem correspondência disponível na API; consulte os intervalos GTFS.'
            return
        payload=client.get('Previsao',{'codigoParada':point['cp'],'codigoLinha':line['cl']},ttl)
        row['api_stop']=point['cp']
    row['api_time']=payload.get('hr')
    row['realtime_status']='Sem previsão de chegada retornada pela SPTrans.'
    for actual in (payload.get('p') or {}).get('l',[]):
        if actual['cl']!=line['cl']: continue
        for vehicle in actual.get('vs',[]):
            if not vehicle.get('t'): continue
            captured=parse_datetime(vehicle.get('ta',''))
            if not captured or timezone.is_naive(captured) or not -60<=(timezone.now()-captured).total_seconds()<=300:
                continue
            row['arrivals'].append({'time':vehicle['t'],'vehicle':str(vehicle['p']),'accessible':vehicle.get('a'), 'observed_at':vehicle.get('ta')})
    if row['arrivals']:
        reference=payload.get('hr','00:00')
        def minutes(value):
            h,m=map(int,value.split(':'));return h*60+m
        row['arrivals'].sort(key=lambda v:(minutes(v['time'])-minutes(reference))%1440)
        row['realtime_status']='Previsão SPTrans (sujeita a atualização).'


def positions(row, ttl=30):
    line=line_mapping(row)
    if not line: return [],'Sentido sem correspondência inequívoca na API.'
    payload=client.get('Posicao/Linha',{'codigoLinha':line['cl']},ttl)
    vehicles=[]
    for v in payload.get('vs',[]):
        from django.utils.dateparse import parse_datetime
        captured=parse_datetime(v.get('ta',''))
        if not captured or timezone.is_naive(captured): continue
        age=(timezone.now()-captured).total_seconds()
        if not -60<=age<=180: continue
        if not (-90<=v['py']<=90 and -180<=v['px']<=180): continue
        vehicles.append({'id':str(v['p']),'lat':v['py'],'lon':v['px'],'observed_at':v['ta'],'code':row['code'],'accessible':v.get('a')})
    return vehicles, 'Posições SPTrans atualizadas nos últimos 3 minutos.' if vehicles else 'Nenhuma posição recente disponível para esta linha.'
