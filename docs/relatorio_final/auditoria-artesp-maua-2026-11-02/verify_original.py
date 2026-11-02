import csv,io,json,hashlib,zipfile,sqlite3
from pathlib import Path
from collections import defaultdict,Counter
from shapely.geometry import shape,Point
R=Path('/home/avale/Projetos/maua_bus_map'); A=R/'artifacts/benchmarks/maua-artesp-20261102'; P=R/'artifacts/transport/artesp-20261102'; O=Path(__file__).parent
z=zipfile.ZipFile(P/'artesp_gtfs.zip')
def rows(name):
    return csv.DictReader(io.TextIOWrapper(z.open(name),encoding='utf-8-sig'))
boundary=shape(json.loads((A/'maua-ibge-2024.geojson').read_text())['geometry'])
stops={r['stop_id']:r for r in rows('stops.txt') if boundary.covers(Point(float(r['stop_lon']),float(r['stop_lat'])))}
old_stops={r['stop_id'] for r in csv.DictReader((A/'stops.csv').open())}
assert {'artesp:'+s for s in stops}==old_stops
trips={r['trip_id']:r for r in rows('trips.txt')}; selected=set(); calls=0
for r in rows('stop_times.txt'):
    if r['stop_id'] in stops:selected.add(r['trip_id']); calls+=1
old_trips={r['trip_id'] for r in csv.DictReader((A/'trips.csv').open())}
assert {'artesp:'+t for t in selected}==old_trips
sequences=defaultdict(list)
for r in rows('stop_times.txt'):
    if r['trip_id'] in selected:sequences[r['trip_id']].append(r)
def seconds(x):
    h,m,s=map(int,x.split(':'));assert h>=0 and 0<=m<60 and 0<=s<60
    return h*3600+m*60+s
for tid,seq in sequences.items():
    seq.sort(key=lambda r:int(r['stop_sequence']));assert len({r['stop_id'] for r in seq})>=2
    previous=-1
    for r in seq:
        a,d=seconds(r['arrival_time']),seconds(r['departure_time']);assert previous<=a<=d;previous=d
cal={r['service_id']:r for r in rows('calendar.txt')}
daily={}
for label in ['tuesday','saturday','sunday']:
    tids={t for t in selected if cal[trips[t]['service_id']][label]=='1'}
    daily[label]={'trips':len(tids),'routes':len({trips[t]['route_id'] for t in tids}),'stops':len({r['stop_id'] for t in tids for r in sequences[t] if r['stop_id'] in stops})}
report={'source_url':'https://dadosabertos.artesp.sp.gov.br/dataset/92e8bb31-df66-4700-ad9a-42a48f04fb7f/resource/3918f5ec-206d-4826-8a88-5d9f6f791fe2/download/artesp_gtfs.zip','feed_info':list(rows('feed_info.txt')),'calendars':list(cal.values()),'zip_md5':hashlib.file_digest((P/'artesp_gtfs.zip').open('rb'),'md5').hexdigest(),'zip_sha256':hashlib.file_digest((P/'artesp_gtfs.zip').open('rb'),'sha256').hexdigest(),'stops':len(stops),'routes':sorted({trips[t]['route_id'] for t in selected}),'distinct_trips':len(selected),'local_stop_calls_not_trip_count':calls,'days':daily,'all_raw_sequences_valid':True,'raw_stop_and_trip_ids_equal_imported_census':True,'calendar_dates':list(rows('calendar_dates.txt')) if 'calendar_dates.txt' in z.namelist() else []}
(O/'original-gtfs-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
