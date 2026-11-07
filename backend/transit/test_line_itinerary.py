from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase
from transit.sptrans.tracking import itinerary
from transit.test_sptrans import GTFSCase

class ItineraryTests(SimpleTestCase):
    shape=[(-23.5,-46.6),(-23.51,-46.6),(-23.52,-46.6)]
    stops=[{'id':str(i),'name':str(i),'lat':p[0],'lon':p[1]} for i,p in enumerate(shape,1)]
    def result(self,origin,positions=None,stops=None,index=None,shape=None):
        with patch('transit.sptrans.tracking.store.database_path',return_value=Path(__file__)),patch('transit.sptrans.tracking.trip_geometry',return_value=(self.shape if shape is None else shape,positions if positions is not None else [(i,p) for i,p in enumerate(self.shape)])):
            return itinerary('T',stops or self.stops,origin,index)
    def test_middle_stop_preserves_both_sides_and_terminal(self):
        r=self.result('2');self.assertEqual(r['before'],self.shape[:2]);self.assertEqual(r['after'],self.shape[1:]);self.assertEqual(r['terminal'],self.stops[-1]);self.assertTrue(r['split_available'])
    def test_endpoints_do_not_invent_segment(self):
        self.assertEqual(self.result('1')['before'],self.shape[:1]);self.assertEqual(self.result('3')['after'],self.shape[-1:])
    def test_fractional_projection_is_shared_by_segments(self):
        p=(-23.515,-46.6);r=self.result('2',[(0,self.shape[0]),(1.5,p),(2,self.shape[2])]);self.assertEqual(r['before'],self.shape[:2]+[p]);self.assertEqual(r['after'],[p,self.shape[-1]])
    def test_ambiguous_stop_requires_occurrence(self):
        stops=[self.stops[0],self.stops[1],self.stops[0]];self.assertFalse(self.result('1',stops=stops)['split_available']);self.assertTrue(self.result('1',stops=stops,index=2)['split_available'])
    def test_missing_projection_or_shape_remains_unavailable(self):
        self.assertFalse(self.result('2',positions=[None]*3)['split_available']);self.assertEqual(self.result('2',positions=[],shape=[])['geometry'],[])
    def test_shape_extends_beyond_last_stop(self):
        extended=self.shape+[(-23.53,-46.6)]
        r=self.result('2',shape=extended)
        self.assertTrue(r['terminal_mismatch'])
        self.assertEqual(r['terminal'],self.stops[-1])
        self.assertEqual(r['endpoint'],{'kind':'shape','lat':-23.53,'lon':-46.6})
        self.assertEqual(r['after'][-1],extended[-1])
    def test_consistent_terminal_uses_stop(self):
        r=self.result('2')
        self.assertFalse(r['terminal_mismatch'])
        self.assertEqual(r['endpoint']['kind'],'stop')
    def test_loop_tail_detected_even_if_endpoint_near_stop(self):
        r=self.result('2',shape=self.shape+[(-23.53,-46.6),self.shape[-1]])
        self.assertTrue(r['terminal_mismatch'])

    def test_invalid_index_rejected(self):
        with self.assertRaises(ValueError):self.result('2',index=0)

class ItineraryApiTests(GTFSCase):
    @patch('transit.sptrans.realtime.add_predictions')
    @patch('transit.sptrans.realtime.positions',return_value=([], 'unavailable'))
    def test_itinerary_without_any_live_vehicle(self,positions,predictions):
        r=self.client.get('/api/sptrans/trips/T/',{'origin':'2','next':'1','all':'1'})
        self.assertEqual(r.status_code,200);data=r.json();self.assertEqual(data['vehicles'],[]);self.assertIsNone(data['approach']);self.assertTrue(data['itinerary']['split_available']);self.assertEqual(data['itinerary']['terminal']['id'],'3')
