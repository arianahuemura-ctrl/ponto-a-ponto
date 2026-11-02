import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from transit.test_staged_materialized import StagedKernelTests
from transit.test_short_walks import ShortWalkTests
from transit.sptrans import staged_parallel, staged_materialized as staged, short_walks
from transit.sptrans import walking_slots, store


class ParallelStagedTests(StagedKernelTests):
    def test_cost_one_preserves_the_stage_zero_walking_slot(self):
        services=[(i,0,[0,2],1000) for i in range(4)]+[(10,0,[0,1],30),(11,0,[1,2],30)]
        engine,source=self.engine(services)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);target=p/'staged.sqlite3';feet=p/'walks.sqlite3';gtfs=p/'source.sqlite3'
            with sqlite3.connect(feet) as db:
                db.execute('CREATE TABLE walk_edge(origin,destination,distance_meters,seconds,source,status)')
                db.execute("INSERT INTO walk_edge VALUES('0','2',100,80,'verified fixture','verified')")
            with sqlite3.connect(gtfs) as db:
                db.execute('CREATE TABLE stops(stop_id,stop_lat,stop_lon)')
                db.executemany('INSERT INTO stops VALUES(?,?,?)',[(str(i),-23.5,-46.6+i*.001) for i in range(3)])
            signature={'walks':[str(feet)]}
            with sqlite3.connect(target) as db:
                source.backup(db)
                db.execute('ALTER TABLE stops ADD COLUMN sid TEXT');db.execute('UPDATE stops SET sid=cast(id as text)')
                db.executescript('CREATE TABLE metadata(id,value);CREATE TABLE paths(origin,destination,data,PRIMARY KEY(origin,destination));CREATE TABLE progress(stage,origin,paths,pairs,seconds,PRIMARY KEY(stage,origin));')
                db.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'signature':signature,'complete_stages':[0,1]}),))
                for o in range(3):
                    rows=list(engine.rows(o,3));db.executemany('INSERT INTO paths VALUES(?,?,?)',rows)
                    db.execute('INSERT INTO progress VALUES(1,?,?,?,0)',(o,sum(r[2][0] for r in rows),len(rows)))
            with patch.object(staged,'signature',return_value=signature),patch.object(store,'database_path',return_value=gtfs):
                result=walking_slots.reserve(target,progress=lambda x:None,min_free_gib=0)
                self.assertEqual(result['reserved_stage_zero_walks'],1)
                self.assertEqual(result['transport_alternatives_replaced'],1)
                self.assertEqual(result['walking']['walking_routes'],1)
                self.assertEqual(walking_slots.reserve(target,min_free_gib=0)['transport_alternatives_replaced'],1)
            with sqlite3.connect(target) as db:
                routes=staged.decode(db.execute('SELECT data FROM paths WHERE origin=0 AND destination=2').fetchone()[0])
                self.assertEqual(len(routes),4)
                self.assertTrue(all(r['units']==0 for r in routes))

    def test_parallel_matches_serial_native_and_resumes(self):
        engine, source=self.engine([(0,0,[0,1,2],60),(1,0,[2,3],60),(2,1,[3,4],60)],[(2,4,0,90,100)])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'network.staged.sqlite3'
            with sqlite3.connect(path) as db:
                source.backup(db)
                db.executescript('CREATE TABLE metadata(id,value);CREATE TABLE paths(origin,destination,data,PRIMARY KEY(origin,destination));CREATE TABLE progress(stage,origin,paths,pairs,seconds,PRIMARY KEY(stage,origin));')
                db.execute('INSERT INTO metadata VALUES(1,?)',(json.dumps({'signature':{'walks':['unused']},'complete_stages':[]}),))
            with patch.object(staged,'signature',return_value={'walks':['unused']}):
                partial=staged_parallel.build(0,path,workers=2,min_free_gib=0,origins=[0],progress=lambda x:None)
                self.assertFalse(partial['complete'])
                for stage in (0,1):
                    result=staged_parallel.build(stage,path,workers=2,min_free_gib=0,progress=lambda x:None)
                    self.assertTrue(result['complete'])
                    with sqlite3.connect(path) as db:
                        actual=db.execute('SELECT * FROM paths ORDER BY origin,destination').fetchall()
                    self.assertEqual(actual,sorted(row for o in range(5) for row in engine.rows(o,stage*3)))


class EarlyShortWalkTests(ShortWalkTests):
    def test_zero_stage_needs_no_expansion_tables_and_invalidates_after_upgrade(self):
        with sqlite3.connect(self.path) as db:
            db.execute('DROP TABLE expanded_paths');db.execute('DROP TABLE topup_paths')
            db.execute('UPDATE metadata SET value=?',(json.dumps({'signature':self.base,'complete_stages':[0]}),))
        report=short_walks.build(min_free_gib=0)
        self.assertEqual(report['walking_routes'],4)
        self.assertIsNotNone(short_walks.route(self.points['A'],self.points['B']))
        with sqlite3.connect(self.path) as db:
            meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0]);meta['complete_stages']=[0,1]
            db.execute('UPDATE metadata SET value=?',(json.dumps(meta),))
        self.assertIsNone(short_walks.route(self.points['A'],self.points['B']))
