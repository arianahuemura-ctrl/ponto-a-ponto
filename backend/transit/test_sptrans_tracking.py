from django.test import SimpleTestCase
from transit.sptrans.tracking import select_approach

class TrackingTests(SimpleTestCase):
    shape=[(-23.55,-46.65),(-23.55,-46.64),(-23.55,-46.63)]
    boarding=(1.5,(-23.55,-46.635))

    def vehicle(self,identifier,lon,lat=-23.55):
        return {'id':identifier,'lat':lat,'lon':lon}

    def test_selects_upstream_and_clips_at_boarding(self):
        result=select_approach(self.shape,self.boarding,[self.vehicle('passed',-46.631),self.vehicle('far',-46.648),self.vehicle('next',-46.642)])
        self.assertEqual(result['vehicle']['id'],'next')
        self.assertEqual(result['selection'],'upstream')
        self.assertAlmostEqual(result['geometry'][0][1],-46.642)
        self.assertEqual(result['geometry'][-1],self.boarding[1])
        self.assertNotIn(self.shape[-1],result['geometry'])

    def test_prediction_overrides_nearest_vehicle(self):
        result=select_approach(self.shape,self.boarding,[self.vehicle('near',-46.64),self.vehicle('predicted',-46.645)],[{'vehicle':'predicted'}])
        self.assertEqual(result['vehicle']['id'],'predicted')
        self.assertEqual(result['selection'],'prediction')

    def test_off_route_or_passed_vehicles_are_not_shown(self):
        self.assertIsNone(select_approach(self.shape,self.boarding,[self.vehicle('off',-46.64,-23.56),self.vehicle('past',-46.631)]))

    def test_repeated_return_passage_is_ambiguous(self):
        self.assertIsNone(select_approach(self.shape+[self.shape[0]],self.boarding,[self.vehicle('ambiguous',-46.645)]))

    def test_missing_geometry_or_boarding_is_unavailable(self):
        self.assertIsNone(select_approach([],self.boarding,[self.vehicle('x',-46.64)]))
        self.assertIsNone(select_approach(self.shape,None,[]))

class ReachableArrivalTests(SimpleTestCase):
    def test_walk_excludes_early_bus_and_unknown_vehicle_fallback(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from transit.sptrans.tracking import reachable_arrivals
        now=datetime(2026,10,7,6,45,tzinfo=ZoneInfo('America/Sao_Paulo'))
        rows=[{'vehicle':v,'time':t,'observed_at':now.isoformat()} for v,t in [('early','06:48'),('rounded','06:58'),('next','06:59')]]
        result=reachable_arrivals(rows,now,13.5*60)
        self.assertEqual([a['vehicle'] for a in result],['next'])
        vehicles=[{'id':'early','lat':-23.55,'lon':-46.64},{'id':'next','lat':-23.55,'lon':-46.645}]
        approach=select_approach(TrackingTests.shape,TrackingTests.boarding,vehicles,result,require_prediction=True)
        self.assertEqual(approach['vehicle']['id'],'next')
        self.assertIsNone(select_approach(TrackingTests.shape,TrackingTests.boarding,vehicles,[],require_prediction=True))

    def test_midnight_and_stale_observations(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from transit.sptrans.tracking import reachable_arrivals
        now=datetime(2026,10,7,23,55,tzinfo=ZoneInfo('America/Sao_Paulo'))
        rows=[{'vehicle':'next','time':'00:10','observed_at':now.isoformat()}, {'vehicle':'old','time':'00:20','observed_at':'2026-10-07T23:40:00-03:00'}]
        result=reachable_arrivals(rows,now,14*60)
        self.assertEqual(len(result),1)
        self.assertTrue(result[0]['arrival_at'].startswith('2026-10-08T00:10'))

class DirectPredictionTests(SimpleTestCase):
    def test_stop_missing_from_catalogue_still_has_direct_predictions(self):
        from unittest.mock import patch
        from django.utils import timezone
        from transit.sptrans import realtime
        row={'code':'715M-10','headsign':'Lgo. Da Pólvora','arrivals':[]}
        origin={'id':'1211364','lat':-23.570983,'lon':-46.70966}
        payload={'hr':'06:52','p':{'cp':1211364,'py':origin['lat'],'px':origin['lon'],'l':[{'cl':490,'vs':[{'p':81604,'t':'06:59','ta':timezone.now().isoformat()}]}]}}
        with patch.object(realtime,'line_mapping',return_value={'cl':490}),patch.object(realtime,'stop_mapping') as mapping,patch.object(realtime.client,'get',return_value=payload) as get:
            realtime.add_predictions(row,origin,ttl=15)
        mapping.assert_not_called()
        get.assert_called_once_with('Previsao',{'codigoParada':1211364,'codigoLinha':490},15)
        self.assertEqual(row['api_stop'],1211364)
        self.assertEqual(row['arrivals'][0]['vehicle'],'81604')

    def test_direct_response_for_wrong_location_is_rejected(self):
        from unittest.mock import patch
        from transit.sptrans import realtime
        row={'code':'715M-10','headsign':'Destino','arrivals':[]}
        origin={'id':'1211364','lat':-23.570983,'lon':-46.70966}
        for point in [{'cp':999,'py':origin['lat'],'px':origin['lon']},{'cp':1211364,'py':-23.6,'px':-46.7}]:
            with patch.object(realtime,'line_mapping',return_value={'cl':490}),patch.object(realtime,'stop_mapping',return_value=None),patch.object(realtime.client,'get',return_value={'p':point}):
                realtime.add_predictions(row,origin)
            self.assertEqual(row['arrivals'],[])

class PassedVehicleTests(SimpleTestCase):
    def test_next_and_passed_are_separate_and_limit_uses_route_distance(self):
        from transit.sptrans.tracking import select_passed
        from transit.sptrans.directions import distance
        shape=[(0,0),(0,.02)];anchor=(.5,(0,.01))
        meter=1/distance((0,0),(0,1))
        vehicles=[{'id':str(m),'lat':0,'lon':.01+m*meter} for m in (-100,100,499,501,800)]
        result=select_passed(shape,anchor,vehicles)
        self.assertEqual([v['vehicle']['id'] for v in result],['100','499'])
        self.assertEqual(select_approach(shape,anchor,vehicles)['vehicle']['id'],'-100')
        self.assertTrue(all(v['selection']=='passed' and v['geometry']==[] for v in result))

    def test_return_path_and_missing_coordinates_are_not_guessed(self):
        from transit.sptrans.tracking import select_passed
        shape=[(0,0),(0,.01),(0,.02),(0,0)]
        self.assertEqual(select_passed(shape,(1,(0,.01)),[{'id':'x','lat':0,'lon':.011}]),[])
        self.assertEqual(select_passed(shape,(1,(0,.01)),[{'id':'x'}]),[])
