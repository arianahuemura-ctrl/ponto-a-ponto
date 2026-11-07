"""Paired statistics; never count empty completions as fast first routes."""
import json,statistics,csv
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OLD=ROOT/'artifacts/benchmarks/coverage-audit-20261101';NEW=ROOT/'artifacts/benchmarks/async-comparison-20261101'
key=lambda r:(r['group'],r['hour'],r['origin'],r['destination'])
oldrows=[json.loads(l) for l in (OLD/'latency-results.jsonl').read_text().splitlines()];newrows=[json.loads(l) for l in (NEW/'latency-results.jsonl').read_text().splitlines()]
a={key(r):r for r in oldrows};b={key(r):r for r in newrows};assert len(a)==len(oldrows)==len(b)==len(newrows)==3264 and a.keys()==b.keys()
assert all(a[k]['batch']==b[k]['batch'] and a[k]['departure']==b[k]['departure'] for k in a)
previous_validation=json.loads((OLD/'validation.json').read_text())
for name in ['sptrans.sqlite3','sptrans.staged.sqlite3','sptrans.staged-walks.sqlite3']:
 st=(ROOT/name).stat();assert previous_validation[name]=={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
def success(r):return r['flow']['state']=='first_route' and r['flow']['first_route_seconds']<=30
def percentile(v,q):return sorted(v)[round((len(v)-1)*q)] if v else None
def stats(v):return {'n':len(v),'median':statistics.median(v) if v else None,'p95':percentile(v,.95),'max':max(v) if v else None}
def paired(keys):
 both=[k for k in keys if success(a[k]) and success(b[k])]
 return {'n':len(both),'old':stats([a[k]['flow']['first_route_seconds'] for k in both]),'new':stats([b[k]['flow']['first_route_seconds'] for k in both]),'faster':sum(b[k]['flow']['first_route_seconds']<a[k]['flow']['first_route_seconds'] for k in both),'old_success':sum(success(a[k]) for k in keys),'new_success':sum(success(b[k]) for k in keys),'newly_served':sum(not success(a[k]) and success(b[k]) for k in keys),'lost_success':sum(success(a[k]) and not success(b[k]) for k in keys)}
keys=list(a);cohorts={'all':keys,'prepared_previously_available':[k for k in keys if a[k]['prepared']['state']=='first_route'],'external_before_ready_materialized':[k for k in keys if a[k]['flow']['state']=='external_required' and a[k]['prepared']['state']=='first_route'],'previously_above_5s':[k for k in keys if success(a[k]) and a[k]['flow']['first_route_seconds']>5]}
report={'queries':len(keys),'same_inputs_and_data':True,'old_states':dict(Counter(r['flow']['state'] for r in oldrows)),'new_states':dict(Counter(r['flow']['state'] for r in newrows)), 'cohorts':{name:paired(ks) for name,ks in cohorts.items()},'by_hour':{str(h):paired([k for k in keys if k[1]==h]) for h in [8,14,2]},'by_group':{g:paired([k for k in keys if k[0]==g]) for g in dict.fromkeys(k[0] for k in keys)},'by_old_cost':{str(c):paired([k for k in keys if success(a[k]) and a[k]['flow'].get('planner')!='walk' and a[k]['flow'].get('cost')==c]) for c in [0,1,2,3,4]},'new_source_failures':sum(bool(r['flow'].get('failed_sources')) for r in newrows),'new_source_saturation':sum(bool(r['flow'].get('busy_sources')) for r in newrows),'new_first_with_parallel_external_attempt':sum(success(r) and r['flow']['external_attempts_before_return']>0 for r in newrows)}
for name,ks in cohorts.items():report['cohorts'][name]['new_success_times']=stats([b[k]['flow']['first_route_seconds'] for k in ks if success(b[k])])
(NEW/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
with (NEW/'paired-results.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['group','hour','origin','destination','old_state','new_state','old_first_seconds','new_first_seconds','delta_seconds'])
 for k in keys:
  x,y=a[k]['flow'],b[k]['flow'];w.writerow([*k,x['state'],y['state'],x.get('first_route_seconds'),y.get('first_route_seconds'),y['first_route_seconds']-x['first_route_seconds'] if success(a[k]) and success(b[k]) else None])
lines=['','## Resultados','',f"Foram repetidas as {len(keys):,} consultas, sem alteração dos três bancos de dados. A comparação pareada inclui somente os casos que entregaram rota em até 30 s nos dois levantamentos; ganhos e perdas de disponibilidade são contados separadamente.",'', '| Resultado | Antes | Depois |','|---|---:|---:|']
for state in sorted(set(report['old_states'])|set(report['new_states'])):lines.append(f"| {state} | {report['old_states'].get(state,0)} | {report['new_states'].get(state,0)} |")
x=report['cohorts']['all'];lines+=['',f"Casos com primeira rota nos dois testes: {x['n']}. Passaram a receber rota: {x['newly_served']}. Não reproduziram o sucesso anterior: {x['lost_success']}. As diferenças de disponibilidade não são atribuídas automaticamente à alteração: buscas com orçamento interno dependem de carga/cache e chamadas externas continuam bloqueadas.",'',
'| Horário | Pares com sucesso em ambos | Mediana antes | Mediana depois | P95 antes | P95 depois |','|---|---:|---:|---:|---:|---:|']
for h,x in report['by_hour'].items():lines.append(f"| {int(h):02d}:00 | {x['n']} | {x['old']['median']:.3f} s | {x['new']['median']:.3f} s | {x['old']['p95']:.3f} s | {x['new']['p95']:.3f} s |")
lines+=['','### Custo da primeira rota do teste anterior','', 'A classificação usa o custo anterior para manter os mesmos pares em cada grupo; a alternativa entregue agora pode ser diferente.','', '| Custo | Pares com sucesso em ambos | Mediana antes | Mediana depois | P95 antes | P95 depois |','|---|---:|---:|---:|---:|---:|']
for c,x in report['by_old_cost'].items():
 if x['n']:lines.append(f"| {c} | {x['n']} | {x['old']['median']:.3f} s | {x['new']['median']:.3f} s | {x['old']['p95']:.3f} s | {x['new']['p95']:.3f} s |")
lines+=['','### Materialização disponível antes da dependência externa','']
x=report['cohorts']['external_before_ready_materialized'];v=x['new_success_times'];lines.append(f"Dos 89 casos em que o fluxo antigo parava na dependência externa, apesar de uma opção materializada disponível, {x['new_success']} entregaram rota no novo fluxo. Mediana {v['median']:.3f} s, P95 {v['p95']:.3f} s, máximo {v['max']:.3f} s.")
lines+=['',f"Falhas internas de fontes: {report['new_source_failures']}. Saturações: {report['new_source_saturation']}. Primeiras rotas entregues apesar de tentativa externa concorrente: {report['new_first_with_parallel_external_attempt']}.",'',
'### Evidências','', '- [Comparação completa em JSON](../artifacts/benchmarks/async-comparison-20261101/comparison.json).','- [Resultados pareados em CSV](../artifacts/benchmarks/async-comparison-20261101/paired-results.csv).','- [Medições individuais](../artifacts/benchmarks/async-comparison-20261101/latency-results.jsonl).','',
'Os grupos são deliberadamente heterogêneos e incluem muitos pares problemáticos. Não se estima uma taxa de sucesso municipal. A medição usa 32 processos simultâneos e exclui a latência do roteador externo, HTTP e celular. A remoção de uma espera sequencial não implica que toda primeira rota deva ficar abaixo de um segundo.']
p=ROOT/'docs/async-performance-comparison.md';text=p.read_text().split('\n## Resultados')[0];p.write_text(text+'\n'+'\n'.join(lines)+'\n')
print(json.dumps(report,indent=2))
