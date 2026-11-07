import csv
import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from transit.sptrans import graph, store, walking

NOW = datetime(2026,10,7,8,tzinfo=ZoneInfo('America/Sao_Paulo'))


class GraphTests(SimpleTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'gtfs.sqlite3';self.index=self.root/'routing.sqlite3'
        self.settings=override_settings(SPTRANS_DATABASE=self.source,SPTRANS_TOKEN='')
        self.settings.enable();self.addCleanup(self.settings.disable)
        rows={name:[] for name in store.TABLES}
        coords={'A':(-23.55,-46.64),'B':(-23.55,-46.63),'C':(-23.55,-46.62),'D':(-23.55,-46.61),'E':(-23.5499,-46.63)}
        rows['stops']=[[sid,sid,'',*p] for sid,p in coords.items()]
        rows['calendar']=[['daily',1,1,1,1,1,1,1,'20260101','20261231']]
        routes=[('R1','A','B','08:00:00','08:10:00'),('R2','B','C','08:15:00','08:25:00'),
                ('R3','C','D','08:30:00','08:40:00'),('DIRECT','A','D','08:00:00','09:00:00'),
                ('ONE','B','D','08:15:00','08:55:00'),('E1','E','C','08:15:00','08:25:00')]
        for tid,a,b,depart,arrive in routes:
            rows['routes'].append([tid,'1',tid,tid,'3','005cec'])
            rows['trips'].append([tid,'daily',tid,'Destino','0',tid])
            rows['stop_times'] += [[tid,depart,depart,a,1],[tid,arrive,arrive,b,2]]
            shape=[coords[a],(-23.552,(coords[a][1]+coords[b][1])/2),coords[b]]
            rows['shapes'] += [[tid,*p,i] for i,p in enumerate(shape)]
        for table,cols in store.TABLES.items():
            with (self.root/(table+'.txt')).open('w') as f:
                w=csv.writer(f);w.writerow(cols);w.writerows(rows[table])
        store.import_gtfs(self.root,self.source)
        graph.build(target=self.index)

    def query(self,a='A',b='D',**kw):
        return graph.query(a,b,now=NOW,path=self.index,**kw)

    def db(self):
        db=sqlite3.connect(self.index);db.row_factory=sqlite3.Row;return db

    def edit_source(self,sql,args=()):
        with sqlite3.connect(self.source) as db:db.execute(sql,args)
        graph.build(target=self.index)

    def test_zero_one_two_transfers_and_costs(self):
        r=self.query()
        self.assertTrue(r['candidate_search_complete'])
        self.assertEqual([(x['transfers'],x['duration_seconds']) for x in r['journeys']],[(2,2400),(1,3300),(0,3600)])
        self.assertEqual([l['code'] for l in r['journeys'][0]['legs']],['R1','R2','R3'])
        self.assertEqual(r['journeys'][0]['legs'][1]['wait_seconds'],180)
        self.assertEqual(self.query('D','A')['journeys'],[])

    def test_distance_uses_curved_shape_and_distinct_patterns(self):
        with self.db() as db:
            row=db.execute("SELECT * FROM direct_adjacency WHERE origin='A' AND destination='B'").fetchone()
            a=db.execute("SELECT lat,lon FROM graph_stop WHERE id='A'").fetchone()
            b=db.execute("SELECT lat,lon FROM graph_stop WHERE id='B'").fetchone()
            self.assertGreater(row['distance_meters'],graph.distance(a,b)+50)
            plan=db.execute("EXPLAIN QUERY PLAN SELECT * FROM ride_edge WHERE destination='D' AND origin='A'").fetchall()
            self.assertTrue(any('INDEX' in r[3] for r in plan))

    def test_missing_shape_is_unknown_distance_not_air_distance(self):
        self.edit_source("DELETE FROM shapes WHERE shape_id='R1'")
        with self.db() as db:
            self.assertIsNone(db.execute("SELECT distance_meters FROM ride_edge WHERE origin='A' AND destination='B'").fetchone()[0])
        self.assertEqual(self.query()['journeys'][0]['duration_seconds'],2400)

    def test_cannot_board_before_access_walk(self):
        self.assertEqual(self.query(access_seconds=450/walking.WALK_METERS_PER_SECOND)['journeys'],[])

    def test_service_exception(self):
        self.edit_source("INSERT INTO calendar_dates VALUES ('daily','20261007','2')")
        self.assertEqual(self.query()['journeys'],[])

    def test_frequency_exact_vs_unknown_phase(self):
        self.edit_source("INSERT INTO frequencies VALUES ('DIRECT','08:00:00','10:00:00',600,'1')")
        r=self.query(transfers=(0,),access_seconds=60)['journeys'][0]
        self.assertEqual(r['duration_seconds'],4200)
        self.assertFalse(r['frequency_estimate'])
        self.edit_source("UPDATE frequencies SET exact_times='0' WHERE trip_id='DIRECT'")
        r=self.query(transfers=(0,),access_seconds=60)['journeys'][0]
        self.assertEqual(r['duration_seconds'],3960)
        self.assertTrue(r['frequency_estimate'])

    def test_previous_service_day_after_24_hours(self):
        with sqlite3.connect(self.source) as db:
            db.execute("UPDATE stop_times SET arrival_time='25:00:00',departure_time='25:00:00' WHERE trip_id='DIRECT' AND stop_sequence=1")
            db.execute("UPDATE stop_times SET arrival_time='26:00:00',departure_time='26:00:00' WHERE trip_id='DIRECT' AND stop_sequence=2")
            db.execute("INSERT INTO calendar_dates VALUES ('daily','20261007','2')")
        graph.build(target=self.index)
        r=graph.query('A','D',now=NOW.replace(hour=0,minute=55),path=self.index,transfers=(0,))['journeys'][0]
        self.assertEqual(r['duration_seconds'],3900)

    def test_calendar_and_later_faster_trip_of_same_pattern(self):
        with sqlite3.connect(self.source) as db:
            db.execute("INSERT INTO trips VALUES ('DIRECT','daily','FAST','Destino','0','DIRECT')")
            db.execute("INSERT INTO stop_times VALUES ('FAST','08:05:00','08:05:00','A',1)")
            db.execute("INSERT INTO stop_times VALUES ('FAST','08:35:00','08:35:00','D',2)")
        graph.build(target=self.index)
        r=self.query(transfers=(0,))['journeys'][0]
        self.assertEqual(r['legs'][0]['trip_id'],'FAST')
        with self.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM pattern WHERE route_id='DIRECT'").fetchone()[0],1)

    def test_walks_are_directed_verified_and_use_4_5_kmh(self):
        # Substitua a conexão na mesma parada por transferência a uma parada próxima distinta.
        self.edit_source("DELETE FROM trips WHERE trip_id='R2'")
        before=self.query('A','C')
        self.assertEqual(before['journeys'],[])
        with self.db() as db:
            a=db.execute("SELECT lat,lon FROM graph_stop WHERE id='B'").fetchone()
            b=db.execute("SELECT lat,lon FROM graph_stop WHERE id='E'").fetchone()
            self.assertEqual(graph.put_walk(db,'B','E',{'available':True,'distance_meters':450,'geometry':[list(a),list(b)],'source':'test fixture'}),'verified')
            self.assertEqual(db.execute("SELECT seconds FROM walk_adjacency WHERE origin='B' AND destination='E'").fetchone()[0],360)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM walk_adjacency WHERE origin='E' AND destination='B'").fetchone()[0],0)
        # 08:10 + 6 min a pé + 2 min de margem perde a partida das 08:15.
        self.assertEqual(self.query('A','C')['journeys'],[])
        with self.db() as db:
            graph.put_walk(db,'B','E',{'available':True,'distance_meters':75,'geometry':[list(a),list(b)]})
        r=self.query('A','C')['journeys'][0]
        self.assertEqual(r['transfers'],1);self.assertEqual(r['duration_seconds'],1500)
        self.assertEqual(r['walks'][0]['seconds'],60)

    def test_walk_over_limit_and_provider_failure_never_become_edges(self):
        with self.db() as db:
            a=db.execute("SELECT lat,lon FROM graph_stop WHERE id='B'").fetchone()
            b=db.execute("SELECT lat,lon FROM graph_stop WHERE id='E'").fetchone()
            self.assertEqual(graph.put_walk(db,'B','E',{'available':True,'distance_meters':1200,'geometry':[list(a),list(b)]}),'over_limit')
            self.assertEqual(graph.put_walk(db,'E','B',{'available':False}),'unavailable')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM walk_adjacency').fetchone()[0],0)
            with self.assertRaises(ValueError):graph.put_walk(db,'B','E',{'available':True,'distance_meters':float('nan'),'geometry':[list(a),list(b)]})

    def test_cache_invalidated_when_walk_changes(self):
        self.query()
        with self.db() as db:
            self.assertGreater(db.execute('SELECT COUNT(*) FROM candidate_cache').fetchone()[0],0)
            graph.put_walk(db,'B','E',{'available':False})
            self.assertEqual(db.execute('SELECT COUNT(*) FROM candidate_cache').fetchone()[0],0)

    def test_gtfs_change_rejects_stale_index(self):
        with sqlite3.connect(self.source) as db:db.execute("UPDATE stops SET stop_name='Updated' WHERE stop_id='A'")
        with self.assertRaisesRegex(ValueError,'desatualizado'):self.query()

    def test_atomic_rebuild_keeps_previous_index_on_error(self):
        original=self.index.read_bytes()
        with patch.object(graph,'projected_positions',side_effect=RuntimeError('failure')):
            with self.assertRaises(RuntimeError):graph.build(target=self.index)
        self.assertEqual(original,self.index.read_bytes())

    def test_bounded_cartesian_query_reports_incomplete(self):
        r=self.query(max_candidates=1)
        # Adicione um padrão paralelo para garantir mais de um candidato direto.
        with sqlite3.connect(self.source) as db:
            db.execute("INSERT INTO trips VALUES ('R1','daily','PARALLEL','Outro','0','DIRECT')")
            db.execute("INSERT INTO stop_times VALUES ('PARALLEL','08:00:00','08:00:00','A',1)")
            db.execute("INSERT INTO stop_times VALUES ('PARALLEL','09:00:00','09:00:00','D',2)")
        graph.build(target=self.index)
        r=self.query(transfers=(0,),max_candidates=1)
        self.assertFalse(r['candidate_search_complete'])

    def test_repeated_stop_occurrences_preserved(self):
        positions=graph.projected_positions([(0,0),(0,.001),(.001,.001),(0,0),(0,-.001)],[(0,0),(0,.001),(0,0),(0,-.001)])
        self.assertGreater(positions[2]['meters'],positions[0]['meters'])
        self.assertGreater(positions[3]['meters'],positions[2]['meters'])

    def test_build_and_query_do_not_call_external_router(self):
        with patch.object(walking,'route',side_effect=AssertionError('network')):
            graph.build(target=self.index);self.query()
        called=[]
        def unavailable(a,b):called.append((a['id'],b['id']));return {'available':False}
        graph.verify_walks(self.index,limit=1,origins=['B'],resolver=unavailable)
        self.assertEqual(len(called),1);self.assertEqual(called[0][0],'B')

    def test_utc_query_uses_local_service_day_and_time(self):
        r=graph.query('A','D',now=NOW.astimezone(ZoneInfo('UTC')),path=self.index)
        self.assertEqual(r['journeys'][0]['duration_seconds'],2400)

    def test_cost_components_sum_to_total(self):
        for j in self.query()['journeys']:
            self.assertEqual(j['duration_seconds'],sum(j[k] for k in ('access_seconds','egress_seconds','ride_seconds','wait_seconds','transfer_walk_seconds','transfer_buffer_seconds')))

    def test_same_stop_does_not_create_a_trip_around_a_cycle(self):
        self.assertEqual(self.query('A','A')['journeys'],[])
