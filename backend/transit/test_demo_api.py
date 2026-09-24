import json
from django.test import TestCase, Client
from transit.network import dataset
from transit.models import Evaluation


class DemoApiTests(TestCase):
    def setUp(self):
        self.origin = dataset()["stops"][0]["id"]
        self.destination = dataset()["stops"][6]["id"]

    def test_qr_entry_data(self):
        self.assertEqual(
            self.client.get("/api/demo/network/").json()["mode"], "simulation"
        )
        response = self.client.get("/api/demo/stops/" + self.origin + "/")
        self.assertEqual(response.json()["stop"]["id"], self.origin)
        self.assertEqual(self.client.get("/api/demo/stops/unknown/").status_code, 404)

    def test_journey_and_invalid_parameters(self):
        params = {"origin": self.origin, "destination": self.destination, "at": 28800}
        response = self.client.get("/api/demo/journey/", params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["itineraries"][0]["transfers"], 1)
        for key, value in [
            ("origin", "bad"),
            ("at", "nan"),
            ("at", -1),
            ("max_transfers", 5),
        ]:
            self.assertEqual(
                self.client.get(
                    "/api/demo/journey/", {**params, key: value}
                ).status_code,
                400,
            )

    def test_no_connection_and_outside_recorte(self):
        params = {"origin": self.origin, "destination": dataset()["stops"][7]["id"]}
        self.assertEqual(
            self.client.get("/api/demo/journey/", params).json()["itineraries"], []
        )
        self.assertEqual(
            self.client.get(
                "/api/demo/journey/", {"origin": self.origin, "lat": 0, "lon": 0}
            ).json()["itineraries"],
            [],
        )
        self.assertEqual(
            self.client.get(
                "/api/demo/journey/", {"origin": self.origin, "lat": "nan", "lon": 0}
            ).status_code,
            400,
        )

    def test_qr_svg(self):
        response = self.client.get("/api/demo/qr/" + self.origin + "/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("image/svg+xml", response["Content-Type"])
        self.assertIn(b"<svg", response.content)
        self.assertEqual(self.client.get("/api/demo/qr/invalid/").status_code, 404)

    def test_board_validation(self):
        self.assertEqual(
            self.client.get("/api/demo/board/", {"at": "nan"}).status_code, 400
        )
        self.assertEqual(
            self.client.get("/api/demo/board/", {"origin": self.origin}).json()["mode"],
            "simulation",
        )

    def test_feedback_persists_and_is_not_exposed(self):
        response = self.client.post(
            "/api/demo/evaluation/",
            data=json.dumps({"notes": "Troca clara", "scenario": "Baldeação"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Evaluation.objects.get().notes, "Troca clara")
        self.assertNotIn(
            "Troca clara", self.client.get("/api/demo/evaluation/").content.decode()
        )

    def test_feedback_validation_and_csrf(self):
        for data in ({}, {"notes": ""}, {"notes": "a" * 5001}, [], {"notes": 5}):
            self.assertEqual(
                self.client.post(
                    "/api/demo/evaluation/",
                    data=json.dumps(data),
                    content_type="application/json",
                ).status_code,
                400,
            )
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post("/api/demo/evaluation/", data={"notes": "test"}).status_code,
            403,
        )
        client.get("/api/demo/network/")
        response = client.post(
            "/api/demo/evaluation/",
            data=json.dumps({"notes": "CSRF válido"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        self.assertEqual(response.status_code, 201)
