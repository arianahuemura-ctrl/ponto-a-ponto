import random
from django.test import SimpleTestCase
from transit import test_staged_materialized as fixtures
from transit.sptrans import staged_materialized as staged
from mbm import routing_config as config


class ExpandedKernelTests(SimpleTestCase):
    def test_native_boundaries_are_checked_before_entering_legacy_code(self):
        engine,old,_=self.network([(0,0,[0,1],10)])
        for target,origin,units in [(old,0,8),(engine,-1,8),(engine,2,8),(engine,0,9)]:
            with self.assertRaises(ValueError):list(target.rows(origin,units))
        with self.assertRaises(ValueError):old.baseline([])
        engine.close()
        with self.assertRaises(ValueError):list(engine.rows(0,8))

    def network(self,services,walks=()):
        old,db=fixtures.StagedKernelTests.engine(self,services,walks)
        engine=staged.Engine(db,expanded=True);self.addCleanup(engine.close)
        return engine,old,db

    def test_eight_thirds_includes_eight_rail_changes_but_excludes_three_bus_changes(self):
        engine,_,_=self.network([(i,1,[i,i+1],60) for i in range(10)]+
            [(20+i,0,[20+i,21+i],60) for i in range(4)])
        rows={b:staged.decode(blob) for _,b,blob in engine.rows(0,8)}
        self.assertEqual(rows[9][0]['units'],8);self.assertEqual(len(rows[9][0]['legs']),9)
        self.assertNotIn(10,rows)
        bus={b:staged.decode(blob) for _,b,blob in engine.rows(20,8)}
        self.assertEqual(bus[23][0]['units'],6);self.assertNotIn(24,bus)

    def test_minimum_plus_one_and_existing_rows_are_preserved(self):
        services=[(i,0,[0,6],1000+i) for i in range(5)]
        services += [(10,0,[0,1],10),(11,0,[1,2],10),(12,0,[2,3,4,5],10)]
        engine,old,_=self.network(services)
        baseline=[(b,data) for _,b,data in old.rows(0,3)]
        engine.baseline(baseline)
        changes={b:staged.decode(data) for _,b,data in engine.rows(0,8)}
        self.assertNotIn(6,changes)  # five existing direct services stay untouched
        self.assertNotIn(2,changes)  # no additional distinct valid sequence
        self.assertEqual(changes[5][0]['units'],6)
        # A direct alternative forbids cost-two detours even with empty slots.
        engine,_,_=self.network([(0,0,[0,3],1000),(1,0,[0,1],10),(2,0,[1,2],10),(3,0,[2,3],10)])
        rows={b:staged.decode(data) for _,b,data in engine.rows(0,8)}
        self.assertEqual([p['units'] for p in rows[3]],[0])

    def test_two_later_bus_services_can_exclude_the_first_two_prefixes(self):
        services=[(i,0,[0,1],10+i) for i in range(9)]
        services += [(0,0,[1,2],10),(1,0,[2,3],10)]
        engine,_,db=self.network(services)
        actual={b:staged.decode(blob) for _,b,blob in engine.rows(0,8)}
        self.assertEqual(actual,self.exhaustive(db,0,8))
        self.assertEqual(len(actual[3]),5)

    def test_topup_keeps_the_original_encoded_paths_as_a_prefix(self):
        services=[(0,0,[0,1],10),(1,0,[1,4],10),(2,0,[1,2],10),(3,0,[2,4],10)]
        engine,old,_=self.network(services)
        baseline={b:data for _,b,data in old.rows(0,3)}
        engine.baseline(baseline.items())
        changes={b:data for _,b,data in engine.rows(0,8)}
        self.assertEqual(changes[4][0],2)
        self.assertEqual(changes[4][1:len(baseline[4])],baseline[4][1:])

    def test_optimized_enumeration_matches_exhaustive_search(self):
        for seed in range(24):
            rng=random.Random(seed)
            services=[(i,int(rng.random()<.6),rng.sample(range(5),2),rng.randrange(1,8)*10) for i in range(8)]
            walks=[(0,1,1,20,0),(2,3,0,30,40)]
            engine,_,db=self.network(services,walks)
            for ceiling in (3,8):
                actual={b:staged.decode(blob) for _,b,blob in engine.rows(0,ceiling)}
                self.assertEqual(actual,self.exhaustive(db,0,ceiling),(seed,ceiling))

    @staticmethod
    def exhaustive(db,origin,ceiling):
        patterns={pid:(service,rail,wait) for pid,service,rail,wait in db.execute('SELECT id,service,rail,wait FROM patterns')}
        rides={row[0]:row for row in db.execute('SELECT * FROM rides')}
        feet={row[0]:row for row in db.execute('SELECT * FROM walks')}
        outgoing={};walks={};answers={}
        for row in rides.values():outgoing.setdefault(row[2],[]).append(row)
        for row in feet.values():walks.setdefault(row[1],[]).append(row)
        def visit(at,legs,units,seconds,walking,sequence,railway):
            def offer(dest,egress,extra):
                if dest==origin:return
                edges=tuple(e for e,w in legs)+(0,)*(9-len(legs))
                ws=tuple(w for e,w in legs)+(0,)*(9-len(legs))+(egress,)
                score=(units,seconds+extra,walking+extra,edges,ws)
                bucket=answers.setdefault(dest,{})
                if sequence not in bucket or score<bucket[sequence][0]:
                    bucket[sequence]=(score,{'units':units,'legs':list(legs),'egress':egress})
            offer(at,0,0)
            for wid,a,b,internal,secs,meters in walks.get(at,[]):offer(b,wid,secs)
            options=[(at,0,1,0)]+[(b,wid,internal,secs) for wid,a,b,internal,secs,meters in walks.get(at,[])]
            for stop,wid,internal,secs in options:
                for eid,pid,a,b,boarding,alighting,ride_seconds in outgoing.get(stop,[]):
                    service,rail,wait=patterns[pid]
                    cost=1 if internal and railway and rail else 3
                    if units+cost>ceiling or service in sequence or b==origin:continue
                    visit(b,legs+((eid,wid),),units+cost,seconds+secs+config.TRANSFER_SECONDS+wait+ride_seconds,walking+secs,sequence+(service,),rail)
        starts=[(origin,0,0)]+[(b,wid,secs) for wid,a,b,internal,secs,meters in walks.get(origin,[]) if internal]
        for stop,wid,secs in starts:
            for eid,pid,a,b,boarding,alighting,ride_seconds in outgoing.get(stop,[]):
                if b==origin:continue
                service,rail,wait=patterns[pid]
                visit(b,((eid,wid),),0,secs+ride_seconds+wait,secs,(service,),rail)
        result={}
        for dest,paths in answers.items():
            ranked=sorted(paths.values(),key=lambda x:x[0]);minimum=ranked[0][0][0]
            result[dest]=[p for score,p in ranked if score[0]<=minimum+3][:5]
        return result


