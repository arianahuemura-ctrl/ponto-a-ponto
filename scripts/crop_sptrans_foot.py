"""Extrato viário com referências completas e preservação dos nós com barreiras."""
import argparse
import json
from pathlib import Path
import sqlite3
import time
import osmium
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from mbm import routing_config as config

p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('output',type=Path)
p.add_argument('--graph',type=Path,default=Path('sptrans.routing.sqlite3'))
a=p.parse_args()
with sqlite3.connect(a.graph.resolve().as_uri()+'?mode=ro',uri=True) as db:
    low_lat,low_lon,high_lat,high_lon=db.execute('SELECT min(lat),min(lon),max(lat),max(lon) FROM graph_stop').fetchone()
margin=config.OSM_MARGIN_DEGREES
bbox=(low_lat-margin,low_lon-margin,high_lat+margin,high_lon+margin)
started=time.perf_counter();count=0
with osmium.BackReferenceWriter(a.output,a.source,remove_tags=False) as writer:
    for item in osmium.FileProcessor(a.source).with_locations('flex_mem').with_filter(osmium.filter.KeyFilter('highway')):
        if item.is_way() and any(bbox[0]<=n.lat<=bbox[2] and bbox[1]<=n.lon<=bbox[3] for n in item.nodes):
            writer.add_way(item);count+=1
print(json.dumps({'bbox':bbox,'ways':count,'seconds':time.perf_counter()-started}))
