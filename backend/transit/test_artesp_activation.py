from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import tempfile
from threading import Barrier
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, override_settings
from transit.sptrans import store, supplementary, staged_adapter, realtime


class SupplementarySourceTests(SimpleTestCase):
    def test_sources_remain_isolated_across_parallel_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory)/name for name in ('combined.sqlite3','original.sqlite3')]
            for path in paths:
                with sqlite3.connect(path) as db:
                    db.execute('CREATE TABLE stops(stop_id TEXT)')
                    db.executemany('INSERT INTO stops VALUES(?)', [('A',),('B',)])
            barrier = Barrier(2)
            def read(db, *args):
                barrier.wait(timeout=5)
                actual = Path(db.execute('PRAGMA database_list').fetchone()[2])
                self.assertEqual(actual, store.database_path())
                yield {'journeys':[{'id':actual.name}], 'complete':True}
            def query(path):
                result=list(supplementary.progressive(path, {'id':'A'}, {'id':'B'}, 4, None))
                self.assertEqual(store.database_path(), paths[0])
                return result[0]['journeys'][0]['id']
            with override_settings(SPTRANS_DATABASE=paths[0]), patch.object(staged_adapter,'progressive',read):
                with ThreadPoolExecutor(2) as pool:
                    futures=[pool.submit(query,path) for path in paths]
                    self.assertEqual([f.result() for f in futures],[p.name for p in paths])
                self.assertEqual(store.database_path(),paths[0])

    def test_missing_artesp_endpoint_does_not_use_numeric_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'old.sqlite3'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE stops(stop_id TEXT)')
                db.execute("INSERT INTO stops VALUES('123')")
            with patch.object(staged_adapter,'progressive') as reader:
                rows=list(supplementary.progressive(path,{'id':'artesp:123'},{'id':'123'},4,None))
            reader.assert_not_called()
            self.assertEqual(rows,[{'journeys':[],'complete':True}])

    def test_context_restored_after_failure(self):
        original=store.database_path()
        with self.assertRaises(RuntimeError):
            with store.using_database('/tmp/fixture.sqlite3'):
                raise RuntimeError('fixture')
        self.assertEqual(store.database_path(),original)


class ArtespPassengerTests(SimpleTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'network.sqlite3'
        with sqlite3.connect(path) as db:
            for table,columns in store.TABLES.items():
                db.execute('CREATE TABLE '+table+' ('+','.join(c+(' REAL' if c in store.NUMERIC else ' TEXT') for c in columns)+')')
            db.executemany('INSERT INTO stops VALUES(?,?,?,?,?)',[
                ('artesp:1','Mauá','',-23.668,-46.461),('artesp:2','Destino','',-23.67,-46.46)])
            db.execute("INSERT INTO routes VALUES('artesp:158','artesp:A','158','Mauá - Sacomã','3','005cec')")
            db.execute("INSERT INTO trips VALUES('artesp:158','artesp:WD','artesp:EARLY','Sacomã','0','artesp:S')")
            db.execute("INSERT INTO trips VALUES('artesp:158','artesp:WD','artesp:T','Sacomã','0','artesp:S')")
            db.executemany('INSERT INTO stop_times VALUES(?,?,?,?,?)',[
                ('artesp:EARLY','07:00:00','07:00:00','artesp:1',1),('artesp:EARLY','07:30:00','07:30:00','artesp:2',2),
                ('artesp:T','09:00:00','09:00:00','artesp:1',1),('artesp:T','09:30:00','09:30:00','artesp:2',2)])
            db.execute("INSERT INTO calendar VALUES('artesp:WD','1','1','1','1','1','0','0','20260101','20261231')")
            db.execute('CREATE TABLE metadata(value TEXT)')
            db.execute('INSERT INTO metadata VALUES(?)',(json.dumps({'counts':{'stops':2}}),))
        override=override_settings(SPTRANS_DATABASE=path,SPTRANS_LEGACY_DATABASE='')
        override.enable();self.addCleanup(override.disable)
        self.now=datetime(2026,11,3,8,tzinfo=ZoneInfo('America/Sao_Paulo'))

    def test_namespaced_stops_visible_in_catalogue_and_viewport(self):
        data=self.client.get('/api/sptrans/stop-catalogue/').json()
        self.assertEqual({r[0] for r in data['rows']},{'artesp:1','artesp:2'})
        response=self.client.get('/api/sptrans/stops/',{'south':-23.68,'north':-23.66,'west':-46.47,'east':-46.45})
        self.assertEqual({s['id'] for s in response.json()['stops']},{'artesp:1','artesp:2'})

    def test_board_and_trip_use_schedules_without_sptrans_network_calls(self):
        with patch('transit.sptrans.store.timezone.localtime',return_value=self.now), \
             patch.object(realtime.client,'get',side_effect=AssertionError('ARTESP must not query SPTrans')):
            response=self.client.get('/api/sptrans/board/',{'origin':'artesp:1'})
            self.assertEqual(response.status_code,200)
            line=response.json()['lines'][0]
            self.assertEqual(line['trip_id'],'artesp:T')
            self.assertEqual(line['programme'][0]['kind'],'scheduled')
            self.assertEqual(line['programme'][0]['start'],'2026-11-03T09:00:00-03:00')
            self.assertIn('ARTESP',line['realtime_status'])
            response=self.client.get('/api/sptrans/trips/artesp:T/',{'origin':'artesp:1'})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['vehicles'],[])
            self.assertIn('ARTESP',response.json()['vehicle_status'])

    def test_artesp_identity_blocks_even_colliding_sptrans_line_code(self):
        line={'trip_id':'artesp:T','code':'1000-10','headsign':'Destino','arrivals':[]}
        with patch.object(realtime.client,'get',side_effect=AssertionError('network')):
            self.assertIsNone(realtime.line_mapping(line))
            realtime.add_predictions(line,{'id':'1'})
            self.assertEqual(realtime.positions(line)[0],[])
