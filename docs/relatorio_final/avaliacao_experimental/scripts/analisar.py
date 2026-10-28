"""Análise descritiva de ficha manual; não lê telemetria nem bancos."""
import argparse,csv,json,hashlib,math,statistics
from pathlib import Path
FIELDS=['toques','longos','rolagens','arrastos']
STATUS={'sucesso_sem_ajuda','sucesso_assistido','falha','limite_tempo','interrupcao_tecnica','retirada'}
def number(v):
    if v is None or v=='':return None
    n=float(v)
    if not math.isfinite(n) or n<0:raise ValueError('Valor não finito/negativo')
    return n

def quartile(v,p):
    v=sorted(v);i=(len(v)-1)*p;a=int(i);b=min(a+1,len(v)-1)
    return v[a]+(v[b]-v[a])*(i-a)

def describe(v):
    if not v:return {'n':0,'mediana':None,'minimo':None,'maximo':None,'q1':None,'q3':None,'iqr':None}
    q1=quartile(v,.25) if len(v)>1 else None;q3=quartile(v,.75) if len(v)>1 else None
    return dict(n=len(v),mediana=statistics.median(v),minimo=min(v),maximo=max(v),q1=q1,q3=q3,iqr=q3-q1 if q1 is not None else None)

def metrics(r):
    vals={f:number(r.get(f)) for f in FIELDS};actions=sum(vals.values()) if all(v is not None for v in vals.values()) else None
    for v in vals.values():
        if v is not None and not v.is_integer():raise ValueError('Ações devem ser inteiras')
    seq=number(r.get('SEQ_1_7'))
    if seq is not None and (seq!=int(seq) or not 1<=seq<=7):raise ValueError('SEQ fora de 1–7')
    t={f:number(r.get(f)) for f in ['t0','to','td','ta','tc','ts','tf']}
    if any(v is not None and t['t0'] is not None and v<t['t0'] for v in t.values()):raise ValueError('Marco anterior a t0')
    if t['ts'] is not None and t['ta'] is not None and t['ts']<t['ta']:raise ValueError('Seleção anterior à alternativa observada')
    if t['tf'] is not None and t['ts'] is not None and t['tf']<t['ts']:raise ValueError('Detalhes anteriores à seleção')
    result={'acoes':actions,'SEQ':seq}
    for f in ['to','td','ta','tc','tf']:
        result[f+'_s']=t[f]-t['t0'] if t[f] is not None and t['t0'] is not None else None
    result['escolha_s']=t['ts']-t['ta'] if t['ts'] is not None and t['ta'] is not None else None
    return result

def analyze(rows):
    groups={};eff={};excluded=[]
    for r in rows:
        if not any(r.values()):continue
        if r.get('condicao') not in ('MAN','QR') or r.get('conclusao') not in STATUS:raise ValueError('Condição/conclusão inválida')
        key=(r.get('participante_pseudonimo'),r.get('cenario_id'),r.get('tarefa'),r.get('escopo'))
        if not all(key):raise ValueError('Identificação/tarefa/cenário ausente')
        metrics(r)
        eff[(r['condicao'],r['conclusao'])]=eff.get((r['condicao'],r['conclusao']),0)+1
        group=groups.setdefault(key,{})
        if r['condicao'] in group:raise ValueError('Mais de uma tentativa na mesma condição; adjudique sem selecionar a melhor')
        group[r['condicao']]=r
    pairs=[]
    compare=['experimento_id','gabarito_revisao','versao_build','dispositivo','dataset_hash','partida_fixa','ordem']
    for key,g in groups.items():
        reason=None
        if set(g)!={'MAN','QR'}:reason='par_incompleto'
        elif any(g[c].get('comparavel')!='sim' for c in g):reason='comparabilidade_nao_confirmada'
        elif any(g[c]['conclusao']!='sucesso_sem_ajuda' for c in g):reason='par_fora_eficiencia_sem_ajuda'
        elif any(not g['MAN'].get(f) or g['MAN'].get(f)!=g['QR'].get(f) for f in compare):reason='contexto_diferente_ou_ausente'
        elif g['MAN'].get('ordem') not in ('MAN_QR','QR_MAN'):reason='ordem_invalida'
        else:
            expected={'MAN':'1','QR':'2'} if g['MAN']['ordem']=='MAN_QR' else {'QR':'1','MAN':'2'}
            if any(str(g[c].get('periodo'))!=expected[c] for c in g):reason='periodo_incompativel'
        if reason:excluded.append({'participante':key[0],'cenario':key[1],'motivo':reason});continue
        m,q=metrics(g['MAN']),metrics(g['QR'])
        for metric in m:
            if m[metric] is None or q[metric] is None:continue
            pairs.append(dict(participante_pseudonimo=key[0],cenario_id=key[1],ordem=g['MAN']['ordem'],metrica=metric,MAN=m[metric],QR=q[metric],diferenca_QR_MAN=q[metric]-m[metric]))
    summaries=[]
    for metric in sorted({p['metrica'] for p in pairs}):
        for order in ['todas','MAN_QR','QR_MAN']:
            vals=[p['diferenca_QR_MAN'] for p in pairs if p['metrica']==metric and (order=='todas' or p['ordem']==order)]
            summaries.append(dict(metrica=metric,ordem=order,**describe(vals)))
    efficacy=[dict(condicao=c,conclusao=s,n_tentativas=n,denominador=sum(v for (cc,ss),v in eff.items() if cc==c)) for (c,s),n in sorted(eff.items())]
    return pairs,summaries,efficacy,excluded

