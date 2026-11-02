import random
from django.test import SimpleTestCase
from transit import test_staged_materialized as fixtures
from transit.test_expanded_materialized import ExpandedKernelTests
from transit.sptrans import staged_materialized as staged


class TopupKernelTests(SimpleTestCase):
    def network(self,services,walks=()):
        _,db=fixtures.StagedKernelTests.engine(self,services,walks)
        engine=staged.Engine(db,topup=True);old=staged.Engine(db,expanded=True)
        self.addCleanup(engine.close);self.addCleanup(old.close)
        return engine,old,db

    def test_inclusive_four_means_twelve_rail_or_four_bus_changes(self):
        engine,old,_=self.network([(i,1,[i,i+1],10) for i in range(14)]+
            [(20+i,0,[20+i,21+i],10) for i in range(6)])
        base={b:data for _,b,data in old.rows(0,8)};engine.baseline(base.items())
        rows={b:staged.decode(data) for _,b,data in engine.rows(0,12)}
        self.assertEqual(rows[13][0]['units'],12);self.assertEqual(len(rows[13][0]['legs']),13)
        self.assertNotIn(14,rows)
        base={b:data for _,b,data in old.rows(20,8)};engine.baseline(base.items())
        rows={b:staged.decode(data) for _,b,data in engine.rows(20,12)}
        self.assertEqual(rows[25][0]['units'],12);self.assertNotIn(26,rows)
        with self.assertRaises(ValueError):list(engine.rows(20,13))

    def test_four_future_buses_can_exclude_four_first_prefixes(self):
        services=[(i,0,[0,1],10+i) for i in range(10)]+[(i,0,[i+1,i+2],10) for i in range(4)]
        engine,_,db=self.network(services)
        actual={b:staged.decode(data) for _,b,data in engine.rows(0,12)}
        self.assertEqual(actual,ExpandedKernelTests.exhaustive(db,0,12))
        self.assertEqual(len(actual[5]),5)

    def test_multiple_visited_buses_and_multiple_future_exclusions(self):
        services=[(i,0,[0,1],10+i) for i in range(7)]+[(20+i,0,[1,2],10+i) for i in range(7)]
        services += [(0,0,[2,3],10),(20,0,[3,4],10),(1,0,[4,5],10)]
        engine,_,db=self.network(services)
        actual={b:staged.decode(data) for _,b,data in engine.rows(0,12)}
        self.assertEqual(actual,ExpandedKernelTests.exhaustive(db,0,12))

    def test_preserves_full_pairs_old_bytes_and_minimum_plus_one(self):
        services=[(i,0,[0,5],1000+i) for i in range(5)]
        services += [(10,0,[0,1],10),(11,0,[1,2],10),(12,0,[2,4],10),
                     (13,0,[2,3],10),(14,0,[3,4],10),(15,0,[4,6],10),(16,0,[6,7],10)]
        engine,old,_=self.network(services)
        base={b:data for _,b,data in old.rows(0,8)};engine.baseline(base.items())
        changes={b:data for _,b,data in engine.rows(0,12)}
        self.assertNotIn(5,changes)
        self.assertEqual(changes[4][1:len(base[4])],base[4][1:])
        self.assertEqual([p['units'] for p in staged.decode(changes[4])],[6,9])
        for b,data in changes.items():
            before=base.get(b,b'\0');self.assertLess(before[0],data[0]);self.assertLessEqual(data[0],5)
            self.assertEqual(data[1:len(before)],before[1:])
            paths=staged.decode(data);self.assertLessEqual(max(p['units'] for p in paths),min(p['units'] for p in paths)+3)

    def test_target_pruning_and_representatives_match_exhaustive_enumeration(self):
        for seed in range(35):
            rng=random.Random(7200+seed)
            services=[(i,int(rng.random()<.5),rng.sample(range(6),2),rng.randrange(1,8)*10) for i in range(10)]
            walks=[(0,1,1,20,0),(2,3,0,30,40),(4,5,1,10,0)]
            engine,old,db=self.network(services,walks)
            actual={b:staged.decode(data) for _,b,data in engine.rows(0,12)}
            expected=ExpandedKernelTests.exhaustive(db,0,12)
            self.assertEqual(actual,expected,seed)
            base={b:data for _,b,data in old.rows(0,8)};engine.baseline(base.items())
            changes={b:staged.decode(data) for _,b,data in engine.rows(0,12)}
            expected_changes={b:paths for b,paths in expected.items() if len(paths)>base.get(b,b'\0')[0]}
            self.assertEqual(changes,expected_changes,('topup',seed))
            for schedule in ((9,10,11,12),(9,12)):
                merged=dict(base);incremental={};floor=8
                for ceiling in schedule:
                    engine.baseline(merged.items(),completed_units=floor)
                    for _,b,data in engine.rows(0,ceiling):merged[b]=data;incremental[b]=staged.decode(data)
                    floor=ceiling
                self.assertEqual(incremental,expected_changes,('incremental',seed,schedule))


