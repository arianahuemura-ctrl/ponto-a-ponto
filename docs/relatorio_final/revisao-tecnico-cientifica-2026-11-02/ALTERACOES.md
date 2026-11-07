# Revisão técnico-científica — alterações e evidências

Data: 2 de novembro de 2026. Branch `relatorio`, HEAD `e5077b9c12b89c099f900cad0911f7498dafb06d`. Revisão editorial sem commit; a referência de árvore anterior é `refs/auditoria/relatorio-20261102-original-tecnico-cientifica` (`fe1b7a141552c478d511eb19bba930ab4c4becc8`). Ela inclui o trabalho local preexistente. Não confundir o diff contra HEAD com as alterações desta revisão.

## Localização, motivo e evidência

As páginas abaixo são a numeração impressa; some cinco para localizar a página física no PDF.

| Localização final | Alteração e problema corrigido | Evidência e limite |
|---|---|---|
| Resumo; introdução, pp. 1–3; objetivos, p. 4 | Contribuição como fluxo integrado QR → navegador → destino → alternativas/transferências. Retiradas alegações de diferencial isolado e benefícios demonstrados. | Capturas existentes, código documentado e comparação dos serviços. A leitura física e a redução de esforço não foram demonstradas. |
| 2.3, p. 24; `comparacao.tex` | Síntese comparativa de seis entradas: QRCodeAdesivo, Olho Vivo, Cittamobi, Santos/Quanto Tempo Falta, Google Maps/Moovit e PaP. | Capturas e estudo de cliques preservados; distingue ausência no fluxo, não verificação e funcionalidade observada. Santos é evidência indireta. Sem novo ensaio de produtos. |
| 2.5, pp. 27–28; `metodologia.tex`; Apêndice A, pp. 80–92 | Dez procedimentos separados por método, evidência, execução e alcance. Histórico detalhado deslocado para apêndice. | Entrevista, documentos, auditorias, testes históricos, benchmark, parecer e navegações exploratórias. Protocolo com passageiros explicitamente futuro. |
| 3, pp. 29–30; 3.1, pp. 31–45 | Resultados atuais e fluxo visual separados das propostas e interlocuções históricas, agora no Apêndice C, pp. 94–102. | Sequências e procedências das capturas mantidas; telas de cenários independentes não viram sessão única. |
| 3.2, p. 46; `dados-e-desempenho.tex` | Comparação Mauá histórico/SPTrans/ARTESP e quatro níveis de cobertura; síntese dos pares descobertos. | Censo de 1/11 e auditoria de 2/11: 99,666% estrutural no universo anterior; 1.657.654 pares sem materialização, 1.313.444 explicados por regras e 344.210 sem causa esclarecida. Sem imputar erro cadastral. |
| 3.3, pp. 47–48; Figura 25 | Distribuições empíricas e diferenças individuais de 1.637 sucessos pareados; tabela dos 3.264 desfechos por versão. | `paired-results.csv`, sem reconstruir amostras nem repetir benchmark. Mediana piora; P95/máximo agregados melhoram; P95 das 02h piora. Não há conclusão causal. |
| 3.4, pp. 49–51 | Preservados 337 pontos, 16 linhas/variantes e 705/427/359 viagens distintas. Explicitação do limite da observação da primeira carga. | Auditoria ARTESP e doze consultas existentes; não mede população ou operação de campo. |
| 3.4.1, pp. 52–54; `mapa-e-captura.tex`; Figuras 26–28 | Mapa vetorial com a malha IBGE 2024 original e três estações destacadas. Inclusão da consulta ônibus 157 + CPTM Linha 10, com painel ampliado. | `stops.csv`, `summary.json`, `maua-ibge-2024.geojson`, imagens e `live-capture.json` da auditoria ARTESP. Consulta 02h19, 4h6min48s, chegada 06h26, busca parcial; não misturada à sessão 02h52 nem às consultas de 08h. |
| 3.5, pp. 55–63 | Conferida a coerência de consentimento, coleta, retenção, exclusão e exportações; limites existentes preservados e referenciados. | Leitura de `usability.py`, `usability_admin.py`, `research.py`, `researchChoice.js` e `visualRecording.js` no worktree da aplicação. Expurgo depende de coleta; exclusão de arquivos pode falhar; sem garantia de eliminação integral em 30 dias. |
| 3.6, pp. 64–65 | Capturas ferroviárias em figuras separadas, ampliadas, com versão/data explícitas. | Mesmas imagens históricas de 2/11, sem editar pixels. Não representam as correções posteriores do aplicativo/vídeo. |
| 3.7, pp. 66–67; `validade.tex` | Matriz IHC/decisão/evidência/limite e ameaças internas, externas, de construção, dados, reprodução e passageiros. | Princípios já citados e evidências existentes. Matriz não equivale a inspeção heurística independente. |
| Conclusão, pp. 68–69 | Resposta direta à pergunta, resultado parcial, expansão ARTESP, medidas técnicas e continuidade. | Mantida a ausência de demonstração empírica de redução do esforço dos passageiros. |
| Referências, pp. 70–75; glossário, pp. 76–79 | Ordenação alfabética das mesmas 54 referências; novos conceitos de cobertura, ARTESP, pareamento e estatística. | Comparação das entradas antes/depois: textos bibliográficos inalterados. |
| Apêndice B, p. 93; `protocolo-qr.tex` | Protocolo reproduzível de leitura física, separado da comprovação da eficácia. | Acervo contém URL, emulação e ilustração identificada como gerada; não comprova leitura física. |
| Apêndices D–H | Correção de referências fixas B/E após reorganização; atualização da pendência de captura; ajustes de espaços no diagrama GTFS e nas quebras, sem reduzir sua fonte. | Rótulos LaTeX conferidos. Conteúdo histórico de `benchmarks/2026-10-23/situacao.tex` permanece idêntico. |
| Apêndice G, pp. 144–147; Anexo A, pp. 157–163 | Procedência separa preparatórios, recebido, confirmado e autorização; novembro não atribuído ao parecer de outubro. | PDFs/DOCX originais e confirmado preservados por hash. O PDF confirmado de seis páginas é incluído como antes. Nenhuma assinatura reutilizada ou editada nesta revisão. |
| Figuras 1–2 e demais imagens/tabelas | Detalhe ampliado do QRCodeAdesivo, capturas de integração, fontes e cabeçalhos; correções de páginas residuais. | Recortes feitos apenas na diagramação; arquivos originais intactos. Não se inventam detalhes para aumentar resolução. |
| Capa | Mantidos link e aviso de versão provisória. | Falta confirmação externa do vídeo definitivo. |

