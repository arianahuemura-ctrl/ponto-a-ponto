"""Validate the exhaustive census and samples, then write the Portuguese report."""
import json,hashlib,statistics
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/benchmarks/coverage-audit-20261101'
def read(name):return json.loads((OUT/name).read_text())
census=read('census-summary.json');audit=read('endpoint-audit.json');summary=read('latency-summary.json')
rows=[json.loads(l) for l in (OUT/'latency-results.jsonl').read_text().splitlines()]
assert len(rows)==len({(r['origin'],r['destination'],r['hour'],r['group']) for r in rows})==summary['queries']
assert census['covered_pairs']+census['missing_pairs']==census['stops']*(census['stops']-1)
assert all(r['origin']!=r['destination'] for r in rows)
assert all(r['flow']['state']!='error' and r['prepared']['state']!='error' for r in rows)
for point in audit['points']:
 for hour in [8,14,2]:
  role=point['blocked_role'];group='blocked_'+role
  assert any(r['group']==group and r[role]==point['stop']['id'] and r['hour']==hour for r in rows),(point,hour)
for group in summary['groups']:
 assert group['n'] in [32,128]
 assert len(group['batches']) in [1,4]
 assert all(b['n']==32 for b in group['batches'])
first=[r for r in rows if r['flow']['state']=='first_route'];unknown=[r for r in rows if r['flow']['state']=='external_required'];empty=[r for r in rows if r['flow']['state']=='no_route_completed'];limited=[r for r in empty if r['flow'].get('search_limited')]
assert all(0<=r['flow']['first_route_seconds']<=30 for r in first)
ready=[r for r in unknown if r['prepared']['state']=='first_route']
def quantile(v,q):return sorted(v)[round((len(v)-1)*q)] if v else None
def fmt(n):return f'{n:,}'.replace(',','.')
labels={'blocked_origin':'Origem com acesso bloqueado','blocked_destination':'Destino com acesso bloqueado','endpoint_near':'Ponto sinalizado ↔ ponto próximo','short_walk':'Caminhada materializada','missing_connected_endpoints':'Par vazio com embarque/desembarque','bus_direct':'Ônibus direto','bus_one_transfer':'Ônibus: uma baldeação','bus_multiple_transfers':'Ônibus: múltiplas baldeações','near_materialized':'Par próximo com materialização','rail_or_mixed':'Ferroviário ou misto'}
state={'first_route':'rota','external_required':'externo não medido','no_route_completed':'sem rota','timeout_30s':'limite 30 s','error':'erro'}
validation={'unique_queries':len(rows),'all_59_endpoints_tested_in_all_three_hours':True,'all_batches_have_32_queries':True,'groups_with_four_batches':sum(g['n']==128 for g in summary['groups']),'groups_with_one_batch':sum(g['n']==32 for g in summary['groups']),'successful_first_routes':len(first),'first_route_max_seconds':max(r['flow']['first_route_seconds'] for r in first),'all_successful_first_routes_within_30s':True,'external_required':len(unknown),'no_route_completed':len(empty),'search_limited_without_route':len(limited),'external_before_prepared_available':len(ready),'workers_per_run':32,'timeout_count':sum(r['flow']['state']=='timeout_30s' for r in rows),'scope':'No HTTP/browser or public pedestrian service latency; not a representative success-rate estimate for all pairs.'}
for name in ['sptrans.sqlite3','sptrans.staged.sqlite3','sptrans.staged-walks.sqlite3']:
 p=ROOT/name;st=p.stat();validation[name]={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
lines=['# Cobertura e tempo até a primeira rota — levantamento de 01/11/2026','',
'Censo exaustivo dos pares distintos e amostragem adaptativa do fluxo local de consulta. Foram usados 32 processos simultâneos. Os cenários representam 03/11/2026, terça-feira, em America/Sao_Paulo: 08:00, 14:00 e 02:00. Não se alterou o aplicativo nem as materializações.','',
'## Censo completo','',
f"Dos {fmt(census['directed_pairs'])} pares direcionais, **{fmt(census['covered_pairs'])} têm materialização (99,6659%)** e **{fmt(census['missing_pairs'])} não têm**. O censo varreu {fmt(census['rows_scanned'])} registros das quatro tabelas em {census['wall_seconds']:.2f} s. Esse tempo é de processamento em lote, não de resposta a um passageiro.",'',
'| Rotas por par | Pares |','|---:|---:|']
for i,n in enumerate(census['histogram_routes_per_pair']):lines.append(f'| {i} | {fmt(n)} |')
lines+=['','## Auditoria de acesso','',
'Foram examinados individualmente os 50 pontos sem saída e os nove sem chegada. Todos os 50 primeiros aparecem somente na última posição das viagens em que constam. Todos possuem caminhada externa verificada até um ponto com embarque: a menor opção por ponto varia de 9,54 a 493,61 m. A política de materialização admite apenas integração interna antes do primeiro embarque, bloqueando esses acessos externos. Não é uma proibição oficial de embarque.','',
'Os nove destinos aparecem somente na primeira posição das viagens. Oito tiveram todas as conexões pedestres rejeitadas pelo limite de encaixe de 20 m; os encaixes desses pontos vão de 21,65 a 40,45 m. O nono, parada 8313677, tem caminhada mínima calculada de 1.104,64 m, superior ao limite materializado de 1.000 m. Há diferença entre esse limite e o de revisão final do aplicativo (1.500 m), assim como entre os limites de encaixe local (20 m) e público (30 m). Não foi testado aqui se o mapa público oferece o mesmo percurso.','',
'[Tabela individual dos 59 pontos](endpoint-audit-20261101.md). A classificação por acesso explica 1.313.444 pares ainda vazios; os outros 344.210 não foram declarados inacessíveis.','',
'## Primeira rota e limite de 30 segundos','',
f"Foram executadas **{fmt(len(rows))} consultas amostrais** em {summary['wall_seconds_total']:.1f} s de execução dos dois ciclos sequenciais. Houve {len(first)} primeiras rotas, {len(unknown)} interrupções ao necessitar de serviço externo não medido e {len(empty)} buscas terminadas sem rota. Das buscas sem rota, {len(limited)} atingiram limites internos de pesquisa; portanto continuam inconclusivas. Não houve erro de execução nem interrupção pelo teto experimental de 30 s.",'',
'Os tempos abaixo incluem somente os casos que entregaram uma rota. A amostra deliberadamente concentra pontos problemáticos e pares vazios: sua taxa de sucesso não representa a taxa de sucesso dos 496 milhões de pares.','',
'| Cenário | Consultas | Com primeira rota | Mediana | P95 | Máximo |','|---|---:|---:|---:|---:|---:|']
for hour,name in [(8,'Pico — 08:00'),(14,'Entrepico — 14:00'),(2,'Madrugada — 02:00')]:
 rs=[r for r in rows if r['hour']==hour];times=[r['flow']['first_route_seconds'] for r in rs if r['flow']['state']=='first_route']
 lines.append(f'| {name} | {len(rs)} | {len(times)} | {quantile(times,.5):.3f} s | {quantile(times,.95):.3f} s | {max(times):.3f} s |')
lines+=['',f"Todas as {len(first)} primeiras rotas medidas chegaram antes de 30 s. Isso **não comprova o limite de ponta a ponta**: HTTP, túnel, renderização e roteador pedestre público foram excluídos. Ao precisar de rede externa, o teste parou e registrou `external_required`, sem substituir a caminhada por linha reta nem considerar a interrupção como resposta útil.",'',
f"Em **{len(ready)} consultas**, o fluxo exigiu uma chamada externa antes de entregar rota, enquanto o leitor materializado isolado entregou uma opção. A mediana desse leitor foi {statistics.median(r['prepared']['first_route_seconds'] for r in ready):.3f} s e o máximo {max(r['prepared']['first_route_seconds'] for r in ready):.3f} s. A comparação isolada ocorre depois da consulta principal e pode aproveitar cache de geometria; ela identifica a dependência desnecessária, mas não estima exatamente a economia no celular.",'',
'## Regra adaptativa e quatro lotes','',
'Cada lote tem 32 consultas distintas, executadas com 32 processos. Estabilidade: um único estado de saída e P90−P10 ≤ máximo de 50 ms e 20% da mediana. Grupos estáveis encerram após o lote; os demais chegaram a quatro lotes (128 consultas por grupo/horário). O quarto lote foi acrescentado em um segundo ciclo de processos, reaproveitando todos os resultados anteriores. O cache de respostas é esvaziado por consulta; GTFS permanece carregado e o cache de geometria varia naturalmente por processo.','',
'Os três grupos/horários de caminhada materializada foram estáveis com primeira rota. Os três de pares próximos foram estáveis apenas quanto à interrupção para serviço externo: **seu tempo até a primeira rota continua desconhecido**. Os 24 demais grupos/horários continuaram heterogêneos após quatro lotes; não foram tratados como tendo tempo constante.','',
'| Grupo | Hora | Consultas | Rotas entregues | Dependência externa | Sem rota | Lotes |','|---|---:|---:|---:|---:|---:|---:|']
for g in summary['groups']:
 st=g['states'];lines.append(f"| {labels[g['group']]} | {g['hour']:02d}:00 | {g['n']} | {st.get('first_route',0)} | {st.get('external_required',0)} | {st.get('no_route_completed',0)} | {len(g['batches'])} |")
attribution=OUT/'source-attribution.json'
if attribution.exists():
 ar=json.loads(attribution.read_text());counts=Counter(','.join(r.get('sources',[])) if r['state']=='first_route' else r['state'] for r in ar)
 lines+=['','## Origem das respostas adicionais','',
 f"Uma repetição diagnóstica de {len(ar)} consultas que haviam tido sucesso no fluxo completo, mas não no leitor materializado isolado, identificou as seguintes fontes. Não é um quinto lote de desempenho, e seus tempos não entram nas estatísticas acima.",'', '| Fonte da primeira rota | Casos |','|---|---:|']
 for k,v in sorted(counts.items()):lines.append(f'| {k} | {v} |')
 confirmed=[r for r in ar if r['state']=='first_route' and 'raptor' in r.get('sources',[])]
 lines+=['',f"O RAPTOR foi confirmado em {len(confirmed)} consultas de {len({(r['origin'],r['destination']) for r in confirmed})} pares distintos da amostra. As outras {len(ar)-len(confirmed)} respostas não se reproduziram nesse replay: 27 pararam em dependência externa e cinco terminaram sem rota. A busca tem limites de tempo internos e o estado de cache/carga varia; não atribuímos essas 32 respostas originais a nenhum mecanismo.",'', 'Esse resultado impede concluir que o fallback se tornou dispensável apenas pela cobertura estrutural. A prioridade é entregar materializações válidas primeiro e usar busca complementar quando as sequências salvas não atendem ao horário. Não há estimativa global de quantos pares precisam do RAPTOR a partir desta amostra dirigida.','', 'O fluxo multimodal também consulta o índice antigo de conexões. Uma resposta fora do leitor novo não pode ser atribuída automaticamente ao RAPTOR.']
lines+=['','## Evidências e limites','',
'- [Contrato e método](coverage-audit-contract.md).',
'- [Censo completo](../artifacts/benchmarks/coverage-audit-20261101/census-summary.json); os 32 arquivos `census-*.jsonl` registram as 22.274 origens.',
'- [Resultados das consultas](../artifacts/benchmarks/coverage-audit-20261101/latency-results.jsonl) e [resumo por grupo](../artifacts/benchmarks/coverage-audit-20261101/latency-summary.json).',
'- [Validação cruzada](../artifacts/benchmarks/coverage-audit-20261101/validation.json).',
'- Fontes e método não avaliam incidentes, trânsito real, lotação ou alterações posteriores ao cadastro local. Uma sequência materializada não garante serviço naquele horário. Nenhum teste de carga foi feito contra o roteador público.',
'',
'O próximo ajuste fundamentado por este levantamento é servir uma rota materializada válida antes de aguardar caminhada externa e revisar as regras de acesso dos 59 pontos. A utilidade de cada fallback deve ser avaliada pela fonte real das respostas, preservando a distinção entre cobertura estrutural e disponibilidade no horário.']
(ROOT/'docs/coverage-audit-20261101.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(validation,indent=2))
