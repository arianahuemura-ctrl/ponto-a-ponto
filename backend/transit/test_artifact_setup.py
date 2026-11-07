import io
import json
import shutil
import sqlite3
from contextlib import nullcontext
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from transit import test_sptrans_graph as fixtures
from transit.sptrans import graph, walk_artifacts, materialized_connections as m
from transit.management.commands import prepare_sptrans_artifacts as preparation


class ArtifactSetupTests(SimpleTestCase):
    def setUp(self):
        fixtures.GraphTests.setUp(self)
        patcher=patch.object(graph,'graph_path',return_value=self.index)
        patcher.start();self.addCleanup(patcher.stop)

    def fake_walk_build(self,*args,**kw):
        path=walk_artifacts.database_path()
        shutil.copy(self.index,path)
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE walk_meta(id PRIMARY KEY,value)')
            db.execute('INSERT INTO walk_meta VALUES(1,?)',(json.dumps({'version':1,'source_gtfs':graph.fingerprint(self.source),
                'profile':'foot','max_meters':1000,'speed_kmh':4.5,'configuration':preparation.config.walking_signature()}),))
        return {'database':str(path)}

    def run_prepare(self):
        call_command('prepare_sptrans_artifacts',min_free_gib=0,stdout=io.StringIO(),stderr=io.StringIO())

    def test_complete_small_city_then_reuse_without_rebuilding_or_network(self):
        with patch.object(preparation,'foot_router',return_value=nullcontext(('http://127.0.0.1:9999','fixture'))) as router, \
             patch.object(walk_artifacts,'build',side_effect=self.fake_walk_build):
            self.run_prepare();router.assert_called_once()
        self.assertTrue(preparation.metadata(m.database_path(),'materialization_meta')['city_complete'])
        self.assertTrue(m.query('A','D')['trajetos'])
        contents=m.database_path().read_bytes()
        with patch.object(preparation,'foot_router',side_effect=AssertionError('network')), \
             patch.object(preparation,'call_command',side_effect=AssertionError('unnecessary rebuild')):
            self.run_prepare()
        self.assertEqual(contents,m.database_path().read_bytes())

    def test_changed_snap_rebuilds_walks_and_preserves_old_materialization(self):
        with patch.object(preparation,'foot_router',return_value=nullcontext(('http://127.0.0.1:9999','fixture'))), \
             patch.object(walk_artifacts,'build',side_effect=self.fake_walk_build):
            self.run_prepare()
        before=m.database_path().read_bytes()
        with patch.object(preparation.config,'WALK_SNAP_METERS',10), \
             patch.object(preparation,'foot_router',return_value=nullcontext(('http://127.0.0.1:9999','fixture'))) as router, \
             patch.object(walk_artifacts,'build',side_effect=self.fake_walk_build):
            self.run_prepare()
            router.assert_called_once()
            self.assertTrue(preparation.metadata(m.database_path(),'materialization_meta')['city_complete'])
        backups=list(self.root.glob('*.obsolete-*'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_bytes(),before)

    def test_pending_materialization_does_not_claim_installation_success(self):
        with patch.object(preparation,'foot_router',return_value=nullcontext(('http://127.0.0.1:9999','fixture'))), \
             patch.object(walk_artifacts,'build',side_effect=self.fake_walk_build):
            self.run_prepare()
        with sqlite3.connect(m.database_path()) as db:
            data=preparation.metadata(m.database_path(),'materialization_meta');data['city_complete']=False
            db.execute('UPDATE materialization_meta SET value=?',(json.dumps(data),))
        with patch.object(preparation,'call_command') as command, self.assertRaisesRegex(CommandError,'pendentes'):
            self.run_prepare()
        self.assertEqual(command.call_args.args[0],'materialize_sptrans_connections')
        self.assertTrue(command.call_args.kwargs['all'])

    def test_incompatible_materialization_is_backed_up(self):
        with patch.object(preparation,'foot_router',return_value=nullcontext(('http://127.0.0.1:9999','fixture'))), \
             patch.object(walk_artifacts,'build',side_effect=self.fake_walk_build):
            self.run_prepare()
        with sqlite3.connect(m.database_path()) as db:
            data=preparation.metadata(m.database_path(),'materialization_meta');data['signature']['version']=-1
            db.execute('UPDATE materialization_meta SET value=?',(json.dumps(data),))
        before=m.database_path().read_bytes()
        self.run_prepare()
        backups=list(self.root.glob('*.obsolete-*'))
        self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),before)
        self.assertTrue(preparation.metadata(m.database_path(),'materialization_meta')['city_complete'])

    def test_graph_stage_does_not_start_network_or_materialization(self):
        with patch.object(preparation,'foot_router',side_effect=AssertionError('network')):
            call_command('prepare_sptrans_artifacts',until='graph',min_free_gib=0,stdout=io.StringIO())
        self.assertFalse(m.database_path().exists())

    def test_native_router_terminates_on_consumer_failure(self):
        from django.test import override_settings
        from unittest.mock import MagicMock
        tools=self.root/'.cache/osrm-6.0.0'
        (tools/'build').mkdir(parents=True)
        (tools/'source/profiles').mkdir(parents=True)
        (tools/'source/profiles/foot.lua').write_text('-- fixture')
        for name in ('osrm-extract','osrm-partition','osrm-customize','osrm-routed'):
            (tools/'build'/name).touch()
        pbf=self.root/'fixture.pbf';pbf.write_bytes(b'fixture')
        def run(args,**kwargs):
            if 'crop_sptrans_foot.py' in str(args[1]):
                from pathlib import Path
                Path(args[3]).write_bytes(b'cropped')
        process=MagicMock();process.poll.return_value=None
        with override_settings(BASE_DIR=self.root), \
             patch.object(preparation.subprocess,'run',side_effect=run) as runner, \
             patch.object(preparation.subprocess,'Popen',return_value=process) as spawn, \
             patch.object(preparation.urllib.request,'urlopen',return_value=io.BytesIO(b'{"code":"Ok"}')):
            with self.assertRaisesRegex(ValueError,'consumer failed'):
                with preparation.foot_router(pbf,self.index) as (url,network):
                    self.assertTrue(url.startswith('http://127.0.0.1:'))
                    self.assertTrue(network.startswith('osrm-6.0.0-foot:'))
                    raise ValueError('consumer failed')
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=10)
        self.assertIn('--ip',spawn.call_args.args[0])
        self.assertFalse(any('docker' in str(c) for c in runner.call_args_list))
