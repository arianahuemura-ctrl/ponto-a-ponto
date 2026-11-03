# Capturas atualizadas — 2 de novembro de 2026

Foram substituídas **17 imagens** apresentadas como interface atual do PaP. O relatório permanece com **167 páginas**, sem alterar resultados experimentais, bibliografia, autores, data documental, Apêndices A–H ou Anexo A.

Entrega: [PDF atualizado](../PaP_relatorio_2026-11-02_capturas_atualizadas.pdf). A [revisão editorial anterior](../PaP_relatorio_2026-11-02_revisao_editorial.pdf) permanece íntegra. O ZIP técnico-científico anterior não corresponde a esta atualização.

## Referências e condições

- Fonte do relatório: branch `relatorio`, HEAD de referência `f58078abeed5a30e18c8de8d514d54a4dd0c215e`; esta atualização está sem commit.
- Aplicativo: branch `feat/busca-bidirecional`, HEAD `78e39355ce23aa545c4006978bcc59060f6db24f`; código consolidado em `80a35640eaf537a7df72ef77aebaa62b0d8159bb`. Árvore limpa antes da captura; nenhum código alterado nesta tarefa.
- Instância temporária real Django em `http://127.0.0.1:18082/`, encerrada ao final. Não houve importação, materialização nem publicação pública.
- Chromium/Playwright, português brasileiro e fuso America/Sao_Paulo, densidade 2. Janelas móveis de 430×932; computador de 1366×1000. Tema escuro, exceto a figura ferroviária clara.
- Capturas originais sem retoque, montagem ou substituição de respostas de transporte. Os recortes ampliados antigos deixaram de ser usados: não correspondiam à disposição atual. As novas figuras mostram as telas completas.
- Escolha explícita de continuar sem contribuir; nenhum POST à API observado nos registros, nenhuma nota ou mensagem de feedback enviada. O primeiro aviso foi capturado antes dessa escolha.
- Localização simulada no MASP pelo parâmetro documentado do aplicativo. Favoritos preparados com paradas reais e nomes ilustrativos, sem dados de participantes.

## Imagens atualizadas

| Grupo | Quantidade | Alteração representada |
| --- | ---: | --- |
| Primeiro acesso | 1 | Aviso real de participação e acesso sem contribuir |
| Entrada sem localização e localização simulada | 2 | Cabeçalho, controles atuais e atalhos Casa/Trabalho |
| Consulta da parada e QR Code | 2 | Painel atual e previsões realmente observadas |
| Favoritos | 1 | Lista atual, controles e atalho Casa preparado |
| Alternativas | 1 | Ordenação, resposta parcial, previsão e planejamento identificados |
| Viagem completa e último trecho | 2 | Percurso da mesma resposta parcial e controles de trechos |
| Cancelamento | 1 | Confirmação atual |
| Linha 6L10-41 | 1 | Traçado completo e indisponibilidade de posição do veículo |
| Alteração manual de embarque | 1 | Controles recolhidos/expandidos e posição simulada |
| Toque prolongado | 1 | Menu de destino/local favorito, antes da confirmação |
| Pesquisa e feedback | 2 | Escolha recusada e avaliação opcional por estrelas |
| Rede ferroviária clara e escura | 2 | Mapa colorido, nome completo e um rótulo por linha |

A correspondência de cada arquivo está em [substituicoes.json](substituicoes.json). Imagens e manifestos: [capturas atuais](../capturas/2026-11-02-interface-atual/). Os manifestos registram data/hora UTC, URL, dimensões, hashes e respostas HTTP; os horários exibidos na interface são locais. O script reproduz os cenários, mas horários e respostas não são congelados.

## Evidências históricas preservadas

- Consulta ARTESP Mauá–Brás de 02/11, por volta de 02h19, inclusive seus avisos e tempos: sustenta um registro temporal específico.
- Caso de sobreposição da linha 6L10, estudos de IHC de outubro, capturas de serviços comparados e QR ilustrativo: vinculados aos estudos e relatos originais.
- Arquitetura e revisão ferroviária históricas dos apêndices: não são apresentadas como a interface recapturada.
- Parecer externo assinado integral: seis páginas visualmente idênticas à referência, descontando o cabeçalho de numeração do relatório.
- Todos os arquivos originais de captura e PDFs anteriores permanecem no disco; nenhum foi substituído ou regravado. O manifesto de base cobre 1.202 arquivos preexistentes.

## Limites encontrados

A primeira tentativa de planejamento encerrou o navegador antes de uma captura utilizável; o manifesto de falha foi preservado. Uma nova consulta real, às 11h42, forneceu a opção exibida de cinco ônibus e quatro baldeações, ainda com busca em andamento. O texto agora explicita essa condição; não foi alegada conclusão da busca, melhor itinerário ou validação da viagem. Os números do exemplo antigo foram retirados da descrição da tela atual, sem alterar os resultados dos experimentos históricos.

O QR Code aponta para a instância local temporária. A captura demonstra sua geração, não leitura física nem endereço público utilizável depois do encerramento do servidor.

O aviso inicial da própria aplicação ainda menciona apenas SPTrans/São Paulo, apesar da integração ARTESP documentada. A captura conserva fielmente esse texto; sua atualização no aplicativo fica registrada como pendência separada. Não houve correção de código ou alteração de consentimento nesta tarefa.

## Validação

- LuaLaTeX/latexmk com `-norc`: código 0, compilação final em `build-3.log`.
- 167 páginas antes e depois; nenhuma página vazia ou página isolada apenas com uma linha introduzida. Paginação contínua, 119 entradas de sumário/listas, 64 marcadores e 462 links internos conferidos.
- 84 links externos preservados; disponibilidade HTTP de todos eles não reavaliada.
- 17 novas imagens incorporadas na resolução original, com pixels idênticos aos PNGs; sem redução de resolução ou compressão com perdas.
- Otimização do PDF de 29.986.160 para 28.877.638 bytes, com igualdade de pixels a 144 dpi, texto, links, marcadores e metadados em todas as páginas.
- Metadados Title, Author, Subject e Keywords preservados. Resumo, oito autores, data documental e bibliografia sem alteração.
- Zero referências indefinidas, caracteres ausentes ou Overfull; permanecem 13 Underfull e três avisos de compatibilidade já conhecidos. Conferência visual das 17 capturas e das páginas afetadas, sem corte introduzido observado.
- `git diff --check` aprovado. Nenhuma suíte da aplicação foi reexecutada: esta etapa altera documentação, usando a aplicação real apenas para capturas.

Resultados completos e hashes de renderização: [VALIDACAO.json](VALIDACAO.json). Preservação dos originais: [originais-sha256.json](originais-sha256.json). Logs completos em `.cache/setup/capturas-atuais-20261102/`, no worktree do relatório, e `.cache/setup/capturas-relatorio-20261102/server.log`, no worktree do aplicativo.

PDF final: **28.877.638 bytes**. MD5: `b253dea82eb68d251fee52a4fae225cf`. SHA-256: `7a93bb8d7e2820a72a261e435585b8ee75403e82a8556181e4d272a18f3bd77d`.

Continuam pendentes a confirmação institucional sobre abstract/keywords, o link definitivo do vídeo, o protocolo físico de QR e a avaliação com passageiros. Não houve commit ou push desta atualização, nem alterações nas sessões ou configurações globais do Codex.
