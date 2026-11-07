from django.test import SimpleTestCase


class LocationConfigTests(SimpleTestCase):
    def test_url_defines_test_position(self):
        response=self.client.get('/api/location-config/', {'latitude':'0','longitude':'180'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['position'], {'lat':0,'lon':180,'accuracy':0,'simulated':True})
        self.assertEqual(response['Cache-Control'],'no-store')

    def test_no_parameters_uses_browser_location(self):
        response=self.client.get('/api/location-config/')
        self.assertEqual(response.status_code,200)
        self.assertIsNone(response.json()['position'])
        self.assertEqual(response['Cache-Control'],'no-store')

    def test_invalid_url_is_rejected(self):
        for params in ({'latitude':'1'}, {'longitude':'2'}, {'latitude':'','longitude':''},
                       {'latitude':'NaN','longitude':'0'}, {'latitude':'0','longitude':'inf'},
                       {'latitude':'91','longitude':'0'}, {'latitude':'0','longitude':'-181'},
                       {'latitude':'abc','longitude':'0'}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/api/location-config/',params).status_code,400)


    def test_maps_coordinates_with_spaces_and_precision(self):
        for value in ('-23.561902423411315, -46.680757605637645', ' -23.561902423411315,-46.680757605637645 '):
            response=self.client.get('/api/location-config/',{'location':value})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['position'],{'lat':-23.561902423411315,'lon':-46.680757605637645,'accuracy':0,'simulated':True})

    def test_invalid_or_ambiguous_pair_is_rejected(self):
        for value in ('', '1', '1,2,3', ',2', 'NaN,0', '0,inf', '91,0', '0,-181', 'abc,2'):
            with self.subTest(value=value):
                self.assertEqual(self.client.get('/api/location-config/',{'location':value}).status_code,400)
        self.assertEqual(self.client.get('/api/location-config/',{'location':'1,2','latitude':'1','longitude':'2'}).status_code,400)
