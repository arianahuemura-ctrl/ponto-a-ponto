import json
import sqlite3
from unittest.mock import patch
from django.test import SimpleTestCase
from transit import test_sptrans_graph as fixtures
from transit.sptrans import direct, graph


class DirectIndexTests(SimpleTestCase):
    def setUp(self):
        fixtures.GraphTests.setUp(self)
        self.direct_path=self.root/'direct.sqlite3'
        self.report=direct.build(source=self.index,target=self.direct_path)

    def lookup(self,point,**kw):
        return direct.lookup(point,path=self.direct_path,**kw)

    def test_reverse_is_same_edge_not_wrong_way_bus(self):
        forward=self.lookup('A',other='B')['connections']
        reverse=self.lookup('B',reverse=True,other='A')['connections']
        self.assertEqual(forward,reverse)
        self.assertEqual(forward[0]['origin'],'A');self.assertEqual(forward[0]['destination'],'B')
        self.assertEqual(self.lookup('B',other='A')['connections'],[])
        self.assertEqual(self.lookup('A',reverse=True,other='B')['connections'],[])

    def test_meets_correct_direction_at_intermediate_stop(self):
        found=direct.transfers('A','C',path=self.direct_path)
        self.assertTrue(found['complete']);self.assertTrue(found['structural_only'])
        self.assertEqual(len(found['candidates']),1)
        candidate=found['candidates'][0]
        self.assertEqual(candidate['transfer_stop'],'B')
        self.assertEqual([(l['origin'],l['destination']) for l in candidate['legs']],[('A','B'),('B','C')])
        self.assertEqual([l['code'] for l in candidate['legs']],['R1','R2'])
        self.assertEqual(candidate['distance_meters'],sum(l['distance_meters'] for l in candidate['legs']))
        self.assertEqual(direct.transfers('C','A',path=self.direct_path)['candidates'],[])

    def test_indexed_access_in_both_directions(self):
        with direct.connection(self.direct_path) as db:
            for column,index in [('origin','direct_out'),('destination','direct_in')]:
                plan=db.execute(f'SELECT 1 FROM ride_edge INDEXED BY {index} WHERE {column}=?',('A',)).fetchall()
                explain=db.execute(f'EXPLAIN QUERY PLAN SELECT * FROM ride_edge INDEXED BY {index} WHERE {column}=?',('A',)).fetchall()
                self.assertTrue(any(index in r[3] and 'SEARCH' in r[3] for r in explain))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM direct_reverse').fetchone()[0],self.report['edges'])
            reverse=db.execute("SELECT origin,destination,search_from,search_to FROM direct_reverse WHERE search_from='B' AND search_to='A'").fetchone()
            self.assertEqual(tuple(reverse),('A','B','B','A'))

    def test_full_direction_and_distance_equality_with_original(self):
        with graph.connection(self.index) as old,direct.connection(self.direct_path) as new:
            columns='origin,destination,pattern_id,boarding_index,alighting_index,distance_meters,min_ride_seconds'
            old_rows=[tuple(r) for r in old.execute('SELECT '+columns+' FROM ride_edge ORDER BY pattern_id,boarding_index,alighting_index')]
            new_rows=[tuple(r) for r in new.execute('SELECT '+columns+' FROM ride_edge ORDER BY pattern_id,boarding_index,alighting_index')]
            self.assertEqual(old_rows,new_rows)
            self.assertEqual(new.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_no_top16_loss_in_search_index(self):
        with sqlite3.connect(self.source) as db:
            for i in range(20):
                tid='VARIANT'+str(i)
                db.execute('INSERT INTO trips VALUES (?,?,?,?,?,?)',('DIRECT','daily',tid,str(i),'0','DIRECT'))
                db.executemany('INSERT INTO stop_times VALUES (?,?,?,?,?)',[(tid,'08:00:00','08:00:00','A',1),(tid,'09:00:00','09:00:00','D',2)])
        graph.build(source=self.source,target=self.index)
        direct.build(source=self.index,target=self.direct_path)
        result=self.lookup('D',reverse=True,other='A',limit=100)
        self.assertEqual(len(result['connections']),21)
        limited=self.lookup('A',other='D',limit=16)
        self.assertEqual(len(limited['connections']),16);self.assertTrue(limited['has_more'])

    def test_all_later_stops_only(self):
        with sqlite3.connect(self.source) as db:
            db.execute("DELETE FROM stop_times WHERE trip_id='DIRECT'")
            for i,sid in enumerate(['A','B','C','D']):
                stamp=f'08:{i*10:02d}:00'
                db.execute('INSERT INTO stop_times VALUES (?,?,?,?,?)',('DIRECT',stamp,stamp,sid,i+1))
        graph.build(source=self.source,target=self.index)
        direct.build(source=self.index,target=self.direct_path)
        with direct.connection(self.direct_path) as db:
            pairs=[tuple(r) for r in db.execute("SELECT origin,destination FROM direct_services WHERE code='DIRECT' ORDER BY boarding_index,alighting_index")]
        self.assertEqual(pairs,[('A','B'),('A','C'),('A','D'),('B','C'),('B','D'),('C','D')])

    def test_missing_distance_keeps_reverse_connectivity(self):
        with sqlite3.connect(self.source) as db:db.execute("DELETE FROM shapes WHERE shape_id='R1'")
        graph.build(source=self.source,target=self.index)
        report=direct.build(source=self.index,target=self.direct_path)
        rows=self.lookup('B',reverse=True,other='A')['connections']
        self.assertEqual(len(rows),1);self.assertIsNone(rows[0]['distance_meters'])
        self.assertGreater(report['unknown_distances'],0)
        self.assertEqual(direct.transfers('A','C',path=self.direct_path)['candidates'],[])

    def test_atomic_failure_preserves_existing_artifact(self):
        before=self.direct_path.read_bytes()
        with sqlite3.connect(self.index) as db:db.execute('DELETE FROM timetable')
        with self.assertRaisesRegex(ValueError,'sem programação'):
            direct.build(source=self.index,target=self.direct_path)
        self.assertEqual(self.direct_path.read_bytes(),before)

    def test_refuses_source_overwrite(self):
        for target in [self.index,self.source]:
            with self.assertRaises(ValueError):direct.build(source=self.index,target=target)

    def test_stale_gtfs_is_rejected(self):
        with sqlite3.connect(self.source) as db:db.execute("UPDATE stops SET stop_name='Alterado' WHERE stop_id='A'")
        with self.assertRaisesRegex(ValueError,'desatualizado'):self.lookup('A')

    def test_stops_and_schedules_preserved(self):
        with direct.connection(self.direct_path) as db,graph.connection(self.index) as src:
            for table in ['graph_stop','pattern','timetable','calendar','calendar_dates']:
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+table)],
                                 [tuple(r) for r in src.execute('SELECT * FROM '+table)])

    def test_same_stop_is_not_a_cycle(self):
        self.assertEqual(direct.transfers('A','A',path=self.direct_path)['candidates'],[])

    def test_invalid_query_arguments(self):
        with self.assertRaises(ValueError):self.lookup('not-a-stop')
        with self.assertRaises(ValueError):self.lookup('A',limit=0)
        with self.assertRaises(ValueError):direct.transfers('A','C',seconds=float('nan'),path=self.direct_path)

    def test_build_makes_no_router_or_operational_requests(self):
        from transit.sptrans import realtime,walking
        with patch.object(realtime,'add_predictions',side_effect=AssertionError('network')),patch.object(walking,'route',side_effect=AssertionError('network')):
            direct.build(source=self.index,target=self.direct_path)
            self.lookup('A')
            direct.transfers('A','C',path=self.direct_path)
