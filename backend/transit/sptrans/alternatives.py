"""Door-to-door alternatives with verified pedestrian access at both endpoints."""
from datetime import timedelta
import hashlib
import json
from django.core.cache import cache
from django.utils import timezone
from . import store, planner, walking, directions

WALK_LIMIT = 200

def access_points(db, anchor, outgoing):
    choices=[]; incomplete=False
    for row in db.execute("SELECT s.* FROM stops s WHERE EXISTS (SELECT 1 FROM stop_times st JOIN trips t USING(trip_id) JOIN routes r USING(route_id) WHERE st.stop_id=s.stop_id AND r.route_type='3')"):
        point=store.stop(row)
        gap=directions.distance((anchor['lat'],anchor['lon']),(point['lat'],point['lon']))
        if gap>WALK_LIMIT:continue
        if gap<0.01:
            choices.append((point,None));continue
        path=walking.route(anchor,point,wait_for_slot=True) if outgoing else walking.route(point,anchor,wait_for_slot=True)
        if not path.get('available'):
            incomplete=True;continue
        if path['distance_meters']<=WALK_LIMIT:
            choices.append((point,{**path,'accessType':'boarding' if outgoing else 'destination'}))
    return choices,incomplete

def distinct_routes(journeys):
    """Nearby stops for the same sequence of lines are one passenger choice."""
    groups={}
    for journey in journeys:
        signature=tuple((leg.get('route_id',leg['code']),leg.get('direction_id',leg['trip_id']),leg['headsign']) for leg in journey['legs'])
        # Keep the nearby boarding preference, then choose the alighting point
        # by door-to-door time: staying on the bus can save a longer final walk.
        def rank(route):
            boarding_walk=sum(w['distance_meters'] for w in route['walks'] if w['accessType']=='boarding') if 'walks' in route else route['walking_meters']
            return (boarding_walk,route['duration_minutes'],route['walking_meters'],route['id'])
        if signature not in groups or rank(journey)<rank(groups[signature]):
            groups[signature]=journey
    return sorted(groups.values(),key=lambda r:(r['duration_minutes'],r['transfers'],r['walking_meters'],r['id']))


def progressive(db, origin, destination, max_transfers=2, now=None):
    now=now or timezone.localtime()
    stat=store.database_path().stat()
    key='pap.alternatives.v4:'+hashlib.sha256(json.dumps([origin,destination,max_transfers,int(now.timestamp()//30),stat.st_mtime_ns,stat.st_size],sort_keys=True).encode()).hexdigest()
    cached=cache.get(key)
    if cached is not None:
        yield {**cached,"complete":True}
        return
    # Return the selected-stop itinerary before asking for pedestrian paths.
    initial=[]
    if not origin['id'].startswith('address-') and not destination['id'].startswith('address-'):
        for trip in planner.journeys(db,origin['id'],destination['id'],max_transfers,now=now):
            fingerprint='|'.join(f"{leg['trip_id']}:{leg['origin']['id']}:{leg['destination']['id']}" for leg in trip['legs'])
            initial.append({**trip,'id':fingerprint,'walking_minutes':0,'walking_meters':0,'walks':[]})
    yield {'journeys':distinct_routes(initial),'walking_incomplete':False,'complete':False}
    starts,missing_start=access_points(db,origin,True)
    ends,missing_end=access_points(db,destination,False)
    found={j['id']:j for j in initial}
    transfer_paths={}
    incomplete=missing_start or missing_end
    starts.sort(key=lambda entry:entry[1]['distance_meters'] if entry[1] else 0)
    ends.sort(key=lambda entry:entry[1]['distance_meters'] if entry[1] else 0)
    for start,access in starts:
        access_minutes=access['distance_meters']/walking.WALK_METERS_PER_MINUTE if access else 0
        for end,egress in ends:
            egress_minutes=egress['distance_meters']/walking.WALK_METERS_PER_MINUTE if egress else 0
            while True:
                trips=planner.journeys(db,start['id'],end['id'],max_transfers,now=now+timedelta(minutes=access_minutes),transfer_paths=transfer_paths)
                pending={(w['origin']['id'],w['destination']['id']):(w['origin'],w['destination']) for t in trips for w in t['transfer_walks'] if (w['origin']['id'],w['destination']['id']) not in transfer_paths}
                if not pending:break
                for pair,(a,b) in pending.items():
                    foot=walking.route(a,b,wait_for_slot=True)
                    if not foot.get('available'):incomplete=True
                    transfer_paths[pair]=foot if foot.get('available') and foot['distance_meters']<=WALK_LIMIT else None
            for trip in trips:
                fingerprint='|'.join(f"{leg['trip_id']}:{leg['origin']['id']}:{leg['destination']['id']}" for leg in trip['legs'])
                total=round(access_minutes+trip['duration_minutes']+egress_minutes,1)
                transfer_walks=trip.get('transfer_walks',[])
                walking_meters=sum(p['distance_meters'] for p in [access,egress,*transfer_walks] if p)
                result={**trip,'id':fingerprint,'duration_minutes':total,'walking_minutes':round(walking_meters/walking.WALK_METERS_PER_MINUTE,1),
                        'walking_meters':round(walking_meters),
                        'arrival':(timezone.datetime.fromisoformat(trip['arrival'])+timedelta(minutes=egress_minutes)).isoformat(),
                        'walks':[p for p in [access,*transfer_walks,egress] if p]}
                if fingerprint not in found or total<found[fingerprint]['duration_minutes']:found[fingerprint]=result
            yield {'journeys':distinct_routes(found.values()),'walking_incomplete':incomplete,'complete':False}
    result={'journeys':distinct_routes(found.values()),
            'walking_incomplete':incomplete}
    cache.set(key,result,30)
    yield {**result,'complete':True}

def alternatives(db, origin, destination, max_transfers=2, now=None):
    result=None
    for result in progressive(db,origin,destination,max_transfers,now):pass
    return result
