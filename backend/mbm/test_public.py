"""Contrato da instância pública; não cria nem migra bancos."""
from pathlib import Path
from unittest import mock
from django.conf import settings
from django.http import JsonResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from .public_boundary import PublicBoundary


class PublicContractTests(SimpleTestCase):
    def test_settings_are_isolated_and_readonly(self):
        self.assertFalse(settings.DEBUG)
        self.assertGreaterEqual(len(settings.SECRET_KEY), 50)
        self.assertIn('?mode=ro', settings.DATABASES['default']['NAME'])
        self.assertTrue(settings.DATABASES['default']['OPTIONS']['uri'])
        self.assertIsNone(settings.SECURE_PROXY_SSL_HEADER)
        self.assertFalse(settings.USE_X_FORWARDED_HOST)

    def test_frontend_and_every_compiled_asset(self):
        self.assertEqual(self.client.get('/', HTTP_HOST='localhost').status_code, 200)
        for asset in Path(settings.STATIC_ROOT).rglob('*'):
            if asset.is_file():
                response = self.client.get('/assets/' + asset.relative_to(settings.STATIC_ROOT).as_posix(), HTTP_HOST='localhost')
                self.assertEqual(response.status_code, 200, str(asset))
                response.close()

    def test_admin_evaluation_and_private_files_are_not_exposed(self):
        for path in ['/admin', '/admin/', '/admin/login/', '/api/demo/evaluation/', '/explorar/', '/.env', '/db.sqlite3', '/assets/../.env']:
            self.assertEqual(self.client.get(path, HTTP_HOST='localhost').status_code, 404, path)
        self.assertEqual(self.client.post('/api/demo/evaluation/', HTTP_HOST='localhost').status_code, 404)
        self.assertEqual(self.client.post('/api/sptrans/board/', HTTP_HOST='localhost').status_code, 405)

    def test_host_validation_also_precedes_static_files(self):
        asset = next(Path(settings.STATIC_ROOT).glob('*.js'))
        for path in ['/', '/api/health/', '/assets/' + asset.name]:
            self.assertEqual(self.client.get(path, HTTP_HOST='attacker.invalid').status_code, 400)

    @override_settings(PUBLIC_HOST='pap.example.com', ALLOWED_HOSTS=['localhost', 'pap.example.com'])
    def test_https_uses_server_scheme_not_untrusted_header(self):
        boundary = PublicBoundary(lambda request: JsonResponse({'secure': request.is_secure()}))
        factory = RequestFactory()
        response = boundary(factory.get('/api/health/', HTTP_HOST='pap.example.com', HTTP_X_FORWARDED_PROTO='https'))
        self.assertEqual(response.status_code, 301)
        response = boundary(factory.get('/api/health/', secure=True, HTTP_HOST='pap.example.com'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'true')
        response = boundary(factory.get('/api/health/', HTTP_HOST='localhost'))
        self.assertEqual(response.status_code, 200)

    def test_api_error_hides_internal_details(self):
        boundary = PublicBoundary(lambda request: JsonResponse({'error': '/private/secret'}, status=500))
        response = boundary(RequestFactory().get('/api/sptrans/stops/', HTTP_HOST='localhost'))
        self.assertNotIn(b'/private', response.content)

    def test_ndjson_stream_contract(self):
        result = {'journeys': [], 'complete': True, 'planner_fallback': '/private/artifacts/file.sqlite3'}
        # Exercita o endpoint real, isolando somente GTFS e serviço de planejamento.
        with mock.patch('transit.sptrans.views.store.connection') as connection, mock.patch('transit.sptrans.views.store.get_stop', return_value={'id':'1','lat':-23.55,'lon':-46.63}), mock.patch('transit.sptrans.views.alternatives.progressive', return_value=iter([result])):
            response = self.client.get('/api/sptrans/board/?origin=1&destination=2&stream=1', HTTP_HOST='localhost')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/x-ndjson')
            body = b''.join(response.streaming_content)
            self.assertIn(b'"complete": true', body)
            self.assertNotIn(b'/private', body)

class PublicHeadersTests(SimpleTestCase):
    def test_framing_and_report_only_policy(self):
        response=self.client.get('/',HTTP_HOST='localhost')
        self.assertEqual(response['X-Frame-Options'],'DENY')
        self.assertIn("frame-ancestors 'none'",response['Content-Security-Policy'])
        self.assertIn("default-src 'self'",response['Content-Security-Policy-Report-Only'])
