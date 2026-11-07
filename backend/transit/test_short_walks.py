from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch
from django.test import SimpleTestCase
from transit.sptrans import short_walks, staged_materialized as staged, store, graph, journey_completion, transfer_policy


class ShortWalkTests(SimpleTestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        root=Path(folder.name);self.path=root/'staged.sqlite3';source=root/'source.sqlite3';feet=root/'feet.sqlite3'
        self.points={s:{'id':s,'name':s,'lat':-23.55+i*.0001,'lon':-46.63} for i,s in enumerate('ABCDE')}
        with sqlite3.connect(source) as db:
            db.execute('CREATE TABLE stops(stop_id,stop_lat,stop_lon)')
            db.executemany('INSERT INTO stops VALUES(?,?,?)',[(s,p['lat'],p['lon']) for s,p in self.points.items()])
        with sqlite3.connect(feet) as db:
            db.execute('CREATE TABLE walk_edge(origin,destination,distance_meters,seconds,source,status)')
            db.executemany('INSERT INTO walk_edge VALUES(?,?,?,?,?,?)',[
                ('A','B',13.27,10.616,'OSRM foot local','verified'),
                ('B','A',13.27,10.616,'OSRM foot local','verified'),
                ('A','C',300,240,'OSRM foot local','verified'),
                ('A','D',200,160,'OSRM foot local','verified'),
                ('A','E',300.001,240.0008,'OSRM foot local','verified'),
                ('B','E',20,16,'OSRM foot local','unreachable')])
        self.base={'walks':graph.fingerprint(feet),'gtfs':graph.fingerprint(source)}
        with sqlite3.connect(self.path) as db:
            db.executescript('CREATE TABLE metadata(id INTEGER PRIMARY KEY,value);CREATE TABLE stops(id INTEGER PRIMARY KEY,sid TEXT UNIQUE);')
            db.executemany('INSERT INTO stops VALUES(?,?)',enumerate(self.points))
            for table in ('paths','expanded_paths','topup_paths'):
                db.execute(f'CREATE TABLE {table}(origin,destination,data BLOB,PRIMARY KEY(origin,destination)) WITHOUT ROWID')
            db.executemany('INSERT INTO paths VALUES(?,?,?)',[(1,0,bytes([1])),(0,2,bytes([4])),(0,3,bytes([1]))])
            db.execute('INSERT INTO topup_paths VALUES(?,?,?)',(0,3,bytes([5])))
            db.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'signature':self.base,'topup_complete_units':12,'topup_signature':{'kernel':'fixture'}}),))
        self.enterContext(patch.object(staged,'database_path',return_value=self.path))
        self.signature=self.enterContext(patch.object(staged,'signature',return_value=self.base))
        self.enterContext(patch.object(store,'database_path',return_value=source))

    def test_verified_distance_boundary_vacancies_and_idempotence(self):
        with sqlite3.connect(self.path) as db:
            before={t:db.execute(f'SELECT * FROM {t}').fetchall() for t in ('paths','expanded_paths','topup_paths')}
        report=short_walks.build(min_free_gib=0)
        self.assertEqual(report['walking_routes'],3);self.assertEqual(report['new_pairs'],1)
        self.assertEqual(report['pairs_newly_full'],1);self.assertEqual(report['skipped_full_pairs'],1)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT origin,destination FROM short_walk_paths ORDER BY origin,destination').fetchall(),[(0,1),(0,2),(1,0)])
            for table,rows in before.items():self.assertEqual(db.execute(f'SELECT * FROM {table}').fetchall(),rows)
        self.assertEqual(short_walks.build(min_free_gib=0)['walking_routes'],3)
        self.assertIsNone(short_walks.route(self.points['C'],self.points['A']))

    def test_publishes_walking_without_network_or_vehicle(self):
        short_walks.build(min_free_gib=0)
        now=datetime(2026,11,1,12,tzinfo=timezone.utc)
        with patch.object(journey_completion.walking,'route',side_effect=AssertionError('Network not required')):
            journey=journey_completion.direct_walk(self.points['A'],self.points['B'],now)
        self.assertTrue(journey['materialized']);self.assertEqual(journey['legs'],[])
        self.assertEqual(journey['transfer_cost_units'],0);self.assertEqual(journey['duration_seconds'],10.616)
        self.assertEqual(journey['walks'][0]['distance_meters'],13.27)
        self.assertTrue(journey['walks'][0]['geometry_pending'])
        self.assertEqual(journey['walks'][0]['geometry'],[])

    def test_modified_coordinates_and_stale_sources_are_not_reused(self):
        short_walks.build(min_free_gib=0)
        self.assertIsNone(short_walks.route({**self.points['A'],'lat':-23.6},self.points['B']))
        self.assertIsNone(short_walks.route({**self.points['A'],'id':'passenger-location'},self.points['B']))
        self.signature.return_value={'changed':True}
        self.assertIsNone(short_walks.route(self.points['A'],self.points['B']))
        with self.assertRaises(ValueError):short_walks.build(min_free_gib=0)

    def test_disk_guard_leaves_no_partial_publication(self):
        with self.assertRaises(OSError):short_walks.build(min_free_gib=10**9)
        with sqlite3.connect(self.path) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='short_walk_paths'").fetchone())
            self.assertNotIn('short_walk_complete',json.loads(db.execute('SELECT value FROM metadata').fetchone()[0]))

    def test_walking_uses_one_of_the_five_display_slots(self):
        buses=[{'id':str(i),'legs':[{'mode':'bus'}],'duration_minutes':10+i,'walking_meters':0} for i in range(5)]
        foot={'id':'foot','mode':'walk','legs':[],'duration_minutes':4,'walking_meters':300}
        selected,_=transfer_policy.select(buses+[foot])
        self.assertEqual(len(selected),5);self.assertIn('foot',[j['id'] for j in selected])

    def test_combined_stream_counts_foot_in_five_options(self):
        from transit.sptrans import alternatives
        buses=[{'id':str(i),'legs':[{'mode':'bus','code':str(i),'trip_id':str(i),'headsign':'D','geometry':[[0,0],[0,.01]]}],
                'walks':[],'transfers':0,'duration_minutes':10+i,'walking_meters':0} for i in range(5)]
        foot={'id':'foot','mode':'walk','legs':[],'duration_minutes':4,'walking_meters':300}
        with patch.object(journey_completion,'direct_walk',return_value=foot), \
             patch.object(journey_completion.Completion,'improve',side_effect=lambda j:j), \
             patch.object(alternatives,'_multimodal_progressive',return_value=iter([{'journeys':buses,'complete':True}])):
            result=list(alternatives.progressive(None,self.points['A'],self.points['B']))[-1]
        self.assertEqual(len(result['journeys']),5)
        self.assertEqual(result['journeys'][0]['id'],'foot')