## Comparação da extensão e organização

| Elemento | Referência de 2/11 | Revisão |
|---|---:|---:|
| Total do PDF | 155 páginas | 168 páginas |
| Corpo, da introdução ao fim da conclusão | 80 páginas | 69 páginas |
| Metodologia no corpo | 13 páginas | 2 páginas + 13 no Apêndice A |
| Figuras numeradas | 34 | 40 |
| Tabelas numeradas | 16 | 21 |
| Referências bibliográficas | 54 | 54 |
| Apêndices | 5 (A–E) | 8 (A–H) |
| Parecer reproduzido | 6 páginas | mesmas 6 páginas |

O crescimento líquido de 13 páginas preserva o histórico, acrescenta sínteses, mapa, gráficos e ampliações. O corpo ficou 11 páginas menor pela reorganização, sem usar redução de páginas como critério de exclusão de evidências. O modelo local foi confrontado; a ambiguidade sobre a abertura conjunta de capítulo e seção está em `AUDITORIA.md`.

## Pendências externas e de coleta

1. Confirmar a URL e a versão definitiva do vídeo de entrega; o endereço da capa não foi substituído.
2. Executar e documentar leitura física do QR em celular e avaliar tarefas com passageiros consentidos; sem participantes, taxas ou benefícios inventados.
3. Obter, se disponíveis, documento original, data e setor da resposta de Santos e o vídeo original referido pelo grupo; capturas de serviços sem data/versão continuam limitadas ao acervo.
4. Complementar a identificação da versão examinada em 21/10 e o protocolo/duração/tarefas da avaliação externa, se existirem registros. A autorização posterior menciona “4 procedimentos” sem enumerá-los; não foi ampliada nem usada para nova alteração de assinatura.
5. Não reconstruir retroativamente o manifesto contemporâneo completo do benchmark. Uma nova avaliação controlada deve registrar fontes, alterações locais, carga, hardware e condições de cache.
6. Validar cadastro/acessos, calendário e operação em campo; resolver 344.210 pares sem causa esclarecida, sem tratar a cobertura estrutural como garantia de viagem.
7. Para trabalho futuro de implementação: limpeza independente da coleta e política verificável para exportações/cópias. Nenhuma mudança de privacidade foi implementada nesta tarefa editorial.
8. Confirmar com a instituição eventual preferência diferente para as quebras indicadas contraditoriamente no texto e no sumário de exemplo do modelo fornecido.

A revisão está concluída no escopo editorial. Essas pendências não foram convertidas em atividades executadas ou aprovação acadêmica.
