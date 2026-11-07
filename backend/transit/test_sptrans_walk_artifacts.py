from django.test import SimpleTestCase
from transit.sptrans import walk_artifacts

class WalkArtifactTests(SimpleTestCase):
    def test_distances_include_both_access_offsets(self):
        self.assertEqual(walk_artifacts.classify(900,980,10,10),('verified',1000))
        self.assertEqual(walk_artifacts.classify(900,981,10,10),('over_limit',1001))
    def test_no_invented_paths_for_unreachable_or_invalid(self):
        self.assertEqual(walk_artifacts.classify(10,None,0,0),('unreachable',None))
        self.assertEqual(walk_artifacts.classify(900,20,0,0),('invalid_distance',None))
        self.assertEqual(walk_artifacts.classify(0,float('inf'),0,0),('invalid_distance',None))
    def test_bulk_public_router_is_rejected(self):
        with self.assertRaises(ValueError):
            walk_artifacts.build('https://routing.openstreetmap.de/routed-foot','foot')


class WalkMatrixBuildTests(SimpleTestCase):
    def setUp(self):
        from transit import test_sptrans_graph as fixtures
        fixtures.GraphTests.setUp(self)
        self.target=self.root/'gtfs.walks.sqlite3'

    def response(self,url,timeout):
        import io,json,urllib.parse
        from transit.sptrans import graph
        parsed=urllib.parse.urlsplit(url)
        coords=[tuple(map(float,p.split(','))) for p in parsed.path.split('/')[-1].split(';')]
        if '/nearest/' in parsed.path:
            value={'code':'Ok','waypoints':[{'distance':0,'location':coords[0],'hint':'fixture'}]}
        else:
            a=coords[0][::-1]
            value={'code':'Ok','distances':[[graph.distance(a,b[::-1])*1.1 for b in coords[1:]]]}
        return io.StringIO(json.dumps(value))

    def test_full_pipeline_classification_and_atomic_failure(self):
        import json,sqlite3
        from unittest.mock import patch
        from transit.sptrans import graph,direct,city_connections
        with patch('urllib.request.urlopen',side_effect=self.response):
            report=walk_artifacts.build('http://127.0.0.1:5099','test-foot',source=self.index,target=self.target)
        with sqlite3.connect(self.target) as db:
            self.assertEqual(sum(report['counts'].values()),report['candidate_pairs'])
            self.assertGreater(report['counts'].get('verified',0),0)
            self.assertEqual(db.execute("SELECT count(*) FROM walk_edge WHERE status='verified' AND (distance_meters>1000 OR abs(seconds-distance_meters/1.25)>0.00001)").fetchone()[0],0)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        dp=self.root/'direct.sqlite3';cp=self.root/'connections.sqlite3'
        direct.build(source=self.index,target=dp)
        combined=city_connections.build(source=dp,graph_source=self.index,target=cp)
        self.assertEqual(combined['verified_walks'],report['counts']['verified'])
        city_connections.structural_query('A','E',path=cp)
        before=self.target.read_bytes()
        with patch('urllib.request.urlopen',side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                walk_artifacts.build('http://127.0.0.1:5099','test-foot',source=self.index,target=self.target)
        self.assertEqual(self.target.read_bytes(),before)
        with sqlite3.connect(self.target) as db:
            db.execute("UPDATE walk_edge SET source='changed'")
        with self.assertRaisesRegex(ValueError,'pedestre desatualizado'):
            city_connections.structural_query('A','E',path=cp)
