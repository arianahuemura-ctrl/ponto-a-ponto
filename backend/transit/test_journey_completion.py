from datetime import datetime, timezone
import sqlite3
from unittest.mock import patch
from django.test import SimpleTestCase
from transit.sptrans import journey_completion as completion
from transit.sptrans.alternatives import distinct_routes


class CompletionTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 8, 5, tzinfo=timezone.utc)
        self.a = {'id': 'A', 'lat': -23.55, 'lon': -46.65, 'name': 'A'}
        self.b = {**self.a, 'id': 'B', 'lat': -23.551, 'name': 'B'}
        self.path = {'available': True, 'distance_meters': 750, 'geometry': [[-23.55,-46.65],[-23.551,-46.65]]}

    def test_direct_walk_cost_and_contract(self):
        with patch.object(completion.walking, 'route', return_value=self.path):
            result = completion.direct_walk(self.a, self.b, self.now)
        self.assertEqual(result['duration_minutes'], 10)
        self.assertEqual(result['legs'], [])
        self.assertEqual(result['mode'], 'walk')
        self.assertEqual(result['arrival'], '2026-10-08T05:10:00+00:00')
        self.assertEqual(distinct_routes([result]), [result])

    def test_unavailable_or_excessive_walk_is_not_published(self):
        for path in ({'available': False}, {**self.path, 'distance_meters': 999999}):
            with patch.object(completion.walking, 'route', return_value=path):
                self.assertIsNone(completion.direct_walk(self.a, self.b, self.now))

    def test_earlier_alighting_same_trip_and_midnight(self):
        db = sqlite3.connect(':memory:');db.row_factory = sqlite3.Row
        self.addCleanup(db.close)
        db.execute('CREATE TABLE stop_times(trip_id,stop_id,stop_sequence,arrival_time,departure_time,drop_off_type)')
        db.executemany('INSERT INTO stop_times VALUES (?,?,?,?,?,?)', [
            ('t','A',1,'24:00:00','24:00:00','0'),('t','B',2,'24:05:00','24:05:00','0'),
            ('t','C',3,'24:10:00','24:10:00','0')])
        leg = {'trip_id':'t','boarding_index':0,'alighting_index':2,'origin':self.a,
               'destination':{**self.b,'id':'C'},'departure':'2026-10-09T00:00:00+00:00',
               'arrival':'2026-10-09T00:10:00+00:00','ride_minutes':10}
        journey = {'id':'bus','legs':[leg],'walks':[{'accessType':'destination','distance_meters':750}],
                   'duration_minutes':20,'walking_meters':750,'duration_seconds':1200,'egress_seconds':600}
        with patch.object(completion.store,'get_stop',side_effect=lambda db,sid:{**self.b,'id':sid}), patch.object(completion.planner,'leg_shape',return_value=[]), patch.object(completion.Walks,'route',return_value=None):
            result = completion.Completion(db,self.b).improve(journey)
            self.assertEqual(result['legs'][0]['alighting_index'],1)
            self.assertEqual(result['duration_minutes'],5)
            self.assertEqual(result['duration_seconds'],300)
            self.assertEqual(result['walking_meters'],0)
            self.assertEqual(result['arrival'],'2026-10-09T00:05:00+00:00')
            self.assertEqual(journey['legs'][0]['alighting_index'],2)
            db.execute("UPDATE stop_times SET drop_off_type='1' WHERE stop_id='B'")
            self.assertEqual(completion.Completion(db,self.b).improve(journey),journey)

    def test_unavailable_egress_keeps_original(self):
        # A falta de caminho pedestre jamais autoriza um desembarque em linha reta.
        with patch.object(completion.walking,'route',return_value={'available':False}):
            with self.assertRaises(ValueError):
                completion.Walks().route(self.a,self.b,'destination')

    def test_walk_to_destination_removes_unnecessary_second_bus(self):
        first={'destination':self.a,'departure':'2026-10-08T05:00:00+00:00','arrival':'2026-10-08T05:10:00+00:00'}
        second={'destination':self.b,'departure':'2026-10-08T05:25:00+00:00','arrival':'2026-10-08T05:30:00+00:00'}
        journey={'id':'two','legs':[first,second],'transfers':1,'arrival':second['arrival'],'duration_minutes':30,'walking_meters':584,'walks':[{'accessType':'transfer','before_leg':1,'distance_meters':584}]}
        foot={**self.path,'distance_meters':300,'seconds':240,'duration_minutes':4,'accessType':'destination'}
        reviewer=completion.Completion(None,self.b)
        with patch.object(reviewer.walks,'route',return_value=foot):
            result=reviewer.improve(journey)
        self.assertEqual(result['legs'],[first])
        self.assertEqual(result['transfers'],0)
        self.assertEqual(result['arrival'],'2026-10-08T05:14:00+00:00')
        self.assertEqual(result['duration_minutes'],14)
        self.assertEqual(result['walking_meters'],300)
        self.assertEqual(result['walks'],[foot])
        self.assertEqual(result['transfer_walks'],[])
        with patch.object(reviewer.walks,'route',side_effect=ValueError('Sem caminho')):
            self.assertEqual(reviewer._finish_before_transfer(journey),journey)
        with patch.object(reviewer.walks,'route',return_value={**foot,'seconds':1800}):
            self.assertEqual(reviewer._finish_before_transfer(journey),journey)

    def test_short_bus_uses_shape_distance(self):
        self.assertTrue(completion.has_short_bus_leg({'legs':[{'geometry':[[0,0],[0,.004]]}]}))
        self.assertFalse(completion.has_short_bus_leg({'legs':[{'geometry':[[0,0],[0,.006]]}]}))
        self.assertFalse(completion.has_short_bus_leg({'legs':[{'geometry':[]}]}))

    def test_final_walk_accepts_up_to_1500_meters(self):
        reviewer=completion.Completion(None,self.b)
        with patch.object(completion.walking,'route',return_value={**self.path,'distance_meters':1400}):
            self.assertEqual(reviewer.walks.route(self.a,self.b,'destination')['distance_meters'],1400)
        reviewer=completion.Completion(None,self.b)
        with patch.object(completion.walking,'route',return_value={**self.path,'distance_meters':1501}):
            with self.assertRaises(ValueError):reviewer.walks.route(self.a,self.b,'destination')

    def test_access_walk_is_classified_by_sequence_and_keeps_total(self):
        journey={'legs':[{'origin':self.b,'destination':self.a}], 'duration_minutes':25,
                 'walks':[{'origin':self.a,'destination':self.b,'accessType':'transfer','before_leg':0,'distance_meters':675}]}
        result=completion.normalize_walks(journey)
        self.assertEqual(result['walks'][0]['accessType'],'boarding')
        self.assertEqual(result['walks'][0]['duration_minutes'],9)
        self.assertEqual(result['duration_minutes'],25)
        self.assertEqual(result['transfer_walks'],[])

    def test_final_walk_is_not_access_walk(self):
        journey={'legs':[{'origin':self.a,'destination':self.b}],
                 'walks':[{'origin':self.b,'destination':self.a,'accessType':'transfer','before_leg':1,'distance_meters':675}]}
        result=completion.normalize_walks(journey)
        self.assertEqual(result['walks'][0]['accessType'],'destination')
        self.assertEqual(result['walks'][0]['duration_minutes'],9)

    def test_progressive_removes_bus_dominated_by_verified_direct_walk(self):
        from transit.sptrans import alternatives
        foot={'id':'foot','legs':[], 'duration_minutes':10.8,'walking_meters':813}
        bus={'id':'backtrack','legs':[{'code':'8700-10','trip_id':'t','headsign':'Centro','geometry':[[0,0],[0,.01]]}],
             'transfers':0,'walks':[],'duration_minutes':25.3,'walking_meters':1302}
        cases=[(foot,bus,False),
               (None,bus,True),
               (foot,{**bus,'walking_meters':300},True),
               (foot,{**bus,'duration_minutes':8},True)]
        for direct, candidate, keep in cases:
            with self.subTest(direct=direct,bus=candidate), \
                 patch.object(completion,'direct_walk',return_value=direct), \
                 patch.object(completion.Completion,'improve',side_effect=lambda j:j), \
                 patch.object(alternatives,'_bus_progressive',return_value=iter([
                     {'journeys':[candidate],'planner':'raptor','complete':False},
                     {'journeys':[candidate],'planner':'raptor','complete':True}])):
                results=list(alternatives.progressive(None,self.a,self.b,now=self.now))
            for result in results:
                self.assertEqual(any(j['id']=='backtrack' for j in result['journeys']),keep)
                self.assertEqual(any(j['id']=='foot' for j in result['journeys']),bool(direct))

    def test_short_verified_walk_skips_raptor_but_keeps_connections_search(self):
        from transit.sptrans import alternatives, connection_adapter
        for selected in ('connections','raptor'):
            for meters in (813,999,1000,1001,None):
                foot=None if meters is None else {'id':'foot','legs':[], 'duration_minutes':15,'walking_meters':meters}
                with self.subTest(selected=selected,meters=meters), self.settings(SPTRANS_PLANNER=selected), \
                     patch.object(completion,'direct_walk',return_value=foot), \
                     patch.object(connection_adapter,'prepare',return_value=None) as prepare, \
                     patch.object(alternatives,'_raptor_progressive',return_value=iter([{'journeys':[],'complete':True}])) as raptor:
                    result=list(alternatives.progressive(None,self.a,self.b,now=self.now))[-1]
                    self.assertEqual(raptor.called,meters is None or meters>=1000)
                    self.assertEqual(prepare.called,selected=='connections')
                    self.assertTrue(result['complete'])
                    self.assertEqual(result['journeys'],[foot] if foot else [])
