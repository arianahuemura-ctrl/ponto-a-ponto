"""Precedência e propagação da configuração sem ler credenciais reais."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from django.conf import settings
from django.test import SimpleTestCase
from mbm.environment import load_environment


class EnvironmentTests(SimpleTestCase):
    def test_precedence_and_dotenv_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'.env.example').write_text('BASE=default\nLOCAL=default\nEXTERNAL=default\nEMPTY=default\n')
            (root/'.env').write_text('export LOCAL="valor com espaço" # comentário\nEXTERNAL=local\nEMPTY=\nLITERAL=${BASE}\nIGNORED\n')
            env={'EXTERNAL':'process'}
            load_environment(root,env)
            self.assertEqual(env,dict(BASE='default',LOCAL='valor com espaço',EXTERNAL='process',EMPTY='',LITERAL='${BASE}'))

    def test_missing_local_file_keeps_example(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'.env.example').write_text('VALUE=42\n')
            self.assertEqual(load_environment(root,{}),{'VALUE':'42'})

    def child(self, overrides, code):
        # O subprocesso recebe apenas os padrões públicos e os valores do teste.
        from dotenv import dotenv_values
        env={k:v for k,v in os.environ.items() if not k.startswith(('PAP_','SPTRANS_'))}
        env.update({k:v for k,v in dotenv_values(settings.BASE_DIR/'.env.example',interpolate=False).items() if v is not None})
        env.update(overrides)
        return subprocess.run([sys.executable,'-c',code],cwd=settings.BASE_DIR/'backend',env=env,capture_output=True,text=True)

    def test_custom_parameters_reach_algorithms_and_commands(self):
        result=self.child({'PAP_WALK_LIMIT_METERS':'1500','PAP_WALK_SPEED_KMH':'3.6','PAP_ROUTES_DIRECT':'12','PAP_ROUTE_SECONDS':'42'},
            "from mbm import routing_config as c; from transit.sptrans import walking, walk_artifacts, city_connections; "
            "from transit.management.commands.prepare_sptrans_artifacts import Command; "
            "p=Command().create_parser('manage.py','prepare'); "
            "assert walking.WALK_LIMIT==1500; assert walk_artifacts.SPEED_MPS==1; "
            "assert walk_artifacts.classify(1200,1400,0,0)[0]=='verified'; "
            "assert city_connections.QUOTAS[1]==12; assert p.parse_args([]).seconds==42; "
            "assert p.parse_args(['--seconds','7']).seconds==7")
        self.assertEqual(result.returncode,0,result.stderr)

    def test_invalid_configuration_fails_with_parameter_name(self):
        for key,value in [('PAP_WALK_SPEED_KMH','0'),('PAP_WALK_SPEED_KMH','nan'),('PAP_WALK_WORKERS','17'),
                          ('PAP_ROUTES_DIRECT','1.5'),('PAP_WALK_BATCH_SIZE','200'),('PAP_MIN_FREE_GIB','-1')]:
            with self.subTest(key=key,value=value):
                result=self.child({key:value},'from mbm import routing_config')
                self.assertNotEqual(result.returncode,0)
                self.assertIn(key if key!='PAP_WALK_BATCH_SIZE' else 'PAP_OSRM_MAX_TABLE_SIZE',result.stderr)

    def test_signature_changes_for_result_parameters_only(self):
        code='import json; from mbm.routing_config import walking_signature; print(json.dumps(walking_signature(),sort_keys=True))'
        default=self.child({},code);self.assertEqual(default.returncode,0,default.stderr)
        parallel=self.child({'PAP_WALK_WORKERS':'2'},code)
        changed=self.child({'PAP_WALK_SNAP_METERS':'10'},code)
        self.assertEqual(default.stdout,parallel.stdout)
        self.assertNotEqual(default.stdout,changed.stdout)
