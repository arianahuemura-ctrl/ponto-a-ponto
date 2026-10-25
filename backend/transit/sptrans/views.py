import json
import math
import time
from io import BytesIO
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from . import store, realtime, planner, directions, walking, viewport, alternatives, tracking
from .client import APIError


def endpoint(fn):
    @require_GET
    def wrapped(request, *args, **kwargs):
        try:
            with store.connection() as db:
                result=fn(request,db,*args,**kwargs)
                return result if isinstance(result,StreamingHttpResponse) else JsonResponse(result)
        except (ValueError, KeyError, TypeError):
            return JsonResponse({'error':'Consulta inválida ou GTFS ainda não importado. Execute import_sptrans no servidor.'},status=400)
    return wrapped

@endpoint
def stops(request,db):
    query=request.GET.get('q','').strip()[:150]
    lat=float(request.GET.get('lat',-23.5505));lon=float(request.GET.get('lon',-46.6333))
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180: raise ValueError()
    bounds_keys=('south','west','north','east')
    bounded=any(key in request.GET for key in bounds_keys)
    if request.GET.get('id'):
        rows=[store.get_stop(db,request.GET['id'])]
    elif bounded:
        south,west,north,east=(float(request.GET[key]) for key in bounds_keys)
        if not all(math.isfinite(v) for v in (south,west,north,east)) or not (-90<=south<=north<=90 and -180<=west<=east<=180): raise ValueError()
        offset=int(request.GET.get('offset',0))
        batch=int(request.GET['batch_size']) if 'batch_size' in request.GET else None
        if offset<0 or batch is not None and not 1<=batch<=200: raise ValueError()
        lat=float(request.GET.get('lat',(south+north)/2));lon=float(request.GET.get('lon',(west+east)/2))
        return viewport.page(db,south,west,north,east,lat,lon,offset,batch)
    else:
        rows=store.search(db,query,lat,lon)
    directions.enrich(db, rows)
    return {'stops':rows,'limit':None if bounded else 80,'metadata':json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])}

@endpoint
def board(request,db):
    if request.GET.get('stream')=='1' and request.GET.get('destination'):
        return stream_board(request)
    origin=store.get_stop(db,request.GET['origin'])
    destination=store.get_stop(db,request.GET['destination']) if request.GET.get('destination') else None
    rows=[] if destination and destination['id']==origin['id'] else store.alternatives(db,origin['id'],destination['id'] if destination else None)
    max_transfers=int(request.GET.get('max_transfers','2'))
    if not 0<=max_transfers<=3: raise ValueError()
    connections=planner.journeys(db,origin['id'],destination['id'],max_transfers) if destination else []
    walking_incomplete=False
    if destination and request.GET.get('nearby')=='1':
        anchors=[]
        for prefix,point in (('from',origin),('to',destination)):
            anchor=dict(point)
            if prefix+'_lat' in request.GET:
                lat,lon=float(request.GET[prefix+'_lat']),float(request.GET[prefix+'_lon'])
                if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError()
                anchor.update(id='address-'+prefix,lat=lat,lon=lon,catalog_stop_id=point['id'])
            anchors.append(anchor)
        planned=alternatives.alternatives(db,*anchors,max_transfers=max_transfers)
        connections=planned['journeys'];walking_incomplete=planned['walking_incomplete']
    selected=next((j for j in connections if j.get('id')==request.GET.get('journey')),connections[0] if connections else None)

    points = {s['id']:s for journey in connections for leg in journey['legs'] for s in [leg['origin'],leg['destination']]}
    directions.enrich(db, list(points.values()))
    for journey in connections:
        for leg in journey['legs']:
            for key in ('origin','destination'): leg[key]=points[leg[key]['id']]
    route_only=request.GET.get('route_only')=='1' and destination is not None
    if route_only:
        rows=[{'trip_id':leg['trip_id'],'code':leg['code'],'headsign':leg['headsign'],
               'origin':leg['origin'],'destination':leg['destination'],'transfer':index,
               'arrivals':[],'programme':[],'planned_departure':leg['departure'],
               'wait_minutes':leg['wait_minutes']} for index,leg in enumerate(selected['legs'])] if selected else []
    warning=''
    started=time.monotonic()
    # Limite consultas externas em terminais grandes.
    for index,row in enumerate(rows):
        if warning or index>=12 or time.monotonic()-started>8:
            row['realtime_status']=warning or 'Previsão não consultada nesta atualização.'
            continue
        try: realtime.add_predictions(row,row.get('origin',origin))
        except APIError as error:
            warning=str(error);row['realtime_status']=warning
        except (ValueError, KeyError, TypeError):
            row['realtime_status']='Resposta inesperada da SPTrans; previsões indisponíveis.'
    def next_arrival(row):
        if not row['arrivals']: return 10000
        def minute(value):
            h,m=map(int,value.split(':'));return h*60+m
        return (minute(row['arrivals'][0]['time'])-minute(row.get('api_time') or '00:00'))%1440
    if not route_only: rows.sort(key=next_arrival)
    return {'origin':origin,'destination':destination,'lines':rows,'queried_at':timezone.now().isoformat(),'warning':warning,'source':'SPTrans GTFS / Olho Vivo','direct_only':max_transfers==0,'journeys':connections,'selected_journey':selected.get('id') if selected else None,'walking_incomplete':walking_incomplete,'max_transfers':max_transfers,
            'planning':{'horizon_hours':6,'transfer_minutes':2,'waiting':'half_headway','same_stop_only':True}}

