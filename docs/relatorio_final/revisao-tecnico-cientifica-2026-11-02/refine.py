from pathlib import Path
import re,unicodedata
r=Path('/home/avale/Projetos/maua_bus_map-relatorio/docs/relatorio_final');o=r/'revisao-tecnico-cientifica-2026-11-02'
p=r/'relatorio_final_pi2_v2.tex';s=p.read_text()
# Objective states integration and separates hypothesis from execution. Preserve letters a-i.
a=s.index('Desenvolver e avaliar um protótipo web');b=s.index('\n\n',a)
s=s[:a]+r'Desenvolver e avaliar uma aplicação web que integre identificação da parada por QR Code, escolha por destino, comparação de alternativas e visualização de transferências, sem instalação obrigatória ou conhecimento prévio das linhas. Investigar a hipótese de redução do esforço, distinguindo dados cadastrados, programação, previsão operacional e simulação identificada.'+s[b:]
s=s.replace(r'\papsubsection*{Objetivo geral}',r'\noindent\textbf{Objetivo geral}\par').replace(r'\papsubsection*{Objetivos específicos}',r'\noindent\textbf{Objetivos específicos}\par')
s=s.replace(r'\begin{enumerate}[label=\alph*)]',r'\begin{enumerate}[label=\alph*),itemsep=2pt,parsep=0pt]')
s=s.replace('eliminando entradas e etapas desnecessárias','evitando entradas repetidas')
# Avoid duplicate introductory statements and ambiguous retrospective scope.
a=s.index('O projeto denomina-se');b=s.index('\n\n',a)
s=s[:a]+r'O nome Ponto a Ponto expressa o apoio desde a identificação do embarque até a leitura do destino e das eventuais trocas. Trata-se de um propósito de projeto: os benefícios deverão ser avaliados com a comunidade.'+s[b:]
s=s.replace('A implementação funcional do PaP utiliza dados de São Paulo, provenientes do GTFS da SPTrans e da API Olho Vivo, além de serviços geográficos complementares. Neste relatório, essa configuração é denominada cenário São Paulo. A implementação técnica não equivale à validação com a comunidade.', 'A implementação original, denominada cenário São Paulo, utiliza GTFS da SPTrans e API Olho Vivo, com serviços geográficos complementares. A integração ARTESP ampliou posteriormente o planejamento para Mauá, preservando a separação das fontes e da simulação histórica.')
s=s.replace('Favoritos já são armazenados no navegador, sem conta nem sincronização entre dispositivos. O acesso inicial pelo QR Code permanece independente dessa personalização.', 'Favoritos locais são opcionais, sem conta ou sincronização entre dispositivos.')
# Preserve long descriptive history in appendix; leave primary results focused.
a=s.index('A apresentação conserva os registros históricos');b=s.index('\\input{revisao-tecnico-cientifica-2026-11-02/dados-e-desempenho.tex}',a)
history=s[a:b]
history=re.sub(r'A Tabela~\\ref\{tab:sintese-20261101\}.*?(?=\n\n)',r'A síntese quantitativa está nas Seções~\\ref{sec:cobertura-revisada} e~\\ref{sec:desempenho-revisado}; o protocolo controlado histórico não equivale às medições locais de 1 de novembro.',history,flags=re.S)
history=history.replace(r'\label{tab:sintese-20261101}','')
s=s[:a]+r'As capturas preservam as versões e os cenários indicados em suas fontes. O detalhamento da evolução, da interlocução e das propostas de continuidade está no Apêndice~\ref{ap:notas-historicas}; os resultados quantitativos atuais são apresentados a seguir.'+'\n\n'+s[b:]
a=s.index('Como possibilidade de trabalho futuro');b=s.index('Durante o desenvolvimento, os responsáveis pela implementação',a)
future=s[a:b]
s=s[:a]+r'\section{Avaliação, participação e privacidade}\label{sec:avaliacao-privacidade}'+'\n'+s[b:]
(o/'notas-historicas.tex').write_text(r'\chapter{Evolução e propostas de continuidade}\label{ap:notas-historicas}'+'\n'+r'Os registros a seguir preservam a evolução descrita no relatório de referência, com suas datas e fontes. Propostas de integração, relatos de lotação e análises de intenção de viagem não são funcionalidades entregues. As sínteses atuais estão no capítulo de resultados e os limites na Seção~\ref{sec:validade}.'+'\n\n'+history+'\n'+future)
s=s.replace(r'\input{revisao-tecnico-cientifica-2026-11-02/protocolo-qr.tex}',r'\input{revisao-tecnico-cientifica-2026-11-02/protocolo-qr.tex}'+'\n'+r'\input{revisao-tecnico-cientifica-2026-11-02/notas-historicas.tex}')
# A section for the implemented interface. Heading gets its required page break.
needle='A Figura~\\ref{fig:fluxo-pap}'
if needle in s:s=s.replace(needle,r'\section{Fluxo implementado e evidência visual}\label{sec:fluxo-implementado}'+'\n'+needle,1)
# Repair hard-coded references after appendix reorganization.
s=s.replace('em B.2',r'na Seção~\ref{sec:historico-arquitetura}')
s=s.replace(r'Seção~\ref{sec:escuta-comunidade}',r'Apêndice~\ref{ap:percurso-metodologico}')
# Bibliography alphabetization, preserving each entry verbatim.
a=s.index('\\bibitem');b=s.index('\\end{thebibliography}',a);entries=re.split(r'(?=\\bibitem)',s[a:b]);entries=[e for e in entries if e.strip()]
def key(e):
 text=e.split('} ',1)[1] if '} ' in e else e
 return unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().casefold()
