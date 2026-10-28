# Preparação da avaliação experimental — PaP
Revisão dos instrumentos: EXP-1, 28/10/2026. Estado: **preparação; nenhuma coleta ou benchmark executado**.
Referência: relatório de 133 páginas, MD5 `cc9f063ec8ae7b225bdf0463d764cd19` (versão 9).
Os protocolos aprovados E.4/B.3 e o Capítulo 3 permanecem intactos. São Paulo é o cenário funcional; os resultados futuros não validarão a operação em Mauá.

## Como usar
1. Leia `matriz_avaliacoes.csv`, `dependencias.csv` e `privacidade.md`. A matriz usa documentos acadêmicos já produzidos, código e metadados dos arquivos; nenhum banco ou exportação de usuário foi aberto.
2. Qualifique os cenários públicos e congele versão, dados e respostas. Preencha `formularios/cenarios_ihc.csv` e `formularios/gabarito.csv`; são campos deliberadamente vazios até validação, não resultados negativos.
3. Use `qr_man.md` e a ficha canônica existente em `../estudo_ihc_ampliado/ficha_coleta_vazia.csv`, atualizada sem preencher participantes. Os demais CSVs completam observações, cronologia e problemas. `formularios/instrumentos.xlsx` reúne os mesmos modelos para edição; CSV e XLSX são alternativas de preenchimento, nunca fontes divergentes a combinar.
4. Faça um piloto técnico sem participantes, em ambiente isolado, para validar QR, respostas congeladas e instrumentos. Esse piloto ainda não foi feito. Só depois libere a coleta mediante os critérios de prontidão abaixo.
5. Crie um manifesto a partir de `manifesto_modelo.json`, inventarie os arquivos com `scripts/manifesto.py` e execute `scripts/prontidao.py`. Ausências bloqueiam a liberação; não são substituídas por valores presumidos.
6. Faça análises apenas após autorização, usando `analise.md`. Scripts recebem arquivos explícitos e não procuram automaticamente dados privados. Exemplos artificiais ficam exclusivamente em `testes/` e saídas em `/tmp`; `modelos_resultados/` contém apenas cabeçalhos.

## Instrumentos reaproveitados
E.4, E.1–E.3, matriz de comparabilidade, inventário de sessões e auditorias antigas não foram recriados nem reexecutados. O script antigo `estudo_ihc_ampliado/auditar.py` lê eventos/capturas: **não foi executado** nesta tarefa. A nova matriz referencia essas fontes e mantém suas ressalvas.

## Critérios de liberação
- Responsável e contato de pesquisa definidos, consentimento manual e escolhas opcionais documentados, retenção e exclusão operacionalizadas.
- Cenário, gabarito múltiplo, revisão dos dados, data de serviço, dispositivo, cache e resposta congelada validados; QR decodificado e aberto no ponto correto pelo celular.
- Piloto documentado; instrumentos e hashes fixados antes de observar resultados.
- Para benchmark: isolamento, bloqueio de rede, procedência de candidatos e fixtures completas verificados. Para telemetria real: autorização expressa específica antes de abrir dados.

A preparação documental e os scripts de apoio estão entregues. As autorizações, a qualificação dos cenários/gabaritos e o piloto constituem condições reais para iniciar, não experimentos concluídos. Não alterar o PDF para antecipar resultados.
