import json
import sqlite3
from unittest.mock import patch
from django.test import SimpleTestCase
from transit import test_sptrans_graph as fixtures
from transit.sptrans import direct,city_connections,materialized_connections as m


class MaterializedConnectionsTests(SimpleTestCase):
    def setUp(self):
        fixtures.GraphTests.setUp(self)
        self.dp=self.root/'direct.sqlite3';self.cp=self.root/'components.sqlite3';self.mp=self.root/'materialized.sqlite3'
        direct.build(source=self.index,target=self.dp)
        with sqlite3.connect(self.index) as db:
            db.execute("UPDATE walk_edge SET status='verified',distance_meters=58.75,seconds=999 WHERE origin='B' AND destination='E'")
            db.execute("INSERT OR REPLACE INTO walk_edge(origin,destination,air_meters,status,distance_meters,seconds) VALUES ('D','E',0,'verified',900,999)")
        city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)

    def build(self,pairs=(('A','D'),),**kw):
        return m.materialize(pairs,source=self.cp,target=self.mp,min_free_bytes=0,**kw)

    def test_exact_top_categories_with_intermediate_and_final_walks(self):
        self.build((('A','D'),('A','E'),('D','A')))
        for a,b in [('A','D'),('A','E'),('D','A')]:
            expected=city_connections.structural_query(a,b,path=self.cp,categories=(1,2))
            actual=m.query(a,b,path=self.mp)
            self.assertEqual(actual['trajetos'],expected['trajetos'])
            self.assertTrue(actual['complete']);self.assertTrue(actual['materialized'])
            for p in actual['trajetos']:
                self.assertAlmostEqual(p['caminhada_s'],p['distancia_caminhada_m']/1.25)
        self.assertFalse(m.query('D','A',path=self.mp)['trajetos'])

    def test_query_never_runs_composition_and_uses_physical_index(self):
        self.build()
        with patch.object(city_connections,'structural_query',side_effect=AssertionError('runtime composition')),patch.object(city_connections,'_rank_three',side_effect=AssertionError('runtime ranking')):
            self.assertTrue(city_connections.query('A','D',path=self.mp)['trajetos'])
        with sqlite3.connect(self.mp) as db:
            self.assertEqual(db.execute("SELECT type FROM sqlite_master WHERE name='conexoes'").fetchone()[0],'table')
            plan=str(db.execute("EXPLAIN QUERY PLAN SELECT * FROM conexoes WHERE origin='A' AND destination='D' AND boardings=3 ORDER BY distance_meters,rank LIMIT 4").fetchall())
            self.assertIn('conexoes_distancia',plan);self.assertNotIn('TEMP B-TREE',plan)

    def test_resume_skips_ready_and_pending_is_not_empty_result(self):
        self.build()
        with patch.object(city_connections,'structural_query',side_effect=AssertionError('already ready')):
            self.assertEqual(self.build()['skipped_categories'],2)
        with self.assertRaises(m.MaterializationPending):m.query('B','D',path=self.mp)
        with self.assertRaises(ValueError):m.query('A','D',path=self.mp,quotas={1:17,2:8,3:4})

    def test_timeout_not_published_and_resumes(self):
        real=city_connections.structural_query
        def timeout(*args,**kw):
            if kw['categories']==(2,):return {'categories':{2:{'complete':False,'count':0}},'trajetos':[]}
            return real(*args,**kw)
        with patch.object(city_connections,'structural_query',side_effect=timeout):
            self.assertEqual(self.build()['timed_out_categories'],1)
        with self.assertRaises(m.MaterializationPending):m.query('A','D',path=self.mp)
        self.assertEqual(self.build()['skipped_categories'],1)
        self.assertTrue(m.query('A','D',path=self.mp)['complete'])

    def test_changed_source_rejected_and_no_overwrite(self):
        self.build()
        before=self.mp.read_bytes()
        with sqlite3.connect(self.cp) as db:db.execute('CREATE TABLE changed(x)')
        with self.assertRaisesRegex(ValueError,'desatualizadas'):m.query('A','D',path=self.mp)
        with self.assertRaises(ValueError):self.build()
        self.assertEqual(self.mp.read_bytes(),before)
        with self.assertRaises(ValueError):m.initialize(self.cp,self.cp)

    def test_reachability_enumerates_real_directions_and_covers_exhaustive(self):
        pairs=set(m.city_pairs(self.cp))
        self.assertIn(('A','D'),pairs);self.assertNotIn(('D','A'),pairs)
        with direct.connection(self.cp) as db:
            exact=set(tuple(r) for r in db.execute('SELECT DISTINCT origin,destination FROM conexoes WHERE boardings<=2'))
        self.assertTrue(exact<=pairs)

    def test_disk_guard_preserves_ready_data(self):
        self.build()
        with self.assertRaises(OSError):m.materialize([('A','E')],source=self.cp,target=self.mp,min_free_bytes=10**30)

    def test_shared_origin_preserves_all_pairs_and_reuses_preparation(self):
        from transit.sptrans.offline_three import rank_three
        import time
        with direct.connection(self.cp) as db:
            stops=[r[0] for r in db.execute('SELECT DISTINCT stop FROM occurrence')]
            shared={}
            hits=0
            for origin in stops:
                for destination in stops:
                    expected=rank_three(db,origin,destination,4,time.perf_counter()+30)
                    statements=[]
                    db.set_trace_callback(statements.append)
                    actual=rank_three(db,origin,destination,4,time.perf_counter()+30,shared=shared)
                    db.set_trace_callback(None)
                    self.assertEqual(actual,expected,(origin,destination))
                    self.assertLessEqual(len(shared),1)
                    if actual and not any('max(position)' in sql for sql in statements):
                        hits+=1
            self.assertGreater(hits,0,'O cenário deve exercitar reutilização real')

    def test_shared_origin_timeout_does_not_publish_partial_preparation(self):
        from transit.sptrans.offline_three import rank_three
        shared={}
        with direct.connection(self.cp) as db:
            with self.assertRaises(sqlite3.OperationalError):
                rank_three(db,'A','D',4,float('-inf'),shared=shared)
        self.assertEqual(shared,{})

    def test_experimental_artifact_records_policy_and_resumes(self):
        self.build(experimental=True)
        result=m.query('A','D',path=self.mp)
        self.assertEqual(result['selection_policy'],'coverage_then_midpoint_last_v1')
        self.assertEqual({d['boardings'] for d in result['policy_decisions']},{1,2})
        self.assertEqual(self.build(experimental=True)['skipped_categories'],2)
        expected=city_connections.structural_query('A','D',path=self.cp,experimental=True,categories=(1,2))
        self.assertEqual(result['trajetos'],expected['trajetos'])

    def test_policy_cannot_mix_with_existing_reference_artifact(self):
        self.build()
        before=self.mp.read_bytes()
        with self.assertRaisesRegex(ValueError,'incompatível'):
            self.build(experimental=True)
        self.assertEqual(before,self.mp.read_bytes())
        self.assertNotEqual(m.database_path(),m.database_path(experimental=True))

    def test_preparation_never_calls_three_bus_composition(self):
        with patch('transit.sptrans.offline_three.rank_three',side_effect=AssertionError('Três ônibus são do RAPTOR')):
            result=self.build()
        self.assertEqual(result['built_categories'],2)
        with sqlite3.connect(self.mp) as db:
            self.assertEqual(db.execute('SELECT DISTINCT boardings FROM materialization_status ORDER BY boardings').fetchall(),[(1,),(2,)])
        self.assertEqual(set(m.query('A','D',path=self.mp)['categories']),{1,2})

    def test_adapter_reads_ready_categories_independently(self):
        from transit.sptrans import alternatives, materialized_adapter
        self.build((('A','B'),('A','D')))
        with sqlite3.connect(self.mp) as db:
            categories = db.execute('SELECT DISTINCT boardings FROM conexoes').fetchall()
        self.assertEqual(set(categories), {(1,), (2,)})
        for ready in (1, 2):
            with self.subTest(boardings=ready):
                with sqlite3.connect(self.mp) as db:
                    db.execute("UPDATE materialization_status SET state=CASE WHEN boardings=? THEN 'ready' ELSE 'timeout' END", (ready,))
                def access(db, point, boarding, **kwargs):
                    ids = ['A'] if boarding else ['B', 'D']
                    return [({'id': sid}, None) for sid in ids], False
                with patch.object(m, 'database_path', return_value=self.mp), patch.object(alternatives, 'access_points', side_effect=access):
                    result = materialized_adapter.prepare(None, {'id':'A'}, {'id':'D'})
                self.assertIsNotNone(result)
                self.assertTrue(result['paths'])
                self.assertEqual({sum(leg['modo']=='onibus' for leg in p['trechos']) for p in result['paths']}, {ready})
