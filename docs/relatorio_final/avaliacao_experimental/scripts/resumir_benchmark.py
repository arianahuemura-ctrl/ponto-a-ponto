"""Agrega CSVs explícitos; não importa nem executa planejadores."""
import argparse,csv,json
from pathlib import Path
from analisar import describe,number,write_csv
STATUS={'concluido','timeout','falha_tecnica','artefato_incompativel','fixture_ausente'}
METRICS=['primeira_alternativa_s','termino_s','validas','cpu_s','rss_pico_kib']
def summarize(rows):
    groups={};seen=set()
    for r in rows:
        if not any(r.values()):continue
        if r['execucao_id'] in seen:raise ValueError('Execução duplicada')
        seen.add(r['execucao_id'])
        if r['variante'] not in ('A','B','C') or r['status'] not in STATUS or r['cache'] not in ('frio','quente'):raise ValueError('Categoria inválida')
        if r.get('fallback') not in ('sim','nao',''):raise ValueError('Fallback inválido')
        if r['variante']!='C' and r.get('fallback')=='sim':raise ValueError('Fallback fora de C')
        for f in METRICS:number(r.get(f))
        if r['status']=='concluido' and (number(r.get('validas')) is None or number(r.get('termino_s')) is None):raise ValueError('Conclusão exige contagem e término')
        groups.setdefault((r['cenario_id'],r['variante'],r['cache']),[]).append(r)
    out=[]
    for (scenario,variant,cache),data in sorted(groups.items()):
        ok=[r for r in data if r['status']=='concluido']
        fallback=[r for r in ok if r.get('fallback') in ('sim','nao')]
        base=dict(cenario_id=scenario,variante=variant,cache=cache,n_tentativas=len(data),n_concluidas=len(ok),n_timeouts=sum(r['status']=='timeout' for r in data),n_com_alternativa=sum(number(r['validas'])>0 for r in ok),fallback_observado=sum(r['fallback']=='sim' for r in fallback) if variant=='C' else None,fallback_denominador=len(fallback) if variant=='C' else None)
        for f in METRICS:
            values=[number(r.get(f)) for r in ok if number(r.get(f)) is not None]
            out.append({**base,'metrica':f,**describe(values)})
    return out

def plot(rows,out,artificial=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for cache in ('frio','quente'):
        for metric in ('primeira_alternativa_s','termino_s','validas','cpu_s','rss_pico_kib'):
            data=[r for r in rows if r['cache']==cache and r['metrica']==metric and r['mediana'] is not None]
            if not data:continue
            fig,ax=plt.subplots(figsize=(9,4));labels=[r['cenario_id']+' / '+r['variante'] for r in data]
            ax.plot(range(len(data)),[r['mediana'] for r in data],'o');ax.set_xticks(range(len(data)),labels,rotation=60,ha='right')
            ax.set_ylabel(metric);ax.set_title(('ARTIFICIAL — TESTE\n' if artificial else '')+'Medianas por cenário — cache '+cache)
            fig.tight_layout();fig.savefig(out/(cache+'_'+metric+'.svg'));plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('csv',type=Path);p.add_argument('saida',type=Path);p.add_argument('--manifesto',required=True,type=Path);p.add_argument('--graficos',action='store_true');a=p.parse_args()
    manifest=json.loads(a.manifesto.read_text());nature=manifest.get('natureza')
    if nature not in ('real','artificial','piloto'):p.error('Natureza ausente')
    if nature!='artificial' and not manifest.get('autorizacao_ref'):p.error('Autorização ausente')
    if nature=='artificial' and (not str(a.saida.resolve()).startswith('/tmp/') or 'ARTIFICIAL' not in str(a.saida)):p.error('Artificial exige saída /tmp/ARTIFICIAL...')
    with a.csv.open(newline='') as f:rows=summarize(list(csv.DictReader(f)))
    a.saida.mkdir(parents=True,exist_ok=False)
    fields=list(rows[0]) if rows else ['cenario_id','variante','cache','metrica','n','mediana']
    write_csv(a.saida/'benchmark_resumos.csv',fields,rows)
    import hashlib
    (a.saida/'proveniencia.json').write_text(json.dumps({'natureza':nature,'entrada_sha256':hashlib.sha256(a.csv.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'quartis':'tipo7','sem_inferencia_municipal':True},indent=2))
    if a.graficos:plot(rows,a.saida,nature=='artificial')
