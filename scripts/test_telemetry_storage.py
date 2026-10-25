import sqlite3
import unittest
from scripts.telemetry_storage import setup,encode,decode,read_rows,collect,block_size,raw_size

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');setup(self.db)
        self.db.execute('CREATE TABLE events(session TEXT,seq INTEGER,received REAL,type TEXT,data TEXT)')
    def tearDown(self):self.db.close()
    def test_roundtrip_and_sharing(self):
        text='{"payload":"'+('ônibus e imagem repetida '*1000)+'"}'
        first=encode(self.db,'a',text);size=block_size(self.db)
        second=encode(self.db,'a',text)
        self.assertEqual(block_size(self.db),size)
        self.assertEqual(decode(self.db,'a',second),text)
        self.assertEqual(raw_size(first),len(text.encode()))
        self.assertLess(size+len(first),len(text.encode()))
        self.assertEqual(decode(self.db,'a','{}'),'{}')
    def test_session_isolation_and_cleanup(self):
        text='abc'*1000;data=encode(self.db,'a',text)
        with self.assertRaises(ValueError):decode(self.db,'b',data)
        other=encode(self.db,'b',text)
        self.db.execute('INSERT INTO events VALUES (?,?,?,?,?)',('b',1,0,'trace',other))
        collect(self.db)
        self.assertEqual(block_size(self.db,'a'),0)
        self.assertEqual(read_rows(self.db,'b')[0][3],text)
    def test_corrupt_block_rejected(self):
        data=encode(self.db,'a','abc'*1000)
        self.db.execute("UPDATE telemetry_blocks SET data=x'00'")
        with self.assertRaises(Exception):decode(self.db,'a',data)
