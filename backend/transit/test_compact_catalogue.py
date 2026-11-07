import gzip
import json
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory
from transit.sptrans import compact

class CompactCatalogueTests(SimpleTestCase):
    def test_negotiation_and_conditional_request(self):
        raw=compact.encode([dict(id='001',lat=-23.55,lon=-46.73,name='Casa')],'test')
        with patch.object(compact.viewport,'revision',return_value='test'),patch.dict(compact._cache,{'test':(raw,gzip.compress(raw))},clear=True):
            factory=RequestFactory()
            response=compact.catalogue(factory.get('/',HTTP_ACCEPT_ENCODING='gzip'))
            self.assertEqual(json.loads(gzip.decompress(response.content))['rows'][0],['001',-2355000,-4673000,'Casa'])
            unchanged=compact.catalogue(factory.get('/',HTTP_IF_NONE_MATCH=response['ETag']))
            self.assertEqual(unchanged.status_code,304)
            self.assertEqual(unchanged.content,b'')
            plain=compact.catalogue(factory.get('/',HTTP_ACCEPT_ENCODING='gzip;q=0'))
            self.assertNotIn('Content-Encoding',plain)
            self.assertEqual(plain.content,raw)
