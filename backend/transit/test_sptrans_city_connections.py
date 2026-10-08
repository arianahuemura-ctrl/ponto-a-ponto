import itertools
import json
import sqlite3
from unittest.mock import patch
from django.test import SimpleTestCase
from transit import test_sptrans_graph as fixtures
from transit.sptrans import direct, city_connections


class CityConnectionsTests(SimpleTestCase):
    def setUp(self):
        fixtures.GraphTests.setUp(self)
        self.dp=self.root/'direct.sqlite3'
        self.cp=self.root/'connections.sqlite3'
        direct.build(source=self.index,target=self.dp)
        self.report=city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)

    def query(self, a='A', b='D', **kw):
        return city_connections.structural_query(a,b,path=self.cp,**kw)

    def test_all_categories_match_exhaustive_directed_paths(self):
        result=self.query()
        self.assertTrue(result['complete'])
        with direct.connection(self.dp) as db:
            edges=[dict(r) for r in db.execute('SELECT * FROM ride_edge')]
        for n in (1,2,3):
            expected=[]
            for path in itertools.product(edges,repeat=n):
                if path[0]['origin']!='A' or path[-1]['destination']!='D': continue
                if any(a['destination']!=b['origin'] or a['pattern_id']==b['pattern_id'] for a,b in zip(path,path[1:])): continue
                if any(e['destination']=='D' for e in path[:-1]): continue
                if any(e['destination']=='A' for e in path[1:]): continue
                expected.append((sum(e['distance_meters'] for e in path),tuple(e['id'] for e in path)))
            actual=[(r['distancia_m'],tuple(e['aresta_id'] for e in r['trechos'])) for r in result['trajetos'] if r['embarques']==n]
            self.assertEqual([(round(d,6),ids) for d,ids in actual],
                             [(round(d,6),ids) for d,ids in sorted(expected)[:city_connections.QUOTAS[n]]])
            self.assertTrue(actual)
        self.assertEqual(self.query('D','A')['trajetos'],[])
        self.assertEqual(self.query('A','A')['trajetos'],[])
        self.assertTrue(result['structural_only'])
        self.assertFalse(result['temporal_feasibility_checked'])

    def test_verified_walking_only_and_precomputed_seconds(self):
        with sqlite3.connect(self.index) as db:
            db.execute("UPDATE walk_edge SET status='verified',distance_meters=58.75,seconds=999 WHERE origin='B' AND destination='E'")
        city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)
        result=self.query('A','C')
        walks=[w for p in result['trajetos'] for w in p['trechos'] if w['modo']=='caminhada']
        self.assertEqual(len(walks),1)
        self.assertEqual(walks[0]['tempo_s'],47)
        self.assertEqual(walks[0]['distancia_m'],58.75)
        for p in result['trajetos']:
            self.assertAlmostEqual(p['distancia_m'],sum(e['distancia_m'] for e in p['trechos']))
        self.assertEqual(self.query('C','A')['trajetos'],[])

    def test_unknown_distance_excluded_from_ranked_paths(self):
        with sqlite3.connect(self.dp) as db:
            db.execute("UPDATE ride_edge SET distance_meters=NULL WHERE origin='A' AND destination='B'")
        city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)
        result=self.query()
        self.assertEqual([p['embarques'] for p in result['trajetos']],[1])
        self.assertEqual(result['coverage']['unknown_ride_distances'],1)

    def test_preserves_schedules_indexes_and_physical_direction(self):
        with direct.connection(self.cp) as db,direct.connection(self.dp) as src:
            for table in ('pattern','timetable','calendar','calendar_dates','ride_edge'):
                self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+table)],
                                 [tuple(r) for r in src.execute('SELECT * FROM '+table)])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('SELECT count(*) FROM conexoes WHERE origin=? AND destination=?',('D','A')).fetchone()[0],0)
        for p in self.query()['trajetos']:
            self.assertTrue(all(e['embarque_indice']<e['desembarque_indice'] for e in p['trechos']))

    def test_invalid_generation_preserves_previous_database(self):
        before=self.cp.read_bytes()
        with sqlite3.connect(self.index) as db:
            db.execute('DROP TABLE walk_edge')
        with self.assertRaises(sqlite3.Error):
            city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)
        self.assertEqual(self.cp.read_bytes(),before)

    def test_cannot_overwrite_sources(self):
        for path in (self.dp,self.index,self.source):
            with self.assertRaises(ValueError):
                city_connections.build(source=self.dp,graph_source=self.index,target=path)

    def test_limits_and_timeout_are_explicit(self):
        with patch.object(city_connections, 'PROGRESS_STEPS', 1):
            result=self.query(seconds=1e-12)
        self.assertFalse(result['complete'])
        self.assertFalse(all(c['complete'] for c in result['categories'].values()))
        with self.assertRaises(ValueError): self.query(seconds=0)
        limited=self.query(quotas={1:1,2:1,3:1})
        self.assertEqual(len(limited['trajetos']),3)

    def test_stale_walking_revision_rejected(self):
        with sqlite3.connect(self.index) as db:
            meta=json.loads(db.execute('SELECT value FROM graph_meta').fetchone()[0])
            meta['revision']+=1
            db.execute('UPDATE graph_meta SET value=?',(json.dumps(meta),))
        with self.assertRaisesRegex(ValueError,'Caminhadas desatualizadas'):
            self.query()

    def test_stale_gtfs_rejected(self):
        with sqlite3.connect(self.source) as db:
            db.execute("UPDATE stops SET stop_name='Novo' WHERE stop_id='A'")
        with self.assertRaisesRegex(ValueError,'desatualizado'):
            self.query()

    def verify_walk(self,a,b,meters):
        with sqlite3.connect(self.index) as db:
            db.execute("INSERT OR REPLACE INTO walk_edge(origin,destination,air_meters,status,distance_meters,seconds) VALUES (?,?,0,'verified',?,?)",
                       (a,b,meters,meters/1.25))
        city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)

    def test_bus_followed_by_final_walk_and_reverse_keeps_direction(self):
        self.verify_walk('B','E',58.75)
        result=self.query('A','E')
        one=[p for p in result['trajetos'] if p['embarques']==1]
        self.assertEqual(len(one),1)
        self.assertEqual([l['modo'] for l in one[0]['trechos']],['onibus','caminhada'])
        self.assertEqual(one[0]['caminhada_s'],47)
        with direct.connection(self.cp) as db:
            forward=db.execute("SELECT origin,destination,edge_id,walk_id FROM bus_walk_forward WHERE search_from='A' AND search_to='E'").fetchall()
            reverse=db.execute("SELECT origin,destination,edge_id,walk_id FROM bus_walk_reverse WHERE search_from='E' AND search_to='A'").fetchall()
            self.assertEqual([tuple(x) for x in forward],[tuple(x) for x in reverse])
            self.assertTrue(forward)
            self.assertFalse(db.execute("SELECT 1 FROM bus_walk_forward WHERE search_from='E' AND search_to='A'").fetchone())

    def test_excludes_destination_reachable_on_same_bus_not_other_line(self):
        # R1 alcança apenas B: a caminhada B->C é válida mesmo com outro ônibus atendendo B->C.
        self.verify_walk('B','C',900)
        one=[p for p in self.query('A','C')['trajetos'] if p['embarques']==1]
        self.assertEqual(len(one),1)
        # DIRECT passa a A->B->C. A caminhada B->C desse mesmo ônibus deve ser excluída.
        with sqlite3.connect(self.source) as db:
            db.execute("DELETE FROM stop_times WHERE trip_id='DIRECT'")
            for i,sid in enumerate(('A','B','C')):
                t=f'08:{i*10:02d}:00'
                db.execute('INSERT INTO stop_times VALUES (?,?,?,?,?)',('DIRECT',t,t,sid,i+1))
        from transit.sptrans import graph
        graph.build(source=self.source,target=self.index)
        direct.build(source=self.index,target=self.dp)
        self.verify_walk('B','C',900)
        with direct.connection(self.cp) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM bus_walk_forward b JOIN pattern p ON p.id=b.pattern_id WHERE b.origin='A' AND b.destination='C' AND p.code='DIRECT'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM bus_walk_forward b JOIN pattern p ON p.id=b.pattern_id WHERE b.origin='A' AND b.destination='C' AND p.code='R1'").fetchone()[0],1)

    def test_one_kilometer_inclusive_and_no_over_limit_walk(self):
        self.verify_walk('B','E',1000)
        self.assertEqual(self.query('A','E')['trajetos'][0]['caminhada_s'],800)
        self.verify_walk('B','E',1000.01)
        self.assertEqual(self.query('A','E')['trajetos'],[])

    def test_three_bus_route_can_end_in_walk(self):
        # Ligação pedestre dirigida sintética após o terceiro ônibus.
        self.verify_walk('D','E',900)
        result=self.query('A','E')
        two=[p for p in result['trajetos'] if p['embarques']==3]
        self.assertEqual(len(two),1)
        self.assertEqual([l['modo'] for l in two[0]['trechos']],['onibus','onibus','onibus','caminhada'])
        self.assertEqual(two[0]['caminhada_s'],720)

    def test_bidirectional_distance_bound_matches_exhaustive_sql(self):
        import time
        # Grafo pedestre sintético denso permite observar todas as posições de composição.
        with sqlite3.connect(self.index) as db:
            for i,a in enumerate('ABCDE'):
                for j,b in enumerate('ABCDE'):
                    if a==b:continue
                    meters=40+(i*3+j)*7
                    db.execute("INSERT OR REPLACE INTO walk_edge(origin,destination,air_meters,status,distance_meters,seconds) VALUES (?,?,0,'verified',?,?)",
                               (a,b,meters,meters/1.25))
        city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)
        with direct.connection(self.cp) as db:
            for a in 'ABCDE':
                for b in 'ABCDE':
                    for limit in (1,4):
                        expected=db.execute("SELECT * FROM conexoes_3 WHERE origin=? AND destination=? ORDER BY distance_meters,edge1,edge2,edge3,final_walk LIMIT ?",(a,b,limit)).fetchall()
                        actual=city_connections._rank_three(db,a,b,limit,time.perf_counter()+5)
                        self.assertEqual([dict(r) for r in actual],[dict(r) for r in expected],(a,b,limit))

    def test_offline_middle_composition_matches_exhaustive_sql(self):
        import time
        # Grafo pedestre sintético denso permite observar todas as posições de composição.
        with sqlite3.connect(self.index) as db:
            for i,a in enumerate('ABCDE'):
                for j,b in enumerate('ABCDE'):
                    if a==b:continue
                    meters=40+(i*3+j)*7
                    db.execute("INSERT OR REPLACE INTO walk_edge(origin,destination,air_meters,status,distance_meters,seconds) VALUES (?,?,0,'verified',?,?)",
                               (a,b,meters,meters/1.25))
        city_connections.build(source=self.dp,graph_source=self.index,target=self.cp)
        caches={1:{},4:{}}
        with direct.connection(self.cp) as db:
            for a in 'ABCDE':
                for b in 'ABCDE':
                    for limit in (1,4):
                        expected=db.execute("SELECT * FROM conexoes_3 WHERE origin=? AND destination=? ORDER BY distance_meters,edge1,edge2,edge3,final_walk LIMIT ?",(a,b,limit)).fetchall()
                        from transit.sptrans.offline_three import rank_three
                        actual=rank_three(db,a,b,limit,time.perf_counter()+5)
                        self.assertEqual([dict(r) for r in actual],[dict(r) for r in expected],(a,b,limit))
                        reused=rank_three(db,a,b,limit,time.perf_counter()+5,shared=caches[limit])
                        self.assertEqual([dict(r) for r in reused],[dict(r) for r in expected],(a,b,limit,'reuso'))
