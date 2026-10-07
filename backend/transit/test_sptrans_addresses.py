import io
import json
from unittest.mock import patch
from urllib.error import URLError
from django.core.cache import cache
from django.test import SimpleTestCase


class AddressTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_neighborhoods_preserved_duplicates_removed_and_response_cached(self):
        features=[{'properties':{'name':'Rua de teste','district':district,'city':'São Paulo','osm_id':i},
                   'geometry':{'coordinates':[-46.63,-23.55]}} for i,district in enumerate(['Centro','Bela Vista','Centro'])]
        with patch('transit.sptrans.addresses.urlopen',return_value=io.StringIO(json.dumps({'features':features}))) as fetch:
            first=self.client.get('/api/sptrans/addresses/',{'q':'Rua de teste'})
            second=self.client.get('/api/sptrans/addresses/',{'q':'rua de teste'})
        self.assertEqual(first.status_code,200)
        self.assertEqual(first.json(),second.json())
        self.assertEqual([s['district'] for s in first.json()['suggestions']],['Centro','Bela Vista'])
        fetch.assert_called_once()

    def test_short_query_never_contacts_provider(self):
        with patch('transit.sptrans.addresses.urlopen') as fetch:
            self.assertEqual(self.client.get('/api/sptrans/addresses/',{'q':'ru'}).json(),{'suggestions':[]})
        fetch.assert_not_called()

    def test_provider_failure_does_not_cache_error(self):
        with patch('transit.sptrans.addresses.urlopen',side_effect=URLError('unavailable')) as fetch:
            for _ in range(2):
                self.assertEqual(self.client.get('/api/sptrans/addresses/',{'q':'Rua teste'}).status_code,502)
        self.assertEqual(fetch.call_count,2)

    def test_numbers_before_after_and_numeric_street_names(self):
        from transit.sptrans.addresses import split_number
        for query in ('123 Rua Augusta','Rua Augusta 123','Rua Augusta, 123'):
            self.assertEqual(split_number(query),('Rua Augusta','123'))
        self.assertEqual(split_number('Rua 25 de Março'),('Rua 25 de Março',''))
        self.assertEqual(split_number('Avenida 23 de Maio'),('Avenida 23 de Maio',''))

    def test_missing_house_number_is_not_silently_replaced_by_street_center(self):
        features=[{'properties':{'name':'Rua Augusta','osm_key':'highway'},'geometry':{'coordinates':[-46.63,-23.55]}}]
        with patch('transit.sptrans.addresses.urlopen',return_value=io.StringIO(json.dumps({'features':features}))):
            result=self.client.get('/api/sptrans/addresses/',{'q':'Rua Augusta 123'}).json()
        self.assertEqual(result['suggestions'],[])

    def test_street_suggestion_has_explicit_kind_and_unabbreviated_name(self):
        features=[{'properties':{'name':'Rua Augusta','osm_key':'highway'},'geometry':{'coordinates':[-46.63,-23.55]}}]
        with patch('transit.sptrans.addresses.urlopen',return_value=io.StringIO(json.dumps({'features':features}))):
            result=self.client.get('/api/sptrans/addresses/',{'q':'Rua Augusta'}).json()['suggestions'][0]
        self.assertEqual(result['kind'],'street')
        self.assertEqual(result['street'],'Rua Augusta')

    def test_engineer_abbreviation_matches_full_avenue_name(self):
        from transit.sptrans.addresses import street_key
        self.assertEqual(street_key('Av. Eng. Heitor Antônio Eiras Garcia, 363'),street_key('Avenida Engenheiro Heitor Antônio Eiras Garcia'))
