from pathlib import Path
import json,re
r=Path('/home/avale/Projetos/maua_bus_map-relatorio');d=r/'docs/relatorio_final';a=d/'revisao-editorial-2026-11-02';changes=[]
p=d/'relatorio_final_pi2_v2.tex';s=p.read_text()
def replace(old,new,why):
 global s
 assert s.count(old)==1,(why,s.count(old));s=s.replace(old,new);changes.append({'reason':why,'before':old,'after':new})
replace(r'\hypersetup{hypertexnames=false,hidelinks}',r'''% Metadados bibliográficos; nomes e data documental preservados.
\hypersetup{
  hypertexnames=false,hidelinks,unicode=true,
  bookmarksnumbered=true,pdfdisplaydoctitle=true,
  pdftitle={Sistema de acesso a informações do transporte público por QR Code em pontos de ônibus},
  pdfauthor={André Meneghelli Vale; Ariana Harumi Uemura; Bruno Gabriel Migliari de Souza; Caio Wellington Procopio Ferreira; Ingrid Emanuelle Sousa Dias; Leonardo Souza Leite; Maurício Gonçalves Marques; Nathalia Almeida Amorim},
  pdfsubject={Relatório Técnico-Científico Final — Projeto Integrador em Computação II — UNIVESP — 2026},
  pdfkeywords={transporte público; QR Code; informação ao passageiro; mobilidade urbana; pontos de interesse}
}
% Compressão sem perdas dos fluxos e objetos; não altera as evidências.
\pdfvariable compresslevel=9
\pdfvariable objcompresslevel=3''','Preencher metadados, numerar marcadores e comprimir fluxos sem perdas')
replace('\\end{resumo}\n% Ajuste local',r'''\end{resumo}
% O modelo institucional prevê estas duas listas opcionais. Abstract não está
% previsto nesse modelo; a exigência institucional permanece a confirmar.
\begingroup
\SingleSpacing
\setlength{\beforechapskip}{0pt}
\setlength{\afterchapskip}{12pt}
\renewcommand{\listfigurename}{Lista de figuras}
\pdfbookmark[0]{Lista de figuras}{listafiguras}
\listoffigures*
\clearpage
\pdfbookmark[0]{Lista de tabelas}{listatabelas}
\listoftables*
\cleardoublepage
\endgroup
% Ajuste local''','Incluir listas opcionais autorizadas pelo modelo, sem inclusão automática de abstract')
start=s.index('Uma vez organizadas as paradas e as viagens,')
end=s.index('Separar preparação e consulta permite',start)
replace(s[start:end],r'''Grafos representam paradas e conexões por vértices e arestas. Dijkstra encontra caminhos de menor custo com pesos não negativos; no transporte, a avaliação temporal deve compatibilizar calendários, partidas, espera e transferências \citep{sedgewicksp,dijkstra1959,bast2015,transitplanner}. No demonstrador de Mauá, busca-se a chegada mais cedo com os tempos fornecidos, sem previsão autônoma de atrasos; parâmetros e limites estão na Seção~\ref{sec:implementar-testar}.

O RAPTOR organiza a busca por rodadas associadas às transferências \citep{delling2012}, referência conceitual do planejador inicial do PaP, mantido como alternativa. O CSA utiliza varredura de conexões temporais \citep{dibbelt2018}. No PaP, conexão também designa uma estrutura reutilizável de percurso e não implica adoção do CSA.

''','2.3: reunir explicações repetidas sobre grafos, horários e Dijkstra, mantendo todas as citações e limites')
start=s.index('O planejamento do percurso pressupõe que a origem esteja identificada.')
end=s.index('\\clearpage',start)
replace(s[start:end],r'''O QR Code pode identificar a origem por um endereço vinculado à parada. Em Southampton, códigos únicos foram instalados em 44 pontos para consultar chegadas \citep{southampton}; a SPTrans documentou sua adoção junto à sinalização física em 2014 \citep{qrsptrans2014}. A orientação daquela notícia para instalar um aplicativo referia-se ao leitor do código. No PaP, o acesso contextualizado abre a consulta no navegador, sem cadastro obrigatório nem aplicativo específico do projeto, mas depende de leitor de QR Code e conexão à internet. O fluxo implementado é apresentado na Seção~\ref{sec:fluxo-implementado}.

''','2.3: condensar explicação do QR já detalhada no fluxo, mantendo os antecedentes e requisitos de acesso')
start=s.index('\\clearpage\nA captura (Figura~\\ref{fig:olho-vivo-lista-extensa})')
end=s.index('\\clearpage\nNo fluxo observado, o acesso',start)
replace(s[start:end],r'''A consulta de várias linhas (Figura~\ref{fig:olho-vivo-previsoes}) também motiva a hipótese de sobrecarga visual, ainda não avaliada com passageiros. O registro complementar de uma lista extensa permanece no acervo, em \nolinkurl{imgs/olho_vivo7.png}; sua reprodução adicional foi dispensada por reiterar essa característica. A filtragem por destino proposta pelo PI deverá ser avaliada quanto à seleção das alternativas relevantes.

''','2.3: retirar apenas a reprodução complementar da lista extensa, redundante com a consulta mult linhas; original e hipótese preservados')
start=s.index('As capturas foram realizadas em 22 e 23 de outubro de 2026,')
end=s.index('\\begin{figure}',start)
replace(s[start:end],r'''As capturas documentam a aplicação local em desenvolvimento, não uma avaliação por participantes externos. Em 22 de outubro de 2026, o registro identifica o commit \texttt{aee66eb} e alterações locais: Chromium, tema escuro, emulação móvel de 430 por 932 pixels, densidade 2, localização simulada no Butantã e favoritos preparados. Foram usados serviços reais de transporte; somente a telemetria foi interceptada no navegador. A procedência está em \nolinkurl{capturas/2026-10-22/registro.json}.

Em 23 de outubro, contextos novos sem localização autorizada conferiram o fluxo (\nolinkurl{capturas/2026-10-23/procedencia.json}). Entrada e acompanhamento foram recapturados após alterações do consentimento e dos percursos, escolhendo não contribuir com a pesquisa e sem substituir respostas de transporte. Foram mantidas as dimensões móveis; para a linha 6L10-41, usou-se 1366 por 1000 pixels, também com densidade 2. Roteiro, horários e hashes estão em \nolinkurl{capturas/2026-10-23-rotas/}.

Em 25 de outubro, na revisão \texttt{85417bc}, foram recapturados entrada, navegação sem localização, configurações de pesquisa, feedback e linha 6L10-41. Os registros estão em \nolinkurl{capturas/2026-10-25/}; a procedência das cinco recapturas complementares sem substituição de respostas nem retoque está em \nolinkurl{capturas/2026-10-25-sem-aviso/}. Cada figura mantém sua data e cenário; as demais telas continuam identificadas como históricas.

''','3.1: consolidar procedência sem perder revisões, datas, dimensões, simulação, interceptação e caminhos dos manifestos')
start=s.rfind('\\begin{figure}',0,s.index('{capturas/2026-10-22/pap-05-viagem-completa.png}'))
end=s.index('\\clearpage',s.index('O seletor de trechos permite',start))+len('\\clearpage')
replace(s[start:end],r'''\begin{figure}[H]\centering
\begin{minipage}[t]{0.48\textwidth}\centering\vspace{0pt}
\includegraphics[width=\linewidth,height=0.68\textheight,keepaspectratio]{capturas/2026-10-22/pap-05-viagem-completa.png}
\caption{Viagem completa, com embarque, baldeação e destino.}\label{fig:print-05-viagem-completa}
\end{minipage}\hfill
\begin{minipage}[t]{0.48\textwidth}\centering\vspace{0pt}
\includegraphics[width=\linewidth,height=0.68\textheight,keepaspectratio]{capturas/2026-10-22/pap-06-ultimo-trecho.png}
\caption{Visualização do último trecho da viagem selecionada.}\label{fig:print-06-ultimo-trecho}
\end{minipage}
\fonte{Capturas da aplicação em emulação móvel, 22 out. 2026.}
\end{figure}
A rota selecionada é representada no mapa, cuja legenda distingue ônibus e caminhada. O controle inferior permite retornar à lista ou examinar um trecho, inclusive a parte final, mantendo a referência da viagem escolhida.
\clearpage''','3.1: colocar viagem completa e último trecho lado a lado, preservando as duas capturas, legendas e rótulos')
p.write_text(s)
p=d/'revisao-tecnico-cientifica-2026-11-02/notas-historicas.tex';old=p.read_text();ps=old.split('\n\n')
news={
1:r'''A extensão de São Paulo, examinada na revisão \texttt{4992027}, de 7 de outubro de 2026, acrescentou GTFS/SPTrans e consultas ao Olho Vivo quando havia correspondência de linha e parada. Esse registro histórico não equivale ao fornecimento de dados operacionais de Mauá nem confunde programação com previsão em tempo real.''',
2:r'''O fluxo de origem, destino, favoritos e resultados progressivos está documentado na Seção~\ref{sec:fluxo-implementado}. Na revisão histórica, o mapa iniciava no passageiro, com raio mínimo de 250 m no menor eixo e ação de recentralização. Coordenadas simuladas configuráveis substituíam o GPS nos cenários de reprodução; sem elas, utilizava-se a localização autorizada pelo navegador.''',
3:r'''O toque prolongado de aproximadamente 0,65 segundo selecionava coordenadas segundo a tarefa ativa (origem ou destino), cancelando a seleção em arrastos ou gestos com dois dedos. O cálculo incluía as caminhadas de acesso. As regras de alteração do embarque, confirmação de cancelamento e preservação de favoritos e enquadramento estão documentadas na Seção~\ref{sec:fluxo-implementado} e no Apêndice~\ref{ap:engenharia}. Fechar o painel apenas mudava a visualização.''',
4:r'''A ampulheta sinalizava o cálculo; ao concluir, o recálculo manual ignorava o cache. A busca não reiniciava automaticamente a cada 30 segundos nem a cada atualização do GPS: a atualização periódica pertencia à consulta de próximos ônibus. Nessa consulta, frequência significava intervalo entre veículos e faixa de vigência, com união de faixas consecutivas iguais, não contagem regressiva. A identidade visual própria mantinha a identificação das fontes na documentação e na aplicação.''',
5:r'''A distinção entre o demonstrador simulado de Mauá, a implementação funcional, a apreciação profissional de outubro e as verificações posteriores é retomada no capítulo de resultados. O fluxo técnico implementado não comprova redução do esforço do passageiro; essa avaliação permanece pendente. A comparação com Cittamobi, QRCodeAdesivo e Olho Vivo está na fundamentação e não estabelece superioridade do PaP. Mockups anteriores são registros de prototipação, não evidências da solução final.''',
6:None,7:None,
14:r'''A arquitetura React/Leaflet, Django/Python e SQLite é apresentada na Figura~\ref{fig:arquitetura-pap}; o índice GTFS, separado dos modelos Django históricos de Mauá, na Figura~\ref{fig:banco-mbm}. A evolução concorrente de 1 de novembro está na Seção~\ref{sec:atualizacao-20261101}. Cobertura e desempenho são sintetizados nas Seções~\ref{sec:cobertura-revisada} e~\ref{sec:desempenho-revisado}; essas medições locais não substituem o protocolo controlado proposto.''',
15:None,16:None,17:None}
for i,new in news.items():changes.append({'reason':f'Apêndice C, parágrafo {i}: condensação/remissão; detalhes únicos e relatos externos mantidos','before':ps[i],'after':new or ''});ps[i]=new
p.write_text('\n\n'.join(x for x in ps if x is not None))
(a/'alteracoes-textuais.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2));print('Aplicadas',len(changes),'alterações localizadas; E.2 preservada por conter contratos e protocolo necessários.')
