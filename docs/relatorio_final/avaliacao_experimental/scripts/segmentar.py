"""Segmentação inicial de eventos já minimizados; nunca lê formato bruto/SQLite."""
import argparse,json,re
from pathlib import Path
ALLOWED={'session_alias','epoch','seq','elapsed_ms','kind','origin_alias','destination_alias','association','has_alternatives','complete'}
KINDS={'session_start','context','planning_explicit','api_result','selection_explicit','details_observed','cancel_intent','cancel_confirmed','feedback_saved','error'}
def segment(events,gap_s=120):
    if gap_s<=0:raise ValueError('Limiar deve ser positivo')
    groups={}
    for e in events:
        if set(e)-ALLOWED or e.get('kind') not in KINDS:raise ValueError('Formato bruto/não autorizado ou campo desconhecido')
        if not re.fullmatch(r'S\d{3,}',e.get('session_alias','')):raise ValueError('Usar alias de sessão, não UUID')
        if not isinstance(e.get('epoch'),int) or not isinstance(e.get('seq'),int) or not isinstance(e.get('elapsed_ms'),(int,float)) or not 0<=e['elapsed_ms']<86400000:raise ValueError('Relógio/seq inválido')
        for f in ['origin_alias','destination_alias']:
            if e.get(f) is not None and not re.fullmatch(r'L\d+',str(e[f])):raise ValueError('Local deve ser alias, nunca coordenada/texto')
        groups.setdefault((e['session_alias'],e['epoch']),[]).append(e)
    result=[]
    for (sid,epoch),rows in sorted(groups.items()):
        rows.sort(key=lambda e:e['seq']);current=None;previous=None;context=(None,None);seen={}
        def close(reason):
            nonlocal current
            if current:
                current['encerramento']=reason;result.append(current);current=None
        def start(e,truncated=False):
            return {'session_alias':sid,'epoch':epoch,'inicio_fonte':e['kind'],'inicio_ms':e['elapsed_ms'],'fim_ms':e['elapsed_ms'],'eventos':0,'inicio_truncado':truncated,'ressalvas':[],'alternativa_resposta_ms':None,'selecao_explicita_ms':None,'detalhes_ms':None,'erros_tecnicos':0,'dificuldade':'nao_inferida'}
        for e in rows:
            if e['seq'] in seen:
                if seen[e['seq']]!=e and current:current['ressalvas'].append('seq_conflitante')
                continue
            seen[e['seq']]=e
            if previous:
                if e['elapsed_ms']<previous['elapsed_ms']:
                    if current:current['ressalvas'].append('relogio_reiniciado_sem_epoch')
                    close('relogio_reiniciado');context=(None,None)
                elif e['elapsed_ms']-previous['elapsed_ms']>gap_s*1000:close('lacuna_inatividade_nao_abandono')
                if e['seq']>previous['seq']+1 and current:current['ressalvas'].append('lacuna_seq')
            kind=e['kind'];pair=(e.get('origin_alias'),e.get('destination_alias'))
            if kind=='context':
                if pair!=context:close('reconfiguracao_nao_erro');context=pair
                if all(pair) and not current:current=start(e)
            elif kind=='planning_explicit':
                if current and current['inicio_fonte']=='context' and current['eventos']==1:
                    current['inicio_fonte']='planning_explicit'
                else:
                    close('nova_consulta_explicita');current=start(e)
            elif kind=='api_result' and not current:current=start(e,True)
            if current:
                current['eventos']+=1;current['fim_ms']=e['elapsed_ms']
                if kind=='api_result':
                    if e.get('association')!='confirmed':current['ressalvas'].append('resposta_sem_associacao_segura')
                    elif e.get('has_alternatives') and current['alternativa_resposta_ms'] is None:current['alternativa_resposta_ms']=e['elapsed_ms']
                if kind=='selection_explicit':current['selecao_explicita_ms']=e['elapsed_ms']
                if kind=='details_observed':current['detalhes_ms']=e['elapsed_ms']
                if kind=='error':current['erros_tecnicos']+=1
                if kind=='cancel_confirmed':close('cancelamento_confirmado')
            previous=e
        close('fim_observacao_nao_abandono')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('jsonl',type=Path);p.add_argument('saida',type=Path);p.add_argument('--autorizacao',required=True);p.add_argument('--gap-s',type=float,default=120);a=p.parse_args()
    rows=[json.loads(l) for l in a.jsonl.read_text().splitlines() if l.strip()];out=segment(rows,a.gap_s)
    with a.saida.open('x') as f:json.dump({'acesso':'restrito_nao_publicar','sessões_nao_sao_pessoas':True,'tentativas':out},f,ensure_ascii=False,indent=2)
