"""Instalação retomável dos artefatos de rotas na ordem das dependências."""
from contextlib import closing, contextmanager
from datetime import datetime
import hashlib
from mbm import routing_config as config
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import graph, direct, catalog, city_connections, walk_artifacts, materialized_connections as materialized

OSRM_VERSION = config.OSRM_VERSION
PBF_URL = config.OSM_PBF_URL


def metadata(path, table):
    with closing(graph.readonly(path)) as db:
        return json.loads(db.execute(f'SELECT value FROM {table} WHERE id=1').fetchone()[0])


def valid(check):
    try:
        return bool(check())
    except (OSError, ValueError, KeyError, sqlite3.Error):
        return False


@contextmanager
def foot_router(pbf, graph_path):
    """OSRM nativo em processo local privado, sempre encerrado ao sair."""
    tools=settings.BASE_DIR/'.cache'/('osrm-'+OSRM_VERSION)
    source=tools/'source';build=tools/'build'
    names=('osrm-extract','osrm-partition','osrm-customize','osrm-routed')
    if not all((build/name).is_file() for name in names):
        for tool in ('git','cmake','c++'):
            if not shutil.which(tool):raise CommandError('Dependências OSRM ausentes. Execute ./setup.sh --system --routes.')
        tools.mkdir(parents=True,exist_ok=True)
        if not source.exists():
            subprocess.run(['git','clone','--branch','v'+OSRM_VERSION,'--depth','1','--recurse-submodules',
                            'https://github.com/Project-OSRM/osrm-backend.git',str(source)],check=True)
        subprocess.run(['git','-C',str(source),'submodule','update','--init','--recursive'],check=True)
        subprocess.run(['cmake','-S',str(source),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DENABLE_LTO=OFF'],check=True)
        subprocess.run(['cmake','--build',str(build),'--parallel',str(config.OSRM_BUILD_JOBS),'--target',*names],check=True)
    profile=source/'profiles/foot.lua'
    if not profile.is_file():raise CommandError('Perfil foot do OSRM ausente.')
    cache=settings.BASE_DIR/'.cache/pap-foot';cache.mkdir(parents=True,exist_ok=True)
    if pbf is None:
        pbf=cache/'sudeste.osm.pbf'
        if not pbf.exists():
            partial=pbf.with_suffix('.part')
            subprocess.run(['curl','-fL','--retry','2','-o',str(partial),PBF_URL],check=True)
            partial.replace(pbf)
    pbf=Path(pbf).resolve()
    if not pbf.is_file():raise CommandError('Arquivo OSM/PBF não encontrado.')
    # Isole cada preparação para nunca reutilizar uma extração OSRM interrompida.
    import tempfile
    import sys
    with tempfile.TemporaryDirectory(prefix='prepare-',dir=cache) as temporary:
        work=Path(temporary);cropped=work/'sao-paulo-foot.osm.pbf'
        subprocess.run([sys.executable,str(settings.BASE_DIR/'scripts/crop_sptrans_foot.py'),str(pbf),str(cropped),'--graph',str(graph_path)],check=True)
        with cropped.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        for arguments in ([str(build/'osrm-extract'),'-p',str(profile),str(cropped)],
                          [str(build/'osrm-partition'),str(work/'sao-paulo-foot.osrm')],
                          [str(build/'osrm-customize'),str(work/'sao-paulo-foot.osrm')]):
            subprocess.run([*arguments,'--threads',str(config.OSRM_THREADS)],check=True,cwd=source/'profiles')
        import socket
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url='http://127.0.0.1:'+str(port)
        with (work/'router.log').open('w') as log:
            process=subprocess.Popen([str(build/'osrm-routed'),'--ip','127.0.0.1','--port',str(port),
                '--algorithm','mld','--threads',str(config.OSRM_THREADS),'--max-table-size',str(config.OSRM_MAX_TABLE_SIZE),str(work/'sao-paulo-foot.osrm')],stdout=log,stderr=log)
            try:
                deadline=time.monotonic()+config.OSRM_STARTUP_SECONDS
                while True:
                    if process.poll() is not None:raise CommandError('OSRM encerrou: '+(work/'router.log').read_text()[-2000:])
                    try:
                        with urllib.request.urlopen(url+'/nearest/v1/foot/-46.6333,-23.5505',timeout=2) as response:
                            if json.load(response).get('code')=='Ok':break
                    except (OSError,ValueError):pass
                    if time.monotonic()>=deadline:raise CommandError(f'OSRM não ficou disponível em {config.OSRM_STARTUP_SECONDS:g} segundos.')
                    time.sleep(1)
                yield url,'osrm-'+OSRM_VERSION+'-foot:'+digest
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()


class Command(BaseCommand):
    help='Prepara grafo, custos, diretas, caminhadas, componentes e conexões físicas da cidade, nessa ordem.'

    def add_arguments(self,p):
        p.add_argument('--osm-pbf',type=Path,help='Extrato OSM existente; sem ele baixa o Sudeste da Geofabrik.')
        p.add_argument('--experimental',action='store_true',help='Materialização com heurísticas em banco separado.')
        p.add_argument('--until',choices=['graph','direct','walks','components','all'],default='all')
        p.add_argument('--force',action='store_true',help='Preserva backups e reconstrói artefatos derivados.')
        p.add_argument('--seconds',type=float,default=config.ROUTE_SECONDS)
        p.add_argument('--min-free-gib',type=float,default=config.MIN_FREE_GIB)

    def handle(self,*args,**o):
        try:
            if not math.isfinite(o['seconds']) or not math.isfinite(o['min_free_gib']) or o['seconds']<=0 or o['min_free_gib']<0:raise ValueError('Limites de tempo/disco inválidos.')
            gtfs=graph.store.database_path()
            if not gtfs.is_file():raise ValueError('Importe o GTFS antes de gerar os artefatos.')
            if shutil.disk_usage(gtfs.parent).free < o['min_free_gib']*1024**3:
                raise ValueError('Espaço livre abaixo da reserva para geração dos artefatos.')
            signature=graph.fingerprint(gtfs)
            backup=None
            if o['force']:
                backup=gtfs.parent/('artifacts-backup-'+datetime.now().strftime('%Y%m%d%H%M%S%f'))
                backup.mkdir()
                for path in [graph.graph_path(),direct.database_path(),walk_artifacts.database_path(),city_connections.database_path(),materialized.database_path()]:
                    if path.exists():path.replace(backup/path.name)
                self.stdout.write('Artefatos anteriores preservados em '+str(backup))
            measurements=[]
            report=settings.BASE_DIR/'.cache/setup'/('artifacts-'+datetime.now().strftime('%Y%m%d%H%M%S%f')+'.json')
            report.parent.mkdir(parents=True,exist_ok=True)
            def stage(command,**kwargs):
                start=time.monotonic();entry={'stage':command,'status':'failed'}
                try:
                    result=call_command(command,**kwargs);entry['status']='complete';return result
                finally:
                    entry['seconds']=time.monotonic()-start;measurements.append(entry)
                    report.write_text(json.dumps(measurements,indent=2))
                    self.stdout.write(f"{command}: {entry['seconds']:.2f} s ({entry['status']}); relatório: {report}")
            def graph_valid():
                with graph.connection() as db:
                    return metadata(graph.graph_path(),'graph_meta')['walk_radius']>=config.WALK_LIMIT_METERS
            if not valid(graph_valid):stage('build_sptrans_graph',stdout=self.stdout,stderr=self.stderr)
            # Instale tabelas de custos históricos apenas quando ausentes; preserve os perfis existentes.
            def costs_ready():
                with graph.connection() as db:
                    return db.execute("SELECT count(*) FROM sqlite_master WHERE name IN ('connection_segments','historical_profiles','historical_days','connection_operational_mappings')").fetchone()[0]==4
            if not valid(costs_ready):catalog.install()
            if backup and (backup/graph.graph_path().name).exists():
                with sqlite3.connect(graph.graph_path()) as db:
                    db.execute('ATTACH DATABASE ? AS old',(str(backup/graph.graph_path().name),))
                    old=db.execute("SELECT value FROM old.graph_meta").fetchone()
                    if old and json.loads(old[0]).get('source')==signature:
                        for table in ('historical_profiles','historical_days'):
                            if db.execute("SELECT 1 FROM old.sqlite_master WHERE name=?",(table,)).fetchone():
                                db.execute(f'INSERT OR REPLACE INTO {table} SELECT * FROM old.{table}')
            if o['until']=='graph':return
            def direct_valid():
                with direct.connection():return True
            if not valid(direct_valid):stage('build_sptrans_direct',stdout=self.stdout,stderr=self.stderr)
            if o['until']=='direct':return
            def walks_valid():
                m=metadata(walk_artifacts.database_path(),'walk_meta')
                return m['version']==walk_artifacts.VERSION and m['source_gtfs']==signature and m['profile']=='foot' and m['max_meters']==config.WALK_LIMIT_METERS and m['speed_kmh']==config.WALK_SPEED_KMH and m.get('configuration')==config.walking_signature()
            if not valid(walks_valid):
                with foot_router(o['osm_pbf'],graph.graph_path()) as (url,network):
                    stage('build_sptrans_walks',router=url,network_id=network,stdout=self.stdout,stderr=self.stderr)
            if o['until']=='walks':return
            def components_valid():
                m=materialized._source_meta(city_connections.database_path())
                return m['source_gtfs']==signature and m.get('walk_source')==graph.fingerprint(walk_artifacts.database_path()) and m.get('walking_speed_kmh')==config.WALK_SPEED_KMH and m.get('max_walk_meters')==config.WALK_LIMIT_METERS and m.get('quotas')=={str(k):v for k,v in city_connections.QUOTAS.items()}
            if not valid(components_valid):
                stage('build_sptrans_city_connections',walk_database=str(walk_artifacts.database_path()),stdout=self.stdout,stderr=self.stderr)
            if o['until']=='components':return
            target=materialized.database_path(o['experimental'])
            def final_valid():
                materialized._validate(metadata(target,'materialization_meta'))
                return True
            if target.exists() and not valid(final_valid):
                backup=target.with_name(target.name+'.obsolete-'+datetime.now().strftime('%Y%m%d%H%M%S%f'))
                target.replace(backup)
                self.stdout.write('Materialização incompatível preservada em '+str(backup))
            if not target.exists() or not metadata(target,'materialization_meta').get('city_complete'):
                stage('materialize_sptrans_connections',all=True,experimental=o['experimental'],seconds=o['seconds'],min_free_gib=o['min_free_gib'],stdout=self.stdout,stderr=self.stderr)
            if not metadata(target,'materialization_meta').get('city_complete'):
                raise CommandError('Materialização ainda tem categorias pendentes. Execute novamente para retomá-las; instalação não concluída.')
            self.stdout.write(self.style.SUCCESS('Artefatos de rotas completos e compatíveis com o GTFS.'))
        except (OSError,ValueError,KeyError,sqlite3.Error,subprocess.CalledProcessError) as error:
            raise CommandError(str(error)) from error
