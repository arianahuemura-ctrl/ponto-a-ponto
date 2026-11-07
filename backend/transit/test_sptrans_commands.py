"""Exercita os contratos públicos da CLI com pequenos artefatos GTFS descartáveis."""
import io
import json
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from transit import test_sptrans_graph as fixtures
from transit.sptrans import graph, direct, city_connections, materialized_connections


class PlannerCommandTests(SimpleTestCase):
    def setUp(self):
        fixtures.GraphTests.setUp(self)
        self.dp=self.root/'direct.sqlite3'; self.cp=self.root/'components.sqlite3'; self.mp=self.root/'materialized.sqlite3'

    def command(self, name, *args, **kw):
        output=io.StringIO()
        call_command(name,*args,stdout=output,stderr=io.StringIO(),**kw)
        return output.getvalue()

    def structures(self):
        self.command('build_sptrans_direct',graph_database=str(self.index),database=str(self.dp))
        self.command('build_sptrans_city_connections',direct_database=str(self.dp),graph_database=str(self.index),database=str(self.cp))

    def test_build_query_and_resume_physical_connections(self):
        # Sem HTTP durante a geração, inclusive nos comandos que encapsulam os geradores.
        with patch('urllib.request.urlopen',side_effect=AssertionError('network')):
            self.command('build_sptrans_graph',database=str(self.index))
            self.structures()
            pairs=self.root/'pairs.json';pairs.write_text(json.dumps({'pairs':[{'a':'A','b':'D'}]}))
            options=dict(source=str(self.cp),database=str(self.mp),pairs_file=str(pairs),min_free_gib=0)
            first=json.loads(self.command('materialize_sptrans_connections',**options))
            second=json.loads(self.command('materialize_sptrans_connections',**options))
            self.assertEqual(first['built_categories'],2)
            self.assertEqual(second['skipped_categories'],2)
            result=json.loads(self.command('query_sptrans_city_connections','A','D',database=str(self.mp)))
            self.assertEqual({r['embarques'] for r in result['trajetos']},{1,2})
            self.assertTrue(result['complete'])

    def test_direct_forward_reverse_and_transfer_cli(self):
        self.structures()
        for args in (('A','D'),('D','A','--reverse'),('A','D','--transfer')):
            with self.subTest(args=args):
                result=json.loads(self.command('query_sptrans_direct',*args,database=str(self.dp)))
                self.assertTrue(result)
        with self.assertRaises(CommandError):
            self.command('query_sptrans_direct','A','--transfer',database=str(self.dp))

    def test_catalog_stream_and_coordinate_costs(self):
        self.command('build_sptrans_connections','--pair','A','D',database=str(self.index))
        structural=json.loads(self.command('query_sptrans_connections','A','D','--structure',database=str(self.index)))
        self.assertEqual({r['embarques'] for r in structural['trajetos']},{1,2,3})
        kwargs=dict(database=str(self.index),at=fixtures.NOW.isoformat(),egress_meters=150)
        stream=[json.loads(line) for line in self.command('query_sptrans_connections','A','D','--stream',**kwargs).splitlines()]
        self.assertFalse(stream[0]['complete']);self.assertTrue(stream[-1]['complete'])
        self.assertEqual(stream[-1]['journeys'][0]['duration_seconds'],2520)
        self.assertEqual(json.loads(self.command('query_sptrans_connections','A','D',**kwargs))['journeys'],stream[-1]['journeys'])
        result=json.loads(self.command('query_sptrans_graph','A','D',database=str(self.index),at=fixtures.NOW.isoformat()))
        self.assertEqual(result['journeys'][0]['duration_seconds'],2400)

    def test_missing_artifacts_and_invalid_dates_fail_clearly(self):
        for command in ('query_sptrans_connections','query_sptrans_graph','query_sptrans_city_connections'):
            with self.subTest(command=command),self.assertRaises(CommandError):
                self.command(command,'A','D',database=str(self.root/'absent.sqlite3'))
        with self.assertRaises(CommandError):
            self.command('query_sptrans_graph','A','D',database=str(self.index),at='invalid')
        self.assertFalse((self.root/'absent.sqlite3').exists())

    def test_bad_pair_file_and_negative_disk_reserve(self):
        self.structures()
        p=self.root/'invalid.json';p.write_text('[["A"]]')
        for kw in ({'min_free_gib':0},{'min_free_gib':-1}):
            with self.subTest(kw=kw),self.assertRaises(CommandError):
                self.command('materialize_sptrans_connections',source=str(self.cp),database=str(self.mp),pairs_file=str(p),**kw)
        self.assertFalse(self.mp.exists())

    def test_walk_jsonl_import_uses_four_point_five_kmh(self):
        p=self.root/'walks.jsonl'
        p.write_text('\n'+json.dumps({'origin':'B','destination':'E','result':{'available':True,
            'distance_meters':75,'geometry':[[-23.55,-46.63],[-23.5499,-46.63]]}})+'\n')
        result=json.loads(self.command('verify_sptrans_walks',database=str(self.index),file=str(p)))
        self.assertEqual(result['imported'],1)
        with graph.connection(self.index) as db:
            row=db.execute("SELECT * FROM walk_edge WHERE origin='B' AND destination='E'").fetchone()
            self.assertEqual(row['seconds'],60);self.assertEqual(row['status'],'verified')

    def test_all_marks_complete_and_origin_limits_scope(self):
        self.structures()
        self.command('materialize_sptrans_connections','--origin','A',source=str(self.cp),database=str(self.mp),min_free_gib=0)
        with graph.readonly(self.mp) as db:
            self.assertEqual({r[0] for r in db.execute('SELECT DISTINCT origin FROM materialization_status')},{'A'})
            self.assertFalse(materialized_connections._read_meta(db)['city_complete'])
        self.command('materialize_sptrans_connections','--all',source=str(self.cp),database=str(self.mp),min_free_gib=0)
        with graph.readonly(self.mp) as db:self.assertTrue(materialized_connections._read_meta(db)['city_complete'])