def write_csv(p,fields,rows):
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)

def plots(pairs,out,artificial=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for metric in ['acoes','tf_s','SEQ']:
        data=[p for p in pairs if p['metrica']==metric]
        if not data:continue
        fig,ax=plt.subplots(figsize=(6,4))
        for r in data:ax.plot([0,1],[r['MAN'],r['QR']],marker='o',alpha=.65)
        ax.set_xticks([0,1],['MAN','QR']);ax.set_ylabel(metric);ax.set_title(('ARTIFICIAL — TESTE\n' if artificial else '')+f'{metric}: {len(data)} pares válidos')
        fig.tight_layout();fig.savefig(out/(metric+'.svg'));plt.close(fig)

def distributions(rows):
    comprehension=[];seq=[]
    for condition in ('MAN','QR'):
        data=[r for r in rows if r.get('condicao')==condition]
        for item in ('linha','sentido','embarque','baldeacao'):
            vals=[r.get('compreensao_'+item,'') for r in data]
            if any(v not in ('','correto','parcial','incorreto','nao_aplicavel') for v in vals):raise ValueError('Classificação de compreensão inválida')
            for value in ('correto','parcial','incorreto','nao_aplicavel'):
                comprehension.append(dict(condicao=condition,item=item,classificacao=value,n=vals.count(value),denominador_aplicavel=sum(v in ('correto','parcial','incorreto') for v in vals),ausentes=vals.count('')))
        vals=[number(r.get('SEQ_1_7')) for r in data]
        for value in range(1,8):seq.append(dict(condicao=condition,SEQ_1_7=value,n=vals.count(value),denominador=sum(v is not None for v in vals),ausentes=vals.count(None)))
    return comprehension,seq

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('csv',type=Path);p.add_argument('saida',type=Path);p.add_argument('--manifesto',type=Path,required=True);p.add_argument('--graficos',action='store_true');a=p.parse_args()
    manifest=json.loads(a.manifesto.read_text());nature=manifest.get('natureza')
    if nature not in ('real','artificial'):p.error('Natureza explícita real/artific ial necessária'.replace('artific ial','artificial'))
    if nature=='real' and not manifest.get('autorizacao_ref'):p.error('Autorização de análise ausente')
    if nature=='artificial' and (not str(a.saida.resolve()).startswith('/tmp/') or 'ARTIFICIAL' not in str(a.saida)):p.error('Teste artificial exige /tmp/ARTIFICIAL...')
    with a.csv.open(newline='') as f:input_rows=list(csv.DictReader(f))
    result=analyze(input_rows);comprehension,seq=distributions(input_rows)
    a.saida.mkdir(parents=True,exist_ok=False)
    names=['pares','resumos','eficacia','exclusoes'];default=[['participante_pseudonimo','cenario_id','ordem','metrica','MAN','QR','diferenca_QR_MAN'],['metrica','ordem','n','mediana','minimo','maximo','q1','q3','iqr'],['condicao','conclusao','n_tentativas','denominador'],['participante','cenario','motivo']]
    for name,rows,fields in zip(names,result,default):write_csv(a.saida/(name+'.csv'),fields,rows)
    (a.saida/'proveniencia.json').write_text(json.dumps({'natureza':nature,'entrada_sha256':hashlib.sha256(a.csv.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'quartis':'tipo7','sem_inferencia_populacional':True},indent=2))
    write_csv(a.saida/'compreensao.csv',['condicao','item','classificacao','n','denominador_aplicavel','ausentes'],comprehension)
    write_csv(a.saida/'seq_distribuicao.csv',['condicao','SEQ_1_7','n','denominador','ausentes'],seq)
    if a.graficos:plots(result[0],a.saida,nature=='artificial')
