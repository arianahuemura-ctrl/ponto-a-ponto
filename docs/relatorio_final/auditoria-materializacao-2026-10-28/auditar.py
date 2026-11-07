"""Auditoria somente de leitura; não importa nem executa planejadores/materializadores."""
from pathlib import Path
import hashlib, json, sqlite3, statistics, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

OUT=Path(__file__).resolve().parent
ROOT=Path('/home/avale/Projetos/maua_bus_map')
ART=Path('/home/avale/Documentos/univesp/PI2/artifacts/materializacao-completa-2026-10-28')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def ro(p):
    assert not Path(str(p)+'-wal').exists(), 'Auditoria exige ausência de WAL externo.'
    db=sqlite3.connect(p.as_uri()+'?mode=ro&immutable=1',uri=True)
    db.execute('PRAGMA query_only=ON')
    return db
def inventory(p):
    before=(p.stat().st_size,p.stat().st_mtime_ns,sha(p))
    with ro(p) as db:
        result={'path':str(p),'bytes':p.stat().st_size,'sha256':before[2],
            'integridade':db.execute('PRAGMA quick_check').fetchone()[0],
            'categorias':db.execute('SELECT boardings,state,count(*),sum(path_count) FROM materialization_status GROUP BY boardings,state').fetchall(),
            'trajetos_por_categoria':db.execute('SELECT boardings,count(*) FROM conexoes GROUP BY boardings').fetchall(),
            'pares_ambas_prontas':db.execute("SELECT count(*) FROM (SELECT origin,destination FROM materialization_status WHERE state='ready' GROUP BY origin,destination HAVING count(DISTINCT boardings)=2)").fetchone()[0],
            'pares_com_candidato_pronto':db.execute("SELECT count(*) FROM (SELECT DISTINCT c.origin,c.destination FROM conexoes c JOIN materialization_status m USING(origin,destination,boardings) WHERE m.state='ready')").fetchone()[0],
            'categorias_prontas_vazias':db.execute("SELECT boardings,count(*) FROM materialization_status WHERE state='ready' AND path_count=0 GROUP BY boardings").fetchall(),
            'ultimo_registro':db.execute('SELECT max(updated_at) FROM materialization_status').fetchone()[0],
            'meta':json.loads(db.execute('SELECT value FROM materialization_meta').fetchone()[0])}
    assert before==(p.stat().st_size,p.stat().st_mtime_ns,sha(p))
    return result

result={'data':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
    'git':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'banco_atual':inventory(ROOT/'sptrans.materialized.sqlite3'),
    'backup_anterior':inventory(ART/'materializado-antes.sqlite3')}
e=json.loads((ART/'estimativa-escala.json').read_text())
values=list(e['amostra_estratificada'].values())
raw=statistics.mean(values)*e['origens']
gib=raw*e['bytes_ocupados']/e['pares_prontos_observados']/1024**3
result['estimativa']={'dados_registrados':e,'media':statistics.mean(values),'min':min(values),
    'max':max(values),'mediana':statistics.median(values),'desvio_padrao_amostral':statistics.stdev(values),
    'pares_projetados_sem_arredondar':raw,'pares_arredondados':round(raw),
    'gib_reproduzido':gib,'diferenca_gib':gib-e['estimativa_gib_por_extrapolacao']}
with ro(ROOT/'sptrans.connections.sqlite3') as db:
    patterns=[json.loads(r[0]) for r in db.execute('SELECT stops FROM pattern')]
    starts=sorted({s for p in patterns for s in p[:-1]})
    indices=[starts.index(s) for s in e['amostra_estratificada']]
    result['amostragem']={'universo':len(starts),'indices':indices,
        'selecao_sistematica_compativel':indices==[i*(len(starts)-1)//31 for i in range(32)],
        'nota':'Padrão inferido dos identificadores; script original da seleção não está no diretório de evidências.'}
    walks={}
    for a,b in db.execute('SELECT origin,destination FROM walking_link'):
        walks.setdefault(a,set()).add(b)
    reproduced={}
    # Mesma alcançabilidade de city_pairs: duas expansões dirigidas e caminhadas.
    # Apenas confere os 32 totais; não enumera/grava candidatos nem avalia horários.
    for origin in e['amostra_estratificada']:
        frontier={origin};reached=set()
        for _ in range(2):
            bus=set()
            for stops in patterns:
                boarding=False
                for stop in stops:
                    if boarding:bus.add(stop)
                    if stop in frontier:boarding=True
            frontier=set(bus)
            for stop in bus:frontier.update(walks.get(stop,()))
            reached.update(frontier)
        reproduced[origin]=len(reached-{origin})
    result['amostragem']['totais_reproduzidos']=reproduced
    result['amostragem']['todos_iguais']=reproduced==e['amostra_estratificada']

sources=['materialized_adapter.py','materialized_connections.py','connection_planner.py',
    'planner.py','alternatives.py','connection_adapter.py','city_connections.py','catalog.py',
    'graph.py','direct.py','walking.py','journey_completion.py']
(OUT/'codigo').mkdir(exist_ok=True)
result['codigo']={}
for name in sources:
    p=ROOT/'backend/transit/sptrans'/name
    (OUT/'codigo'/name).write_bytes(p.read_bytes())
    result['codigo'][str(p)]={'sha256':sha(p)}
result['evidencias_origem']={str(p):sha(p) for p in ART.iterdir() if p.is_file()}
(OUT/'evidencias.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('codigo','evidencias_origem')},ensure_ascii=False,indent=2))
