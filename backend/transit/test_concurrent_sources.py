from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Event, get_ident
import sqlite3
import time
from unittest.mock import patch
from django.test import SimpleTestCase
from transit.sptrans import concurrent_sources as sources, alternatives, staged_adapter, store, journey_completion


def event(identifier):
    return {'journeys':[{'id':identifier}], 'complete':True}


class ConcurrentSourcesTests(SimpleTestCase):
    def test_ready_source_publishes_while_other_source_is_blocked(self):
        release=Event();finished=Event()
        def slow():
            try:
                release.wait(3)
                yield event('slow')
            finally:finished.set()
        def fast():yield event('fast')
        stream=sources.merge({'slow':slow,'prepared':fast})
        try:
            name,result,done=next(stream)
            self.assertEqual(name,'prepared');self.assertEqual(result['journeys'][0]['id'],'fast')
            self.assertFalse(done);self.assertFalse(finished.is_set())
            release.set()
            remainder=list(stream)
            self.assertTrue(remainder[-1][2]);self.assertTrue(finished.wait(1))
        finally:release.set();stream.close();finished.wait(1)

    def test_disconnect_does_not_wait_for_running_source(self):
        release=Event();started=Event();finished=Event()
        def slow():
            try:
                started.set();release.wait(3);yield event('slow')
            finally:finished.set()
        def fast():
            started.wait(1);yield event('fast')
        stream=sources.merge({'slow':slow,'prepared':fast})
        try:
            next(stream);start=time.monotonic();stream.close()
            self.assertLess(time.monotonic()-start,.2)
        finally:release.set();self.assertTrue(finished.wait(1))

    def test_failure_keeps_other_results_and_marks_incomplete(self):
        def failed():
            raise ValueError('fixture')
            yield
        def fast():yield event('fast')
        with self.assertLogs(sources.log,level='ERROR'):
            rows=list(sources.merge({'broken':failed,'prepared':fast}))
        self.assertTrue(any(r and r.get('failed_sources')==['broken'] for _,r,_ in rows))
        self.assertTrue(any(r and r['journeys']==[{'id':'fast'}] for _,r,_ in rows))
        self.assertEqual(sum(done for _,_,done in rows),1)

    def test_timeout_preserves_partial_result(self):
        release=Event();finished=Event()
        def slow():
            try:release.wait(3);yield event('slow')
            finally:finished.set()
        def fast():yield event('fast')
        try:
            rows=list(sources.merge({'slow':slow,'prepared':fast},timeout=.1,heartbeat=.02))
            self.assertTrue(any(r and r.get('timed_out_sources')==['slow'] for _,r,_ in rows))
            self.assertTrue(any(r and r['journeys']==[{'id':'fast'}] for _,r,_ in rows))
            self.assertTrue(rows[-1][2])
        finally:release.set();finished.wait(1)

    def test_saturation_is_explicit_without_waiting(self):
        with patch.object(sources,'BACKGROUND_SLOTS') as slots:
            slots.acquire.return_value=False
            rows=list(sources.merge({'rail':lambda:iter([])}))
        self.assertEqual(rows[0][1]['busy_sources'],['rail'])
        self.assertTrue(rows[-1][2])

    def test_second_materialized_option_passes_filter_before_slow_searches(self):
        release=Event();parent=get_ident();finished=[]
        @contextmanager
        def connection():
            db=sqlite3.connect(':memory:');db.execute('CREATE TABLE routes(route_type)')
            try:yield db
            finally:db.close()
        def route(name,short=False):
            return {'id':name,'duration_minutes':10,'walking_meters':0,'walking_minutes':0,'walks':[],'transfers':0,
                    'legs':[{'code':name,'trip_id':name,'route_id':name,'headsign':'Destino','mode':'bus',
                             'geometry':[[0,0],[0,.00001 if short else .01]]}]}
        def prepared(db,*args):
            self.assertNotEqual(get_ident(),parent);db.execute('SELECT 1')
            yield {'journeys':[route('short',True)],'complete':False}
            yield {'journeys':[route('valid')],'complete':True}
        def slow(db,*args,**kwargs):
            done=Event();finished.append(done)
            try:
                self.assertNotEqual(get_ident(),parent);db.execute('SELECT 1')
                release.wait(3);yield {'journeys':[],'complete':True}
            finally:done.set()
        def foot(*args,**kwargs):
            if kwargs.get('materialized_only'):return None
            release.wait(3);return None
        with connection() as db,patch.object(store,'connection',connection),patch.object(staged_adapter,'progressive',prepared),\
             patch.object(alternatives,'_bus_progressive',slow),patch.object(alternatives,'_raptor_progressive',slow),\
             patch.object(journey_completion,'direct_walk',foot),patch.object(journey_completion.Completion,'improve',side_effect=lambda j:j):
            stream=alternatives.progressive(db,{}, {},now=datetime(2026,11,3,tzinfo=timezone.utc))
            try:
                for result in stream:
                    if result['journeys']:break
                self.assertEqual([j['id'] for j in result['journeys']],['valid'])
                self.assertFalse(result['complete']);self.assertFalse(release.is_set())
                release.set();remaining=list(stream)
                self.assertTrue(remaining[-1]['complete'])
                self.assertEqual([j['id'] for j in remaining[-1]['journeys']],['valid'])
            finally:
                release.set();stream.close()
                for done in finished:done.wait(1)
