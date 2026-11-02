from pathlib import Path
import re
r=Path('/home/avale/Projetos/maua_bus_map-relatorio/docs/relatorio_final');o=r/'revisao-tecnico-cientifica-2026-11-02'
p=r/'relatorio_final_pi2_v2.tex';s=p.read_text();s=s.replace(r'\renewcommand{\ABNTEXchapterfontsize}{\normalsize}',r'''\renewcommand{\ABNTEXchapterfontsize}{\normalsize}
% Modelo fornecido: títulos no sumário em negrito, subtítulos sem negrito.
\renewcommand{\cftsectionfont}{\normalfont}
\renewcommand{\cftsectionpagefont}{\normalfont}
\renewcommand{\cftsubsectionfont}{\normalfont}
\renewcommand{\cftsubsectionpagefont}{\normalfont}''')
# Preserve chapter/objective sharing as explicitly illustrated in template TOC.
# Repair appendix glossary scope.
s=s.replace('No cenário de Mauá, os veículos demonstrativos permanecem simulados.', 'No cenário histórico dos ônibus municipais de Mauá, os veículos demonstrativos permanecem simulados.')
s=s.replace('A extensão de São Paulo importa GTFS; isso não representa integração operacional confirmada em Mauá.', 'SPTrans e ARTESP fornecem cadastros programados; sua importação não comprova integração operacional com os ônibus municipais de Mauá.')
p.write_text(s)
# New generic service comparison based on preserved click study, without ranking unequal tasks.
p=o/'comparacao.tex';t=p.read_text();needle='PaP & Entrada contextual';idx=t.index(needle)
t=t[:idx]+r'''Google Maps e Moovit & Planejamento por destino e uso de favoritos registrados no estudo de ações em celular, em 25 e 26/10; Apêndice~\ref{ap:cliques}. & Destinos, anúncios e estados iniciais diferem. Entrada por QR físico não examinada; contagens não estabelecem superioridade geral.\\[5pt]
'''+t[idx:];p.write_text(t)
# Numbered appendix sections start a page; introductory lead-ins remain paragraphs.
p=r/'estudo_cliques.tex';t=p.read_text().replace('\\papsection{','\\section{');t=t.replace(r'\section{Procedimento e condições}',r'\section{Procedimento e condições}\label{sec:cliques-condicoes}').replace(r'\section{Resultados consolidados}',r'\section{Resultados consolidados}\label{sec:cliques-resultados}').replace(r'\section{Interpretação e alcance}',r'\section{Interpretação e alcance}\label{sec:cliques-interpretacao}');p.write_text(t)
p=r/'estudo_ihc_ampliado/protocolo.tex';t=p.read_text().replace('\\papsection{','\\section{').replace('E.1--E.3',r'as Seções~\ref{sec:cliques-condicoes} a~\ref{sec:cliques-interpretacao}');p.write_text(t)
# Avoid orphan tail in validity; remove duplication already detailed under privacy.
p=o/'validade.tex';t=p.read_text();a=t.index(r'\textbf{Privacidade.}');t=t[:a]+r'Os limites de retenção, exclusão e exportação da pesquisa estão na Seção~\ref{sec:avaliacao-privacidade}; sua implementação não comprova anonimato ou conformidade legal integral.'+'\n';p.write_text(t)
# Add reproduced detail from the SAME existing night query, not invented data.
p=o/'mapa-e-captura.tex';t=p.read_text();t=t.replace(r'\includegraphics[width=\textwidth]{auditoria-apresentacao-artesp-2026-11-02/captura-maua-bras-mapa.png}',r'\includegraphics[width=\textwidth,trim=160bp 0 160bp 0,clip]{auditoria-apresentacao-artesp-2026-11-02/captura-maua-bras-mapa.png}')
t=t.replace('A imagem original foi preservada.', 'Foram retiradas apenas as margens laterais vazias na diagramação; a imagem original foi preservada. O detalhe da alternativa está na Figura~\\ref{fig:artesp-consulta-detalhe}.')
t+=r'''
\begin{figure}[H]\centering
\includegraphics[width=\textwidth]{auditoria-apresentacao-artesp-2026-11-02/captura-maua-bras-consulta.png}
\caption{Alternativa ônibus--ferrovia e aviso de busca parcial na consulta de madrugada.}\label{fig:artesp-consulta-detalhe}
\fonte{Mesma sessão de captura da Figura~\ref{fig:artesp-onibus-trem}, em 2 nov. 2026. Programação e estimativas; não há previsão operacional ARTESP.}
\end{figure}
''';p.write_text(t)
# Avoid hidden ambiguity on historical single-run ARTESP load.
p=r/'artesp_resultados_20261102.tex';t=p.read_text().replace('com o maior valor na primeira carga da rede;','com o maior valor observado na primeira carga da rede, sem isolamento causal desse fator;');p.write_text(t)
# Document template conflict rather than silently overriding the source.
p=o/'AUDITORIA.md';p.write_text(p.read_text()+'''\n## Conferência do modelo institucional\n\nO arquivo `Modelo_Relatorio_Final.docx` pede Times New Roman 12 no corpo, margens superior/esquerda de 3 cm e inferior/direita de 2 cm, espaçamento 1,5, resumo de até 250 palavras, cinco palavras-chave, títulos à esquerda e página nova para títulos/subtítulos. O sumário de exemplo, porém, coloca “Desenvolvimento” e “Objetivos” na mesma página. A revisão conserva essa abertura conjunta ilustrada no próprio modelo, usa parágrafos em negrito para os enunciados dos objetivos e inicia as demais seções numeradas em página nova, inclusive no estudo de cliques. O sumário passa a distinguir capítulos em negrito e seções sem negrito. Esta decisão e a ambiguidade do modelo ficam registradas; confirmação institucional de preferência distinta é uma pendência externa, não uma regra genérica presumida.\n''')
print('Final layout refinements written.')
