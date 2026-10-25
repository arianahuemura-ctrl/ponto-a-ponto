"""Inventário somente leitura; não executa benchmark ou materialização."""
import hashlib,json,sqlite3,subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path('/home/avale/Projetos/maua_bus_map')
result={'collected_at':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),'kind':'inventario_provisorio_nao_benchmark','commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'databases':[]}
for name in ['sptrans.sqlite3','sptrans.routing.sqlite3','sptrans.direct.sqlite3','sptrans.walks.sqlite3','sptrans.connections.sqlite3','sptrans.materialized.sqlite3']:
 p=ROOT/name;before=p.stat();h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 after=p.stat()
 result['databases'].append({'file':name,'bytes':after.st_size,'sha256':h.hexdigest(),'stable_during_hash':(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)})
with sqlite3.connect((ROOT/'sptrans.materialized.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
 result['metadata']=json.loads(db.execute('select value from materialization_meta').fetchone()[0])
 result['status']=[{'boardings':b,'state':s,'pairs':n} for b,s,n in db.execute('select boardings,state,count(*) from materialization_status group by boardings,state')]
 result['pairs_with_both_categories']=db.execute("select count(*) from (select origin,destination from materialization_status where state='ready' group by origin,destination having count(distinct boardings)=2)").fetchone()[0]
 result['stored_paths']=db.execute('select count(*) from conexoes').fetchone()[0]
result['notes']=['ready indica processamento da categoria, não existência de itinerário viável','city_complete=false; três embarques não estão materializados neste artefato','Tamanhos atuais não representam armazenamento final municipal','Tempo total de preparação e métricas A/B/C não medidos nesta rodada']
Path(__file__).with_name('inventario.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
