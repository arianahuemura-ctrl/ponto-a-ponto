from pathlib import Path
import pymupdf as fitz,json,hashlib,re,subprocess
R=Path('/home/avale/Projetos/maua_bus_map-relatorio');D=R/'docs/relatorio_final';A=D/'auditoria-alcance-ferroviario-2026-11-02';pdf=A/'build/PaP_relatorio_2026-11-02_multimodal.pdf';P=Path('/tmp/pap-alcance-ferroviario-20261102');doc=fitz.open(pdf)
texts=[page.get_text() for page in doc];keys=['conferência local de 2 de novembro','A cobertura temporal depende','Foi executada uma consulta','CONSIDERAÇÕES FINAIS','fornecedor dos ônibus municipais']
pages=sorted({i for i,t in enumerate(texts) for key in keys if key.lower() in t.lower()});print('review pages',[i+1 for i in pages])
for i in pages:doc[i].get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False).save(P/f'pagina-{i+1}.png')
(P/'pdf-text.txt').write_text('\n\f\n'.join(texts))
text=' '.join(' '.join(texts).split());assert all(s in text for s in ['Guapituba','18935','18937','68 minutos','75 minutos','1 de maio de 2027','04h26','05h32min30s','99,666'])
log=(A/'build/PaP_relatorio_2026-11-02_multimodal.log').read_text();warnings=[l for l in log.splitlines() if any(s in l for s in ['Warning:','Overfull','Underfull'])];(P/'latex-warnings.txt').write_text('\n'.join(warnings));print('warnings',len(warnings));print('\n'.join(warnings[:12]));print('MD5',hashlib.file_digest(pdf.open('rb'),'md5').hexdigest());print('pages',len(doc))
# Compare chapter-external source bytes with the backup, and check unchanged source files used by the build.
old=(A/'antes/relatorio_final_pi2_v2.tex').read_bytes();new=(D/'relatorio_final_pi2_v2.tex').read_bytes();start=old.index(b'\\chapter{Resultados:');end=old.index(b'\\postextual',start);assert old[:start]==new[:start] and old[end:]==new[new.index(b'\\postextual',start):]
(P/'pdf-validation.json').write_text(json.dumps({'pages':len(doc),'review_pages':[i+1 for i in pages],'md5':hashlib.file_digest(pdf.open('rb'),'md5').hexdigest(),'sha256':hashlib.file_digest(pdf.open('rb'),'sha256').hexdigest(),'outside_authorized_chapters_source_identical':True,'expected_evidence_in_pdf':True,'unresolved_references':bool(re.search(r'There were undefined references|Citation .*undefined|Reference .*undefined',log)),'bytes':pdf.stat().st_size},indent=2))
