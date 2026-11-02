"""Crop OSM streets around every input stop, retaining complete ways and barriers."""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import sqlite3
import time
import zipfile
import osmium

p = argparse.ArgumentParser()
p.add_argument('base', type=Path)
p.add_argument('archive', type=Path)
p.add_argument('osm', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
cells = set()
def add(lat, lon):
    y, x = math.floor(float(lat)/.01), math.floor(float(lon)/.01)
    # More than 3 km around each stop; all paths <=1 km fit inside the crop.
    cells.update((y+dy,x+dx) for dy in range(-4,5) for dx in range(-4,5))
with sqlite3.connect(a.base.resolve().as_uri()+'?mode=ro', uri=True) as db:
    for lat, lon in db.execute('SELECT stop_lat,stop_lon FROM stops'):
        add(lat,lon)
with zipfile.ZipFile(a.archive) as z:
    for row in csv.DictReader(io.TextIOWrapper(z.open('stops.txt'), encoding='utf-8-sig')):
        add(row['stop_lat'],row['stop_lon'])
started=time.monotonic(); count=0
with osmium.BackReferenceWriter(a.output,a.osm,remove_tags=False) as writer:
    for item in osmium.FileProcessor(a.osm).with_locations('flex_mem').with_filter(osmium.filter.KeyFilter('highway')):
        if item.is_way() and any((math.floor(n.lat/.01),math.floor(n.lon/.01)) in cells for n in item.nodes):
            writer.add_way(item); count+=1
print(json.dumps({'source':str(a.osm),'grid_cells':len(cells),'ways':count,'seconds':time.monotonic()-started,'bytes':a.output.stat().st_size}),flush=True)
