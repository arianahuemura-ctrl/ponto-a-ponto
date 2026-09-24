from .test_support import DemoDatabaseTestCase
from datetime import timedelta
from django.contrib.auth import get_user_model
from transit.models import Simulation
from transit.network import dataset, snapshot
from transit.geometry import point_on_segment


class RuntimeTests(DemoDatabaseTestCase):
    def setUp(self):
        self.config = Simulation.objects.create(
            enabled=True, running=False, seconds=28800
        )
        self.origin = dataset()["stops"][0]["id"]

    def test_passenger_cannot_override_server_clock(self):
        result = self.client.get(
            "/api/board/", {"origin": self.origin, "at": 40000}
        ).json()
        self.assertEqual(result["at"], 28800)
        self.assertEqual(self.config.current_seconds(), 28800)

    def test_turning_off_removes_all_operational_simulation(self):
        self.config.enabled = False
        self.config.save()
        self.assertEqual(self.client.get("/api/network/").json()["routes"], [])
        board = self.client.get("/api/board/", {"origin": self.origin}).json()
        self.assertEqual(board["mode"], "unavailable")
        self.assertEqual(board["vehicles"], [])
        self.assertEqual(board["lines"], [])
        self.assertEqual(
            self.client.get(
                "/api/journey/",
                {"origin": self.origin, "destination": dataset()["stops"][6]["id"]},
            ).json()["itineraries"],
            [],
        )

    def test_stop_tracks_simulation_changes(self):
        expected_routes = {
            r["id"] for r in dataset()["routes"] if self.origin in r["stops"]
        }
        self.assertTrue(expected_routes)
        for enabled in (True, False, True):
            self.config.enabled = enabled
            self.config.save()
            with self.subTest(enabled=enabled):
                response = self.client.get(f"/api/demo/stops/{self.origin}/")
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["stop"]["id"], self.origin)
                self.assertEqual(data["mode"], "simulation" if enabled else "unavailable")
                self.assertEqual(
                    {r["id"] for r in data["routes"]},
                    expected_routes if enabled else set(),
                )
                self.assertIn("no-store", response["Cache-Control"])

    def test_clock_is_global_and_speed_applied(self):
        self.config.running = True
        self.config.speed = 15
        self.config.save()
        future = self.config.changed_at + timedelta(seconds=10)
        self.assertEqual(self.config.current_seconds(future), 28950)

    def test_admin_requires_authentication_and_staff(self):
        url = "/admin/transit/simulation/1/change/"
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create_user("regular", password="test")
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 302)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_form_changes_runtime(self):
        user = get_user_model().objects.create_superuser("operator", password="test")
        self.client.force_login(user)
        response = self.client.post(
            "/admin/transit/simulation/1/change/",
            {"simulated_time": "09:30:00", "speed": "15", "_save": "Salvar"},
        )
        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertFalse(self.config.enabled)
        self.assertEqual(self.config.seconds, 34200)
        self.assertFalse(self.config.running)


class GeometryTests(DemoDatabaseTestCase):
    def test_every_demo_leg_has_dense_street_geometry(self):
        for route in dataset()["routes"]:
            self.assertEqual(len(route["segments"]), len(route["stops"]) - 1)
            for i, segment in enumerate(route["segments"]):
                self.assertEqual(segment["from"], route["stops"][i])
                self.assertEqual(segment["to"], route["stops"][i + 1])
                self.assertGreater(len(segment["points"]), 10)
                self.assertTrue(segment["streets"])
                self.assertGreater(segment["distance_m"], 0)

    def test_interpolation_follows_bend_instead_of_chord(self):
        segment = {"points": [[0, 0], [0, 1], [1, 1]]}
        lat, lon = point_on_segment(segment, 0.25)
        self.assertAlmostEqual(lat, 0)
        self.assertAlmostEqual(lon, 0.5, places=3)
        self.assertEqual(point_on_segment(segment, 0), [0, 0])
        self.assertEqual(point_on_segment(segment, 1), [1, 1])

    def test_vehicle_positions_are_on_assigned_road(self):
        route = dataset()["routes"][0]
        # DEMO-A parte às 08:02; após quatro minutos está no meio do primeiro trecho.
        vehicle = next(
            v
            for v in snapshot(8 * 3600 + 6 * 60)["vehicles"]
            if v["id"] == "DEMO-A-28920"
        )
        expected = point_on_segment(route["segments"][0], 0.5)
        self.assertAlmostEqual(vehicle["lat"], expected[0])
        self.assertAlmostEqual(vehicle["lon"], expected[1])
