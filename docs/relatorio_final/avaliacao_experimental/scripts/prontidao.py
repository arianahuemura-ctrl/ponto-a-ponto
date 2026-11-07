"""Validação documental: não prova consentimento, cenário nem funcionamento."""
import json,argparse
from pathlib import Path

def missing(m):
    required=['experimento_id','tipo','protocolo','protocolo_sha256','instrumentos_sha256','responsavel_codigo','autorizacao_ref','data_exclusao_brutos','data_exclusao_derivados','cenario_id','gabarito_sha256','app_head','app_diff_sha256','configuracao_sha256','criterios_sucesso_ref']
    flags=['retencao_aprovada','cenario_validado','piloto_aprovado']
    if m.get('tipo')=='qr_man':required+=['consentimento_ref','gtfs_sha256','fixtures_sha256','dispositivo_categoria']
    elif m.get('tipo')=='telemetria':flags+=['autorizacao_dados_reais'];required+=['consentimento_ref']
    elif m.get('tipo')=='benchmark':required+=['gtfs_sha256','fixtures_sha256','bancos'];flags+=['isolamento_validado','rede_bloqueada','procedencia_validada']
    else:required+=['tipo_valido']
    return [k for k in required if not m.get(k)]+[k for k in flags if m.get(k) is not True]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifesto',type=Path);a=p.parse_args();m=json.loads(a.manifesto.read_text());l=missing(m)
    print(json.dumps({'liberacao_documental':not l,'pendencias':l,'nota':'Não comprova execução nem autorização verdadeira'},ensure_ascii=False,indent=2));raise SystemExit(bool(l))
