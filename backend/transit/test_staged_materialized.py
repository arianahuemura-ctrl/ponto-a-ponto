import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase
from transit.sptrans import staged_materialized as staged
from transit.sptrans import staged_adapter,store,graph,transfer_policy,planner
from transit import test_weighted_transfers as weighted_fixtures
from transit.test_rail import NOW
from mbm import routing_config as config


class StagedKernelTests(SimpleTestCase):
    def test_walking_candidates_cover_full_radius_across_grid_cells(self):
        stops={sid:{'lat':lat,'lon':lon} for sid,lat,lon in [
            ('origin',-23.56,-46.65),('north',-23.552,-46.65),
            ('east',-23.56,-46.641),('outside',-23.549,-46.65)]}
        with patch.object(planner,'_network',return_value=(stops,{},dict.fromkeys(stops,[]))):
            nearby=planner._nearby.__wrapped__('unused',0,0)
        self.assertEqual({sid for sid,_ in nearby['origin']},{'north','east'})

    def engine(self,services,walks=()):
        db=sqlite3.connect(':memory:');self.addCleanup(db.close)
        db.executescript('''CREATE TABLE stops(id INTEGER PRIMARY KEY);CREATE TABLE patterns(id INTEGER PRIMARY KEY,service,rail,wait);
            CREATE TABLE rides(id INTEGER PRIMARY KEY,pattern,origin,destination,boarding,alighting,seconds);
            CREATE TABLE walks(id INTEGER PRIMARY KEY,origin,destination,internal,seconds,meters);''')
        ids={sid for _,_,stops,_ in services for sid in stops}|{sid for walk in walks for sid in walk[:2]}
        db.executemany('INSERT INTO stops VALUES(?)',[(i,) for i in range(max(ids)+1)])
        eid=1
        for pid,(service,is_rail,stops,seconds) in enumerate(services):
            db.execute('INSERT INTO patterns VALUES(?,?,?,?)',(pid,service,is_rail,0))
            for a in range(len(stops)-1):
                for b in range(a+1,len(stops)):
                    if stops[a]==stops[b]:continue
                    db.execute('INSERT INTO rides VALUES(?,?,?,?,?,?,?)',(eid,pid,stops[a],stops[b],a,b,seconds*(b-a)));eid+=1
        db.executemany('INSERT INTO walks VALUES(?,?,?,?,?,?)',[(i+1,*w) for i,w in enumerate(walks)])
        db.commit()
        engine=staged.Engine(db);self.addCleanup(engine.close)
        return engine,db

    def test_zero_cost_covers_all_direct_destinations_and_verified_egress(self):
        engine,_=self.engine([(0,0,[0,1,2],60),(1,0,[2,3],60)],[(2,4,0,30,37.5)])
        rows={b:staged.decode(blob) for _,b,blob in engine.rows(0,0)}
        self.assertEqual(set(rows),{1,2,4})
        self.assertTrue(all(p['units']==0 for paths in rows.values() for p in paths))
        self.assertEqual(rows[4][0]['egress'],1)

    def test_cost_one_means_three_internal_rail_transfers_or_one_bus_transfer(self):
        engine,_=self.engine([(i,1,[i,i+1],60) for i in range(5)]+[(9,0,[0,6],60),(10,0,[6,7],60),(11,0,[7,8],60)])
        rows={b:staged.decode(blob) for _,b,blob in engine.rows(0,3)}
        self.assertEqual(rows[4][0]['units'],3)
        self.assertEqual(len(rows[4][0]['legs']),4)
        self.assertNotIn(5,rows);self.assertNotIn(8,rows)
        self.assertEqual(rows[7][0]['units'],3)
        self.assertEqual(len(rows[7][0]['legs']),2)

    def test_external_walk_between_rail_services_costs_three_units(self):
        services=[(0,1,[0,1],60),(1,1,[2,3],60),(2,1,[3,4],60)]
        for internal,cost in [(0,3),(1,1)]:
            engine,_=self.engine(services,[(1,2,internal,120,0 if internal else 150)])
            rows={b:staged.decode(blob) for _,b,blob in engine.rows(0,3)}
            self.assertEqual(rows[3][0]['units'],cost)
            self.assertEqual(4 in rows,bool(internal))

    def test_five_slots_use_minimum_first_even_when_transfers_are_faster(self):
        services=[(i,0,[0,2],1000+i) for i in range(3)]
        services += [(20,0,[0,1],30)]+[(30+i,0,[1,2],30+i) for i in range(5)]
        engine,_=self.engine(services)
        paths=next(staged.decode(blob) for _,b,blob in engine.rows(0,3) if b==2)
        self.assertEqual(len(paths),5)
        self.assertEqual([p['units'] for p in paths],[0,0,0,3,3])

    def test_intermediate_paths_are_not_cut_to_five(self):
        services=[(i,0,[0,1],60+i) for i in range(7)]
        services += [(0,0,[1,2],60)]
        engine,_=self.engine(services)
        rows={b:staged.decode(blob) for _,b,blob in engine.rows(0,3)}
        self.assertEqual(len(rows[1]),5)
        self.assertEqual(len(rows[2]),5)
        self.assertTrue(all(p['units']==3 for p in rows[2]))
        self.assertTrue(any(p['legs'][0][0]>=6 for p in rows[2]))

    def test_internal_access_is_free_and_directions_are_not_reversed(self):
        engine,_=self.engine([(0,1,[1,2],60)],[(0,1,1,120,0)])
        rows={b:staged.decode(blob) for _,b,blob in engine.rows(0,0)}
        self.assertEqual(rows[2][0]['units'],0)
        self.assertEqual(rows[2][0]['legs'][0][1],1)
        self.assertEqual(list(engine.rows(2,3)),[])

    def test_resume_and_stage_barrier_and_disk_guard(self):
        engine,source=self.engine([(0,0,[0,1],60),(1,0,[1,2],60)])
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'staged.sqlite3'
        with sqlite3.connect(path) as db:
            source.backup(db)
            db.executescript('CREATE TABLE metadata(id,value);CREATE TABLE paths(origin,destination,data,PRIMARY KEY(origin,destination));CREATE TABLE progress(stage,origin,paths,pairs,seconds,PRIMARY KEY(stage,origin));')
            db.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'signature':{'walks':['unused']},'complete_stages':[]}),))
        with patch.object(staged,'signature',return_value={'walks':['unused']}):
            with self.assertRaises(ValueError):staged.build(1,path,min_free_gib=0,progress=lambda x:None)
            with self.assertRaises(OSError):staged.build(0,path,min_free_gib=10**9,progress=lambda x:None)
            partial=staged.build(0,path,min_free_gib=0,origins=[0],progress=lambda x:None)
            self.assertFalse(partial['complete'])
            complete=staged.build(0,path,min_free_gib=0,progress=lambda x:None)
            self.assertTrue(complete['complete']);self.assertEqual(complete['origins'],3)
            with patch.object(staged.Engine,'rows',side_effect=AssertionError('Already ready')):
                self.assertTrue(staged.build(0,path,min_free_gib=0,progress=lambda x:None)['complete'])
            self.assertTrue(staged.build(1,path,min_free_gib=0,progress=lambda x:None)['complete'])
            with sqlite3.connect(path) as db:
                actual=db.execute('SELECT * FROM paths ORDER BY origin,destination').fetchall()
            expected=sorted(row for origin in range(3) for row in engine.rows(origin,3))
            self.assertEqual(actual,expected)