@endpoint
def trip(request,db,trip_id):
    wait_seconds=float(request.GET.get('min_wait_seconds','0'))
    if not math.isfinite(wait_seconds) or not 0<=wait_seconds<=21600: raise ValueError()
    row=db.execute('''SELECT t.*,r.route_short_name,r.route_long_name,r.route_color FROM trips t JOIN routes r USING(route_id) WHERE trip_id=? AND r.route_type='3' ''',(trip_id,)).fetchone()
    if not row: raise ValueError()
    line={'trip_id':trip_id,'code':row['route_short_name'],'name':row['route_long_name'],'headsign':row['trip_headsign'],'arrivals':[]}
    stops=[store.stop(s) for s in db.execute('SELECT s.* FROM stop_times st JOIN stops s USING(stop_id) WHERE trip_id=? ORDER BY stop_sequence',(trip_id,))]
    shape=[[s[0],s[1]] for s in db.execute('SELECT shape_pt_lat,shape_pt_lon FROM shapes WHERE shape_id=? ORDER BY shape_pt_sequence',(row['shape_id'],))]
    vehicles=[];status='';warning=''
    try:
        if request.GET.get('origin'): realtime.add_predictions(line,store.get_stop(db,request.GET['origin']),ttl=5 if request.GET.get('boarding_index') is not None or request.GET.get('vehicle') or request.GET.get('next')=='1' else 30)
        vehicles,status=realtime.positions(line,ttl=5 if request.GET.get('boarding_index') is not None or request.GET.get('vehicle') or request.GET.get('next')=='1' else 30)
    except APIError as error: warning=str(error)
    except (ValueError,KeyError,TypeError): warning='Resposta inesperada da SPTrans; posições indisponíveis.'
    approach=None;passed_approaches=[];approaches=[]
    vehicle_id=request.GET.get('vehicle')
    if vehicle_id or request.GET.get('next')=='1':
        if not request.GET.get('origin'):raise ValueError()
        indices=[i for i,s in enumerate(stops) if s['id']==request.GET['origin']]
        if len(indices)==1:
            matching=[v for v in vehicles if str(v['id'])==vehicle_id] if vehicle_id else vehicles
            arrivals=tracking.reachable_arrivals(line['arrivals'],timezone.now())
            approach=tracking.approaching(trip_id,indices[0],matching,arrivals,require_prediction=not bool(vehicle_id))
            if request.GET.get('all')=='1' and not vehicle_id:
                for vehicle in {str(v['id']):v for v in vehicles}.values():
                    candidate=tracking.approaching(trip_id,indices[0],[vehicle],arrivals,require_prediction=True)
                    if candidate:approaches.append(candidate)
            passed_approaches=tracking.passed(trip_id,indices[0],vehicles)
            if approach is None and vehicle_id and any(str(a['vehicle']['id'])==vehicle_id for a in passed_approaches):
                approach=tracking.approaching(trip_id,indices[0],vehicles,arrivals,require_prediction=True)
        # A troca pelo próximo só ocorre quando o selecionado foi identificado após o ponto.
    elif request.GET.get('boarding_index') is not None:
        index=int(request.GET['boarding_index'])
        if not 0<=index<len(stops) or stops[index]['id']!=request.GET.get('origin'): raise ValueError()
        supplied=bool(line['arrivals'])
        line['arrivals']=tracking.reachable_arrivals(line['arrivals'],timezone.now(),wait_seconds)
        line['no_reachable_arrival']=supplied and not line['arrivals']
        approach=tracking.approaching(trip_id,index,vehicles,line['arrivals'],require_prediction=wait_seconds>0 or supplied)
        passed_approaches=tracking.passed(trip_id,index,vehicles)
    itinerary=tracking.itinerary(trip_id,stops,request.GET['origin'],int(request.GET['boarding_index']) if request.GET.get('boarding_index') is not None else None) if request.GET.get('origin') else None
    return {'itinerary':itinerary,'line':line,'stops':stops,'shape':shape,'vehicles':vehicles,'vehicle_status':status,'warning':warning,'approach':approach,'passed_approaches':passed_approaches,'approaches':approaches}