class ExpandedPersistenceTests(SimpleTestCase):
    def test_resume_keeps_base_immutable_and_reader_uses_new_paths(self):
        import json,sqlite3
        from unittest.mock import patch
        from transit import test_weighted_transfers as weighted
        from transit.sptrans import expanded_materialized as expanded,store,graph,staged_adapter
        from transit.test_rail import NOW
        weighted.WeightedTransferTests.network(self,[(f'L{i}','1',[str(i),str(i+1)],60) for i in range(9)])
        walks=store.database_path().with_suffix('.test-walks.sqlite3')
        with sqlite3.connect(walks) as db:
            db.executescript('CREATE TABLE walk_edge(origin,destination,seconds,distance_meters,status);CREATE TABLE walk_meta(value);')
            db.execute('INSERT INTO walk_meta VALUES(?)',(json.dumps({'source_gtfs':graph.fingerprint(store.database_path()),'configuration':config.walking_signature(),'stops':10}),))
        path=staged.prepare(walks,progress=lambda x:None)
        staged.build(0,min_free_gib=0,progress=lambda x:None)
        staged.build(1,min_free_gib=0,progress=lambda x:None)
        with sqlite3.connect(path) as db:before=db.execute('SELECT * FROM paths ORDER BY origin,destination').fetchall()
        with self.assertRaises(OSError):expanded.build(path,workers=1,min_free_gib=10**9,origins=[0],progress=lambda x:None)
        partial=expanded.build(path,workers=1,min_free_gib=0,origins=[0],progress=lambda x:None)
        self.assertFalse(partial['complete']);self.assertEqual(partial['origins'],1)
        result=expanded.build(path,workers=1,min_free_gib=0,progress=lambda x:None)
        self.assertTrue(result['complete']);self.assertEqual(result['origins'],10)
        with sqlite3.connect(path) as db:self.assertEqual(before,db.execute('SELECT * FROM paths ORDER BY origin,destination').fetchall())
        with patch.object(expanded,'calculate',side_effect=AssertionError('Already complete')):
            self.assertTrue(expanded.build(path,workers=1,min_free_gib=0,progress=lambda x:None)['complete'])
        with store.connection() as db:
            journeys=list(staged_adapter.progressive(db,store.get_stop(db,'0'),store.get_stop(db,'9'),3,NOW))[-1]
            self.assertEqual(journeys['materialization_max_cost_units'],8)
            self.assertEqual(journeys['journeys'][0]['transfer_cost_units'],8)
            self.assertEqual(len(journeys['journeys'][0]['legs']),9)
