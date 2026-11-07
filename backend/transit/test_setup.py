"""Verifica a orquestração da instalação sem APT, rede, credenciais ou bancos reais."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import skipIf
from django.conf import settings
from django.test import SimpleTestCase


@skipIf(not hasattr(os, 'geteuid') or os.geteuid() == 0, 'setup requires a non-root POSIX user')
class SetupTests(SimpleTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='pap setup ')
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        shutil.copy(settings.BASE_DIR/'setup.sh',self.root/'setup.sh')
        for name in ('Makefile','.nvmrc','.env.example','requirements.system','requirements.txt','requirements-dev.txt','requirements-walking.txt'):
            shutil.copy(settings.BASE_DIR/name,self.root/name)
        (self.root/'frontend').mkdir()
        gtfs=self.root/'fonts/sptrans_gtfs';gtfs.mkdir(parents=True)
        (gtfs/'stops.txt').touch();(gtfs/'trips.txt').touch()
        self.bin=self.root/'bin';self.bin.mkdir()
        self.log=self.root/'calls'
        self.executable('python-test', '''
printf 'python %s\\n' "$*" >> "$SETUP_TEST_LOG"
if [[ "$1" == -m && "$2" == venv ]]; then mkdir -p "$3/bin"; cp "$0" "$3/bin/python"; fi
if [[ "$1" == -c && "$2" == *database_path* ]]; then echo "$SETUP_INDEX_EXISTS"; fi
if [[ "$1" == -c && "$2" == *get_user_model* ]]; then echo "$SETUP_ADMIN_EXISTS"; fi
if [[ "$1" == -m && "$2" == pip && "${SETUP_FAIL_PIP:-0}" == 1 ]]; then exit 7; fi
''')
        self.executable('node', 'echo 24\n')
        for command in ('apt-get','npm','npx'):
            self.executable(command, f'printf "{command} %s\\n" "$*" >> "$SETUP_TEST_LOG"\n')
        self.executable('sudo', '"$@"\n')
        nvm=self.root/'nvm';nvm.mkdir()
        (nvm/'nvm.sh').write_text('nvm() { printf "nvm %s\\n" "$*" >> "$SETUP_TEST_LOG"; }\n')
        self.env={**os.environ,'PATH':str(self.bin)+os.pathsep+os.environ['PATH'],
                  'PYTHON_BIN':str(self.bin/'python-test'),'NVM_DIR':str(nvm),
                  'SETUP_TEST_LOG':str(self.log),'SETUP_INDEX_EXISTS':'0','SETUP_ADMIN_EXISTS':'0'}

    def executable(self,name,body):
        p=self.bin/name;p.write_text('#!/bin/bash\nset -e\n'+body);p.chmod(0o755)

    def run_setup(self,*args,ok=True,**env):
        self.log.write_text('')
        result=subprocess.run(['bash',str(self.root/'setup.sh'),*args],cwd='/tmp',
                              env={**self.env,**env},text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode==0,ok,result.stdout+result.stderr)
        return self.log.read_text(),result

    def test_all_orders_every_dependency_before_its_consumers(self):
        calls,_=self.run_setup('--all')
        stages=['apt-get update','apt-get install','nvm install','nvm use','-m venv',
                '-m pip install -r requirements-dev.txt','-m pip install -r requirements-walking.txt',
                'manage.py migrate','manage.py import_sptrans','manage.py prepare_sptrans_artifacts','manage.py import_sources',
                'npm --prefix frontend ci','npm --prefix frontend run build',
                'npx playwright install --with-deps chromium','manage.py check','manage.py createsuperuser']
        positions=[calls.index(stage) for stage in stages]
        self.assertEqual(positions,sorted(positions))
        self.assertTrue((self.root/'.env').exists())

    def test_rerun_preserves_config_gtfs_and_administrator(self):
        (self.root/'.env').write_text('SPTRANS_TOKEN=private-test-placeholder\n')
        calls,result=self.run_setup('--all',SETUP_INDEX_EXISTS='1',SETUP_ADMIN_EXISTS='1')
        self.assertNotIn('manage.py import_sptrans',calls)
        self.assertNotIn('manage.py createsuperuser',calls)
        self.assertEqual((self.root/'.env').read_text(),'SPTRANS_TOKEN=private-test-placeholder\n')
        self.assertNotIn('private-test-placeholder',result.stdout+result.stderr)
        calls,_=self.run_setup('--all','--refresh-gtfs',SETUP_INDEX_EXISTS='1',SETUP_ADMIN_EXISTS='1')
        self.assertIn('manage.py import_sptrans',calls)

    def test_all_rejects_skip_before_side_effects_in_either_order(self):
        for args in (('--all','--skip-gtfs'),('--skip-gtfs','--all')):
            calls,result=self.run_setup(*args,ok=False)
            self.assertEqual(calls,'');self.assertIn('incompatíveis',result.stderr)

    def test_dependency_failure_prevents_dependent_steps(self):
        calls,_=self.run_setup('--all',ok=False,SETUP_FAIL_PIP='1')
        self.assertNotIn('manage.py migrate',calls)
        self.assertNotIn('npm ',calls)
        self.assertNotIn('manage.py createsuperuser',calls)

    def test_custom_gtfs_and_missing_data(self):
        custom=self.root/'custom gtfs';(self.root/'fonts/sptrans_gtfs').rename(custom)
        calls,_=self.run_setup('--all','--gtfs-source',str(custom))
        self.assertIn('import_sptrans --source '+str(custom),calls)
        calls,_=self.run_setup('--all',ok=False)
        self.assertNotIn('manage.py import_sources',calls)
        self.assertNotIn('manage.py createsuperuser',calls)

    def test_help_and_default_preserve_optional_behavior(self):
        calls,result=self.run_setup('--help')
        self.assertEqual(calls,'');self.assertIn('--all',result.stdout)
        calls,_=self.run_setup('--skip-gtfs')
        for unwanted in ('apt-get','nvm install','requirements-dev','requirements-walking','import_sources','createsuperuser','npx '):
            self.assertNotIn(unwanted,calls)
        self.assertIn('-m pip install -r requirements.txt',calls)

    def test_progress_finishes_only_after_success_for_selected_steps(self):
        import re
        for args in (('--all',),('--skip-gtfs',),()):
            with self.subTest(args=args):
                _,result=self.run_setup(*args)
                values=[int(p) for p in re.findall(r'\]\s+(\d+)%',result.stdout)]
                self.assertTrue(values)
                self.assertEqual(values[0],0)
                self.assertEqual(values[-1],100)
                self.assertEqual(values,sorted(values))
        _,result=self.run_setup('--all',ok=False,SETUP_FAIL_PIP='1')
        self.assertNotIn('100%',result.stdout)
        self.assertNotIn('Instalação concluída.',result.stdout)

    def test_artifacts_only_uses_make_and_forwards_paths_without_installing(self):
        self.run_setup('--skip-gtfs')
        calls,_=self.run_setup('--artifacts-only','--rebuild-artifacts','--osm-pbf','/tmp/input data.osm.pbf','--route-seconds','900')
        self.assertNotIn('pip install',calls)
        self.assertNotIn('npm ',calls)
        self.assertEqual(calls.count('--force'),1)
        stages=['--until graph','--until direct','--until walks','--until components','--until all']
        self.assertEqual([calls.index(s) for s in stages],sorted(calls.index(s) for s in stages))
        self.assertIn('--osm-pbf /tmp/input data.osm.pbf',calls)
        self.assertIn('--seconds 900',calls)

    def test_artifacts_only_rejects_conflicting_install_flags(self):
        calls,_=self.run_setup('--all','--artifacts-only',ok=False)
        self.assertEqual(calls,'')
