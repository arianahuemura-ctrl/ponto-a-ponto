from django.test import SimpleTestCase, TestCase
from transit.geolocation import (
    StreetIndex,
    address_parts,
    allowed_directions,
    project,
    distance,
)
from transit.importing import import_network
from transit.models import Stop


def fixture():
    elements = [
        {
            "type": "way",
            "id": 1,
            "nodes": [1, 2],
            "geometry": [
                {"lat": -23.66, "lon": -46.46},
                {"lat": -23.66, "lon": -46.45},
            ],
            "tags": {"name": "Rua Teste", "highway": "residential"},
        }
    ]
    for i, lon in enumerate((-46.458, -46.455, -46.452), 1):
        elements.append(
            {
                "type": "node",
                "id": 100 + i,
                "lat": -23.6599,
                "lon": lon,
                "tags": {
                    "addr:street": "Rua Teste",
                    "addr:housenumber": str(i * 10),
                    "addr:city": "Mauá",
                },
            }
        )
    return elements


class GeolocationTests(SimpleTestCase):
    def test_address_range_and_abbreviations(self):
        parts = address_parts(
            "Av. Papa João XXIII, 4019-4075 - Parque São Vicente, Mauá - SP, Brasil"
        )
        self.assertEqual(parts["number"], 4047)
        self.assertEqual(parts["street"], "avenida papa joao xxiii")
        self.assertEqual(
            address_parts("Rua Juraci Aletto 300, RP2, Mauá")["number"], 300
        )

    def test_bus_exception_and_reverse_oneway(self):
        self.assertEqual(allowed_directions({"oneway": "yes"}), (1,))
        self.assertEqual(allowed_directions({"oneway": "-1"}), (-1,))
        self.assertEqual(
            allowed_directions({"oneway": "yes", "oneway:bus": "no"}), (1, -1)
        )
        self.assertEqual(allowed_directions({"bus": "no"}), ())
        self.assertEqual(
            allowed_directions({"oneway:conditional": "yes @ (08:00-10:00)"}), ()
        )

    def test_projection_clamps_to_segment(self):
        point, ratio, gap = project(
            (-23.65, -46.44), (-23.66, -46.46), (-23.66, -46.45)
        )
        self.assertEqual(ratio, 1)
        self.assertAlmostEqual(point[1], -46.45)
        self.assertGreater(gap, 100)

    def test_sequence_selects_heading_and_right_hand_offset(self):
        index = StreetIndex(fixture())
        candidates = [
            index.candidates(f"Rua Teste, {n} - Mauá")[0] for n in (10, 20, 30)
        ]
        east = index.resolve(candidates)
        west = index.resolve(list(reversed(candidates)))
        self.assertEqual(east[1]["status"], "estimated")
        self.assertAlmostEqual(east[1]["bearing"], 90)
        self.assertLess(east[1]["lat"], -23.66)
        self.assertAlmostEqual(west[1]["bearing"], 270)
        self.assertGreater(west[1]["lat"], -23.66)
        self.assertAlmostEqual(
            distance(east[1]["road_point"], (east[1]["lat"], east[1]["lon"])),
            3,
            places=3,
        )

    def test_reverse_order_cannot_travel_backwards_on_oneway(self):
        data = fixture()
        data[0]["tags"]["oneway"] = "yes"
        index = StreetIndex(data)
        candidates = [
            index.candidates(f"Rua Teste, {n} - Mauá")[0] for n in (30, 20, 10)
        ]
        self.assertEqual(index.resolve(candidates), [None, None, None])

    def test_street_only_is_not_published_without_anchors(self):
        index = StreetIndex(fixture()[:1])
        candidates = [index.candidates("Rua Teste, 10 - Mauá")[0]] * 3
        self.assertTrue(
            all(r["status"] == "pending" for r in index.resolve(candidates))
        )
        self.assertFalse(index.candidates("Rua Inexistente, 50 - Mauá")[0])

    def test_number_interpolation_never_extrapolates(self):
        index = StreetIndex(fixture())
        middle, _ = index.candidates("Rua Teste, 15 - Mauá")
        self.assertTrue(all(c["method"] == "number_interpolation" for c in middle))
        outside, _ = index.candidates("Rua Teste, 999 - Mauá")
        self.assertTrue(all(c["method"] == "street_only" for c in outside))

    def test_missing_street_does_not_bridge_route(self):
        index = StreetIndex(fixture())
        a = index.candidates("Rua Teste, 10 - Mauá")[0]
        b = index.candidates("Rua Teste, 30 - Mauá")[0]
        result = index.resolve([a, [], b])
        self.assertIsNone(result[1])
        self.assertEqual(result[0]["status"], "pending")


class GeolocationPersistenceTests(TestCase):
    def test_reimport_preserves_estimate_only_for_same_address(self):
        payload = {
            "stops": [
                {"id": "citta:a", "name": "Rua Teste, 10", "lat": None, "lon": None}
            ],
            "routes": [],
        }
        import_network(payload, "cittamobi")
        stop = Stop.objects.get()
        stop.lat = -23.66
        stop.lon = -46.46
        stop.data["geolocation"] = {"status": "estimated"}
        stop.save()
        import_network(payload, "cittamobi")
        stop.refresh_from_db()
        self.assertEqual(stop.lat, -23.66)
        payload["stops"][0]["name"] = "Rua Outra, 100"
        import_network(payload, "cittamobi")
        stop.refresh_from_db()
        self.assertIsNone(stop.lat)
        self.assertNotIn("geolocation", stop.data)

    def test_new_algorithm_removes_obsolete_coordinates(self):
        from transit.models import GeolocationRun
        from transit.management.commands.geolocate_stops import publish_estimates

        stop = Stop.objects.create(
            id="citta:old",
            name="Old",
            source="cittamobi",
            lat=-23.66,
            lon=-46.46,
            data={
                "geolocation": {
                    "status": "estimated",
                    "algorithm": "osm-address-directed-old",
                }
            },
        )
        run = GeolocationRun.objects.create(algorithm="test", source_hash="a" * 64)
        publish_estimates("a" * 64, run)
        stop.refresh_from_db()
        self.assertIsNone(stop.lat)
        self.assertEqual(stop.data["geolocation"]["status"], "pending")

    def test_opposite_headings_do_not_publish_same_point(self):
        from transit.models import GeolocationRun, StopEstimate, Route
        from transit.geolocation import VERSION
        from transit.management.commands.geolocate_stops import publish_estimates

        stop = Stop.objects.create(
            id="citta:opposite", name="Parada", source="cittamobi"
        )
        run = GeolocationRun.objects.create(algorithm=VERSION, source_hash="b" * 64)
        for i, bearing in enumerate((90, 270)):
            route = Route.objects.create(id=str(i), name="Sentido", source="test")
            StopEstimate.objects.create(
                stop=stop,
                route=route,
                position=0,
                run=run,
                status="estimated",
                lat=-23.66,
                lon=-46.46,
                evidence={"bearing": bearing},
            )
        self.assertEqual(publish_estimates("b" * 64, run), (0, 1))
        stop.refresh_from_db()
        self.assertIsNone(stop.lat)
        self.assertEqual(stop.data["geolocation"]["status"], "conflict")
