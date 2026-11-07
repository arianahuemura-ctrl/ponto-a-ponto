from pathlib import Path
import shutil,json,subprocess,hashlib,re
r=Path('/home/avale/Projetos/maua_bus_map-relatorio/docs/relatorio_final'); o=r/'revisao-tecnico-cientifica-2026-11-02';o.mkdir(exist_ok=True)
assert subprocess.check_output(['git','branch','--show-current'],cwd=r,text=True).strip()=='relatorio'
assert subprocess.check_output(['git','rev-parse','refs/auditoria/relatorio-20261102-original-tecnico-cientifica'],cwd=r,text=True).strip()=='fe1b7a141552c478d511eb19bba930ab4c4becc8'
for n in ['baseline.json','status-original.txt','alteracoes-preexistentes.patch','preserve.py','generate_figures.py']:
 shutil.copyfile(Path('/tmp/pap-revisao-relatorio-20261102')/n,o/n)
def write(n,t): (o/n).write_text(t.strip()+'\n')
write('AUDITORIA.md','''# Auditoria anterior à edição — 2 de novembro de 2026

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
''')
write('comparacao.tex',r'''
\subsection*{Síntese comparativa dos fluxos examinados}
\label{sec:comparacao-servicos}
A Tabela~\ref{tab:comparacao-servicos} reúne as evidências documentais descritas nesta seção. ``Observado'' significa visível nas capturas examinadas; ``não verificado'' indica insuficiência do acervo. Uma opção ausente do fluxo examinado não é declarada inexistente no serviço. Não foi realizado um ensaio simultâneo de usabilidade entre produtos.
\begingroup\small\SingleSpacing\setlength{\parskip}{0pt}\setlength{\tabcolsep}{4pt}
\begin{longtable}{p{2.4cm}p{5.5cm}p{6.8cm}}
\caption{Serviços e continuidade da consulta: alcance da evidência.}\label{tab:comparacao-servicos}\\\hline
Serviço & Funcionalidade documentada & Limite da comparação\\\hline\endfirsthead
\hline Serviço & Funcionalidade documentada & Limite da comparação\\\hline\endhead
\hline\endfoot
QRCodeAdesivo & Página web contextualizada por parada, linhas e links individuais; Figura~\ref{fig:sptrans-parada}. & Seleção por destino ausente da página examinada. Leitura física pelo grupo e funcionamento completo não verificados; não se conclui encerramento do serviço.\\[5pt]
Olho Vivo & Lista de previsões por ponto e mapa da linha selecionada; Figuras~\ref{fig:olho-vivo-previsoes} e~\ref{fig:olho-vivo-mapa}. & Comparação espacial conjunta e planejamento por destino não observados nesse fluxo. É serviço distinto do QRCodeAdesivo.\\[5pt]
Cittamobi & Busca por destino, alternativas com conexões e mapas nas telas analisadas; Figura~\ref{fig:cittamobi-destino-rotas}. & Integração completa QR físico--destino no navegador não verificada. Destino, favoritos e conexões não são novidades do PaP.\\[5pt]
Santos / Quanto Tempo Falta & Resposta institucional reproduzida pelo grupo e descrição de vídeo relatam QR que abre página web da parada. & Evidência indireta: vídeo original não analisado; destino ausente apenas do percurso descrito. Data e setor da resposta ao protocolo 7657-2026 não informados.\\[5pt]
PaP & Entrada contextual por URL da parada, escolha do destino, alternativas, transferências e mapa no navegador; capturas e testes internos deste relatório. & Cadeia de navegação implementada; leitura física e benefício aos passageiros ainda não demonstrados. Não se estabelece superioridade entre serviços.\\
\end{longtable}
\fonte{Síntese do acervo examinado pelo grupo em 2026; capturas e procedência descritas nesta seção e no Apêndice~\ref{ap:cliques}.}
\endgroup
A contribuição técnica é a continuidade desse conjunto de ações em uma implementação web contextualizada. A hipótese de redução de esforço exige tarefas equivalentes, resultado correto e compreensão do percurso, não apenas a contagem de recursos disponíveis.
''')
write('metodologia.tex',r'''
\section{Metodologia}\label{sec:metodologia-revisada}
O estudo articula desenvolvimento de um artefato e análise de evidências documentais e técnicas. As etapas de ouvir e interpretar o contexto, criar e prototipar, implementar e testar seguem a organização do modelo institucional fornecido e são orientadas pelo Design Thinking e pelo Double Diamond \citep{ideo-designthinking,designcouncil}. Não se afirma execução integral de oficinas formais dessas abordagens. A Tabela~\ref{tab:procedimentos-revisados} separa procedimentos realizados de avaliação futura. O histórico detalhado e os instrumentos permanecem no Apêndice~\ref{ap:percurso-metodologico}; os limites de inferência são reunidos na Seção~\ref{sec:validade}.
\begingroup\small\SingleSpacing\setlength{\parskip}{0pt}\setlength{\tabcolsep}{4pt}
\begin{longtable}{p{2.6cm}p{5.7cm}p{6.4cm}}
\caption{Procedimentos, evidências e alcance das conclusões.}\label{tab:procedimentos-revisados}\\\hline
Procedimento & Método e evidência & Alcance e situação\\\hline\endfirsthead
\hline Procedimento & Método e evidência & Alcance e situação\\\hline\endhead
\hline\endfoot
Necessidades e entrevista & Síntese temática da conversa remota com Osmar Junior; transcrição identificada em 20/8/2026, 2.861 s; intervalos na Tabela~\ref{tab:entrevista-osmar}. & Realizado. Perspectiva profissional da gestão; não representa amostra de passageiros, parceria ou autorização de implantação.\\[5pt]
Pesquisa documental & Literatura sobre informação e IHC; registros públicos, e-mail de 2/9 e resposta sobre Santos, com procedência discriminada. & Realizada. Fundamenta recorte e requisitos; relatos e fontes secundárias não viram cadastros operacionais validados.\\[5pt]
Soluções existentes & Inspeção de capturas de QRCodeAdesivo, Olho Vivo e Cittamobi; análise de favoritos e descrição indireta do fluxo em Santos. & Realizada no acervo disponível. Tabela~\ref{tab:comparacao-servicos}; não é experimento comparativo com usuários.\\[5pt]
Desenvolvimento e prototipação & Mockups, Figma e aplicação Django/React; inspeção de código, requisitos retrospectivos e versões Git. & Implementação e iterações documentadas. Mockup não prova funcionamento; código não prova benefício de uso.\\[5pt]
Integração e auditoria & Importação GTFS; recorte geográfico com malha IBGE 2024; contagem de identificadores, viagens e dias de serviço; consultas temporalmente verificadas. & Realizadas; 337 paradas ARTESP e 16 linhas/variantes em Mauá. Cadastro e programação, não observação da operação em campo.\\[5pt]
Testes funcionais & Testes unitários, integração e navegador registrados por revisão; capturas automatizadas. Apêndice~\ref{ap:engenharia} e registros de 29/9 e 29/10. & Execuções históricas documentadas. Nesta revisão editorial não se repetiram testes do aplicativo; não substituem avaliação de usabilidade.\\[5pt]
Benchmarks & Repetição de 3.264 consultas por versão em 1/11, 32 processos, chamadas externas bloqueadas; CSV individual, 1.637 sucessos pareados. & Medição local até a primeira rota; gráficos da Seção~\ref{sec:desempenho-revisado}. Não mede latência de ponta a ponta ou causa isolada da variação.\\[5pt]
Avaliação profissional & Registros da Alameda Solutions de 21 e 25/10, versões e documento confirmado de 26/10; Apêndice~\ref{ap:feedback-alameda}. & Apreciação qualitativa. Não se atribuem ao avaliador testes internos nem alterações de novembro.\\[5pt]
Navegação exploratória & Relatos de usuários convidados e lista de ajustes; devolutivas de outubro e verificações técnicas da Tabela~\ref{tab:feedback-ajustes}. & Realizada com alcance exploratório. Não há amostra sistemática documentada, taxa de sucesso ou mensuração representativa de esforço.\\[5pt]
Avaliação com passageiros & Protocolo de tarefas QR versus entrada manual, compreensão, tempo, erros, ajuda e percepção de facilidade; instrumentos preservados. & Futura. Participantes, coleta e resultados ainda não apresentados. Leitura física do QR exige evidência própria, conforme protocolo do Apêndice~\ref{ap:protocolo-qr}.\\
\end{longtable}
\fonte{Elaboração do grupo com base no acervo, nas versões e nos registros de execução descritos nos apêndices (revisão em 2 nov. 2026).}
\endgroup
O problema de projeto é ajudar a pessoa no ponto a reconhecer alternativas para chegar ao destino sem conhecer previamente as linhas ou a identificação da parada. Na etapa de ouvir, a entrevista e a análise documental delimitaram esse problema. Na etapa de criar, o grupo comparou formas de acesso e organização da informação; a presença de destino e conexões no Cittamobi afastou a alegação de novidade dessas funções. Na etapa de implementar, o cenário demonstrativo de Mauá foi seguido pelo planejamento com dados SPTrans e pela ampliação ARTESP, com suas fontes separadas.

A auditoria ARTESP verificou a malha municipal e os identificadores antes de contar viagens, evitando somar uma mesma viagem a cada parada. Os instantes de 3, 7 e 8 de novembro são datas de serviço consultadas, não datas de observação da circulação. O benchmark de 1 de novembro antecede essa ampliação. As comparações usam os mesmos pares que receberam rota nas duas versões; os demais estados são contabilizados separadamente. Os procedimentos de reprodução e os arquivos utilizados estão nos Apêndices~\ref{ap:importacao} e~\ref{ap:rotas}.

A interpretação relaciona evidência a requisito e limita a conclusão ao procedimento executado. A apreciação profissional e os relatos exploratórios orientaram correções, enquanto os testes internos conferiram comportamentos. A eficácia, a eficiência e a satisfação dos passageiros permanecem objetos da avaliação futura \citep{iso924111}; não são deduzidas de implementação, quantidade de testes ou número de cliques.
''')
write('dados-e-desempenho.tex',r'''
\section{Escopos da solução e níveis de cobertura}\label{sec:cobertura-revisada}
A evolução do PaP deve ser lida por fonte e por versão. A Tabela~\ref{tab:cenarios-revisados} distingue o demonstrador histórico da integração efetivamente programada; a Tabela~\ref{tab:niveis-cobertura} define o que cada medida permite concluir.
\begingroup\small\SingleSpacing\setlength{\parskip}{0pt}\setlength{\tabcolsep}{4pt}
\begin{longtable}{p{2.7cm}p{6.0cm}p{6.0cm}}
\caption{Comparação das três etapas do projeto.}\label{tab:cenarios-revisados}\\\hline
Etapa & Fonte e entrega & Limite\\\hline\endfirsthead
\hline Etapa & Fonte e entrega & Limite\\\hline\endhead\hline\endfoot
Mauá histórico & Catálogo público, coordenadas parcialmente inferidas e demonstração de horários/veículos em simulação identificada. & Não comprova programação ou operação dos ônibus municipais.\\[4pt]
SPTrans original & GTFS de ônibus e integração ferroviária; 22.274 identificadores no censo de 1/11; Olho Vivo para posições/previsões compatíveis. & Calendário e estimativas condicionam as rotas; previsão depende da API. Não é a rede municipal de Mauá.\\[4pt]
ARTESP em 2/11 & Mais 25.105 registros no cadastro combinado (47.379); em Mauá, 337 paradas, 16 linhas/variantes, conexões com trilhos. & Programação metropolitana de 2026; não integra toda a rede municipal nem demonstra realização da viagem.\\
\end{longtable}
\fonte{Auditorias de 1 e 2 nov. 2026; fontes e procedimentos nos Apêndices~\ref{ap:importacao} e~\ref{ap:rotas}.}
\begin{longtable}{p{2.5cm}p{6.1cm}p{6.1cm}}
\caption{Quatro níveis de cobertura e seus denominadores.}\label{tab:niveis-cobertura}\\\hline
Nível & Evidência existente & O que não mede\\\hline\endfirsthead
\hline Nível & Evidência existente & O que não mede\\\hline\endhead\hline\endfoot
Cadastral & Identificadores, coordenadas, linhas e sequências importadas. Recorte de 337 paradas ARTESP em Mauá, mais três estações ferroviárias separadas. & Percentual da população atendida, estado físico da parada ou completude da rede municipal.\\[4pt]
Estrutural & Em 1/11, 494.451.148 de 496.108.802 pares dirigidos distintos com alternativa materializada (99,666\%), no universo de 22.274 paradas anterior à ARTESP. & Probabilidade de encontrar uma viagem, disponibilidade por horário ou nova cobertura conjunta após 2/11.\\[4pt]
Temporal & Calendários, horários e acessos avaliados para uma consulta; viagens ARTESP distintas em 3, 7 e 8/11 e 12 consultas representativas. & Serviço em todos os horários, feriados não registrados ou datas além da vigência.\\[4pt]
Operacional & Posições/previsões SPTrans quando retornadas e associadas com segurança; não há comprovação de circulação pela simples existência de uma rota GTFS. & Execução real de viagens ARTESP/ferroviárias, pontualidade e viabilidade física de todos os acessos.\\
\end{longtable}
\fonte{Síntese do grupo a partir dos censos e da validação temporal; não se convertem denominadores entre níveis.}
\endgroup
Dos 1.657.654 pares sem alternativa materializada em 1/11, 1.313.444 são explicados pelas regras de acesso examinadas; 344.210 permanecem sem causa esclarecida. A auditoria individual encontrou 50 origens que aparecem apenas no término das viagens GTFS e nove destinos com restrições pedestres. As 50 origens têm acesso externo verificado a embarques entre 9,54 e 493,61 m, bloqueado pela política inicial examinada. Oito destinos excedem a tolerância de encaixe de 20 m (21,65--40,45 m); um exige 1.104,64 m, acima do limite de 1.000 m. Essas constatações explicam limites do modelo e da política; não comprovam erro no GTFS ou inacessibilidade física. Os identificadores e procedimentos detalhados permanecem na auditoria de extremidades referenciada na Seção~\ref{sec:atualizacao-20261101}.

\section{Desempenho: distribuições e comparação pareada}\label{sec:desempenho-revisado}
O ensaio de 1 de novembro repetiu 3.264 consultas por versão, com 32 processos e partidas simuladas em 3 de novembro às 02h, 08h e 14h. Mede o tempo local até a primeira rota, sem HTTP, túnel, rede externa ou renderização no celular. As 1.637 consultas com rota nas duas versões constituem o conjunto pareado: a mediana \textbf{piorou de 0,282 para 0,599 s}, enquanto o P95 caiu de 5,698 para 5,143 s e o maior tempo observado de 10,712 para 5,936 s. A redução da cauda não representa ganho generalizado.
\begin{figure}[H]\centering
\includegraphics[width=\textwidth]{revisao-tecnico-cientifica-2026-11-02/benchmark-pareado.pdf}
\caption{Distribuições e diferenças das 1.637 medições pareadas até a primeira rota.}\label{fig:benchmark-pareado}
\fonte{CSV individual \nolinkurl{paired-results.csv}, ensaio de 1 nov. 2026; recálculo editorial em 2 nov. Cada diferença é depois menos antes para a mesma consulta; a ordenação não indica sequência temporal.}
\end{figure}
A Figura~\ref{fig:benchmark-pareado} utiliza todos os tempos individuais existentes, sem reconstrução de amostras a partir de médias ou percentis. O P95 segue o instrumento original: elemento ordenado de índice arredondado $0{,}95(n-1)$, com índice inicial zero. Os recortes por horário também mostram heterogeneidade: às 02h, o P95 aumentou de 0,739 para 1,281 s; às 08h, caiu de 5,760 para 5,215 s; às 14h, de 5,766 para 5,204 s. Não foram isolados efeitos de cache, carga, escalonamento ou concorrência; não se atribui causalidade a nenhum deles.
\begin{table}[H]\centering\small
\caption{Desfechos de todas as consultas do ensaio, antes do pareamento.}\label{tab:estados-benchmark}
\begin{tabular}{p{8cm}rr}\hline
Estado & Antes & Depois\\\hline
Primeira rota & 1.652 & 1.728\\
Dependência externa não medida & 936 & 839\\
Busca encerrada sem rota & 676 & 697\\\hline
Total & 3.264 & 3.264\\\hline
\end{tabular}
\fonte{Medições individuais de 1 nov. 2026. ``Sem rota'' descreve o encerramento observado, não inexistência de caminho na rede real.}
\end{table}
A Tabela~\ref{tab:estados-benchmark} impede interpretar os sucessos pareados como todos os casos do experimento. Houve 91 novos sucessos e 15 sucessos anteriores não reproduzidos, dos quais 12 dependiam de chamada externa e três encerraram com busca limitada. A amostra inclui casos problemáticos deliberadamente e não estima taxa de atendimento municipal. A documentação de parâmetros, resultados por custo e lacunas de reprodução permanece na Seção~\ref{sec:atualizacao-20261101}. Custo ponderado de transferência não equivale sempre ao número físico de baldeações.
''')
write('mapa-e-captura.tex',r'''
\subsection{Distribuição cadastral e evidência de integração}\label{sec:mapa-artesp}
A Figura~\ref{fig:mapa-artesp} representa as 337 coordenadas existentes no recorte auditado, sem geocodificação ou deslocamento editorial dos pontos. A malha é a municipal IBGE 2024, código 3529401, utilizada na contagem; não foi substituída por um limite simplificado. As estações são símbolos separados e não integram o total das paradas ARTESP. A distribuição é desigual no território e não permite calcular população coberta, acessibilidade física ou disponibilidade operacional.
\begin{figure}[H]\centering
\includegraphics[width=.95\textwidth]{revisao-tecnico-cientifica-2026-11-02/mapa-artesp-maua.pdf}
\caption{Distribuição das paradas ARTESP auditadas e das estações ferroviárias em Mauá.}\label{fig:mapa-artesp}
\fonte{Coordenadas de \nolinkurl{stops.csv} e \nolinkurl{summary.json}; malha \nolinkurl{maua-ibge-2024.geojson}, SIRGAS 2000, auditoria de 2 nov. 2026. Eixos em aproximação métrica local; não representam distância de caminhada.}
\end{figure}
\begin{figure}[H]\centering
\includegraphics[width=\textwidth]{auditoria-apresentacao-artesp-2026-11-02/captura-maua-bras-mapa.png}
\caption{Consulta Oscarito--Brás com ônibus ARTESP 157 e CPTM Linha 10--Turquesa.}\label{fig:artesp-onibus-trem}
\fonte{Captura da interface em 2 nov. 2026, por volta de 02h19; acervo \nolinkurl{auditoria-apresentacao-artesp-2026-11-02/}. Consulta parcial, com chegada planejada às 06h26; não é uma viagem observada.}
\end{figure}
A Figura~\ref{fig:artesp-onibus-trem} já existia no acervo e demonstra a composição das modalidades na interface. O aviso de busca parcial faz parte da evidência e foi mantido. Esta consulta de madrugada não corresponde às consultas das 08h da Tabela~\ref{tab:artesp-maua-consultas}; sua presença não permite substituir resultados, comparar durações entre horários distintos ou afirmar ótimo global. A imagem original foi preservada.
''')
write('validade.tex',r'''
\section{IHC, limitações e ameaças à validade}\label{sec:validade}
\subsection{Relação entre princípios e evidências}
A matriz da Tabela~\ref{tab:ihc-evidencias} liga princípios discutidos na fundamentação às decisões observáveis. Não é uma avaliação heurística independente nem um escore de usabilidade: explicita a hipótese de benefício e a evidência necessária para verificá-la.
\begingroup\small\SingleSpacing\setlength{\parskip}{0pt}\setlength{\tabcolsep}{4pt}
\begin{longtable}{p{2.8cm}p{4.0cm}p{4.2cm}p{3.5cm}}
\caption{Princípios de IHC, decisões, evidências e limitações.}\label{tab:ihc-evidencias}\\\hline
Princípio & Decisão implementada & Evidência & Limitação\\\hline\endfirsthead
\hline Princípio & Decisão implementada & Evidência & Limitação\\\hline\endhead\hline\endfoot
Reconhecimento em vez de memorização & Origem contextual e escolha por destino; favoritos locais. & Capturas de embarque, destino e favoritos; estudo de cliques no Apêndice~\ref{ap:cliques}. & Não mede compreensão ou esforço cognitivo dos passageiros.\\[4pt]
Visibilidade do estado & Progresso da busca, resultados parciais e previsão indisponível explicitados. & Capturas, testes registrados e aviso na Figura~\ref{fig:artesp-onibus-trem}. & Usuário pode confundir programação com previsão; reconhecimento ainda deve ser medido.\\[4pt]
Controle e recuperação & Recálculo manual, confirmação do cancelamento, preservação dos favoritos. & Requisitos e rastreabilidade no Apêndice~\ref{ap:engenharia}. & Teste automatizado não mede erros reais de uso ou compreensão do diálogo.\\[4pt]
Prevenção de erros & Seleção por toque prolongado cancelada em arrasto; distinção de embarque, destino e sentido. & Relatos e correções da Tabela~\ref{tab:feedback-ajustes}. & Episódios exploratórios não equivalem a incidência de erro em uma amostra.\\[4pt]
Hierarquia e redundância visual & Contraste, contornos e identificação textual ferroviária; controle de marcadores. & Seção~\ref{sec:legibilidade-ferroviaria}; capturas e verificações locais. & Não há validação de acessibilidade com participantes de diferentes percepções de cor.\\[4pt]
Liberdade de participação & Consulta ao transporte independente da gravação e comando de interrupção. & Fluxo de pesquisa e inspeção do código; Figura~\ref{fig:pesquisa-voluntaria}. & Consentimento implementado não garante anonimato ou conformidade legal integral.\\
\end{longtable}
\fonte{Síntese do grupo a partir da fundamentação de IHC e das evidências indicadas; revisão de 2 nov. 2026.}
\endgroup
\subsection{Ameaças à validade e alcance das conclusões}\label{sec:ameacas-validade}
\textbf{Validade interna.} Os benchmarks comparam consultas pareadas, mas não isolam variáveis de hardware, carga, cache do sistema operacional e escalonamento. A associação entre revisão e tempos observados não demonstra o efeito causal de uma técnica específica. Testes com respostas controladas verificam contratos, sem reproduzir toda a variabilidade de serviços externos.

\textbf{Validade externa.} A seleção estratificada de casos difíceis não representa a distribuição de viagens do município. Medições locais excluem rede, túnel e celular; datas e horários escolhidos não cobrem toda a operação. Relatos de desenvolvedores e convidados, bem como a apreciação de um profissional, não generalizam benefícios à população.

\textbf{Validade de construção.} Cliques não equivalem a esforço cognitivo; primeira rota não equivale a melhor rota; cobertura estrutural não equivale a viagem viável; intenção de deslocamento não equivale a embarque. Custo ponderado, quantidade de baldeações, frequência, programação e previsão são medidas diferentes. A redução de esforço requer sucesso correto, compreensão e observação de uso, não apenas menos ações.

\textbf{Atualização e qualidade dos dados.} GTFS representa cadastro e programação. O recorte ARTESP usa calendário de 2026 sem exceções de feriados e horários intermediários interpolados. Limites territoriais e coordenadas próximos à divisa exigem leitura cuidadosa; o mapa não homologa localização ou acesso em campo. Previsões operacionais dependem de correspondência segura e disponibilidade da fonte. Dados novos exigirão nova auditoria; o censo de 1/11 não descreve a base ampliada de 2/11.

\textbf{Reprodutibilidade.} Arquivos individuais, scripts e hashes permitem recalcular figuras e estatísticas. Entretanto, o HEAD observado com alterações locais não identifica sozinho o código executado, e não foi localizado manifesto contemporâneo completo da carga e de todos os fontes do benchmark. A revisão preserva essa lacuna. O apêndice técnico registra parâmetros e assinaturas disponíveis; não se reconstruíram medições nem condições ausentes.

\textbf{Avaliação com passageiros.} A entrevista de gestão, a avaliação profissional e as navegações exploratórias são contribuições distintas. Não há avaliação sistemática concluída que demonstre redução de esforço, tempo, espera ou erros para passageiros. Permanecem necessários consentimento, definição de amostra, tarefas equivalentes e registro de compreensão. A leitura física do QR e a implantação autorizada da sinalização também exigem evidências próprias.

\textbf{Privacidade e gestão dos registros.} A inspeção documental e de código confirma a separação da telemetria, a escolha de participação e o expurgo por idade acionado pela coleta. Não confirma anonimato, prazo absoluto de eliminação ou remoção de cópias exportadas. Limpeza periódica independente, tratamento do ciclo de vida das exportações, registro de falhas de exclusão e análise jurídica específica são melhorias futuras, não garantias presentes.
''')
write('protocolo-qr.tex',r'''
\chapter{Protocolo pendente de leitura física do QR Code}\label{ap:protocolo-qr}
O acervo examinado contém abertura de URL, emulação de navegador, QR exibido na interface e uma ilustração de uso identificada em \nolinkurl{capturas/ilustracao-qr.txt}. Esses materiais não comprovam leitura física por câmera. O protocolo a seguir é uma proposta reproduzível, não um teste executado.
\begin{enumerate}[leftmargin=*,itemsep=4pt]
\item Registrar revisão do aplicativo, data, URL estável da instância, identificador da parada, dispositivo, sistema, navegador e conectividade. Separar cenário programado de dados operacionais disponíveis.
\item Gerar um QR com a URL da parada; registrar seu conteúdo textual e hash do arquivo. Preparar uma placa de teste com autorização do local, sem apresentá-la como implantação pública.
\item Com a consulta anterior encerrada, filmar em sequência contínua a placa física, a leitura pela câmera, o endereço aberto e a identificação do embarque no navegador. Evitar capturar rostos, notificações ou dados pessoais alheios ao teste.
\item Escolher um destino conhecido, registrar alternativas, sentido, caminhada e eventual baldeação. Anotar indisponibilidade, resultados parciais e uso de localização simulada, se houver. Separar êxito técnico da leitura da compreensão do passageiro.
\item Para avaliar esforço, executar também a tarefa equivalente com origem manual, com ordem alternada e protocolo consentido. Registrar conclusão correta, tempo, ações, ajuda, erros e explicação do percurso; não contabilizar testes internos como passageiros.
\item Preservar arquivo original e metadados; publicar apenas cópia autorizada e minimizada. Vincular cada conclusão à gravação e à versão, inclusive tentativas malsucedidas. A coleta poderá alterar o planejamento posterior, mas não retroativamente o estado desta revisão.
\end{enumerate}
''')
# Move detailed methodology intact to appendix; preserve all labels/evidence.
p=r/'relatorio_final_pi2_v2.tex';s=p.read_text();start=s.index('\\section{Metodologia}');end=s.index('\\chapter{Resultados: solução final}')
method=s[start+len('\\section{Metodologia}'):end]
write('percurso-metodologico.tex',r'\chapter{Percurso metodológico, decisões e protocolos}\label{ap:percurso-metodologico}'+'\n'+r'Este apêndice preserva o detalhamento do percurso histórico e dos procedimentos da versão de 2 de novembro. A síntese que distingue execução e proposta está na Seção~\ref{sec:metodologia-revisada}. A interrupção de materialização referida abaixo pertence ao desenho histórico de outubro; o censo compacto posterior está na Seção~\ref{sec:atualizacao-20261101}.'+'\n'+method)
s=s[:start]+'\\input{revisao-tecnico-cientifica-2026-11-02/metodologia.tex}\n\n'+s[end:]
s=s.replace('\\section{Aplicação das disciplinas estudadas no projeto integrador}','\\input{revisao-tecnico-cientifica-2026-11-02/comparacao.tex}\n\n\\section{Aplicação das disciplinas estudadas no projeto integrador}')
s=s.replace('\\begin{apendicesenv}','\\begin{apendicesenv}\n\\input{revisao-tecnico-cientifica-2026-11-02/percurso-metodologico.tex}\n\\input{revisao-tecnico-cientifica-2026-11-02/protocolo-qr.tex}')
# Replace introductory contribution paragraph (includes unimplemented proposals).
a=s.index('O uso do QR Code e do ponto físico');b=s.index('\n\n',a)
s=s[:a]+r'''A contribuição central deste PI é integrar, no PaP, a identificação contextualizada da parada por QR Code, o acesso pelo navegador sem instalação obrigatória, a escolha do destino sem conhecimento prévio das linhas, a comparação de alternativas e a visualização dos deslocamentos com eventuais transferências. O encadeamento está implementado na aplicação; a leitura física e o benefício aos passageiros exigem verificação própria. QR Code, destino, favoritos e conexões já aparecem em outros serviços e não são reivindicados como novidades isoladas. A análise das soluções existentes delimita o fluxo observado e suas lacunas documentais, conforme a Tabela~\ref{tab:comparacao-servicos}. A hipótese investigada é que a continuidade entre contexto da parada e planejamento por destino possa facilitar a tarefa, sem alegar superioridade já demonstrada.'''+s[b:]
# Current results lead, then preserved detail of objectives and UI.
a=s.index('O resultado central é um protótipo funcional');b=s.index('\n\n',a)
s=s[:a]+r'''O resultado central é o fluxo web integrado de identificação do embarque, seleção do destino, comparação de alternativas e leitura dos trechos e transferências. A ampliação ARTESP permite aplicá-lo aos ônibus metropolitanos de Mauá em conexão com a ferrovia. Essa entrega técnica é distinta da apreciação profissional favorável e da hipótese de reduzir esforço. O objetivo geral foi parcialmente atendido: a implementação e as avaliações qualitativas estão documentadas; o benefício aos passageiros ainda não foi mensurado. A Tabela~\ref{tab:objetivos-atendimento} delimita o atendimento aos objetivos, sem equiparar implementação, cobertura integral e benefício comprovado.'''+s[b:]
s=s.replace('\\input{artesp_resultados_20261102.tex}','\\input{revisao-tecnico-cientifica-2026-11-02/dados-e-desempenho.tex}\n\\input{artesp_resultados_20261102.tex}\n\\input{revisao-tecnico-cientifica-2026-11-02/mapa-e-captura.tex}')
# Remove duplicated numerical summary; reference new explicit results instead.
a=s.index('\\begin{table}',s.index('\\label{fig:print-qr-atual}'))
# only remove the table carrying synthesis label, not preceding others
lab=s.index('\\label{tab:sintese-20261101}');a=s.rfind('\\begin{table}',0,lab);b=s.index('\\end{table}',lab)+len('\\end{table}')
s=s[:a]+r'\label{tab:sintese-20261101}A síntese quantitativa atual é apresentada nas Seções~\ref{sec:cobertura-revisada} e~\ref{sec:desempenho-revisado}, separando cobertura estrutural de latência e de operação. O detalhamento histórico de parâmetros permanece no Apêndice~\ref{ap:rotas}.'+s[b:]
# Remove obsolete TODOs from current synthesis, not historic evidence.
s=re.sub(r'% TODO-BENCHMARK:[^\n]*\n','',s)
# Update vague scope in legacy prose; municipal integration still pending.
s=s.replace('No cenário de Mauá, o acesso a esses dados ainda não está confirmado.', 'Para a totalidade dos ônibus municipais de Mauá, o acesso operacional a esses dados ainda não está confirmado; a ampliação metropolitana ARTESP está descrita na Seção~\\ref{sec:artesp-maua}.')
s=s.replace('\\chapter{Considerações finais}','\\input{revisao-tecnico-cientifica-2026-11-02/validade.tex}\n\n\\chapter{Considerações finais}')
a=s.index('\\chapter{Considerações finais}')+len('\\chapter{Considerações finais}');b=s.index('\\postextual',a)
s=s[:a]+r'''
A pergunta de pesquisa foi como apoiar a pessoa no ponto de ônibus a reconhecer alternativas para chegar ao destino sem conhecer previamente as linhas ou a identificação da parada. O PaP responde tecnicamente com uma aplicação web que integra identificação contextual do embarque, escolha por destino, comparação de alternativas e visualização dos trechos e transferências, sem instalação obrigatória. A contribuição está nesse encadeamento implementado e documentado; não na alegação de novidade de QR Code, favoritos ou planejamento por destino, já presentes em outras soluções.

A escuta da gestão de Mauá delimitou o problema e as condições de acesso aos dados. O demonstrador histórico permaneceu separado da implementação com GTFS da SPTrans e Olho Vivo. Em 2 de novembro, a integração ARTESP ampliou a aplicação ao contexto metropolitano de Mauá: 337 paradas, 16 linhas ou variantes e 705, 427 e 359 viagens programadas distintas nos dias de referência, além de conexões com a ferrovia. O mapa e a captura de ônibus 157 com Linha 10 documentam cadastro e funcionamento do planejamento, sem comprovar execução da viagem, integração de todos os ônibus municipais ou cobertura da população.

Os resultados técnicos são mensuráveis, mas têm universos diferentes. O censo de 1 de novembro encontrou 99,666\% de cobertura estrutural dos pares anteriores à ARTESP. No benchmark local, entre 1.637 sucessos pareados, a mediana aumentou de 0,282 para 0,599 s, o P95 caiu de 5,698 para 5,143 s e o máximo de 10,712 para 5,936 s. A melhora da cauda coexistiu com regressão da mediana e não ocorreu uniformemente nos estratos. Os arquivos individuais sustentam essas descrições, sem demonstrar causalidade técnica, latência completa no celular ou benefício de usabilidade.

A apreciação da Alameda Solutions sobre as versões de outubro e os relatos exploratórios contribuíram para a revisão da clareza, do controle e da prevenção de erros. O parecer assinado foi preservado e sua procedência distinguida da consolidação editorial; alterações de novembro não são atribuídas ao avaliador. As decisões implementadas são coerentes com os princípios de IHC discutidos, conforme a matriz da Seção~\ref{sec:validade}, mas coerência de projeto e avaliação qualitativa não substituem resultados empíricos com passageiros.

O objetivo geral foi, portanto, parcialmente alcançado. Há solução funcional, integração de fontes e evidências técnicas e qualitativas; não há demonstração empírica de redução do esforço, da espera ou dos erros dos passageiros. Também não foi comprovada a leitura física do QR pelo protocolo proposto. Os limites internos, externos, de construção, atualização, reprodução e participação estão reunidos na Seção~\ref{sec:ameacas-validade}.

A continuidade deve priorizar tarefas consentidas com passageiros, registro físico da leitura do QR, validação de acessos e cadastro com os responsáveis locais e medição da cadeia completa no celular. A atualização de calendários, a investigação dos pares sem cobertura, a limpeza independente da coleta e o tratamento das exportações de pesquisa também permanecem necessários. A eventual implantação da sinalização depende de autorização e manutenção. A contribuição à comunidade é uma solução verificável e uma base para essa avaliação; seu impacto efetivo permanece uma questão aberta, a ser respondida com evidências de uso.

'''+s[b:]
# Abstract, max 250 words excluding bibliographic identification.
a=s.index('Este trabalho apresenta o Ponto a Ponto');b=s.index('\\textbf{Palavras',a) if '\\textbf{Palavras' in s[a:] else -1
if b<0:
 b=s.index('\\vspace',a)
