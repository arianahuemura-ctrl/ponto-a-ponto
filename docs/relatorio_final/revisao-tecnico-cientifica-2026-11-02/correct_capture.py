from pathlib import Path
r=Path('/home/avale/Projetos/maua_bus_map-relatorio/docs/relatorio_final');o=r/'revisao-tecnico-cientifica-2026-11-02'
p=o/'mapa-e-captura.tex';t=p.read_text().replace('auditoria-apresentacao-artesp-2026-11-02/','auditoria-artesp-maua-2026-11-02/')
t=t.replace(r'\includegraphics[width=\textwidth]{auditoria-artesp-maua-2026-11-02/captura-maua-bras-consulta.png}',r'\includegraphics[width=\textwidth,trim=520bp 130bp 520bp 130bp,clip]{auditoria-artesp-maua-2026-11-02/captura-maua-bras-consulta.png}')
t=t.replace('Mesma sessão de captura da Figura~','Recorte ampliado do painel da mesma sessão da Figura~').replace('O aviso de busca parcial faz parte da evidência e foi mantido.','O aviso de busca parcial, visível no painel da Figura~\\ref{fig:artesp-consulta-detalhe}, faz parte da evidência e foi mantido.')
t=t.replace('Eixos em aproximação métrica local;', 'Eixos em aproximação métrica local, origem em $(-23{,}67; -46{,}45)$;')
p.write_text(t)
p=o/'AUDITORIA.md';p.write_text(p.read_text()+'''\n## Conferência das duas sessões de captura\n\nA inspeção visual encontrou duas sessões distintas para Oscarito–Brás: `auditoria-artesp-maua-2026-11-02/live-capture.json` registra 02h19, chegada às 06h26 e aviso de busca parcial; `auditoria-apresentacao-artesp-2026-11-02/live-capture.json` registra 02h52, mesma chegada e busca ainda em andamento. Foram selecionadas as imagens da primeira sessão, coerentes com a consulta já descrita no relatório original. As imagens das 02h52 não foram usadas como evidência das 02h19. Os dois conjuntos permanecem preservados.\n''')