s=s[:a]+''.join(sorted(entries,key=key))+s[b:]
# Alphabetize expanded glossary, no textual changes.
a=s.index('\\begin{description}',s.index('\\chapter*{Glossário}'));b=s.index('\\end{description}',a)
chunk=s[a:b]; first=chunk.index('\\item[');items=re.split(r'(?=\\item\[)',chunk[first:]);items=[i for i in items if i.strip()]
s=s[:a]+chunk[:first]+''.join(sorted(items,key=lambda e:unicodedata.normalize('NFKD',e.split(']')[0]).encode('ascii','ignore').decode().casefold()))+s[b:]
p.write_text(s)
# Ragged-right new tables avoid stretched/hyphenated narrow cells.
for n in ['comparacao.tex','metodologia.tex','dados-e-desempenho.tex','validade.tex']:
 p=o/n;t=p.read_text();t=re.sub(r'(?<!\})p\{([0-9.]+cm)\}',r'>{\\raggedright\\arraybackslash}p{\1}',t);p.write_text(t)
# Shorter appendix title avoids TOC overflow.
p=o/'percurso-metodologico.tex';t=p.read_text().replace('Percurso metodológico, decisões e protocolos','Percurso metodológico detalhado');p.write_text(t)
# Avoid a heading-only page and move duplicated privacy limitations to an explicit cross-reference.
p=o/'validade.tex';t=p.read_text().replace(r'\subsection{Relação entre princípios e evidências}','');a=t.index(r'\textbf{Privacidade e gestão dos registros.}');t=t[:a]+r'\textbf{Privacidade.} A Seção~\ref{sec:avaliacao-privacidade} distingue retenção implementada, exportações e limites da exclusão. Não se conclui anonimato ou conformidade legal integral.'+'\n';p.write_text(t)
# More compact coverage interpretation, preserving full details in technical appendix.
p=o/'dados-e-desempenho.tex';t=p.read_text();a=t.index('Dos 1.657.654 pares');b=t.index('\\section{Desempenho',a)
t=t[:a]+r'''Dos 1.657.654 pares sem materialização, as regras examinadas explicam 1.313.444; 344.210 permanecem sem causa esclarecida. São 50 origens de término de viagens bloqueadas pela política inicial de acesso, embora tenham caminhada externa verificada, e nove destinos: oito excedem o encaixe pedestre de 20 m e um excede a caminhada de 1.000 m. Não se comprovou erro do GTFS nem inacessibilidade física. Distâncias, identificadores e procedimentos estão na Seção~\ref{sec:atualizacao-20261101}.

'''+t[b:]
# Put aggregate table and population explanation before the tall figure.
a=t.index('\\begin{figure}');b=t.index('\\begin{table}',a);fig_and_analysis=t[a:b];table_and_end=t[b:];t=t[:a]+table_and_end+'\n'+fig_and_analysis;p.write_text(t)
# Fix references without guessing new appendix letters.
p=r/'planejador_hibrido.tex';t=p.read_text().replace(r'\section{Registro histórico da arquitetura em 28 de outubro}',r'\section{Registro histórico da arquitetura em 28 de outubro}\label{sec:historico-arquitetura}');t=t.replace('em B.1',r'na Seção~\ref{sec:atualizacao-20261101}').replace('dados de B.1',r'dados da Seção~\ref{sec:atualizacao-20261101}').replace('conforme B.2',r'conforme a Seção~\ref{sec:historico-arquitetura}');p.write_text(t)
p=r/'feedbacks_20261029.tex';t=p.read_text().replace('no Apêndice B.2',r'na Seção~\ref{sec:historico-arquitetura}');p.write_text(t)
# Full-width comparison figures, preserving original raster bytes and dated content.
p=r/'legibilidade_ferroviaria_20261102.tex';t=p.read_text();a=t.index('\\begin{figure}');b=t.index('\\end{figure}',a)+len('\\end{figure}')
t=t[:a]+r'''\begin{figure}[H]\centering
\includegraphics[width=\textwidth]{auditoria-apresentacao-artesp-2026-11-02/capturas/light.png}
\caption{Legibilidade ferroviária no tema claro, na versão registrada em 2 de novembro.}\label{fig:contraste-ferroviario}
\fonte{Captura original do grupo, 2 nov. 2026; lâmpada apagada e mapa em tons de cinza na versão examinada.}
\end{figure}
\begin{figure}[H]\centering
\includegraphics[width=\textwidth]{auditoria-apresentacao-artesp-2026-11-02/capturas/dark.png}
\caption{Legibilidade ferroviária no tema escuro, na mesma revisão de interface.}\label{fig:contraste-ferroviario-escuro}
\fonte{Captura original do grupo, 2 nov. 2026; apresentação ampliada sem alteração dos pixels da evidência.}
\end{figure}'''+t[b:]
t=t.replace('A implementação preservou','Na versão registrada nas capturas, a implementação preservou').replace('A Figura~\\ref{fig:contraste-ferroviario} documenta o estado posterior da interface','As Figuras~\\ref{fig:contraste-ferroviario} e~\\ref{fig:contraste-ferroviario-escuro} documentam o estado daquela revisão da interface');p.write_text(t)
# Existing QRCodeAdesivo tall screenshot: add readable crop, clearly identified, no synthetic pixels.
p=r/'relatorio_final_pi2_v2.tex';s=p.read_text();needle='\\label{fig:sptrans-parada}';a=s.index('\\end{figure}',s.index(needle))+len('\\end{figure}')
addition=r'''
\begin{figure}[H]\centering
\includegraphics[width=.9\textwidth,trim=0 840bp 0 0,clip]{qrcodeadesivo.extapps.sptrans.com.br-QRCodeAdesivo-adesivo.png}
\caption{Detalhe ampliado do cabeçalho e dos primeiros acessos por linha no QRCodeAdesivo.}\label{fig:adesivo-detalhe}
\fonte{Recorte editorial da mesma captura da Figura~\ref{fig:sptrans-parada}; arquivo original preservado, sem reconstrução da interface.}
\end{figure}
'''
# Crop size will be confirmed against raster metadata before insertion.
from PIL import Image
im=Image.open(r/'imgs/qrcodeadesivo.extapps.sptrans.com.br-QRCodeAdesivo-adesivo.png');print('QR IMAGE',im.size)
# Native pixels used by graphicx as bp for PNG without dpi metadata.
w,h=im.size;bottom=int(h*.68);addition=addition.replace('840bp',str(bottom)+'bp')
s=s[:a]+addition+s[a:];p.write_text(s)
print('Layout and cross-reference refinements applied.')