@require_GET
def qr(request,stop_id):
    import qrcode
    import qrcode.image.svg
    from django.conf import settings
    from urllib.parse import urlencode
    with store.connection() as db:
        try: store.get_stop(db,stop_id)
        except ValueError: return HttpResponse(status=404)
    base=(settings.PUBLIC_BASE_URL or request.build_absolute_uri('/')).rstrip('/')
    url=base+'/?'+urlencode({'stop':stop_id})
    if request.GET.get('format')=='json':return JsonResponse({'url':url})
    output=BytesIO()
    qrcode.make(url,image_factory=qrcode.image.svg.SvgPathImage).save(output)
    return HttpResponse(output.getvalue(),content_type='image/svg+xml')

@endpoint
def walk(request, db):
    origin=store.get_stop(db,request.GET['origin'])
    destination=store.get_stop(db,request.GET['destination'])
    for prefix,point in (('from',origin),('to',destination)):
        if prefix+'_lat' in request.GET:
            lat,lon=float(request.GET[prefix+'_lat']),float(request.GET[prefix+'_lon'])
            if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError()
            point.update(id='address-'+prefix,lat=lat,lon=lon)
    return walking.route(origin,destination)

@endpoint
def destination(request, db):
    from .addresses import street_key
    lat,lon=float(request.GET['lat']),float(request.GET['lon'])
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180: raise ValueError()
    rows=db.execute("""SELECT s.* FROM stops s WHERE EXISTS
        (SELECT 1 FROM stop_times st JOIN trips t USING(trip_id) JOIN routes r USING(route_id)
         WHERE st.stop_id=s.stop_id AND r.route_type='3')""")
    candidates=[]
    for row in rows:
        point=store.stop(row)
        gap=directions.distance((lat,lon),(point['lat'],point['lon']))
        candidates.append((gap,point))
    candidates.sort(key=lambda entry:entry[0])
    if request.GET.get('street'):
        key=street_key(request.GET['street'])
        matching=[point for _,point in candidates if street_key(point['name'])==key]
        # Separe locais homônimos geograficamente desconectados usando a sugestão selecionada.
        selected=[]
        if matching and directions.distance((lat,lon),(matching[0]['lat'],matching[0]['lon']))<=2000:
            selected=[matching.pop(0)]
            changed=True
            while changed:
                changed=False
                for point in matching[:]:
                    if any(directions.distance((point['lat'],point['lon']),(s['lat'],s['lon']))<=800 for s in selected):
                        selected.append(point);matching.remove(point);changed=True
        method='street_name'
        if not selected:
            # Reutilize as paradas reais já cadastradas na aplicação, nunca paradas inventadas.
            selected=[point for gap,point in candidates if gap<=400]
            method='nearby'
        directions.enrich(db,selected)
        return {'stops':selected,'match_method':method,'radius_meters':400 if method=='nearby' else None,
                'message':('Nome da rua não encontrado no cadastro; mostrando paradas a até 400 m do local selecionado.' if selected and method=='nearby' else '' if selected else 'Nenhuma parada encontrada pelo nome ou a até 400 m deste local. Explore o mapa ou escolha outro trecho da rua.')}
    if not candidates or candidates[0][0]>2000:
        return {'stop':None,'message':'Nenhuma parada SPTrans encontrada a até 2 km deste endereço.'}
    meters,closest=candidates[0]
    origin=request.GET.get('origin')
    target=request.GET.get('target')
    checked=False
    transfer_limit=2
    if origin or target:
        store.get_stop(db,origin or target)
        # Alternativas próximas cobrem calçadas opostas sem escolher terminais distantes.
        nearby=[entry for entry in candidates if entry[0]<=min(500,meters+250)][:12]
        viable=[]
        now=timezone.localtime()
        if target:
            # Compare as duas calçadas juntas: fixar uma extremidade pode ocultar um ônibus direto.
            target_stop=store.get_stop(db,target)
            boarding_candidates=[entry for entry in candidates if entry[0]<=500][:24]
            alighting_candidates=sorted(
                [(directions.distance((target_stop['lat'],target_stop['lon']),(point['lat'],point['lon'])),point)
                 for _,point in candidates],key=lambda entry:entry[0]
            )
            alighting_candidates=[entry for entry in alighting_candidates if entry[0]<=250][:12]
            starts={point['id']:(gap,point) for gap,point in boarding_candidates}
            ends={point['id']:(gap,point) for gap,point in alighting_candidates}
            direct=[]
            if starts and ends:
                pairs=db.execute(f"""SELECT DISTINCT a.stop_id,b.stop_id FROM stop_times a
                    JOIN stop_times b ON a.trip_id=b.trip_id AND a.stop_sequence<b.stop_sequence
                    JOIN trips t ON t.trip_id=a.trip_id JOIN routes r USING(route_id)
                    WHERE r.route_type='3' AND a.stop_id IN ({','.join('?' for _ in starts)})
                    AND b.stop_id IN ({','.join('?' for _ in ends)})""",[*starts,*ends])
                for start_id,end_id in pairs:
                    routes=planner.journeys(db,start_id,end_id,0,now=now)
                    if routes:
                        gap,point=starts[start_id];end_gap,end_point=ends[end_id]
                        direct.append((routes[0]['duration_minutes']+(gap+end_gap)/walking.WALK_METERS_PER_MINUTE,gap+end_gap,point,end_point))
            if direct:
                _,_,point,end_point=min(direct,key=lambda item:item[:2])
                directions.enrich(db,[point,end_point])
                return {'stop':point,'destination':end_point,'direction_checked':True,'max_transfers':0}
        for distance,point in nearby:
            routes=planner.journeys(db,point['id'] if target else origin,target or point['id'],2,now=now)
            if routes:
                route=min(routes,key=lambda r:(r['transfers'],r['duration_minutes']))
                viable.append((route['transfers'],distance,route['duration_minutes'],point))
        if viable:
            transfer_limit,meters,_,closest=min(viable,key=lambda item:(item[0],item[2]+item[1]/walking.WALK_METERS_PER_MINUTE,item[1]));checked=True
        else:
            return {'stop':None,'message':'Nenhuma rota encontrada para as paradas próximas deste endereço. Escolha outra parada no mapa.'}
    directions.enrich(db,[closest])
    return {'stop':closest,'distance_meters':round(meters),'distance_type':'straight_line','direction_checked':checked,'max_transfers':transfer_limit}


