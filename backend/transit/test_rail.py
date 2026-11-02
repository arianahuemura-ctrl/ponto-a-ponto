import csv
import math
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, override_settings
from transit.sptrans import rail, planner, store, alternatives
from transit.sptrans.journey_completion import normalize_walks

TZ = ZoneInfo('America/Sao_Paulo')
NOW = datetime(2026, 11, 2, 8, tzinfo=TZ)


class RailTimingTests(SimpleTestCase):
    def test_short_segment_has_triangular_motion_and_conserves_distance(self):
        parts = rail.motion(100, 1, 1, 80)
        self.assertEqual(parts['cruise_seconds'], 0)
        self.assertEqual(parts['acceleration_seconds'], 10)
        self.assertEqual(parts['braking_seconds'], 10)
        self.assertEqual(parts['peak_speed_kmh'], 36)

    def test_long_segment_has_cruise_and_respects_speed_ceiling(self):
        parts = rail.motion(1000, 1, 1, 72)
        self.assertEqual(parts['acceleration_seconds'], 20)
        self.assertEqual(parts['braking_seconds'], 20)
        self.assertEqual(parts['cruise_seconds'], 30)
        for bad in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError): rail.motion(bad, 1, 1, 80)

    @patch('transit.sptrans.geometry.leg_shape', return_value=[(-23.5,-46.6),(-23.501,-46.6)])
    def test_dwell_is_not_added_twice_to_aggregate_gtfs(self, shape):
        trip = {'route_id':'L2', 'route_type':'1','trip_id':'T',
                'times':[('a',0,0),('b',180,180),('c',360,360)]}
        rail.prepare_timing(trip)
        self.assertEqual(trip['times'][-1][1], 360)
        self.assertEqual(trip['times'][1][2]-trip['times'][1][1],30)
        detail = rail.timing_detail(trip,0,2)
        self.assertEqual(detail['station_dwell_seconds'],30)
        self.assertEqual(detail['running_seconds']+detail['station_dwell_seconds'],360)
        self.assertAlmostEqual(sum(detail[k] for k in ('acceleration_seconds','cruise_seconds','braking_seconds','operating_margin_seconds','station_dwell_seconds')),360)

    @patch('transit.sptrans.geometry.leg_shape', return_value=[(-23.5,-46.6),(-23.51,-46.6)])
    def test_physics_rejects_impossibly_short_programmed_duration(self, shape):
        trip = {'route_id':'C11','route_type':'2','trip_id':'T','times':[('a',0,0),('b',1,1)]}
        rail.prepare_timing(trip)
        self.assertGreater(trip['times'][-1][1],40)
        self.assertEqual(rail.timing_detail(trip,0,1)['operating_margin_seconds'],0)

    @patch('transit.sptrans.geometry.leg_shape', return_value=[])
    def test_missing_shape_keeps_schedule_without_claiming_motion(self, shape):
        trip = {'route_id':'L2','route_type':'1','trip_id':'T','times':[('a',0,0),('b',180,210),('c',390,390)]}
        rail.prepare_timing(trip)
        self.assertEqual(trip['times'][-1][1],390)
        detail=rail.timing_detail(trip,0,2)
        self.assertFalse(detail['motion_available'])
        self.assertEqual(detail['station_dwell_seconds'],30)

    def test_opening_headway_and_sunday_closure(self):
        trip={'route_type':'1','route_id':'METRÔ L2','times':[('a',0,0)]}
        base=NOW.replace(hour=0).timestamp()
        windows=rail.boarding_windows(trip,0,[(base,base+86400,240,False)],TZ)
        departure=planner.next_departure(trip,0,base+3600,windows)
        self.assertEqual(datetime.fromtimestamp(departure,TZ).strftime('%H:%M'),'04:42')
        self.assertFalse(rail.departure_allowed(trip,base+60,TZ))
        trip['route_id']='METRÔ17A'
        sunday=NOW.replace(day=1,hour=0).timestamp()
        self.assertEqual(rail.boarding_windows(trip,0,[(sunday,sunday+86400,540,False)],TZ),[])
        self.assertFalse(rail.departure_allowed(trip,base+22*3600,TZ))

    def test_clipping_opening_preserves_exact_departure_phase(self):
        trip={'route_type':'1','route_id':'METRÔ L2','times':[('a',0,0)]}
        base=NOW.replace(hour=0).timestamp()
        windows=rail.boarding_windows(trip,0,[(base+4*3600+180,base+86400,600,True)],TZ)
        departure=planner.next_departure(trip,0,base+3600,windows)
        self.assertEqual(datetime.fromtimestamp(departure,TZ).strftime('%H:%M'),'04:43')