old=s[a:b];print('ABSTRACT END',old[-100:])
abstract=r'''Este trabalho apresenta o Ponto a Ponto (PaP), aplicação web do Projeto Integrador em Computação II da UNIVESP. O objetivo é apoiar a identificação do embarque e a escolha do deslocamento sem conhecimento prévio das linhas. A contribuição integra acesso contextualizado por QR Code, planejamento por destino, comparação de alternativas e visualização de transferências no navegador. A metodologia reúne escuta da gestão de Mauá, pesquisa documental, análise de serviços, prototipação, auditorias de dados, testes técnicos, benchmarks, apreciação profissional e navegações exploratórias. O demonstrador histórico de Mauá utiliza simulação identificada; a implementação funcional combina SPTrans, ferrovia e ARTESP. A auditoria metropolitana confirmou 337 paradas ARTESP em Mauá, 16 linhas ou variantes e 705, 427 e 359 viagens programadas distintas nos dias examinados. O censo anterior à ampliação encontrou cobertura estrutural de 99,666\% dos pares, sem garantir viagens em todos os horários. Entre 1.637 sucessos pareados do benchmark local, a mediana aumentou de 0,282 para 0,599 s, enquanto o percentil 95 caiu de 5,698 para 5,143 s. A apreciação externa foi favorável às versões examinadas em outubro; não abrange alterações posteriores. O projeto entrega uma solução funcional e evidências técnicas rastreáveis, mas não demonstra redução empírica do esforço dos passageiros. Avaliação sistemática por tarefas, leitura física do QR, validação operacional e manutenção dos dados permanecem necessárias.
\par\medskip
'''
s=s[:a]+abstract+s[b:]
# Glossary appended before end of description nearest appendices.
pos=s.index('\\begin{apendicesenv}');a=s.rfind('\\end{description}',0,pos)
s=s[:a]+r'''
\item[ARTESP] Agência de Transporte do Estado de São Paulo; fonte do cadastro e da programação metropolitana incorporados em 2 de novembro. Não é a fonte de previsões Olho Vivo.
\item[Cobertura cadastral, estrutural, temporal e operacional] Níveis distintos: presença no cadastro; existência de conexão modelada; viabilidade em uma data e horário; disponibilidade observada ou informada pela operação. Ver Tabela~\ref{tab:niveis-cobertura}.
\item[Diferença pareada] Tempo depois menos tempo antes para a mesma consulta com sucesso nas duas versões. Valor negativo indica menor tempo; não identifica sua causa.
\item[Distribuição acumulada empírica] Fração das observações com valor menor ou igual a um limiar; deriva dos valores individuais, sem supor uma distribuição teórica.
\item[Mediana e percentil 95 (P95)] Medidas de posição da distribuição. O P95 utiliza nesta análise a convenção do instrumento original, explicitada na Seção~\ref{sec:desempenho-revisado}; máximo é apenas o maior valor observado.
\item[Sucesso pareado] Consulta que retornou primeira rota nas duas versões comparadas; não significa que a rota foi realizada por um passageiro.
\item[Viagem programada distinta] Registro de viagem GTFS contado uma vez no dia de serviço, independentemente de quantas paradas atravessa. Não equivale a veículo único ou viagem observada.
\item[Validade de construção] Correspondência entre a medida utilizada e o conceito que se deseja avaliar; por exemplo, contagem de cliques não mede sozinha esforço ou compreensão.
'''+s[a:]
p.write_text(s)
# Fix stale evidence claim in technical appendix without altering original captured files.
p=r/'atualizacao_20261101.tex';s=p.read_text();s=s.replace('Não foi selecionada aqui evidência visual de uma viagem com trecho de ônibus combinado a trilhos; essa captura específica permanece pendente.','Nesse registro de 1 de novembro não foi selecionada evidência visual de ônibus combinado a trilhos. A captura posterior de 2 de novembro, já existente no acervo, é apresentada na Figura~\\ref{fig:artesp-onibus-trem}; os instantes e os escopos das consultas permanecem distintos.');p.write_text(s)
# Provenance: do not touch any signed PDF/DOCX or authorization.
p=r/'avaliacoes_externas/alameda_solutions/comunicacao_thiago.tex';s=p.read_text();a=s.index('O parecer disponível no acervo está');b=s.index('\\endgroup',a)
s=s[:a]+r'''A procedência distingue quatro conjuntos preservados: (1) os arquivos preparatórios \nolinkurl{Registro_feedback_Thiago_Alameda_Solutions.docx} e PDF, no diretório principal; (2) o documento recebido em \nolinkurl{documento_recebido_2026-10-26/}; (3) o documento confirmado \nolinkurl{documento_confirmado_2026-10-26/Registro_feedback_Thiago_Alameda_Solutions_confirmado.pdf}, que é o arquivo efetivamente reproduzido no Anexo~\ref{an:parecer-thiago}; e (4) a autorização posterior \nolinkurl{autorizacao_reutilizacao_assinatura.pdf}, preservada nesse último diretório. A autorização contém uma referência a ``4 procedimentos'', sem enumerá-los no texto do próprio documento; esta revisão não amplia seu alcance. Nenhuma assinatura foi reutilizada ou modificada. O anexo confirmado é mantido integralmente como já constava da versão de referência, sem ser apresentado como novo parecer emitido nesta revisão. As mudanças técnicas de novembro, inclusive ARTESP e medições, são verificações do grupo e não integram retroativamente a avaliação de 21 ou 25 de outubro.
'''+s[b:];p.write_text(s)
# Brief build README; historical sections untouched.
p=r/'README.md';p.write_text('''# Revisão técnico-científica — 2 de novembro de 2026

Fonte ativa: `relatorio_final_pi2_v2.tex`. A revisão editorial e sua validação estão em `revisao-tecnico-cientifica-2026-11-02/`. Veja `AUDITORIA.md`, `ALTERACOES.md` e `VALIDACAO.md` nesse diretório para escopo, evidências, resultados e pendências.

Referência Git original (inclui alterações locais): `refs/auditoria/relatorio-20261102-original-tecnico-cientifica`. É uma referência a árvore, sem novo commit. Exemplo de consulta: `git show refs/auditoria/relatorio-20261102-original-tecnico-cientifica:docs/relatorio_final/relatorio_final_pi2_v2.tex`.

Compilar o fonte ativo com LuaLaTeX em **diretório novo**, evitando o hook histórico de exportação automática:

```sh
latexmk -norc -lualatex -interaction=nonstopmode -halt-on-error -outdir=/tmp/pap-relatorio-build-NOVO relatorio_final_pi2_v2.tex
```

As referências de entrega e os comandos abaixo são registros históricos; não substituem a identificação da revisão acima. O link definitivo do vídeo na capa continua pendente.

---

'''+p.read_text())
print('Edited report and created editorial modules; historical artifacts preserved.')