def stream_board(request):
    # Abra a conexão dentro do iterador: o decorador da requisição fecha a própria conexão.
    def chunks():
        try:
            with store.connection() as db:
                if request.GET['origin']=='passenger-location':
                    lat,lon=float(request.GET['from_lat']),float(request.GET['from_lon'])
                    if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError()
                    origin={'id':'passenger-location','name':'Minha localização','lat':lat,'lon':lon}
                else:
                    origin=store.get_stop(db,request.GET['origin'])
                destination=store.get_stop(db,request.GET['destination'])
                limit=int(request.GET.get('max_transfers','2'))
                if not 0<=limit<=3:raise ValueError()
                anchors=[]
                for prefix,point in (('from',origin),('to',destination)):
                    anchor=dict(point)
                    if prefix+'_lat' in request.GET:
                        lat,lon=float(request.GET[prefix+'_lat']),float(request.GET[prefix+'_lon'])
                        if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError()
                        anchor.update(id='address-'+prefix,lat=lat,lon=lon,catalog_stop_id=point['id'])
                    anchors.append(anchor)
                for result in alternatives.progressive(db,*anchors,max_transfers=limit,refresh=request.GET.get('refresh')=='1'):
                    journeys=result['journeys']
                    selected=next((j for j in journeys if j['id']==request.GET.get('journey')),journeys[0] if journeys else None)
                    rows=[{'trip_id':leg['trip_id'],'code':leg['code'],'headsign':leg['headsign'],'origin':leg['origin'],'destination':leg['destination'],
                           'arrivals':[],'programme':[],'planned_departure':leg['departure']} for leg in selected['legs']] if selected else []
                    payload={**result,'origin':origin,'destination':destination,'lines':rows,'queried_at':timezone.now().isoformat(),'selected_journey':selected['id'] if selected else None}
                    yield json.dumps(payload)+'\n'
                    if result['complete'] and rows and result.get('planner')!='connections':
                        started=time.monotonic();warning=''
                        for row in rows[:12]:
                            if time.monotonic()-started>8:break
                            try:realtime.add_predictions(row,row['origin'])
                            except APIError as error:
                                warning=str(error);break
                            except (ValueError,KeyError,TypeError):break
                        yield json.dumps({**payload,'lines':rows,'warning':warning})+'\n'

        except (ValueError,KeyError,TypeError):
            yield json.dumps({'error':'Não foi possível concluir o cálculo das rotas.','complete':True})+'\n'
    response=StreamingHttpResponse(chunks(),content_type='application/x-ndjson')
    response['Cache-Control']='no-cache'
    response['X-Accel-Buffering']='no'
    return response
