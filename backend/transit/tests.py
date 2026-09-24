from unittest.mock import patch
from django.core.cache import cache
from django.test import SimpleTestCase
from transit import services


class ApiTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_health(self):
        self.assertEqual(self.client.get("/api/health/").json()["backend"], "django")

    @patch("transit.views.services.nearby")
    def test_invalid_coordinates_do_not_call_provider(self, provider):
        for params in (
            {},
            {"lat": "nan", "lon": "0"},
            {"lat": "91", "lon": "0"},
            {"lat": "0", "lon": "inf"},
            {"lat": "abc", "lon": "1"},
        ):
            self.assertEqual(self.client.get("/api/nearby/", params).status_code, 400)
        provider.assert_not_called()

    @patch("transit.views.services.nearby", return_value={"elements": []})
    def test_nearby(self, provider):
        response = self.client.get("/api/nearby/", {"lat": "-23.66", "lon": "-46.46"})
        self.assertEqual(response.json(), {"elements": []})
        provider.assert_called_once_with(-23.66, -46.46)

    @patch("transit.views.services.geocode")
    def test_invalid_address(self, provider):
        self.assertEqual(self.client.get("/api/geocode/").status_code, 400)
        self.assertEqual(
            self.client.get(
                "/api/geocode/", {"address": "Mauá", "state": "XX"}
            ).status_code,
            400,
        )
        provider.assert_not_called()

    @patch("transit.views.services.geocode", return_value=None)
    def test_address_not_found(self, provider):
        self.assertEqual(
            self.client.get("/api/geocode/", {"address": "inexistente"}).status_code,
            404,
        )

    @patch(
        "transit.views.services.geocode",
        return_value={"lat": -23.66, "lon": -46.46, "label": "Mauá"},
    )
    def test_geocode(self, provider):
        self.assertEqual(
            self.client.get(
                "/api/geocode/", {"address": " Mauá ", "state": "sp"}
            ).json()["label"],
            "Mauá",
        )
        provider.assert_called_once_with("Mauá", "SP")

    @patch(
        "transit.views.services.nearby",
        side_effect=services.ProviderError("Falha no OSM"),
    )
    def test_provider_failure(self, provider):
        response = self.client.get("/api/nearby/", {"lat": 0, "lon": 0})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"], "Falha no OSM")

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post("/api/nearby/").status_code, 405)

    @patch(
        "transit.services.request_json",
        side_effect=[services.ProviderError(), {"elements": []}],
    )
    def test_overpass_fallback_and_cache(self, fetch):
        self.assertEqual(services.nearby(-23, -46), {"elements": []})
        self.assertEqual(services.nearby(-23, -46), {"elements": []})
        self.assertEqual(fetch.call_count, 2)

    @patch(
        "transit.services.request_json",
        return_value={"elements": [], "remark": "runtime error"},
    )
    def test_partial_overpass_response_is_rejected(self, fetch):
        with self.assertRaises(services.ProviderError):
            services.nearby(-23, -46)

    @patch(
        "transit.services.request_json",
        return_value=[{"lat": "-23", "lon": "-46", "display_name": "Mauá"}],
    )
    def test_geocode_cached(self, fetch):
        self.assertEqual(services.geocode("Mauá", "SP"), services.geocode("Mauá", "SP"))
        fetch.assert_called_once()

    def test_frontend_build_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/assets/", b"".join(response.streaming_content))
