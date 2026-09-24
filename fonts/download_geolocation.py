from pathlib import Path
import json, hashlib, urllib.request, urllib.parse, datetime

root = Path(__file__).resolve().parent
query = """[out:json][timeout:180];
(
 way(-23.74,-46.54,-23.60,-46.39)["highway"]["highway"!~"^(footway|path|cycleway|steps|pedestrian|construction|proposed)$"];
 nwr(-23.74,-46.54,-23.60,-46.39)["addr:street"]["addr:housenumber"];
 way(-23.74,-46.54,-23.60,-46.39)["addr:interpolation"];
);
out body geom;"""
(root / "geolocation.overpass").write_text(query)
for base in [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]:
    try:
        req = urllib.request.Request(
            base,
            data=urllib.parse.urlencode({"data": query}).encode(),
            headers={"User-Agent": "MauaBusMap/0.3 academic geolocation"},
        )
        with urllib.request.urlopen(req, timeout=240) as r:
            body = r.read()
        data = json.loads(body)
        if data.get("remark") or not data.get("elements"):
            raise ValueError(data.get("remark", "empty"))
        (root / "geolocation_osm.json").write_bytes(body)
        meta = {
            "url": base,
            "query": query,
            "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sha256": hashlib.sha256(body).hexdigest(),
            "osm_timestamp": data.get("osm3s", {}),
            "license": "ODbL",
            "elements": len(data["elements"]),
        }
        (root / "geolocation_osm.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2)
        )
        print(meta, flush=True)
        break
    except Exception as e:
        print(base, e, flush=True)
else:
    raise SystemExit(1)
