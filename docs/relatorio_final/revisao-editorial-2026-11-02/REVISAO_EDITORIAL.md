# Revisão editorial — PaP — 2 de novembro de 2026

[PDF final](../PaP_relatorio_2026-11-02_revisao_editorial.pdf) · [Validação automática](VALIDACAO.json) · [Patch integral dos fontes](alteracoes-editoriais.patch).

## Referência e limites da intervenção

Worktree `/home/avale/Projetos/maua_bus_map-relatorio`, branch `relatorio`, HEAD `e5077b9c12b89c099f900cad0911f7498dafb06d`. Não houve commit, troca de branch, alteração de resultados, dados de transporte, aplicação, sessões Codex ou configurações globais. As alterações locais preexistentes foram preservadas. O PDF de referência de 168 páginas continua com MD5 `64f0e94138166eb508b648910fbe960f` e SHA-256 `2d2a3840bd717aa01b9ee9aa4b0a88883fc0adf9af8caf68b15e2f8b1ac0ff2d`.

## Proposta e redução medida

Antes das alterações, a proposta comunicada estimava 1–2 páginas em 2.3, 1–2 em 3.1 e 2–3 no Apêndice C, sem redução prometida em E.2; estimava acréscimo de 3–4 páginas pelas listas. A recompilação mediu:

| Trecho | Antes | Depois | Redução | Justificativa |
| --- | ---: | ---: | ---: | --- |
| 2.3 Fundamentação teórica | 19 | 17 | 2 | Explicações repetidas sobre grafos, avaliação temporal e QR condensadas; reprodução complementar da lista extensa do Olho Vivo retirada. |
| 3.1 Fluxo implementado e evidência visual | 15 | 14 | 1 | Procedência consolidada e duas vistas da mesma viagem dispostas lado a lado. |
| Apêndice C — Evolução e propostas | 9 | 8 | 1 | Descrições funcionais e arquiteturais repetidas substituídas por remissões. |
| E.2 Arquitetura histórica | 10 | 10 | 0 | Preservados bancos, cotas, diagnóstico, regras históricas e protocolo de reprodução; cortes adicionais perderiam distinções técnicas. |
| Listas de figuras e tabelas | 0 | 3 | −3 | Duas páginas de figuras e uma de tabelas, previstas como opcionais no modelo. |
| **Documento completo** | **168** | **167** | **1** | Quatro páginas retiradas, três acrescentadas. |

O texto principal (Introdução até Considerações finais) passou de 69 para 66 páginas. Os totais de cada seção são contados do início até a página anterior à próxima seção do mesmo nível, não por estimativa de palavras. Nenhuma redução foi obtida diminuindo a fonte, as margens ou o espaçamento institucional; títulos/subtítulos continuam iniciando página conforme o modelo fornecido.

## Conteúdo retirado, reunido ou remetido

- Retirada somente a reprodução da antiga Figura 6 (lista extensa do Olho Vivo, `imgs/olho_vivo7.png`, apresentada em dois recortes). A captura de previsões de várias linhas já sustenta a comparação. A hipótese de sobrecarga visual e o caminho para o registro complementar permanecem; o PNG original não mudou. A sequência de etapas do Olho Vivo foi ajustada de 1/2/4 para 1/2/3 nas legendas.
- A fundamentação conserva todas as referências citadas e as ressalvas sobre horários, limitações do planejamento, leitor de QR e acesso à internet. Foram reunidas explicações já repetidas nos parágrafos próximos ou no fluxo implementado.
- A procedência da Seção 3.1 conserva datas, revisões, dimensões, densidade, simulação, interceptação de telemetria e caminhos dos registros. Viagem completa e último trecho mantêm capturas integrais, numeração e legendas próprias. A largura de cada imagem passou de 219,66 para 217,57 pontos (redução de 0,95%); nenhuma imagem foi recortada ou reamostrada.
- O Apêndice C remete à Seção 3.1, à arquitetura, aos resultados e ao Apêndice F. Foram mantidos os relatos sobre Santos, o retorno da comunidade, propostas de integração, intenções de viagem, privacidade e detalhes históricos únicos, como 250 m, 0,65 s e política de recálculo. Nada foi transferido para fora do acervo de evidências.
- E.2 foi examinada e mantida integralmente. Seus contratos históricos não são uma repetição intercambiável com a arquitetura concorrente posterior.
- Apêndices A–H preservados. O Apêndice G é a comunicação/síntese elaborada pelo grupo; o documento externo integral permanece no Anexo A. O parecer original assinado e suas seis páginas incorporadas foram preservados. Resultados, gráficos, limitações, referências bibliográficas e evidências ARTESP em Mauá não sofreram cortes.

## Elementos pré-textuais e conformidade

Consultado o arquivo institucional [Modelo_Relatorio_Final.docx](../Modelo_Relatorio_Final.docx). Ele prevê listas de ilustrações e tabelas opcionais; ambas foram acrescentadas, com 39 figuras e 21 tabelas. O resumo português foi preservado, com 214 palavras e cinco palavras-chave, abaixo do limite de 250. Capa, oito autores, título e data documental de 2026 são idênticos no fonte.

