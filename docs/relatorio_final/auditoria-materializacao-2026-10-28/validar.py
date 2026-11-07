from pathlib import Path
import subprocess, hashlib, json, difflib, re

A=Path(__file__).resolve().parent
R=Path('/home/avale/Projetos/maua_bus_map-relatorio')
D=R/'docs/relatorio_final'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True)
assert cmd(['git','branch','--show-current'],R).strip()=='relatorio'
check=subprocess.run(['git','diff','--check'],cwd=R,capture_output=True,text=True)
assert check.returncode==0,check.stdout+check.stderr
args=['git','diff','--binary','--','.',':!docs/relatorio_final/planejador_hibrido.tex',':!docs/relatorio_final/relatorio_final_pi2_v2.tex']
assert subprocess.check_output(args,cwd=R)==(A/'diff-outros-antes.patch').read_bytes()
allowed={'docs/relatorio_final/planejador_hibrido.tex','docs/relatorio_final/relatorio_final_pi2_v2.tex'}
preserved=json.loads((A/'preservacao-fontes.json').read_text())
for p,h in preserved.items():
    if p not in allowed:assert sha(R/p)==h,p
old=(A/'antes/planejador_hibrido.tex').read_text();new=(D/'planejador_hibrido.tex').read_text()
separator='\\section{Protocolo do benchmark definitivo}'
assert old.split(separator)[1]==new.split(separator)[1]
for name in ['planejador_hibrido.tex','relatorio_final_pi2_v2.tex']:
    before=(A/'antes'/name).read_text();after=(D/name).read_text()
    assert re.findall(r'\\caption(?:\[[^\]]*\])?\{[^\n]*',before)==re.findall(r'\\caption(?:\[[^\]]*\])?\{[^\n]*',after)
    assert re.findall(r'\\begin\{table\}.*?\\end\{table\}',before,re.S)==re.findall(r'\\begin\{table\}.*?\\end\{table\}',after,re.S)
diff=''.join(''.join(difflib.unified_diff((A/'antes'/n).read_text().splitlines(True),(D/n).read_text().splitlines(True),fromfile='antes/'+n,tofile='depois/'+n)) for n in ['planejador_hibrido.tex','relatorio_final_pi2_v2.tex'])
(A/'alteracoes.patch').write_text(diff)
e=json.loads((A/'evidencias.json').read_text())
for p,info in e['codigo'].items():assert sha(Path(p))==info['sha256'],p
for p,h in e['evidencias_origem'].items():assert sha(Path(p))==h,p
assert sha(Path(e['banco_atual']['path']))==e['banco_atual']['sha256']
app=Path('/home/avale/Projetos/maua_bus_map')
assert cmd(['git','rev-parse','HEAD'],app)+cmd(['git','status','--short'],app)==(A/'desenvolvimento-git.txt').read_text()
log=(D/'relatorio_final_pi2_v2.log').read_text(errors='replace')
assert not re.search(r'(undefined references|Reference .* undefined|Citation .* undefined|Overfull|Rerun to get|Label\(s\) may have changed)',log)
pdf=D/'relatorio_final_pi2_v2.pdf'; info=cmd(['pdfinfo',str(pdf)])
fonts=cmd(['pdffonts',str(pdf)])
assert all(re.search(r'\s+yes\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',l) for l in fonts.splitlines()[2:] if l.strip())
text=cmd(['pdftotext','-layout',str(pdf),'-']);(A/'texto-depois.txt').write_text(text)
pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M)[1])
assert f'{pages} f.' in text
physical=text.split('\f')
assert 'custo, validação e encerramento' in physical[36] and 'permanecem no Apêndice C' in physical[36]
(A/'pdfinfo.txt').write_text(info);(A/'fontes.txt').write_text(fonts)
status=cmd(['git','status','--short'],R);(A/'git-depois.txt').write_text(status)
validation={'paginas_antes':132,'paginas_depois':pages,'md5_antes':hashlib.md5((A/'antes/relatorio_final_pi2_v2.pdf').read_bytes()).hexdigest(),
    'md5_depois':hashlib.md5(pdf.read_bytes()).hexdigest(),'sha256_depois':sha(pdf),'bytes':pdf.stat().st_size,
    'git_diff_check':'ok','branch':'relatorio','head':cmd(['git','rev-parse','HEAD'],R).strip(),
    'fontes_incorporadas':True,'referencias_indefinidas':False,'overfull':False,
    'protocolo_b3_preservado':True,'demais_fontes_e_imagens_preservadas':len(preserved)-2,
    'alteracoes_preexistentes_preservadas':True,'banco_e_evidencias_inalterados':True,
    'aplicacao_inalterada':True,'widow_pagina_33_corrigida':True,
    'avisos_remanescentes':['babel: brazil obsoleto','memoir: comandos obsoletos','Underfull hbox na célula calendar/calendar_dates, tabela preexistente do Apêndice A, linha 1078']}
(A/'validacao.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
for n in [36,37,93,94,95,96,97,98]:
    subprocess.run(['pdftoppm','-f',str(n),'-l',str(n),'-scale-to','1200','-png','-singlefile',str(pdf),str(A/f'pagina-{n}')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print(json.dumps(validation,ensure_ascii=False,indent=2))
