import sqlite3
from unittest.mock import patch
from django.test import SimpleTestCase
from transit import test_rail as fixtures


class RailNetworkTests(SimpleTestCase):
    def setUp(self):
        fixtures.MultimodalTests.setUp(self)
        with sqlite3.connect(self.path) as db:
            db.executemany('INSERT INTO shapes VALUES(?,?,?,?)', [
                ('S',-23.50,-46.6,1),('S',-23.55,-46.6,2),
                ('reverse',-23.55,-46.6,1),('reverse',-23.50,-46.6,2),
            ])
            db.execute("INSERT INTO trips VALUES('L2','daily','duplicate','Volta','1','reverse')")
            db.execute("UPDATE routes SET route_type='2' WHERE route_id='L4'")

    def test_network_without_endpoints_has_colors_and_deduplicated_gtfs_shapes(self):
        with patch('transit.sptrans.realtime.positions',side_effect=AssertionError('No live lookup')):
            response=self.client.get('/api/sptrans/rail-network/')
        self.assertEqual(response.status_code,200)
        result=response.json()
        self.assertTrue(result['revision'])
        self.assertEqual([line['code'] for line in result['lines']],['L2','L4'])
        self.assertEqual([line['mode'] for line in result['lines']],['metro','rail'])
        for line in result['lines']:
            self.assertEqual(line['color'],'#008800')
            self.assertEqual(line['geometries'],[[[-23.50,-46.6],[-23.55,-46.6]]])

    def test_source_revision_invalidates_cache_and_missing_shapes_are_omitted(self):
        before=self.client.get('/api/sptrans/rail-network/').json()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE trips SET shape_id='missing' WHERE route_id='L4'")
        after=self.client.get('/api/sptrans/rail-network/').json()
        self.assertNotEqual(after['revision'],before['revision'])
        self.assertEqual([line['code'] for line in after['lines']],['L2'])