class StagedReaderTests(SimpleTestCase):
    def setUp(self):
        weighted_fixtures.WeightedTransferTests.network(self,[(f'L{i}','1',[str(i),str(i+1)],60) for i in range(4)])
        walks=store.database_path().with_suffix('.walks-test.sqlite3')
        with sqlite3.connect(walks) as db:
            db.executescript('CREATE TABLE walk_edge(origin,destination,seconds,distance_meters,status);CREATE TABLE walk_meta(value);')
            db.execute('INSERT INTO walk_meta VALUES(?)',(json.dumps({'source_gtfs':graph.fingerprint(store.database_path()),'configuration':config.walking_signature(),'stops':5}),))
        staged.prepare(walks,progress=lambda x:None)
        staged.build(0,min_free_gib=0,progress=lambda x:None)
        staged.build(1,min_free_gib=0,progress=lambda x:None)

    def test_reads_materialized_four_trains_without_recomputing_the_network(self):
        with store.connection() as db,patch('transit.sptrans.planner.journeys',side_effect=AssertionError('No online search')),patch('transit.sptrans.walking.route',side_effect=AssertionError('No external walk')):
            results=list(staged_adapter.progressive(db,store.get_stop(db,'0'),store.get_stop(db,'4'),1,NOW))
        result=results[-1]
        self.assertTrue(result['materialized']);self.assertTrue(result['complete'])
        self.assertEqual(result['materialization_complete_stages'],[0,1])
        journey=result['journeys'][0]
        self.assertEqual(journey['transfer_cost'],1)
        self.assertEqual(journey['transfers'],3)
        self.assertEqual(journey['duration_minutes'],14)
        self.assertEqual([leg['code'] for leg in journey['legs']],['L0','L1','L2','L3'])

    def test_ranking_does_not_build_geometry_before_publication(self):
        geometry=[[0,0],[1,1]]
        with store.connection() as db,patch.object(planner,'leg_shape',return_value=geometry) as shape:
            stream=staged_adapter.progressive(db,store.get_stop(db,'0'),store.get_stop(db,'4'),1,NOW)
            try:
                first=next(stream)
                self.assertFalse(first['complete'])
                self.assertEqual(shape.call_count,len(first['journeys'][0]['legs']))
                self.assertTrue(all(l['geometry']==geometry for l in first['journeys'][0]['legs']))
            finally:stream.close()

    def test_materialization_does_not_override_timetable_or_query_ceiling(self):
        with store.connection() as db:
            a,b=store.get_stop(db,'0'),store.get_stop(db,'4')
            for ceiling,now in [(0,NOW),(1,NOW.replace(year=2028))]:
                result=list(staged_adapter.progressive(db,a,b,ceiling,now))[-1]
                self.assertEqual(result['journeys'],[])

    def test_decoder_rejects_trailing_corruption(self):
        with sqlite3.connect(staged.database_path()) as db:
            blob=db.execute('SELECT data FROM paths LIMIT 1').fetchone()[0]
        with self.assertRaises(ValueError):staged.decode(blob+b'\0')

    def test_preparation_rejects_walk_database_missing_stations(self):
        walks=store.database_path().with_suffix('.walks-test.sqlite3')
        with sqlite3.connect(walks) as db:
            meta=json.loads(db.execute('SELECT value FROM walk_meta').fetchone()[0])
            meta['stops']=4
            db.execute('UPDATE walk_meta SET value=?',(json.dumps(meta),))
        with self.assertRaisesRegex(ValueError,'cobertura incompleta'):
            staged.prepare(walks,target=walks.with_name('incomplete.sqlite3'),progress=lambda x:None)
