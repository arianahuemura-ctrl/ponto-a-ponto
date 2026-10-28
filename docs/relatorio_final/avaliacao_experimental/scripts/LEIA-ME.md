# Execução das ferramentas — somente preparação
Python 3.10+; biblioteca padrão para testes/CSV/manifestos. matplotlib é opcional para SVGs. openpyxl foi usado apenas para preparar a planilha, não é necessário para analisar CSV. Não instalar nada no aplicativo.

Verificação segura, sem dados reais, bancos ou rede:
```
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s testes -v
python3 scripts/prontidao.py manifesto_modelo.json
```
O segundo comando deve retornar 1: modelo vazio não está autorizado/pronto.

Depois de coleta/autorização e qualificação, com caminhos explícitos e uma pasta de saída nova:
```
python3 scripts/analisar.py FICHA.csv SAIDA_NOVA --manifesto MANIFESTO.json --graficos
python3 scripts/resumir_benchmark.py EXECUCOES.csv SAIDA_NOVA --manifesto MANIFESTO.json --graficos
python3 scripts/segmentar.py NORMALIZADO.jsonl TENTATIVAS_RESTRITAS.json --autorizacao REFERENCIA
python3 scripts/agregar_telemetria.py TENTATIVAS_RESTRITAS.json AGREGADO.json --autorizacao REFERENCIA
python3 scripts/manifesto.py RAIZ INVENTARIO_NOVO.json bruto.csv manifesto.json
```
Os nomes em maiúsculas são placeholders, não caminhos existentes. `manifesto.py` sela um inventário de evidências, distinto do manifesto operacional. O inventário não inclui a si mesmo; o selo é .sha256. O script não valida a veracidade de autorização informada, não abre banco e não descobre dados por conta própria.

`instrumentacao_benchmark.py` é biblioteca de hooks e medição, **sem comando que execute consultas**. Ler benchmark.md; precisa de controlador isolado, supervisor de timeout, fixtures e piloto reais antes de ser usado. Os testes com objetos artificiais não equivalem à integração aprovada no aplicativo.

Não executar o antigo auditor de capturas para esta validação. Não colocar saídas artificiais no pacote acadêmico; usar /tmp/ARTIFICIAL-*. As funções não imputam números ausentes nem convertem falha técnica em ausência de rota.
