"""Reavalia somente sequências materializadas, usando o serviço/horário da consulta."""
from contextlib import closing
import hashlib
import json
import math
import sqlite3
import time
from . import graph, planner, rail, staged_materialized as staged, store, transfer_policy, walking


def progressive(db,origin,destination,max_transfers,now):
    from .alternatives import access_points, geographic_anchor, distinct_routes
    path=staged.database_path()
    base={'planner':'staged','materialized':True,'complete':False,'walking_incomplete':False,
          'search_limited':False,'optimal_within_limits':False}
    if not path.exists():
        yield {**base,'journeys':[],'complete':True};return
    try:
        with closing(graph.readonly(path)) as prepared:
            meta=json.loads(prepared.execute('SELECT value FROM metadata WHERE id=1').fetchone()[0])
            if meta['signature']!=staged.signature(meta['signature']['walks'][0]):
                raise ValueError('Materializado desatualizado.')
            base['materialization_complete_stages']=meta['complete_stages']
            from . import expanded_materialized
            expanded=meta.get('expanded_signature')==expanded_materialized.signature(meta['signature'])
            if expanded:base['materialization_max_cost_units']=meta.get('expanded_complete_units',3)
            from . import topup_materialized
            topup=expanded and topup_materialized.signature_matches(meta.get('topup_signature'),meta['expanded_signature'])
            if topup:base['materialization_max_cost_units']=meta.get('topup_complete_units',8)
            ids={row['sid']:row['id'] for row in prepared.execute('SELECT * FROM stops')}
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):
        yield {**base,'journeys':[],'complete':True};return
    # Keep a separate read transaction per query; build commits remain immediately visible.
    with closing(graph.readonly(path)) as prepared:
        source=store.database_path();stat=source.stat()
        stops,trips,_=planner._network(str(source),stat.st_mtime_ns,stat.st_size,True)
        windows=planner._service_windows(db,trips,source,stat,now,True,{})
        starts=([(origin,None)] if not geographic_anchor(origin) else access_points(db,origin,True,optimistic=True,endpoint_selection=True,include_rail=True)[0])
        ends=([(destination,None)] if not geographic_anchor(destination) else access_points(db,destination,False,optimistic=True,endpoint_selection=True,include_rail=True)[0])
        candidates=[]
        for start,access in starts:
            if start['id'] not in ids:continue
            for end,egress in ends:
                if end['id'] not in ids:continue
                pair=(ids[start['id']],ids[end['id']])
                row=prepared.execute('SELECT data FROM topup_paths WHERE origin=? AND destination=?',pair).fetchone() if topup else None
                if row is None and expanded:row=prepared.execute('SELECT data FROM expanded_paths WHERE origin=? AND destination=?',pair).fetchone()
                if row is None:row=prepared.execute('SELECT data FROM paths WHERE origin=? AND destination=?',pair).fetchone()
                if row:
                    for route in staged.decode(row[0]):
                        if route['units']<=max_transfers*3:candidates.append((route,start,end,access,egress))
        reverse={value:key for key,value in ids.items()}
        rides={};patterns={};feet={};verified={};found=[]
        def ride(eid):
            if eid not in rides:rides[eid]=dict(prepared.execute('SELECT * FROM rides WHERE id=?',(eid,)).fetchone())
            return rides[eid]
        def variants(pid):
            if pid not in patterns:patterns[pid]=json.loads(prepared.execute('SELECT trips FROM patterns WHERE id=?',(pid,)).fetchone()[0])
            return patterns[pid]
        def foot(wid):
            if not wid:return None
            if wid not in feet:
                row=dict(prepared.execute('SELECT * FROM walks WHERE id=?',(wid,)).fetchone())
                feet[wid]={'origin':stops[reverse[row['origin']]],'destination':stops[reverse[row['destination']]],
                    'distance_meters':row['meters'],'seconds':row['seconds'],'duration_minutes':row['seconds']/60,
                    'internal_transfer':bool(row['internal']),'available':True,'geometry':[],
                    'source':'Integração interna estimada' if row['internal'] else 'OSRM foot local / OpenStreetMap · materializado',
                    'estimated':bool(row['internal'])}
            return feet[wid]
        def endpoint(w):
            if not w:return None
            key=w['origin']['id'],w['destination']['id']
            if key not in verified:
                route=walking.route(w['origin'],w['destination'],wait_for_slot=True)
                verified[key]=({**route,'accessType':w['accessType']} if route.get('available') and route['distance_meters']<=walking.WALK_LIMIT else None)
            if verified[key] is None:raise ValueError('Acesso pedestre não verificado.')
            return verified[key]
        def evaluate(candidate,check_walks):
            route,start,end,access,egress=candidate
            if check_walks:access,egress=endpoint(access),endpoint(egress)
            access_seconds=(access or {}).get('distance_meters',0)/walking.WALK_METERS_PER_SECOND
            egress_seconds=(egress or {}).get('distance_meters',0)/walking.WALK_METERS_PER_SECOND
            reached=now.timestamp()+access_seconds;chain=[];paths={};access_times={}
            for index,(eid,wid) in enumerate(route['legs']):
                edge=ride(eid);walk=foot(wid)
                if walk:
                    a,b=walk['origin']['id'],walk['destination']['id'];paths[a,b]=walk
                    chain.append(('__walk__',a,b,reached,reached+walk['seconds']));reached+=walk['seconds']
                sid=reverse[edge['origin']]
                if index==0:access_times[sid]=reached-now.timestamp()
                ready=reached+(planner.TRANSFER_SECONDS if index else 0)
                options=[]
                for identifier in variants(edge['pattern']):
                    trip=trips[identifier];a,b=edge['boarding'],edge['alighting']
                    departure=planner.next_departure(trip,a,ready,rail.boarding_windows(trip,a,windows[identifier],now.tzinfo))
                    if not rail.departure_allowed(trip,departure,now.tzinfo,index>0):continue
                    arrival=departure+trip['times'][b][1]-trip['times'][a][2]
                    options.append((arrival,departure,identifier,a,b))
                if not options:return None
                reached,departure,identifier,a,b=min(options)
                if not math.isfinite(reached) or reached+egress_seconds>now.timestamp()+planner.HORIZON_SECONDS:return None
                chain.append((identifier,a,b,departure,reached))
            final=foot(route['egress'])
            if final:
                a,b=final['origin']['id'],final['destination']['id'];paths[a,b]=final
                chain.append(('__walk__',a,b,reached,reached+final['seconds']));reached+=final['seconds']
            if reached+egress_seconds>now.timestamp()+planner.HORIZON_SECONDS:return None
            result=planner._format_journey(end['id'],reached,chain,trips,stops,now.timestamp(),now,
                                           {end['id']:egress_seconds},access_times,{},paths,include_geometry=check_walks)
            all_walks=[w for w in [access,*result['transfer_walks'],egress] if w]
            fingerprint='staged-'+hashlib.sha256(json.dumps([route,start['id'],end['id']],sort_keys=True).encode()).hexdigest()[:24]
            result.update(id=fingerprint,walks=all_walks,walking_meters=sum(w['distance_meters'] for w in all_walks),
                          walking_minutes=sum(w.get('seconds',w['distance_meters']/walking.WALK_METERS_PER_SECOND) for w in all_walks)/60)
            return transfer_policy.annotate(result)
        ranked=[]
        for candidate in candidates:
            result=evaluate(candidate,False)
            if result:ranked.append((result['transfer_cost_units'],result['duration_minutes'],candidate))
        ranked.sort(key=lambda item:item[:2]);deadline=time.monotonic()+8
        for _,_,candidate in ranked:
            if time.monotonic()>deadline:
                base['search_limited']=True;break
            try:result=evaluate(candidate,True)
            except ValueError:
                base['walking_incomplete']=True;continue
            if result:
                found.append(result)
                yield {**base,'journeys':distinct_routes(found)}
        yield {**base,'journeys':distinct_routes(found),'complete':True}
