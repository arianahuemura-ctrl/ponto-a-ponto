# Auditoria anterior à edição — 2 de novembro de 2026

Referência original: `refs/auditoria/relatorio-20261102-original-tecnico-cientifica`, árvore `fe1b7a141552c478d511eb19bba930ab4c4becc8`. HEAD `e5077b9`; branch `relatorio`. A árvore preserva fontes e alterações locais preexistentes, imagens, documentos e PDF de referência, sem criar commit, trocar branch ou modificar o índice. Consulte `baseline.json` para hashes e `status-original.txt` para o estado inicial. O PDF original tem 155 páginas.

## Conflitos e decisões

| Proposta | Evidência e conflito | Decisão editorial |
|---|---|---|
| Destacar contribuição | QRCodeAdesivo já identifica o ponto; Cittamobi já planeja por destino/conexões. Capturas não são ensaio comparativo de usabilidade. | Descrever integração do fluxo; distinguir observado, não verificado e ausente apenas na tela examinada. Não alegar ineditismo. |
| Demonstrar ônibus + ferrovia | Existe captura de 2/11, 02h19, Oscarito–Brás, linha 157 + Linha 10; interface avisa busca parcial. Não corresponde à consulta de 08h da tabela. | Incluir captura existente com instante e ressalva; não confundir as duas consultas. |
| Comprovar QR físico | A captura de QR na interface e a abertura de URL não comprovam leitura por câmera. `capturas/ilustracao-qr.txt` identifica imagem gerada, não instalação. | Registrar lacuna e protocolo; nenhum teste físico declarado executado. |
| Mapear cobertura | `stops.csv`, `summary.json` e malha IBGE 2024 da auditoria permitem mapa de distribuição; 337 pontos distintos, 3 estações separadas. | Representar coordenadas existentes e a malha exata; não estimar população atendida, acesso pedestre ou operação. |
| Melhor desempenho | CSV registra 1.637 sucessos pareados em 3.264 casos. Mediana piora, P95/máximo agregados melhoram; às 02h o P95 piora. | Mostrar distribuições individuais, diferenças e estratos; sem causalidade de cache/concorrência. |
| 99,666% de cobertura | Censo de 1/11, 22.274 identificadores, anterior à ARTESP; 1.657.654 pares sem materialização, dos quais 344.210 sem causa esclarecida. | Separar cadastro, estrutura, tempo e operação; não interpretar como sucesso de viagem. |
| Avaliação externa | Documentos preparatórios, recebido e confirmado, autorização posterior e versões 21/25 de outubro são documentos distintos. | Manter anexo confirmado byte a byte; explicitar procedência. Não reutilizar assinatura nem atribuir novembro ao avaliador. |
| Privacidade | Leitura de `usability.py`, `usability_admin.py`, `research.py`, `researchChoice.js` e `visualRecording.js` no worktree da aplicação: expurgo ligado à coleta e exclusão de cache com erros ignorados. | Manter descrição limitada; limpeza independente e política de exportações como futuras; nenhuma declaração de conformidade legal integral. |
| Reduzir repetições/páginas | Modelo institucional local exige títulos e subtítulos em nova página e resumo até 250 palavras. | Preservar estrutura 2.1–2.5 e formatação; deslocar histórico metodológico para apêndice; não perseguir redução arbitrária de páginas. |
| Vídeo da capa | Link identificado como provisório; não há confirmação da versão definitiva de entrega. | Manter link e sinalização de pendência. |

## Escopo das fontes

Foram examinados os fontes ativos `relatorio_final_pi2_v2.tex` e seus includes, o modelo `Modelo_Relatorio_Final.docx`, o PDF ARTESP revisado de 2/11, as auditorias ARTESP e de consistência, o CSV individual do benchmark e a documentação/código de privacidade. Comparações de serviços se referem ao acervo histórico; esta revisão não realizou novas consultas aos aplicativos nem testes em passageiros. A referência anterior a uma captura ônibus–trilho pendente no apêndice de 1/11 será atualizada para apontar a evidência de 2/11.

Nenhuma importação, materialização, execução do aplicativo ou novo benchmark é necessária nesta revisão. Scripts editoriais apenas leem medições/insumos e geram documentos e figuras em diretório novo. Documentos assinados e dados brutos serão conferidos por SHA-256 ao final.

## Conferência do modelo institucional

O arquivo `Modelo_Relatorio_Final.docx` pede Times New Roman 12 no corpo, margens superior/esquerda de 3 cm e inferior/direita de 2 cm, espaçamento 1,5, resumo de até 250 palavras, cinco palavras-chave, títulos à esquerda e página nova para títulos/subtítulos. O sumário de exemplo, porém, coloca “Desenvolvimento” e “Objetivos” na mesma página. A revisão conserva essa abertura conjunta ilustrada no próprio modelo, usa parágrafos em negrito para os enunciados dos objetivos e inicia as demais seções numeradas em página nova, inclusive no estudo de cliques. O sumário passa a distinguir capítulos em negrito e seções sem negrito. Esta decisão e a ambiguidade do modelo ficam registradas; confirmação institucional de preferência distinta é uma pendência externa, não uma regra genérica presumida.

## Conferência das duas sessões de captura

A inspeção visual encontrou duas sessões distintas para Oscarito–Brás: `auditoria-artesp-maua-2026-11-02/live-capture.json` registra 02h19, chegada às 06h26 e aviso de busca parcial; `auditoria-apresentacao-artesp-2026-11-02/live-capture.json` registra 02h52, mesma chegada e busca ainda em andamento. Foram selecionadas as imagens da primeira sessão, coerentes com a consulta já descrita no relatório original. As imagens das 02h52 não foram usadas como evidência das 02h19. Os dois conjuntos permanecem preservados.
