import csv
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from django.test import SimpleTestCase, override_settings
from transit.sptrans import store, planner

NOW=datetime(2026,10,6,8,tzinfo=ZoneInfo('America/Sao_Paulo'))

class TransferPlannerTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        rows={table:[] for table in store.TABLES}
        rows['stops']=[[str(i),f'Ponto {i}','',-23.5-i*.001,-46.6] for i in range(1,5)]
        rows['calendar']=[['daily',1,1,1,1,1,1,1,'20260101','20261231']]
        for i in range(1,4):
            code=f'R{i}'
            rows['routes'].append([code,'1',code,'Linha '+code,'3','005cec'])
            rows['trips'].append([code,'daily',code,'Destino','0','S'])
            rows['stop_times'].extend([[code,'07:00:00','07:00:00',str(i),1],[code,'07:10:00','07:10:00',str(i+1),2]])
            rows['frequencies'].append([code,'07:00:00','26:00:00',600,'0'])
        for table,columns in store.TABLES.items():
            with (root/(table+'.txt')).open('w') as f:
                writer=csv.writer(f);writer.writerow(columns);writer.writerows(rows[table])
        self.path=root/'network.sqlite3'
        store.import_gtfs(root,self.path)
        self.override=override_settings(SPTRANS_DATABASE=self.path,SPTRANS_TOKEN='')
        self.override.enable();self.addCleanup(self.override.disable)
    def plan(self,a='1',b='4',limit=2,now=NOW):
        with store.connection() as db:return planner.journeys(db,a,b,limit,now)
    def edit(self,sql,values=()):
        with sqlite3.connect(self.path) as db:db.execute(sql,values)
        planner._network.cache_clear()
    def test_two_transfers_with_wait_and_buffer(self):
        result=self.plan()[0]
        self.assertEqual(result['transfers'],2)
        self.assertEqual(result['duration_minutes'],49)
        self.assertEqual([l['wait_minutes'] for l in result['legs']],[5,7,7])
        self.assertEqual([l['origin']['id'] for l in result['legs']],['1','2','3'])
        self.assertEqual(self.plan(limit=1),[])
    def test_no_reverse_or_zero_length_journey(self):
        self.assertEqual(self.plan('4','1'),[])
        self.assertEqual(self.plan('1','1'),[])
        self.assertEqual(self.plan('1','2',0)[0]['transfers'],0)
    def test_cannot_catch_bus_before_transfer_buffer(self):
        self.edit("DELETE FROM frequencies WHERE trip_id='R2'")
        self.edit("UPDATE stop_times SET arrival_time='08:16:00',departure_time='08:16:00' WHERE trip_id='R2' AND stop_sequence=1")
        self.edit("UPDATE stop_times SET arrival_time='08:26:00',departure_time='08:26:00' WHERE trip_id='R2' AND stop_sequence=2")
        self.assertEqual(self.plan('1','3'),[])
    def test_exact_frequency_phase(self):
        self.edit("UPDATE frequencies SET exact_times='1'")
        result=self.plan('1','3')[0]
        # Embarque às 08:00; chegada às 08:10; troca de 2 min exige a próxima partida às 08:20.
        self.assertEqual(result['duration_minutes'],30)
    def test_midnight_and_service_exception(self):
        result=self.plan(now=NOW.replace(hour=23,minute=55))[0]
        self.assertTrue(result['arrival'].startswith('2026-10-07T00:44'))
        self.edit("INSERT INTO calendar_dates VALUES ('daily','20261006','2')")
        self.assertEqual(self.plan(),[])
    def test_horizon_and_expired_feed(self):
        self.assertEqual(self.plan(now=NOW.replace(year=2028)),[])
        self.edit("UPDATE frequencies SET start_time='20:00:00',end_time='21:00:00'")
        self.assertEqual(self.plan(),[])
    def test_nearby_distinct_stop_does_not_create_walking_transfer(self):
        self.edit("INSERT INTO stops VALUES ('5','Plataforma vizinha','',-23.502,-46.6)")
        self.edit("UPDATE stop_times SET stop_id='5' WHERE trip_id='R2' AND stop_sequence=1")
        self.assertEqual(self.plan(),[])
    def test_invalid_limit_rejected(self):
        self.assertEqual(self.client.get('/api/sptrans/board/',{'origin':'1','destination':'4','max_transfers':'4'}).status_code,400)
    def test_api_returns_connections_without_realtime_credentials(self):
        from unittest.mock import patch
        with patch('transit.sptrans.planner.timezone.localtime',return_value=NOW):
            data=self.client.get('/api/sptrans/board/',{'origin':'1','destination':'4','max_transfers':'2'}).json()
        self.assertFalse(data['direct_only'])
        self.assertEqual(data['journeys'][0]['transfers'],2)
        self.assertTrue(data['journeys'][0]['estimated'])
    def test_three_transfers_and_faster_alternative_to_direct_bus(self):
        self.edit("INSERT INTO stops VALUES ('5','Último ponto','',-23.505,-46.6)")
        self.edit("INSERT INTO routes VALUES ('R4','1','R4','Linha R4','3','005cec')")
        self.edit("INSERT INTO trips VALUES ('R4','daily','R4','Último ponto','0','S')")
        self.edit("INSERT INTO stop_times VALUES ('R4','07:00:00','07:00:00','4',1)")
        self.edit("INSERT INTO stop_times VALUES ('R4','07:10:00','07:10:00','5',2)")
        self.edit("INSERT INTO frequencies VALUES ('R4','07:00:00','26:00:00',600,'0')")
        self.assertEqual(self.plan('1','5',2),[])
        self.assertEqual(self.plan('1','5',3)[0]['transfers'],3)
        self.edit("INSERT INTO trips VALUES ('R4','daily','DIRECT','Último ponto','0','S')")
        self.edit("INSERT INTO stop_times VALUES ('DIRECT','07:00:00','07:00:00','1',1)")
        self.edit("INSERT INTO stop_times VALUES ('DIRECT','09:00:00','09:00:00','5',2)")
        self.edit("INSERT INTO frequencies VALUES ('DIRECT','07:00:00','26:00:00',600,'0')")
        result=self.plan('1','5',3)
        self.assertEqual([r['transfers'] for r in result],[3,0])
        self.assertLess(result[0]['duration_minutes'],result[1]['duration_minutes'])

    def test_route_only_uses_each_transfer_stop_and_preserves_leg_order(self):
        from unittest.mock import patch
        seen=[]
        def predict(row,stop):
            seen.append(stop['id'])
            row['arrivals']=[{'time':'08:0'+str(4-int(stop['id']))}]
        with patch('transit.sptrans.planner.timezone.localtime',return_value=NOW), patch('transit.sptrans.views.realtime.add_predictions',side_effect=predict):
            data=self.client.get('/api/sptrans/board/',{'origin':'1','destination':'4','route_only':'1'}).json()
        self.assertEqual(seen,['1','2','3'])
        self.assertEqual([row['code'] for row in data['lines']],['R1','R2','R3'])
        self.assertTrue(all(row['planned_departure'] for row in data['lines']))

    def test_address_prefers_nearby_direct_stop_to_return_side_with_transfers(self):
        from unittest.mock import patch
        self.edit("UPDATE stops SET stop_lat=-23.50205 WHERE stop_id='4'")
        with patch('transit.sptrans.views.timezone.localtime',return_value=NOW):
            result=self.client.get('/api/sptrans/destination/',{'lat':-23.50205,'lon':-46.6,'origin':'1'}).json()
        self.assertEqual(result['stop']['id'],'2')
        self.assertTrue(result['direction_checked'])
        self.assertEqual(result['max_transfers'],0)

    def test_address_rechecks_boarding_direction_after_target_selected(self):
        from unittest.mock import patch
        self.edit("UPDATE stops SET stop_lat=-23.50305 WHERE stop_id='1'")
        with patch('transit.sptrans.views.timezone.localtime',return_value=NOW):
            result=self.client.get('/api/sptrans/destination/',{'lat':-23.50305,'lon':-46.6,'target':'4'}).json()
        self.assertEqual(result['stop']['id'],'3')
        self.assertEqual(result['max_transfers'],0)

    def test_street_returns_all_matching_stops_not_disconnected_namesake(self):
        self.edit("UPDATE stops SET stop_name='R. Augusta, 100' WHERE stop_id='1'")
        self.edit("UPDATE stops SET stop_name='Rua Augusta, 200' WHERE stop_id='2'")
        self.edit("UPDATE stops SET stop_name='R. Augusta, 300',stop_lat=-23.6 WHERE stop_id='4'")
        result=self.client.get('/api/sptrans/destination/',{'lat':-23.501,'lon':-46.6,'street':'Rua Augusta'}).json()
        self.assertEqual({s['id'] for s in result['stops']},{'1','2'})

    def test_bus_geometry_keeps_curve_and_clips_to_boarding_stops(self):
        from transit.sptrans.geometry import leg_shape
        points=[(-23.500,-46.6),(-23.501,-46.6),(-23.5015,-46.599),(-23.502,-46.6),(-23.503,-46.6)]
        for i,(lat,lon) in enumerate(points):
            self.edit('INSERT INTO shapes VALUES (?,?,?,?)',('S',lat,lon,i))
        geometry=leg_shape('R1',0,1)
        self.assertEqual(geometry[0],points[1])
        self.assertEqual(geometry[-1],points[3])
        self.assertIn(points[2],geometry)
        self.assertNotIn(points[0],geometry)
        self.assertNotIn(points[4],geometry)

    def test_missing_shape_does_not_invent_straight_route(self):
        self.assertEqual(self.plan('1','2')[0]['legs'][0]['geometry'],[])

    def test_bad_stop_after_selected_leg_does_not_remove_its_geometry(self):
        from transit.sptrans.geometry import leg_shape
        self.edit("INSERT INTO shapes VALUES ('S',-23.501,-46.6,1)")
        self.edit("INSERT INTO shapes VALUES ('S',-23.502,-46.6,2)")
        self.edit("UPDATE stops SET stop_lat=-24 WHERE stop_id='3'")
        self.edit("INSERT INTO stop_times VALUES ('R1','07:20:00','07:20:00','3',3)")
        self.assertTrue(leg_shape('R1',0,1))
        self.assertEqual(leg_shape('R1',1,2),[])

    def test_loop_does_not_snap_first_stop_to_later_return(self):
        from transit.sptrans.geometry import leg_shape
        points=[(-23.501,-46.60001),(-23.502,-46.60001),(-23.502,-46.599),(-23.501,-46.6)]
        for i,(lat,lon) in enumerate(points):
            self.edit('INSERT INTO shapes VALUES (?,?,?,?)',('S',lat,lon,i))
        geometry=leg_shape('R1',0,1)
        self.assertTrue(geometry)
        self.assertLess(geometry[0][1],-46.6)
        self.assertLess(geometry[-1][0],-23.5019)

    def test_street_falls_back_to_existing_nearby_stops(self):
        result=self.client.get('/api/sptrans/destination/',{'lat':-23.501,'lon':-46.6,'street':'Avenida não cadastrada'}).json()
        self.assertEqual(result['match_method'],'nearby')
        self.assertEqual(result['radius_meters'],400)
        self.assertEqual({s['id'] for s in result['stops']},{'1','2','3','4'})
        remote=self.client.get('/api/sptrans/destination/',{'lat':-24,'lon':-46.6,'street':'Avenida não cadastrada'}).json()
        self.assertEqual(remote['stops'],[])

    def test_boarding_checks_both_sides_for_direct_bus(self):
        from unittest.mock import patch
        self.edit("UPDATE stops SET stop_lat=-23.50105 WHERE stop_id='4'")
        self.edit("UPDATE stops SET stop_lat=-23.50205 WHERE stop_id='3'")
        with patch('transit.sptrans.views.timezone.localtime',return_value=NOW):
            result=self.client.get('/api/sptrans/destination/',{'lat':-23.50105,'lon':-46.6,'target':'3'}).json()
        self.assertEqual(result['max_transfers'],0)
        self.assertNotEqual(result['stop']['id'],'4')
        with store.connection() as db:
            routes=planner.journeys(db,result['stop']['id'],result['destination']['id'],0,now=NOW)
        self.assertTrue(routes)

    def test_transfer_walk_changes_boarding_time(self):
        self.edit("INSERT INTO stops VALUES ('5','Outra plataforma','',-23.5021,-46.6)")
        self.edit("UPDATE stop_times SET stop_id='5' WHERE trip_id='R2' AND stop_sequence=1")
        with store.connection() as db:
            self.assertFalse(planner.journeys(db,'1','4',2,now=NOW))
            walk={'available':True,'origin':store.get_stop(db,'2'),'destination':store.get_stop(db,'5'),'distance_meters':200,'duration_minutes':3,'geometry':[[-23.502,-46.6],[-23.5021,-46.6]]}
            # Exclua outras ligações pedestres para isolar esta transferência.
            stat=store.database_path().stat()
            paths={(a,b):None for a,near in planner._nearby(str(store.database_path()),stat.st_mtime_ns,stat.st_size).items() for b,_ in near}
            paths[('2','5')]=walk
            route=planner.journeys(db,'1','4',2,now=NOW,transfer_paths=paths)[0]
        self.assertEqual(route['transfers'],2)
        self.assertEqual(route['duration_minutes'],51.7)
        self.assertEqual(route['transfer_walks'][0]['before_leg'],1)
        self.assertEqual(route['legs'][1]['origin']['id'],'5')

    def test_final_walk_finishes_with_one_bus_without_extra_boarding(self):
        with store.connection() as db:
            foot={'origin':store.get_stop(db,'2'),'destination':store.get_stop(db,'4'),
                  'available':True,'distance_meters':300,'geometry':[[-23.502,-46.6],[-23.504,-46.6]]}
            trips=planner.journeys(db,'1','4',0,now=NOW,
                                  transfer_paths={('2','4'):foot},known_transfers_only=True,
                                  preserve_alternatives=True)
        self.assertTrue(trips)
        best=trips[0]
        self.assertEqual(len(best['legs']),1)
        self.assertEqual(best['transfers'],0)
        self.assertEqual(best['legs'][-1]['destination']['id'],'2')
        self.assertEqual(best['goal_stop_id'],'4')
        self.assertEqual(best['transfer_walks'][-1]['destination']['id'],'4')
        self.assertAlmostEqual(best['duration_minutes'],19)

    def test_all_endpoints_allow_nearby_boarding_and_alighting(self):
        from transit.sptrans import alternatives
        with store.connection() as db:
            point=store.get_stop(db,'1')
            for outgoing in (True,False):
                fixed,_=alternatives.access_points(db,point,outgoing,optimistic=True,endpoint_selection=True)
                self.assertEqual([p['id'] for p,w in fixed],['1','2','3'])
                self.assertIsNone(fixed[0][1])
                for p,w in fixed[1:]:
                    self.assertEqual(w['accessType'],'boarding' if outgoing else 'destination')
                    self.assertEqual(w['origin']['id'] if outgoing else w['destination']['id'],'1')
                anchor={**point,'id':'address-test','lat':point['lat']+.0001}
                choices,_=alternatives.access_points(db,anchor,outgoing,optimistic=True,endpoint_selection=True)
                self.assertEqual([p['id'] for p,w in choices],['1','2','3'])
                for p,w in choices:
                    self.assertEqual(w['origin']['id'] if outgoing else w['destination']['id'],'address-test')

    def test_access_uses_real_walking_distance_and_four_kmh(self):
        from transit.sptrans import alternatives
        from unittest.mock import patch
        self.edit("UPDATE stops SET stop_lat=-23.5011 WHERE stop_id='2'")
        with store.connection() as db:
            origin=store.get_stop(db,'1')
            with patch('transit.sptrans.walking.route',return_value={'available':True,'distance_meters':1001}):
                starts,incomplete=alternatives.access_points(db,origin,True)
            self.assertEqual([p['id'] for p,w in starts],['1'])
            with patch('transit.sptrans.walking.route',return_value={'available':False}):
                starts,incomplete=alternatives.access_points(db,origin,True)
            self.assertTrue(incomplete)

    def test_alternatives_validate_transfer_walks_and_sort_total_time(self):
        from transit.sptrans import alternatives
        from unittest.mock import patch
        from django.core.cache import cache
        cache.clear()
        self.edit("INSERT INTO stops VALUES ('5','Outra plataforma','',-23.5021,-46.6)")
        self.edit("UPDATE stop_times SET stop_id='5' WHERE trip_id='R2' AND stop_sequence=1")
        def foot(a,b,**kwargs):
            if (a['id'],b['id'])!=('2','5'):return {'available':True,'distance_meters':1050}
            return {'available':True,'origin':a,'destination':b,'distance_meters':100,'duration_minutes':1.5,'geometry':[[a['lat'],a['lon']],[b['lat'],b['lon']]]}
        with store.connection() as db,patch('transit.sptrans.walking.route',side_effect=foot):
            a=store.get_stop(db,'1');b=store.get_stop(db,'4')
            with patch('transit.sptrans.alternatives.access_points',side_effect=[([(a,None)],False),([(b,None)],False)]):
                result=alternatives.alternatives(db,a,b,now=NOW)
        routes=result['journeys']
        self.assertTrue(routes)
        self.assertAlmostEqual(routes[0]['walking_minutes'],100/75)
        self.assertEqual(routes[0]['walks'][0]['accessType'],'transfer')
        self.assertEqual(routes[0]['duration_minutes'],50.3)
        self.assertEqual([r['duration_minutes'] for r in routes],sorted(r['duration_minutes'] for r in routes))

    def test_same_bus_at_nearby_stops_keeps_fastest_total(self):
        from transit.sptrans.alternatives import distinct_routes
        def option(identifier,minutes,meters,trip='715M-0',direction='0',code='715M-10'):
            return {'id':identifier,'duration_minutes':minutes,'walking_meters':meters,'transfers':0,
                    'legs':[{'trip_id':trip,'route_id':code,'code':code,'direction_id':direction,'headsign':'Terminal'}]}
        routes=distinct_routes([
            option('far',31,278),option('near',31.1,40),option('middle',31.1,158),
            option('other-departure',31.2,50,trip='715M-extra'),
            option('return',32,0,direction='1'),option('another-line',30,100,code='778J-10')])
        self.assertEqual([r['id'] for r in routes],['another-line','far','return'])

    def test_distinct_transfer_sequences_are_preserved(self):
        from transit.sptrans.alternatives import distinct_routes
        leg=lambda code:dict(trip_id=code,route_id=code,code=code,direction_id='0',headsign='Terminal')
        routes=[dict(id='one',duration_minutes=30,walking_meters=0,transfers=1,legs=[leg('A'),leg('B')]),
                dict(id='two',duration_minutes=31,walking_meters=0,transfers=1,legs=[leg('A'),leg('C')])]
        self.assertEqual(len(distinct_routes(routes)),2)

    def test_later_alighting_compares_bus_time_with_final_walk(self):
        from transit.sptrans.alternatives import distinct_routes
        def option(identifier,total,walk):
            return dict(id=identifier,duration_minutes=total,walking_meters=walk,transfers=0,
                        legs=[dict(trip_id='T',route_id='715M',code='715M',direction_id='0',headsign='Terminal')],
                        walks=[dict(accessType='destination',distance_meters=walk)])
        early=option('early',23,200)  # 20 minutos no ônibus + 3 a pé.
        later=option('later',21.6,40)  # 21 minutos no ônibus + 0,6 a pé.
        self.assertEqual(distinct_routes([early,later])[0]['id'],'later')
        # Um desvio longo de ônibus não deve vencer apenas por reduzir a caminhada final.
        detour=option('detour',30,0)
        self.assertEqual(distinct_routes([early,later,detour])[0]['id'],'later')

    def test_fastest_total_can_change_boarding_without_duplicate_bus(self):
        from transit.sptrans.alternatives import distinct_routes
        leg=dict(trip_id='T',route_id='715M',code='715M',direction_id='0',headsign='Terminal')
        original=dict(id='original',duration_minutes=23,walking_meters=100,transfers=0,legs=[leg],
                      walks=[dict(accessType='destination',distance_meters=100)])
        moved=dict(id='moved',duration_minutes=22,walking_meters=20,transfers=0,legs=[leg],
                   walks=[dict(accessType='boarding',distance_meters=20)])
        self.assertEqual(distinct_routes([moved,original])[0]['id'],'moved')

    def test_progressive_yields_before_pedestrian_requests_and_can_close(self):
        from transit.sptrans import alternatives
        from unittest.mock import patch
        from django.core.cache import cache
        cache.clear()
        with store.connection() as db,patch('transit.sptrans.alternatives.access_points') as access, \
             patch('transit.sptrans.journey_completion.direct_walk',return_value=None):
            iterator=alternatives.progressive(db,store.get_stop(db,'1'),store.get_stop(db,'4'),now=NOW)
            first=next(iterator)
            self.assertFalse(first['complete'])
            self.assertTrue(first['journeys'])
            access.assert_not_called()
            iterator.close()
            access.assert_not_called()

    def test_explicit_refresh_bypasses_cached_result(self):
        from transit.sptrans import alternatives
        from unittest.mock import patch
        cached={'journeys':[],'complete':True,'walking_incomplete':False}
        with store.connection() as db, patch('transit.sptrans.alternatives.cache.get',return_value=cached) as get:
            origin,destination=store.get_stop(db,'1'),store.get_stop(db,'4')
            results=list(alternatives._bus_progressive(db,origin,destination,now=NOW))
            self.assertEqual(len(results),1)
            self.assertEqual({key:results[0][key] for key in cached},cached)
            self.assertEqual(results[0]['planner'],'raptor')
            get.reset_mock()
            iterator=alternatives._bus_progressive(db,origin,destination,now=NOW,refresh=True)
            try:
                first=next(iterator)
                self.assertFalse(first['complete'])
                self.assertTrue(first['journeys'])
                get.assert_not_called()
            finally:
                iterator.close()

    def test_board_stream_passes_explicit_refresh(self):
        from unittest.mock import patch
        with patch('transit.sptrans.alternatives.progressive',return_value=iter([])) as progressive:
            response=self.client.get('/api/sptrans/board/',{'origin':'1','destination':'4','stream':'1','refresh':'1'})
            list(response.streaming_content)
            self.assertTrue(progressive.call_args.kwargs['refresh'])

    def test_board_stream_returns_ndjson_snapshots(self):
        import json
        from unittest.mock import patch
        snapshots=[{'journeys':[],'complete':False,'walking_incomplete':False},
                   {'journeys':[],'complete':True,'walking_incomplete':False}]
        with patch('transit.sptrans.alternatives.progressive',return_value=iter(snapshots)):
            response=self.client.get('/api/sptrans/board/',{'origin':'1','destination':'4','stream':'1'})
            self.assertTrue(response.streaming)
            self.assertEqual(response['X-Accel-Buffering'],'no')
            data=[json.loads(chunk) for chunk in response.streaming_content]
        self.assertEqual([r['complete'] for r in data],[False,True])

    def test_access_accepts_one_km_and_rejects_longer_detour(self):
        from transit.sptrans import alternatives
        from unittest.mock import patch
        with store.connection() as db:
            origin=store.get_stop(db,'1')
            for length,expected in [(500,True),(750,True),(1000,True),(1001,False)]:
                with patch('transit.sptrans.walking.route',return_value={'available':True,'distance_meters':length}):
                    points,_=alternatives.access_points(db,origin,True)
                self.assertEqual(any(s['id']=='4' for s,w in points),expected)

    def test_schedule_context_reuses_service_calendar(self):
        from unittest.mock import patch
        with store.connection() as db,patch('transit.sptrans.store.service_active',wraps=store.service_active) as service:
            context={}
            first=planner.journeys(db,'1','4',now=NOW,context=context)
            calls=service.call_count
            second=planner.journeys(db,'1','4',now=NOW,context=context)
            self.assertEqual(service.call_count,calls)
            self.assertEqual(first,second)

    def test_final_bus_can_alight_before_return_passage(self):
        from transit.sptrans.alternatives import earlier_alighting
        self.edit("INSERT INTO stop_times VALUES ('R1','07:40:00','07:40:00','4',3)")
        with store.connection() as db:
            trip=planner.journeys(db,'1','4',0,now=NOW)[0]
            near=store.get_stop(db,'2');end=store.get_stop(db,'4')
            foot={'distance_meters':40,'duration_minutes':0.6,'accessType':'destination'}
            shortened,walk=earlier_alighting(db,trip,{'2':(near,foot),'4':(end,None)})
        self.assertEqual(shortened['legs'][-1]['destination']['id'],'2')
        self.assertEqual(shortened['legs'][-1]['alighting_index'],1)
        self.assertEqual(shortened['duration_minutes'],trip['duration_minutes']-30)
        self.assertEqual(walk,foot)
        self.assertEqual(trip['legs'][-1]['destination']['id'],'4')

    def test_arrival_bound_skips_transfers_that_cannot_improve_arrival(self):
        from unittest.mock import patch
        self.edit("INSERT INTO trips VALUES ('R3','daily','AFAST','Destino','0','S')")
        self.edit("INSERT INTO stop_times VALUES ('AFAST','07:00:00','07:00:00','1',1)")
        self.edit("INSERT INTO stop_times VALUES ('AFAST','07:02:00','07:02:00','4',2)")
        self.edit("INSERT INTO frequencies VALUES ('AFAST','07:00:00','26:00:00',600,'0')")
        with patch('transit.sptrans.planner.next_departure',wraps=planner.next_departure) as departures:
            routes=self.plan()
        self.assertEqual(routes[0]['duration_minutes'],7)
        self.assertEqual(routes[0]['legs'][0]['trip_id'],'AFAST')
        # R1 chega à transferência depois de o destino já estar alcançável.
        self.assertNotIn('R2',[call.args[0]['trip_id'] for call in departures.call_args_list])

    def test_multi_source_goal_matches_exhaustive_pair_search(self):
        from datetime import timedelta
        starts={'1':0,'2':90};ends={'3':180,'4':0}
        expected=[]
        with store.connection() as db:
            for a,access in starts.items():
                for b,egress in ends.items():
                    for r in planner.journeys(db,a,b,2,now=NOW+timedelta(seconds=access)):
                        expected.append(r['duration_minutes']+(access+egress)/60)
            actual=planner.journeys(db,'1','4',2,now=NOW,access_times=starts,end_times=ends)
        self.assertAlmostEqual(actual[0]['duration_minutes'],min(expected),places=1)
        self.assertTrue(all(r['transfers']<=2 for r in actual))

    def test_access_budget_terminates_with_partial_flag(self):
        from transit.sptrans import alternatives
        from unittest.mock import patch
        budget={'checks':64,'deadline':float('inf'),'limited':False}
        with store.connection() as db,patch('transit.sptrans.walking.route') as foot:
            points,incomplete=alternatives.access_points(db,store.get_stop(db,'1'),True,budget)
        foot.assert_not_called()
        self.assertTrue(incomplete)
        self.assertTrue(budget['limited'])
        self.assertEqual([p['id'] for p,w in points],['1'])

    def test_revalidation_has_finite_round_limit(self):
        from transit.sptrans import alternatives
        from django.core.cache import cache
        from unittest.mock import patch
        cache.clear()
        base=self.plan()[0]
        calls=0
        def search(db,a,b,*args,**kwargs):
            nonlocal calls
            calls+=1
            if 'transfer_paths' not in kwargs:return [base]
            if kwargs.get('known_transfers_only'):return []
            walk={'origin':{'id':f'x{calls}'},'destination':{'id':f'y{calls}'},'distance_meters':20,'accessType':'transfer'}
            return [{**base,'transfer_walks':[walk]}]
        with store.connection() as db:
            a=store.get_stop(db,'1');b=store.get_stop(db,'4')
            with patch('transit.sptrans.alternatives.access_points',side_effect=[([(a,None)],False),([(b,None)],False)]),patch('transit.sptrans.planner.journeys',side_effect=search),patch('transit.sptrans.walking.route',return_value={'available':False}):
                result=alternatives.alternatives(db,a,b,now=NOW)
        self.assertTrue(result['search_limited'])
        self.assertFalse(result['optimal_within_limits'])
        self.assertLessEqual(calls,14)

    def test_longer_final_walk_beats_a_third_bus(self):
        # Dois ônibus e 750 m (11,25 min) superam outra espera e viagem.
        from transit.sptrans.walking import WALK_METERS_PER_MINUTE
        with store.connection() as db:
            routes=planner.journeys(db,'1','4',2,now=NOW,
                access_times={'1':0},end_times={'3':750/WALK_METERS_PER_MINUTE*60,'4':0})
        self.assertTrue(routes)
        best=min(routes,key=lambda r:r['duration_minutes'])
        self.assertEqual(best['legs'][-1]['destination']['id'],'3')
        self.assertEqual(best['transfers'],1)

    def test_useless_final_bus_is_removed_but_walk_saving_is_kept(self):
        from transit.sptrans.alternatives import distinct_routes
        def option(identifier,codes,minutes,meters):
            return dict(id=identifier,legs=[dict(route_id=c,trip_id=c,code=c,direction_id='0',headsign=c) for c in codes],duration_minutes=minutes,walking_meters=meters,transfers=len(codes)-1)
        direct=option('direct',['N801','2582'],121.2,785)
        detour=option('detour',['N801','2582','2765'],132.9,1271)
        self.assertEqual([r['id'] for r in distinct_routes([detour,direct])],['direct'])
        shorter_walk=option('less-walking',['N801','2582','2765'],132.9,400)
        self.assertEqual(len(distinct_routes([direct,shorter_walk])),2)

    def test_same_bus_prefers_less_access_walking_on_equal_arrival(self):
        self.edit("DELETE FROM frequencies WHERE trip_id='R1'")
        self.edit("UPDATE stop_times SET arrival_time='09:00:00',departure_time='09:00:00' WHERE trip_id='R1' AND stop_sequence=1")
        self.edit("UPDATE stop_times SET arrival_time='09:05:00',departure_time='09:05:00' WHERE trip_id='R1' AND stop_sequence=2")
        self.edit("INSERT INTO stop_times VALUES ('R1','09:20:00','09:20:00','4',3)")
        with store.connection() as db:
            for access in ({'1':600,'2':120},{'2':120,'1':600}):
                result=planner.journeys(db,'1','4',0,NOW,access_times=access,end_times={'4':0})[0]
                self.assertEqual(result['legs'][0]['origin']['id'],'2')
                self.assertEqual(result['duration_minutes'],80)
            # Uma caminhada menor não deve vencer se o passageiro perder essa partida.
            result=planner.journeys(db,'1','4',0,NOW,access_times={'1':600,'2':4000},end_times={'4':0})[0]
            self.assertEqual(result['legs'][0]['origin']['id'],'1')
