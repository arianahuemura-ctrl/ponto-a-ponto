import copy
import hashlib
import json
import tempfile
from pathlib import Path
from django.test import TestCase
from transit.importing import import_network, import_collected
from transit.models import Stop, Route, RouteStop, SourceDocument, Simulation
from transit.network import dataset


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