class TopupPersistenceTests(SimpleTestCase):
    def test_resume_preserves_both_previous_tables_and_serves_four(self):
        import json,sqlite3
        from unittest.mock import patch
        from transit import test_weighted_transfers as weighted
        from transit.sptrans import expanded_materialized as expanded,topup_materialized as topup,store,graph,staged_adapter
        from transit.test_rail import NOW
        from mbm import routing_config as config
        weighted.WeightedTransferTests.network(self,[(f'L{i}','1',[str(i),str(i+1)],60) for i in range(13)])
        walks=store.database_path().with_suffix('.test-walks.sqlite3')
        with sqlite3.connect(walks) as db:
            db.executescript('CREATE TABLE walk_edge(origin,destination,seconds,distance_meters,status);CREATE TABLE walk_meta(value);')
            db.execute('INSERT INTO walk_meta VALUES(?)',(json.dumps({'source_gtfs':graph.fingerprint(store.database_path()),'configuration':config.walking_signature(),'stops':14}),))
        path=staged.prepare(walks,progress=lambda x:None)
        for stage in (0,1):staged.build(stage,min_free_gib=0,progress=lambda x:None)
        expanded.build(path,workers=1,min_free_gib=0,progress=lambda x:None)
        with sqlite3.connect(path) as db:
            before={table:db.execute(f'SELECT * FROM {table} ORDER BY origin,destination').fetchall() for table in ('paths','expanded_paths')}
        with self.assertRaises(OSError):topup.build(path,workers=1,min_free_gib=10**9,origins=[0],progress=lambda x:None)
        partial=topup.build(path,workers=1,min_free_gib=0,origins=[0],progress=lambda x:None)
        self.assertFalse(partial['complete']);self.assertEqual(partial['origins'],1)
        with sqlite3.connect(path) as db:
            meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0])
            current=meta['topup_signature']
            self.assertFalse(topup.signature_matches({**current,'kernel':'unknown'},meta['expanded_signature']))
            self.assertTrue(topup.signature_matches({**current,'kernel':topup.PRE_SMALLSETS_KERNEL},meta['expanded_signature']))
            self.assertFalse(topup.signature_matches({**current,'kernel':topup.PRE_PRUNING_KERNEL,'max_cost_units':15},meta['expanded_signature']))
            meta['topup_signature']={**current,'kernel':topup.PRE_PRUNING_KERNEL}
            db.execute('UPDATE metadata SET value=?',(json.dumps(meta),))
        result=topup.build(path,workers=1,min_free_gib=0,progress=lambda x:None)
        self.assertTrue(result['complete']);self.assertEqual(result['origins'],14)
        with sqlite3.connect(path) as db:
            for table,rows in before.items():self.assertEqual(rows,db.execute(f'SELECT * FROM {table} ORDER BY origin,destination').fetchall())
        with patch.object(topup,'calculate',side_effect=AssertionError('Already complete')):
            self.assertTrue(topup.build(path,workers=1,min_free_gib=0,progress=lambda x:None)['complete'])
        with store.connection() as db:
            journeys=list(staged_adapter.progressive(db,store.get_stop(db,'0'),store.get_stop(db,'13'),4,NOW))[-1]
            self.assertEqual(journeys['materialization_max_cost_units'],12)
            self.assertEqual(journeys['journeys'][0]['transfer_cost_units'],12)
            self.assertEqual(len(journeys['journeys'][0]['legs']),13)
