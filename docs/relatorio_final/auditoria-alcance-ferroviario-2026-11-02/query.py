import sys,os,json,sqlite3,hashlib,subprocess,time,socket
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
R=Path('/home/avale/Projetos/maua_bus_map');P=Path('/tmp/pap-alcance-ferroviario-20261102');sys.path.insert(0,str(R/'backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','mbm.settings')
# Every SQLite connection in this process is forced read-only. No network requests.
original_connect=sqlite3.connect;accessed=set()
def readonly(path,*a,**kw):
 s=str(path)
 if s==':memory:':raise RuntimeError('Unexpected memory database')
 if s.startswith('file:'):s=s.split('?')[0]
 else:s=Path(s).resolve().as_uri()
 kw['uri']=True;c=original_connect(s+'?mode=ro',*a,**kw);c.execute('PRAGMA query_only=ON');accessed.add(s);return c
sqlite3.connect=readonly
class NetworkForbidden(RuntimeError):pass
def block(*a,**k):raise NetworkForbidden('Network disabled for read-only audit')
socket.socket.connect=block
import django;django.setup()
from transit.sptrans import store,planner,rail,staged_adapter,staged_materialized,transfer_policy
from mbm import routing_config
from django.conf import settings
now=datetime.now(ZoneInfo('America/Sao_Paulo'))
files=list(R.glob('sptrans*.sqlite3'))+[R/'db.sqlite3']
def stats():return {str(p):{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in files}
before=stats();codefiles=sorted((R/'backend/transit/sptrans').glob('*.py'))+sorted((R/'backend/mbm').glob('*.py'))
manifest={'observed_at':now.isoformat(),'development_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'development_branch':subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip(),'source_sha256':{str(p.relative_to(R)):hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in codefiles},'effective_config':{'SPTRANS_DATABASE':settings.SPTRANS_DATABASE,'HORIZON_SECONDS':planner.HORIZON_SECONDS,'TRANSFER_SECONDS':planner.TRANSFER_SECONDS,'WALK_LIMIT_METERS':routing_config.WALK_LIMIT_METERS,'rail_version':rail.VERSION},'database_stats_before':before,'queries':[]}
(P/'development-status.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=R,text=True));(P/'development-code.diff').write_text(subprocess.check_output(['git','diff','HEAD','--','backend/transit/sptrans','backend/mbm'],cwd=R,text=True))
with store.connection() as db:
 targets=[dict(r) for r in db.execute("SELECT stop_id,stop_name FROM stops WHERE stop_name LIKE '%Tamanduate%' OR stop_id IN ('18935','18937','18859')")];manifest['targets']=targets;print(targets,flush=True)
 fixed=datetime.fromisoformat('2026-11-02T08:00:00-03:00')
 for a,b,when,label in [('18935','18859',now,'horário real da auditoria'),('18935','18859',fixed,'partida de referência às 08h'),('18859','18935',fixed,'retorno às 08h'),('18937','18859',fixed,'Guapituba às 08h'),('18859','18937',fixed,'retorno a Guapituba às 08h'),('18935','18859',datetime.fromisoformat('2027-05-03T08:00:00-03:00'),'controle após vigência')]:
  t=time.monotonic();origin=store.get_stop(db,a);destination=store.get_stop(db,b);snapshots=list(staged_adapter.progressive(db,origin,destination,4,when));q={'origin':origin,'destination':destination,'requested_departure':when.isoformat(),'label':label,'method':'staged_adapter.progressive, real local data, read-only, network disabled','seconds':time.monotonic()-t,'snapshots':snapshots};manifest['queries'].append(q);(P/'queries.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));journeys=snapshots[-1]['journeys'];print(label,'routes',len(journeys),'elapsed',round(q['seconds'],3),flush=True)
  if journeys:print(json.dumps({k:journeys[0].get(k) for k in ['departure','arrival','duration_minutes','transfer_count','transfer_cost']},ensure_ascii=False),[(l['code'],l['origin']['name'],l['destination']['name'],l['departure'],l['arrival']) for l in journeys[0]['legs']],flush=True)
manifest['database_stats_after']=stats();manifest['unchanged_database_stats']=before==stats();assert manifest['unchanged_database_stats'];manifest['sqlite_accessed']=sorted(accessed);manifest['all_sqlite_connections_forced_readonly']=True;manifest['gtfs_sha256_after']=hashlib.file_digest((R/'sptrans.sqlite3').open('rb'),'sha256').hexdigest();assert manifest['gtfs_sha256_after']==json.loads((P/'database-inspection.json').read_text())['db_sha256'];(P/'queries.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print('DONE, DATABASES UNCHANGED',flush=True)
