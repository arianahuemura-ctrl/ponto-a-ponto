import io
import json
from unittest.mock import patch
from django.test import SimpleTestCase
from django.core.cache import cache
from transit.sptrans import walking, directions


class WalkingTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        limiter=patch('transit.sptrans.walking.reserve_request',return_value=True)
        limiter.start();self.addCleanup(limiter.stop)
        self.a={'id':'1','lat':-23.55,'lon':-46.63}
        self.b={'id':'2','lat':-23.5502,'lon':-46.63}
        self.payload={'code':'Ok','waypoints':[{'distance':0},{'distance':0}],
            'routes':[{'distance':40,'geometry':{'coordinates':[[-46.63,-23.55],[-46.63,-23.5502]]}}]}

    def response(self): return io.BytesIO(json.dumps(self.payload).encode())

    @patch('transit.sptrans.walking.reserve_request',return_value=False)
    @patch('transit.sptrans.walking.urlopen')
    def test_rate_limit_does_not_call_provider(self, fetch, reserve):
        self.assertFalse(walking.route(self.a,self.b)['available'])
        fetch.assert_not_called()

    @patch('transit.sptrans.walking.urlopen')
    def test_foot_route_and_cache(self, fetch):
        fetch.return_value=self.response()
        result=walking.route(self.a,self.b)
        self.assertTrue(result['available'])
        self.assertEqual(result['distance_meters'],40)
        self.assertEqual(result['duration_minutes'],0.5)
        self.assertEqual(result['geometry'][0],[-23.55,-46.63])
        self.assertIn('/routed-foot/',fetch.call_args.args[0].full_url)
        self.assertEqual(walking.route(self.a,self.b),result)
        fetch.assert_called_once()

    @patch('transit.sptrans.walking.urlopen')
    def test_detour_is_not_replaced_with_straight_line(self, fetch):
        self.payload['routes'][0]['distance']=2500
        fetch.return_value=self.response()
        self.assertGreater(walking.route(self.a,self.b)['duration_minutes'],30)

    @patch('transit.sptrans.walking.urlopen')
    def test_does_not_claim_zero_length_crossing(self, fetch):
        self.payload['routes'][0]['distance']=0
        fetch.return_value=self.response()
        self.assertFalse(walking.route(self.a,self.b)['available'])

    @patch('transit.sptrans.walking.urlopen',side_effect=TimeoutError)
    def test_timeout_no_invented_geometry(self, fetch):
        result=walking.route(self.a,self.b)
        self.assertFalse(result['available'])
        self.assertNotIn('geometry',result)

    @patch('transit.sptrans.walking.urlopen')
    def test_remote_snap_rejected(self, fetch):
        self.payload['waypoints'][0]['distance']=80
        fetch.return_value=self.response()
        self.assertFalse(walking.route(self.a,self.b)['available'])

    @patch('transit.sptrans.walking.urlopen')
    def test_same_stop_and_range_do_not_call_provider(self, fetch):
        self.assertFalse(walking.route(self.a,self.a)['available'])
        self.assertFalse(walking.route(self.a,dict(self.b,lat=-24))['available'])
        fetch.assert_not_called()


class DirectionTests(SimpleTestCase):
    def test_opposite_shapes_produce_opposite_arrows(self):
        points=[(-23.55,-46.63),(-23.551,-46.63)]
        self.assertEqual(directions.tangent(points,points[0]),180)
        self.assertEqual(directions.tangent(points[::-1],points[0]),0)

    def test_remote_missing_or_ambiguous_shape_omits_arrow(self):
        a=(-23.55,-46.63);b=(-23.551,-46.63)
        self.assertIsNone(directions.tangent([],a))
        self.assertIsNone(directions.tangent([a,b],(-24,-46)))
        self.assertIsNone(directions.tangent([a,b,a],a))