A [ABNT NBR 14724:2024, versão corrigida de 01/04/2025](https://engenhariaedesenvolvimentosustentavel.ufes.br/sites/engenhariaedesenvolvimentosustentavel.ufes.br/files/field/anexo/abnt_nbr_14724.pdf) distingue apêndice produzido pelo autor de anexo de autoria externa. Sua estrutura geral inclui resumo em língua estrangeira, mas o modelo específico fornecido para este relatório técnico-científico não o apresenta. **Abstract e keywords não foram acrescentados automaticamente: permanece pendente confirmar sua exigência com a orientação institucional.** Não se declara conformidade integral com toda a norma com base apenas nessa revisão.

Também permanece o aviso preexistente de confirmação do vídeo definitivo na capa. A numeração começa em 1 na Introdução, como determina o modelo; não se alterou essa regra em favor de outro padrão. Não houve impressão física ou homologação institucional.

## Metadados internos

Configurados no fonte LaTeX com `hyperref`, incluindo Unicode, exibição do título e numeração dos marcadores. O Sumário e as duas listas receberam marcadores próprios.

| Campo | Antes | Depois |
| --- | --- | --- |
| Title | vazio | Sistema de acesso a informações do transporte público por QR Code em pontos de ônibus |
| Author | vazio | André Meneghelli Vale; Ariana Harumi Uemura; Bruno Gabriel Migliari de Souza; Caio Wellington Procopio Ferreira; Ingrid Emanuelle Sousa Dias; Leonardo Souza Leite; Maurício Gonçalves Marques; Nathalia Almeida Amorim |
| Subject | vazio | Relatório Técnico-Científico Final — Projeto Integrador em Computação II — UNIVESP — 2026 |
| Keywords | vazio | transporte público; QR Code; informação ao passageiro; mobilidade urbana; pontos de interesse |

As datas de criação/modificação do PDF são atualizadas pela recompilação; a data documental no texto e os nomes dos autores não foram alterados.

## Imagens e otimização

O PDF original contém 48 referências a imagens e 39 objetos de imagem distintos; cinco objetos são reutilizados. A análise dos fluxos decodificados não encontrou dois objetos distintos com a mesma imagem/dimensões/espaço de cor. Assim, as repetições de uso já compartilhavam recursos e não justificavam apagar evidências. Após a retirada da figura complementar, restam 46 referências e 38 objetos de imagem.

LuaLaTeX foi configurado com compressão 9 e compressão de objetos 3. Após a compilação, aplicou-se pikepdf/qpdf com recompressão Flate nível 9, fluxos de objetos e retirada de recursos não referenciados. Não houve JPEG adicional, redução de resolução, rasterização de gráficos vetoriais ou modificação do parecer assinado. O candidato MuPDF também foi mantido nos logs, mas o menor resultado validado foi o pikepdf.

- Antes: **27.556.752 bytes** (27,56 MB).
- Após a revisão, antes da otimização externa: **27,258,772 bytes**.
- Final: **24,998,553 bytes** (**25.00 MB; 23.84 MiB**), redução de **9.28%** frente à referência.
- As 167 páginas são idênticas pixel a pixel a 144 dpi antes/depois da otimização. Texto, metadados, marcadores e links também conferem. Todos os fluxos de imagens restantes correspondem às imagens originais.

## Validação executada

- Compilação final `latexmk -norc -lualatex -interaction=nonstopmode -halt-on-error`, com saída nova e cache de fontes temporário: **código 0**, `compile-04.log`. O `-norc` evita o exportador histórico que poderia sobrescrever entregas anteriores.
- `validate.py`: **código 0**, `validate-02.log`; 167 páginas renderizadas, zero páginas vazias, 159 páginas numeradas continuamente da Introdução ao final. Sumário e listas: 119 entradas conferidas contra seus destinos e páginas impressas.
- **64 marcadores**, **458 links internos resolvidos**, 84 links externos com URIs preservados. Não foi revalidada a disponibilidade HTTP de cada serviço externo histórico.
- 27 fontes TeX ativos, 94 rótulos, 54 chaves bibliográficas citadas; nenhuma referência ausente ou rótulo duplicado. Bibliografia idêntica à referência.
- Zero Overfull, zero caracteres ausentes, 13 Underfull e três avisos de compatibilidade preexistentes; contatos completos e páginas ampliadas conferidos sem cortes visuais. As imagens pareadas, listas, sumário, mapa/capturas ARTESP e parecer foram examinados.
- Seis páginas externas comparadas à edição anterior, excluindo apenas o cabeçalho de numeração: pixels idênticos. Os arquivos originais de todas as evidências e o PDF de referência conferem com o manifesto de 1.189 arquivos anteriores. Apenas os dois fontes editoriais e o README mudaram nesse conjunto.
- Verificação sintática do PDF: nenhum erro. `git diff --check`: **código 0**; repetir após futuras alterações.
- Testes da aplicação e novas medições não executados, pois a intervenção foi editorial. Nenhum commit automático.

Logs completos: `.cache/setup/editorial-20261102/` neste worktree. Manifesto, inventário, validação e patch estão neste diretório de auditoria. A imagem de contato inicial difere apenas na legenda da etapa 3 e numa frase editorial das páginas 21–22; as prévias ampliadas e hashes finais conferem com a compilação final. O marcador adicional do Sumário não alterou pixels.

## Integridade da entrega

MD5: `5bdbc062a2680394ea8d4f97d715caef`

SHA-256: `b24c37067fc84c389d21a79f97cef1eabc00d6921791bb6d7ad08a69e36b9e55`
