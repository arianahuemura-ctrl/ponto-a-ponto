import csv
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from django.test import SimpleTestCase, override_settings
from django.core.cache import cache
from transit.sptrans import store, realtime, directions, viewport
from transit.sptrans.client import OlhoVivo, APIError

NOW=datetime(2026,10,6,8,tzinfo=ZoneInfo('America/Sao_Paulo'))

class GTFSCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        rows={
          'stops':[['1','Origem','',-23.5,-46.6],['2','Destino','',-23.51,-46.6],['3','Depois','',-23.52,-46.6]],
          'routes':[['R','1','1000-10','Linha','3','005cec']],
          'trips':[['R','daily','T','Destino','0','S'],['R','daily','BACK','Origem','1','S']],
          'stop_times':[['T','07:00:00','07:00:00','1',1],['T','07:10:00','07:10:00','2',2],['T','07:20:00','07:20:00','3',3],['BACK','07:00:00','07:00:00','3',1],['BACK','07:10:00','07:10:00','2',2],['BACK','07:20:00','07:20:00','1',3]],
          'frequencies':[['T','07:00:00','26:00:00',600,'0'],['BACK','07:00:00','23:00:00',900,'0']],
          'calendar':[['daily',1,1,1,1,1,1,1,'20260101','20261231']],
          'calendar_dates':[], 'shapes':[['S',-23.5,-46.6,1],['S',-23.51,-46.6,2]]
        }
        for table,columns in store.TABLES.items():
            with (cls.root/(table+'.txt')).open('w') as f:
                writer=csv.writer(f);writer.writerow(columns);writer.writerows(rows[table])
        cls.path=cls.root/'test.sqlite3'
        store.import_gtfs(cls.root,cls.path)
        cls.settings=override_settings(SPTRANS_DATABASE=cls.path,SPTRANS_TOKEN='')
        cls.settings.enable()
    @classmethod
    def tearDownClass(cls):
        cls.settings.disable();cls.temp.cleanup();super().tearDownClass()
    def setUp(self): cache.clear()

    @patch('transit.sptrans.directions.tangent',return_value=None)
    def test_missing_shape_uses_stop_sequence_and_labels_terminal(self, tangent):
        with store.connection() as db:
            stops=[store.get_stop(db,'1'),store.get_stop(db,'3')]
            directions.enrich(db,stops)
        departure=next(d for d in stops[0]['directions'] if d['headsign']=='Destino')
        self.assertEqual(departure['bearing'],180)
        self.assertEqual(departure['kind'],'departure')
        self.assertTrue(departure['approximate'])
        arrival=next(d for d in stops[1]['directions'] if d['headsign']=='Destino')
        self.assertEqual(arrival['bearing'],180)
        self.assertEqual(arrival['kind'],'arrival')
        self.assertTrue(arrival['approximate'])
        self.assertEqual(stops[1]['direction_status'],'available')

    def test_address_destination_selects_nearest_bus_stop(self):
        response=self.client.get('/api/sptrans/destination/',{'lat':-23.5099,'lon':-46.6})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['stop']['id'],'2')
        self.assertLess(response.json()['distance_meters'],15)
        self.assertEqual(response.json()['distance_type'],'straight_line')

    def test_address_outside_coverage_and_invalid_coordinates(self):
        response=self.client.get('/api/sptrans/destination/',{'lat':0,'lon':0})
        self.assertIsNone(response.json()['stop'])
        for lat in ('nan','inf','91','bad'):
            self.assertEqual(self.client.get('/api/sptrans/destination/',{'lat':lat,'lon':-46.6}).status_code,400)

    def test_viewport_excludes_outside_stops_and_includes_edges(self):
        response=self.client.get('/api/sptrans/stops/',{'south':-23.51,'north':-23.5,'west':-46.61,'east':-46.59})
        self.assertEqual(response.status_code,200)
        self.assertEqual({s['id'] for s in response.json()['stops']},{'1','2'})
        self.assertIsNone(response.json()['limit'])
        for bounds in ({'south':0},{'south':1,'north':0,'west':0,'east':1},{'south':'nan','north':0,'west':0,'east':1}):
            self.assertEqual(self.client.get('/api/sptrans/stops/',bounds).status_code,400)

    def test_viewport_is_not_limited_to_eighty_stops(self):
        import sqlite3
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        self.addCleanup(db.close)
        with store.connection() as source: source.backup(db)
        for i in range(100):
            identifier=str(1000+i)
            db.execute('INSERT INTO stops VALUES (?,?,?,?,?)',(identifier,'Extra','',-23.505,-46.6))
            db.execute('INSERT INTO stop_times VALUES (?,?,?,?,?)',('T','08:00:00','08:00:00',identifier,100+i))
        self.assertEqual(len(store.in_bounds(db,-23.51,-46.61,-23.5,-46.59)),102)

    def test_viewport_batches_are_center_first_and_cache_avoids_sql(self):
        viewport._snapshots.clear()
        with store.connection() as db:
            args=(-23.53,-46.61,-23.49,-46.59,-23.5199,-46.6)
            first=viewport.page(db,*args,0,1)
            self.assertEqual(first['stops'][0]['id'],'3')
            self.assertEqual(first['next_offset'],1)
            second=viewport.page(db,*args,1,1)
            third=viewport.page(db,*args,2,1)
            self.assertEqual([second['stops'][0]['id'],third['stops'][0]['id']],['2','1'])
            self.assertIsNone(third['next_offset'])
            queries=[];db.set_trace_callback(queries.append)
            self.assertEqual(viewport.page(db,*args,0,1),first)
            self.assertEqual(queries,[])

    def test_viewport_cache_invalidates_after_database_revision_changes(self):
        viewport._snapshots.clear()
        args=(-23.53,-46.61,-23.49,-46.59,-23.51,-46.6)
        with store.connection() as db:
            before=viewport.page(db,*args,0,1)
            with patch('transit.sptrans.viewport.revision',return_value='new-import'):
                queries=[];db.set_trace_callback(queries.append)
                after=viewport.page(db,*args,0,1)
                self.assertNotEqual(before['revision'],after['revision'])
                self.assertTrue(queries)

    def test_viewport_rejects_invalid_pagination(self):
        params={'south':-23.53,'north':-23.49,'west':-46.61,'east':-46.59}
        for paging in ({'offset':-1},{'batch_size':0},{'batch_size':201},{'offset':'bad'}):
            self.assertEqual(self.client.get('/api/sptrans/stops/',{**params,**paging}).status_code,400)

    def test_direction_and_sequence(self):
        with store.connection() as db:
            self.assertEqual([r['trip_id'] for r in store.alternatives(db,'1','2',NOW)],['T'])
            self.assertEqual([r['trip_id'] for r in store.alternatives(db,'2','1',NOW)],['BACK'])
            self.assertEqual(store.alternatives(db,'1','1',NOW),[])
    def test_midnight_uses_previous_service_day(self):
        with store.connection() as db:
            rows=store.alternatives(db,'1','2',NOW.replace(hour=1))
            self.assertEqual(rows[0]['programme'][0]['start'],'2026-10-05T07:00:00-03:00')
            self.assertEqual(rows[0]['programme'][0]['kind'],'frequency')
            self.assertEqual(rows[0]['programme'][0]['interval_minutes'],10)
    def test_expired_calendar_not_presented_as_current(self):
        with store.connection() as db: self.assertEqual(store.alternatives(db,'1','2',NOW.replace(year=2028)),[])
    def test_board_falls_back_without_fake_arrivals(self):
        with patch('transit.sptrans.store.timezone.localtime',return_value=NOW):
            response=self.client.get('/api/sptrans/board/',{'origin':'1','destination':'2'})
        self.assertEqual(response.status_code,200)
        self.assertIn('Token',response.json()['warning'])
        self.assertEqual(response.json()['lines'][0]['arrivals'],[])
    def test_validation_and_search(self):
        self.assertEqual(self.client.get('/api/sptrans/stops/',{'lat':'nan'}).status_code,400)
        self.assertEqual(self.client.get('/api/sptrans/board/',{'origin':"' OR 1=1"}).status_code,400)
        response=self.client.get('/api/sptrans/stops/',{'q':'Destino'})
        self.assertEqual(response.json()['stops'][0]['id'],'2')
    def test_old_url_is_removed(self):
        response=self.client.get('/sao-paulo/?stop=1206717')
        self.assertEqual(response.status_code,404)

    @override_settings(PUBLIC_BASE_URL='https://pap.example')
    def test_qr_uses_root_url(self):
        response=self.client.get('/api/sptrans/qr/1/',{'format':'json'})
        self.assertEqual(response.json()['url'],'https://pap.example/?stop=1')

    def test_route_and_qr(self):
        result=self.client.get('/api/sptrans/trips/T/').json()
        self.assertEqual([s['id'] for s in result['stops']],['1','2','3'])
        self.assertEqual(len(result['shape']),2)
        self.assertEqual(self.client.get('/api/sptrans/qr/1/').status_code,200)
    def test_failed_import_preserves_existing_index(self):
        original=self.path.read_bytes()
        with self.assertRaises(FileNotFoundError): store.import_gtfs(self.root/'missing',self.path)
        self.assertEqual(self.path.read_bytes(),original)

