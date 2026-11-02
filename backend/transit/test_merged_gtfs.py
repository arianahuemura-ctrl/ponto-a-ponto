import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile
from django.test import SimpleTestCase
from transit.sptrans import merged_gtfs, store


class MergedGtfsTests(SimpleTestCase):
    def fixture(self, missing_stop=False):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        p=Path(tmp.name);base=p/'original.sqlite3';archive=p/'artesp.zip'
        rows={
            'stops':[{'stop_id':'1','stop_name':'First','stop_lat':'-23.6','stop_lon':'-46.5'},
                     {'stop_id':'2','stop_name':'Last','stop_lat':'-23.61','stop_lon':'-46.5'}],
            'routes':[{'route_id':'1','agency_id':'1','route_short_name':'064','route_type':'3'}],
            'trips':[{'route_id':'1','trip_id':'1','service_id':'1','direction_id':'0','shape_id':'1'}],
            'stop_times':[{'trip_id':'1','stop_id':'1','arrival_time':'08:00:00','departure_time':'08:00:00','stop_sequence':'1'},
                          {'trip_id':'1','stop_id':'missing' if missing_stop else '2','arrival_time':'08:10:00','departure_time':'08:10:00','stop_sequence':'2'}],
            'calendar':[{'service_id':'1','monday':'1','start_date':'20260101','end_date':'20261231'}],
            'shapes':[]}
        with sqlite3.connect(base) as db:
            for t,cols in store.TABLES.items():
                db.execute(f'CREATE TABLE {t} ('+','.join(c+' TEXT' for c in cols)+')')
                db.executemany(f'INSERT INTO {t} VALUES ('+','.join('?' for c in cols)+')',
                               ([r.get(c,'') for c in cols] for r in rows.get(t,[]) if not (missing_stop and t=='stop_times')))
            db.execute('CREATE TABLE metadata(value)');db.execute('INSERT INTO metadata VALUES(?)',('{}',))
        with zipfile.ZipFile(archive,'w') as z:
            for t,data in rows.items():
                f=io.StringIO();w=csv.DictWriter(f,fieldnames=store.TABLES[t]);w.writeheader();w.writerows(data)
                z.writestr(t+'.txt',f.getvalue())
            for t in ('agency','feed_info','fare_attributes','fare_rules'):
                z.writestr(t+'.txt','source\nfixture\n')
        return p,base,archive

    def test_namespace_preserves_base_and_calendar_without_frequencies(self):
        p,base,z=self.fixture();before=hashlib.sha256(base.read_bytes()).digest()
        target=p/'merged.sqlite3';r=merged_gtfs.merge(base,z,target,progress=lambda *a,**k:None)
        self.assertEqual(before,hashlib.sha256(base.read_bytes()).digest())
        self.assertEqual(r['counts']['stops'],4)
        self.assertEqual(r['added']['frequencies'],0)
        with sqlite3.connect(target) as db:
            self.assertEqual(db.execute('SELECT stop_id FROM stops ORDER BY stop_id').fetchall(),[('1',),('2',),('artesp:1',),('artesp:2',)])
            self.assertEqual(db.execute("SELECT service_id,shape_id FROM trips WHERE trip_id='artesp:1'").fetchone(),('artesp:1','artesp:1'))
            self.assertEqual(db.execute("SELECT end_date FROM calendar WHERE service_id='artesp:1'").fetchone()[0],'20261231')
        with self.assertRaises(ValueError):merged_gtfs.merge(base,z,base)
        with self.assertRaises(ValueError):merged_gtfs.merge(base,z,target)

    def test_broken_references_do_not_publish_database(self):
        p,base,z=self.fixture(missing_stop=True);target=p/'bad.sqlite3'
        with self.assertRaises(ValueError):merged_gtfs.merge(base,z,target,progress=lambda *a,**k:None)
        self.assertFalse(target.exists())
