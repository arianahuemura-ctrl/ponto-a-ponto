from pathlib import Path
import subprocess,json,hashlib,re,difflib
A=Path(__file__).resolve().parent;R=Path('/home/avale/Projetos/maua_bus_map-relatorio');D=R/'docs/relatorio_final'
def run(args):return subprocess.check_output(args,cwd=R,text=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert run(['git','branch','--show-current']).strip()=='relatorio'
assert run(['git','rev-parse','HEAD'])==(A/'head-antes.txt').read_text()
subprocess.run(['git','diff','--check'],cwd=R,check=True)
files=['relatorio_final_pi2_v2.tex','planejador_hibrido.tex','diagramas/arquitetura.tex','diagramas/sequencia.tex','relatorio_final_pi2_v2.pdf']
args=['git','diff','--binary','--','.']+[':!docs/relatorio_final/'+n for n in files]
assert subprocess.check_output(args,cwd=R)==(A/'outros-diffs-antes.patch').read_bytes()
protected=json.loads((A/'preservados.json').read_text())
for name,h in protected.items():assert sha(D/name)==h,name
old=(A/'antes/planejador_hibrido.tex').read_text();new=(D/'planejador_hibrido.tex').read_text();key='\\section{Protocolo do benchmark definitivo}'
assert old.split(key)[0]==new.split(key)[0], 'B.1/B.2 alterados'
oldseq=(A/'antes/diagramas/sequencia.tex').read_text().splitlines();newseq=(D/'diagramas/sequencia.tex').read_text().splitlines()
assert len(oldseq)==len(newseq) and all(x==y for i,(x,y) in enumerate(zip(oldseq,newseq)) if i!=4)
a=(A/'antes/relatorio_final_pi2_v2.tex').read_text();b=(D/'relatorio_final_pi2_v2.tex').read_text()
for pattern in [r'\\caption(?:\[[^\]]*\])?\{[^\n]*',r'\\begin\{table\}.*?\\end\{table\}',r'\\includegraphics[^\n]*']:
 assert re.findall(pattern,a,re.S)==re.findall(pattern,b,re.S)
log=(D/'relatorio_final_pi2_v2.log').read_text(errors='replace')
assert not re.search(r'undefined references|Reference .* undefined|Citation .* undefined|Overfull|Rerun to get|Label\(s\) may have changed',log)
p=D/'relatorio_final_pi2_v2.pdf';info=run(['pdfinfo',str(p)]);fonts=run(['pdffonts',str(p)])
assert all(re.search(r'\s+yes\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',l) for l in fonts.splitlines()[2:] if l.strip())
t=run(['pdftotext','-layout',str(p),'-']);pages=t.split('\f');assert 'Essa evolução descreve' not in pages[35]
assert 'Essa evolução descreve' in pages[36] and 'permanecem no Apêndice C' in pages[36]
assert '133 f.' in t and 'Pages:           133' in info
(A/'pdfinfo.txt').write_text(info);(A/'fontes.txt').write_text(fonts)
(A/'git-depois.txt').write_text(run(['git','status','--short']))
diff=''
for f in files[:-1]:diff+=''.join(difflib.unified_diff((A/'antes'/f).read_text().splitlines(True),(D/f).read_text().splitlines(True),fromfile='antes/'+f,tofile='depois/'+f))
(A/'alteracoes.patch').write_text(diff)
v={'branch':'relatorio','head':run(['git','rev-parse','HEAD']).strip(),'paginas_antes':133,'paginas_depois':133,'md5_antes':hashlib.md5((A/'antes/relatorio_final_pi2_v2.pdf').read_bytes()).hexdigest(),'md5_depois':hashlib.md5(p.read_bytes()).hexdigest(),'sha256_pdf':sha(p),'B1_B2_identicos':True,'arquivos_protegidos_preservados':len(protected),'figura30_etapas_1_3_4_5_6_preservadas':True,'tabelas_legendas_caminhos_imagens_preservados':True,'fontes_incorporadas':True,'referencias_indefinidas':False,'overfull':False,'diff_check':'ok','paragrafo_inteiro_pagina_pdf37':True,'alteracoes_preexistentes_preservadas':True,'pendencias':['Instrumentar a procedência dos candidatos antes do benchmark','Verificar equivalência e disponibilidade antes de comparar três embarques','Executar benchmark futuro, não realizado nesta revisão'],'avisos_compilacao':['Obsolescência babel/memoir','Underfull na célula calendar/calendar_dates preexistente, linha 1078']}
(A/'validacao.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(json.dumps(v,ensure_ascii=False,indent=2))