class APICase(SimpleTestCase):
    def setUp(self): cache.clear()
    @override_settings(SPTRANS_TOKEN='test-secret')
    def test_authentication_cookie_client_and_cache(self):
        client=OlhoVivo()
        with patch.object(client,'_request',side_effect=[True,{'vs':[]}]) as request:
            self.assertEqual(client.get('Posicao/Linha',{'codigoLinha':1}),{'vs':[]})
            client.get('Posicao/Linha',{'codigoLinha':1})
            self.assertEqual(request.call_count,2)
    @override_settings(SPTRANS_TOKEN='test-secret')
    def test_auth_failure_does_not_leak_secret(self):
        client=OlhoVivo()
        with patch.object(client,'_request',return_value=False):
            with self.assertRaises(APIError) as caught:client.get('Posicao')
        self.assertNotIn('test-secret',str(caught.exception))
    def test_mapping_uses_terminal_not_direction_number(self):
        with patch.object(realtime.client,'get',return_value=[{'lt':'1000','tl':10,'sl':2,'ts':'Destino','tp':'Origem','cl':44}]):
            self.assertEqual(realtime.line_mapping({'code':'1000-10','headsign':'Destino','direction':'0'})['cl'],44)
    def test_ambiguous_stop_is_not_guessed(self):
        with patch.object(realtime.client,'get',return_value=[{'cp':100,'py':-23.5,'px':-46.6},{'cp':101,'py':-23.5,'px':-46.6}]):
            self.assertIsNone(realtime.stop_mapping({'id':'1','lat':-23.5,'lon':-46.6},{'cl':1}))
    def test_old_positions_are_not_shown_as_live(self):
        with patch.object(realtime,'line_mapping',return_value={'cl':1}),patch.object(realtime.client,'get',return_value={'vs':[{'p':'bus','ta':'2020-01-01T00:00:00Z','py':-23.5,'px':-46.6}]}):
            self.assertEqual(realtime.positions({'code':'1000-10'})[0],[])
    @override_settings(SPTRANS_TOKEN='test-secret')
    def test_expired_cookie_reauthenticates_once(self):
        from urllib.error import HTTPError
        client=OlhoVivo()
        with patch.object(client,'_request',side_effect=[True,HTTPError('https://example.invalid',401,'Unauthorized',{},None),True,{'vs':[]}]) as request:
            self.assertEqual(client.get('Posicao/Linha',{'codigoLinha':99}),{'vs':[]})
            self.assertEqual(request.call_count,4)
    def test_predictions_are_ordered_across_midnight_and_old_data_discarded(self):
        from django.utils import timezone
        now=timezone.now()
        row={'code':'1000-10','headsign':'Destino','arrivals':[]}
        payload={'hr':'23:58','p':{'l':[{'cl':1,'vs':[
            {'p':2,'t':'00:03','ta':now.isoformat()},
            {'p':1,'t':'23:59','ta':now.isoformat()},
            {'p':3,'t':'00:02','ta':'2020-01-01T00:00:00Z'},
        ]}]}}
        with patch.object(realtime,'line_mapping',return_value={'cl':1}),patch.object(realtime,'stop_mapping',return_value={'cp':2}),patch.object(realtime.client,'get',return_value=payload):
            realtime.add_predictions(row,{'id':'1'})
        self.assertEqual([a['vehicle'] for a in row['arrivals']],['1','2'])
