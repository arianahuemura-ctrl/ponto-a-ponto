from pathlib import Path
import re,json,hashlib,subprocess,collections
r=Path('/home/avale/Projetos/maua_bus_map-relatorio');d=r/'docs/relatorio_final';t=Path('/tmp/pap-revisao-relatorio-20261102');build=t/'build';baseline=json.loads((t/'baseline.json').read_text())
files={}
for line in (build/'relatorio_final_pi2_v2.fls').read_text().splitlines():
 if line.startswith('INPUT '):
  p=Path(line[6:]);p=p if p.is_absolute() else d/p
  if p.suffix=='.tex' and p.is_file() and str(p.resolve()).startswith(str(r)):
   files[str(p.resolve())]=p.read_text()
texts='\n'.join(files.values());labels=collections.Counter(re.findall(r'\\label\{([^}]+)\}',texts));refs=set(re.findall(r'\\(?:ref|pageref|autoref)\{([^}]+)\}',texts));cites=set()
for match in re.findall(r'\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}',texts):cites.update(x.strip() for x in match.split(','))
main=(d/'relatorio_final_pi2_v2.tex').read_text();old=subprocess.check_output(['git','show',baseline['reference']+':docs/relatorio_final/relatorio_final_pi2_v2.tex'],cwd=r,text=True)
def bib(s):
 section=s.split(r'\begin{thebibliography}',1)[1].split(r'\end{thebibliography}',1)[0]
 return {re.search(r'\]\{([^}]+)\}',x).group(1):' '.join(x.split()) for x in section.split(r'\bibitem')[1:]}
ob,nb=bib(old),bib(main);log=(build/'relatorio_final_pi2_v2.log').read_text();aux=(build/'relatorio_final_pi2_v2.aux').read_text();changed=[];missing=[]
for name,h in baseline['preserved_files'].items():
 p=r/name
 if not p.exists():missing.append(name)
 elif hashlib.sha256(p.read_bytes()).hexdigest()!=h:changed.append(name)
metric=json.loads((d/'revisao-tecnico-cientifica-2026-11-02/metricas-recalculadas.json').read_text());inputsok=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in metric['inputs'].items())
res={'active_tex':len(files),'labels':len(labels),'missing_refs':sorted(refs-set(labels)-{'LastPage'}),'duplicate_labels':[x for x,n in labels.items() if n>1],'cited_keys':len(cites),'bibliography_items':len(nb),'missing_citations':sorted(cites-set(nb)),'bibliography_unchanged_except_order':ob==nb,'overfull':log.count('Overfull '),'underfull':log.count('Underfull '),'warnings':re.findall(r'(?:Package|Class) .+ Warning:.*',log),'figures':len(re.findall(r'\\contentsline \{figure\}',aux)),'tables':len(re.findall(r'\\contentsline \{table\}',aux)),'preserved_inputs':len(baseline['preserved_files']),'changed_existing_files':changed,'missing_existing_files':missing,'new_figure_inputs_unchanged':inputsok,'baseline_pdf_unchanged':hashlib.sha256((r/baseline['baseline_pdf']).read_bytes()).hexdigest()==baseline['baseline_pdf_sha256'],'pdf_sha256':hashlib.sha256((build/'relatorio_final_pi2_v2.pdf').read_bytes()).hexdigest()}
assert not res['missing_refs'] and not res['duplicate_labels'] and not res['missing_citations'];assert ob==nb;assert not missing and all(x.endswith('.tex') for x in changed);assert inputsok and res['baseline_pdf_unchanged'] and not res['overfull']
(t/'validacao-automatica.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps(res,ensure_ascii=False,indent=2))