class MultimodalTests(SimpleTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        rows={table:[] for table in store.TABLES}
        rows['stops']=[[sid,name,'',lat,-46.6] for sid,name,lat in
            [('a','Origem',-23.50),('18850','Consolação',-23.51),('2600672','Paulista',-23.511),('b','Butantã',-23.55),('c','Destino ônibus',-23.60)]]
        rows['calendar']=[['daily',1,1,1,1,1,1,1,'20260101','20261231']]
        for code,kind,stops in [('L2','1',['a','18850']),('L4','1',['2600672','b']),('BUS','3',['b','c']),('DIRECT','3',['a','c'])]:
            rows['routes'].append([code,'1',code,code,kind,'008800'])
            rows['trips'].append([code,'daily',code,'Destino','0','S'])
            end='09:00:00' if code=='DIRECT' else '07:10:00'
            rows['stop_times'].extend([[code,'07:00:00','07:00:00',stops[0],1],[code,end,end,stops[1],2]])
            rows['frequencies'].append([code,'04:00:00','24:00:00',240,'0'])
        for table,columns in store.TABLES.items():
            with (root/(table+'.txt')).open('w') as f:
                writer=csv.writer(f);writer.writerow(columns);writer.writerows(rows[table])
        self.path=root/'network.sqlite3';store.import_gtfs(root,self.path)
        self.override=override_settings(SPTRANS_DATABASE=self.path,SPTRANS_TOKEN='',SPTRANS_PLANNER='raptor')
        self.override.enable();self.addCleanup(self.override.disable)
        planner._network.cache_clear();planner._nearby.cache_clear()

    def test_bus_metro_connection_preserves_slower_direct_choice(self):
        with store.connection() as db:
            stops={r['stop_id']:store.stop(r) for r in db.execute('SELECT * FROM stops')}
            paths=rail.internal_transfers(stops)
            result=planner.journeys(db,'a','c',2,NOW,transfer_paths=paths,known_transfers_only=True,include_rail=True,preserve_alternatives=True)
        self.assertEqual([l['mode'] for l in result[0]['legs']],['metro','metro','bus'])
        self.assertTrue(any([l['code'] for l in j['legs']]==['DIRECT'] for j in result))
        self.assertEqual(result[0]['duration_minutes'],42)
        walk=result[0]['transfer_walks'][0]
        self.assertTrue(walk['internal_transfer']);self.assertEqual(walk['geometry'],[])
        normalized=normalize_walks({**result[0],'walks':[walk]})
        self.assertEqual(normalized['walking_minutes'],2)
        for journey in result:
            codes=[l['code'] for l in journey['legs']]
            self.assertTrue(all(a!=b for a,b in zip(codes,codes[1:])))

    def test_station_catalogue_and_trip_never_call_bus_live_api(self):
        with patch('transit.sptrans.views.realtime.add_predictions') as predictions, patch('transit.sptrans.views.realtime.positions') as positions, patch('transit.sptrans.store.timezone.localtime',return_value=NOW):
            board=self.client.get('/api/sptrans/board/',{'origin':'2600672'}).json()
            response=self.client.get('/api/sptrans/trips/L4/',{'origin':'2600672'})
        self.assertEqual(board['lines'][0]['mode'],'metro')
        self.assertEqual(response.status_code,200)
        predictions.assert_not_called();positions.assert_not_called()
        with store.connection() as db:
            self.assertEqual(store.search(db,'Paulista')[0]['mode'],'metro')

    def test_nonstream_board_supports_internal_interchange(self):
        with patch('transit.sptrans.planner.timezone.localtime',return_value=NOW):
            data=self.client.get('/api/sptrans/board/',{'origin':'a','destination':'b','route_only':'1'}).json()
        self.assertEqual([l['mode'] for l in data['lines']],['metro','metro'])
        self.assertTrue(data['journeys'][0]['legs'][0]['timing_detail']['estimated'])

    def test_green_yellow_interchange_in_first_snapshot_in_both_directions(self):
        with sqlite3.connect(self.path) as db:
            for code,a,b in [('L4','b','2600672'),('L2','18850','a')]:
                identifier=code+'-reverse'
                db.execute('INSERT INTO trips VALUES (?,?,?,?,?,?)',(code,'daily',identifier,'Volta','1','S'))
                db.executemany('INSERT INTO stop_times VALUES (?,?,?,?,?)',[(identifier,'07:00:00','07:00:00',a,1),(identifier,'07:10:00','07:10:00',b,2)])
                db.execute('INSERT INTO frequencies VALUES (?,?,?,?,?)',(identifier,'04:00:00','24:00:00',240,'0'))
        planner._network.cache_clear()
        with store.connection() as db, patch('transit.sptrans.walking.route') as walking:
            for a,b,codes in [('a','b',['L2','L4']),('b','a',['L4','L2'])]:
                stream=alternatives._raptor_progressive(db,store.get_stop(db,a),store.get_stop(db,b),1,NOW,refresh=True,include_rail=True)
                try:snapshot=next(stream)
                finally:stream.close()
                journey=snapshot['journeys'][0]
                self.assertEqual([l['code'] for l in journey['legs']],codes)
                self.assertEqual(journey['transfers'],1)
                self.assertEqual(journey['duration_minutes'],28)
                self.assertEqual(journey['walking_minutes'],2)
                self.assertTrue(journey['walks'][0]['internal_transfer'])
            walking.assert_not_called()

    def test_train_mode_uses_rail_parameters_and_can_connect_to_bus(self):
        with sqlite3.connect(self.path) as db:db.execute("UPDATE routes SET route_type='2' WHERE route_id='L4'")
        planner._network.cache_clear()
        with store.connection() as db:
            journeys=planner.journeys(db,'2600672','c',1,NOW,include_rail=True)
        self.assertEqual([l['mode'] for l in journeys[0]['legs']],['rail','bus'])
        self.assertEqual(journeys[0]['legs'][0]['timing_detail']['parameters']['acceleration_m_s2'],.9)

    def test_internal_access_before_first_train_does_not_require_a_bus(self):
        with store.connection() as db:
            stops={r['stop_id']:store.stop(r) for r in db.execute('SELECT * FROM stops')}
            journeys=planner.journeys(db,'18850','b',0,NOW,include_rail=True,transfer_paths=rail.internal_transfers(stops),known_transfers_only=True)
        self.assertEqual([l['code'] for l in journeys[0]['legs']],['L4'])
        self.assertEqual(journeys[0]['access_stop_id'],'18850')
        self.assertEqual(journeys[0]['transfer_walks'][0]['accessType'],'boarding')
        self.assertEqual(journeys[0]['duration_minutes'],14)

    def test_unverified_access_does_not_hide_validated_rail_connection(self):
        with store.connection() as db:
            a,b,interchange=(store.get_stop(db,sid) for sid in ('a','b','18850'))
            origin={**a,'id':'passenger-location'}
            foot={'pending':True,'origin':origin,'destination':a,'distance_meters':10}
            shortcut={'pending':True,'origin':origin,'destination':interchange,'distance_meters':11}
            def access(db,anchor,outgoing,**kwargs):
                return ([(a,foot),(interchange,shortcut)] if outgoing else [(b,None)]),False
            def walk(start,end,**kwargs):
                if end['id']!='a':return {'available':False}
                return {'available':True,'origin':start,'destination':end,'distance_meters':100,'geometry':[[a['lat'],a['lon']],[a['lat']+.001,a['lon']]]}
            with patch.object(alternatives,'access_points',side_effect=access),patch('transit.sptrans.walking.route',side_effect=walk):
                results=list(alternatives._raptor_progressive(db,origin,b,2,NOW,refresh=True,include_rail=True))
        self.assertTrue(any([l['code'] for l in journey['legs']]==['L2','L4'] for result in results for journey in result['journeys']))

    def test_progressive_preserves_modes_and_finishes_after_both_sources(self):
        def source(code,mode):
            journey={'id':code,'legs':[{'route_id':code,'code':code,'trip_id':code,'headsign':'Destino','mode':mode}], 'duration_minutes':10,'walking_meters':0,'transfers':0}
            yield {'journeys':[journey],'complete':False}
            yield {'journeys':[journey],'complete':True}
        with store.connection() as db, patch.object(alternatives,'_bus_progressive',return_value=source('BUS','bus')), patch.object(alternatives,'_raptor_progressive',return_value=source('L2','metro')):
            results=list(alternatives._multimodal_progressive(db,{}, {},2,NOW))
        self.assertFalse(any(r['complete'] for r in results[:-1]))
        self.assertTrue(results[-1]['complete'])
        self.assertEqual({j['id'] for j in results[-1]['journeys']},{'BUS','L2'})
