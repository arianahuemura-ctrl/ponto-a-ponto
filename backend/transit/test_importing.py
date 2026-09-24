import copy
import hashlib
import json
import tempfile
from pathlib import Path
from django.test import TestCase
from transit.importing import import_network, import_collected
from transit.models import Stop, Route, RouteStop, SourceDocument, Simulation
from transit.network import dataset, trips, snapshot
from .test_support import DemoDatabaseTestCase


class ImportTests(TestCase):
    def setUp(self):
        self.payload = {
            "stops": [
                {"id": "test:a", "name": "A", "lat": -23.66, "lon": -46.46},
                {"id": "test:b", "name": "B", "lat": None, "lon": None},
            ],
            "routes": [
                {
                    "id": "test:r",
                    "code": "1",
                    "name": "Circular",
                    "stops": ["test:a", "test:b", "test:a"],
                }
            ],
        }

    def test_idempotent_and_repeated_stops_preserve_order(self):
        import_network(self.payload, "test")
        import_network(self.payload, "test")
        self.assertEqual(Stop.objects.count(), 2)
        self.assertEqual(Route.objects.count(), 1)
        self.assertEqual(
            list(RouteStop.objects.values_list("stop_id", flat=True)),
            ["test:a", "test:b", "test:a"],
        )
        self.assertFalse(Route.objects.get().routable)

    def test_invalid_coordinates_rollback_entire_batch(self):
        data = copy.deepcopy(self.payload)
        data["stops"][1]["lat"] = float("nan")
        data["stops"][1]["lon"] = -46
        with self.assertRaises(ValueError):
            import_network(data)
        self.assertEqual(Stop.objects.count(), 0)

    def test_missing_stop_does_not_destroy_previous_sequence(self):
        import_network(self.payload)
        data = copy.deepcopy(self.payload)
        data["routes"][0]["stops"].append("missing")
        with self.assertRaises(ValueError):
            import_network(data)
        self.assertEqual(RouteStop.objects.count(), 3)

    def test_application_reads_database_without_restart_and_keeps_catalogue_when_simulation_off(
        self,
    ):
        import_network(self.payload, "test")
        self.assertEqual([s["id"] for s in dataset()["stops"]], ["test:a"])
        Stop.objects.filter(pk="test:a").update(name="Nome atualizado")
        self.assertEqual(dataset()["stops"][0]["name"], "Nome atualizado")
        Simulation.objects.create(enabled=False)
        result = self.client.get("/api/catalogue/").json()
        self.assertEqual(len(result["routes"]), 1)
        self.assertEqual(result["counts"]["located_stops"], 1)
        detail = self.client.get("/api/catalogue/routes/test:r/").json()
        self.assertEqual(len(detail["stops"]), 3)
        self.assertIsNone(detail["stops"][1]["lat"])

    def test_checksum_failure_rolls_back_documents_and_network(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "source.html").write_text("alterado")
            data = {
                **self.payload,
                "documents": [
                    {
                        "id": "doc",
                        "provider": "test",
                        "url": "https://example.com",
                        "kind": "catalogue",
                        "status": "ok",
                        "path": "source.html",
                        "sha256": hashlib.sha256(b"original").hexdigest(),
                    }
                ],
            }
            (folder / "collected.json").write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                import_collected(folder)
            self.assertFalse(SourceDocument.objects.exists())
            self.assertFalse(Stop.objects.exists())

    def test_duplicate_route_ids_rejected(self):
        self.payload["routes"].append(self.payload["routes"][0].copy())
        with self.assertRaises(ValueError):
            import_network(self.payload)
        self.assertFalse(Stop.objects.exists())


class SimulationIsolationTests(DemoDatabaseTestCase):
    def test_external_routable_route_stays_in_catalogue_without_affecting_simulation(self):
        network = dataset()
        origin = network["stops"][0]["id"]
        at = network["default_time"]
        baseline_trips = trips()
        baseline_snapshot = snapshot(at, origin)
        baseline_journey = self.client.get(
            "/api/journey/",
            {"origin": origin, "destination": network["stops"][6]["id"]},
        ).json()
        for has_demo_fields in (False, True):
            with self.subTest(has_demo_fields=has_demo_fields):
                external = copy.deepcopy(network["routes"][0])
                external.update(id="external:r", source="external", name="Linha externa")
                if not has_demo_fields:
                    external.pop("offset", None)
                    external.pop("color", None)
                import_network({"stops": [], "routes": [external]}, "external")
                route = Route.objects.get(pk="external:r")
                self.assertTrue(route.routable)
                self.assertFalse(route.simulated)
                self.assertEqual(trips(), baseline_trips)
                self.assertEqual(snapshot(at, origin), baseline_snapshot)
                self.assertNotIn(
                    route.pk,
                    [r["id"] for r in self.client.get("/api/network/").json()["routes"]],
                )
                board = self.client.get("/api/board/", {"origin": origin})
                self.assertEqual(board.status_code, 200)
                self.assertEqual(board.json()["lines"], baseline_snapshot["lines"])
                self.assertEqual(
                    self.client.get(
                        "/api/journey/",
                        {"origin": origin, "destination": network["stops"][6]["id"]},
                    ).json(),
                    baseline_journey,
                )
                catalogue = self.client.get("/api/catalogue/").json()
                self.assertIn(route.pk, [r["id"] for r in catalogue["routes"]])
                detail = self.client.get("/api/catalogue/routes/external:r/").json()
                self.assertEqual([s["id"] for s in detail["stops"]], external["stops"])
