"""Resumo minimizado de segmentação já autorizada; não lê eventos originais."""
import argparse,json
from collections import Counter
from pathlib import Path

def aggregate(attempts,k=3):
    if k<3:raise ValueError('Limiar mínimo 3')
    n=len(attempts);sessions={r['session_alias'] for r in attempts}
    if len(sessions)<k:return {'tentativas':'suprimido','nota':'Menos de 3 sessões contribuintes; sessões não representam pessoas.'}
    causes=Counter(r['encerramento'] for r in attempts)
    sensitive=any(len({r['session_alias'] for r in attempts if r['encerramento']==c})<k for c in causes)
    def protected(predicate):
        yes={r['session_alias'] for r in attempts if predicate(r)}
        no={r['session_alias'] for r in attempts if not predicate(r)}
        return 'suprimido' if (0<len(yes)<k or 0<len(no)<k) else sum(bool(predicate(r)) for r in attempts)
    return {'tentativas':n,'encerramentos':'distribuicao_suprimida_celulas_pequenas' if sensitive else dict(causes),'tentativas_com_erros_tecnicos':protected(lambda r:r['erros_tecnicos']>0),'tentativas_com_selecao_explicita':protected(lambda r:r['selecao_explicita_ms'] is not None),'tentativas_com_ressalvas':protected(lambda r:bool(r['ressalvas'])),'nota':'Unidade=tentativa; limiar por sessões contribuintes; sem inferência de abandono/dificuldade; não conta participantes únicos. Revisar risco de combinação com outras divulgações.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('segmentacao',type=Path);p.add_argument('saida',type=Path);p.add_argument('--autorizacao',required=True);a=p.parse_args()
    result=aggregate(json.loads(a.segmentacao.read_text())['tentativas'])
    with a.saida.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
