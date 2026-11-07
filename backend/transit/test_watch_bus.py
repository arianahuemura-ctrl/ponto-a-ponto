from unittest.mock import patch
from django.test import SimpleTestCase
from transit import test_sptrans_graph as fixtures
from transit.sptrans import realtime, tracking

class WatchBusTests(SimpleTestCase):
    def setUp(self):fixtures.GraphTests.setUp(self)

    def test_selected_vehicle_only_and_stop_index_resolved(self):
        with patch.object(realtime,'add_predictions') as predictions, \
             patch.object(realtime,'positions',return_value=([{'id':'81614'},{'id':'other'}],'ok')), \
             patch.object(tracking,'approaching',return_value={'vehicle':{'id':'81614'}}) as approach:
            response=self.client.get('/api/sptrans/trips/R1/',{'origin':'B','vehicle':'81614'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(approach.call_args.args[:3],('R1',1,[{'id':'81614'}]))
        self.assertEqual(predictions.call_args.kwargs['ttl'],5)
        self.assertEqual(response.json()['approach']['vehicle']['id'],'81614')

    def test_vehicle_disappears_without_substitution(self):
        with patch.object(realtime,'add_predictions'), \
             patch.object(realtime,'positions',return_value=([{'id':'other'}],'ok')), \
             patch.object(tracking,'approaching',return_value=None) as approach:
            response=self.client.get('/api/sptrans/trips/R1/',{'origin':'B','vehicle':'81614'})
        self.assertEqual(approach.call_args.args[2],[])
        self.assertIsNone(response.json()['approach'])

    def test_next_vehicle_requires_forecast_at_selected_stop(self):
        with patch.object(realtime,'add_predictions') as predictions, \
             patch.object(realtime,'positions',return_value=([{'id':'first'},{'id':'next'}],'ok')), \
             patch.object(tracking,'approaching',return_value=None) as approach:
            response=self.client.get('/api/sptrans/trips/R1/',{'origin':'B','next':'1'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(approach.call_args.args[:3],('R1',1,[{'id':'first'},{'id':'next'}]))
        self.assertTrue(approach.call_args.kwargs['require_prediction'])
        self.assertEqual(predictions.call_args.kwargs['ttl'],5)
        self.assertIsNone(response.json()['approach'])

    def test_passed_selected_vehicle_keeps_marker_and_adds_next(self):
        passed={'vehicle':{'id':'81614'},'selection':'passed','distance_meters':200,'geometry':[]}
        next_bus={'vehicle':{'id':'81615'},'selection':'prediction'}
        with patch.object(realtime,'add_predictions'), \
             patch.object(realtime,'positions',return_value=([{'id':'81614'},{'id':'81615'}],'ok')), \
             patch.object(tracking,'passed',return_value=[passed]), \
             patch.object(tracking,'approaching',side_effect=[None,next_bus]) as select:
            response=self.client.get('/api/sptrans/trips/R1/',{'origin':'B','vehicle':'81614'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['passed_approaches'],[passed])
        self.assertEqual(response.json()['approach'],next_bus)
        self.assertTrue(select.call_args.kwargs['require_prediction'])
