from pathlib import Path
import pymupdf as f,pikepdf,hashlib,json,re,collections,subprocess
r=Path('/home/avale/Projetos/maua_bus_map-relatorio');d=r/'docs/relatorio_final';c=r/'.cache/setup/editorial-20261102';build=c/'build';base=json.loads((c/'baseline.json').read_text());src=build/'relatorio_final_pi2_v2.pdf';out=c/'optimized-qpdf.pdf';old=d/'PaP_relatorio_2026-11-02_revisao_tecnico_cientifica.pdf'
A=f.open(src);B=f.open(out);OLD=f.open(old)
assert len(A)==len(B)==167 and len(OLD)==168
assert A.metadata==B.metadata and A.get_toc()==B.get_toc()
for k in ['title','author','subject','keywords']:assert B.metadata[k]
assert len(B.metadata['author'].split(';'))==8
# All pages after lossless optimization: pixel-, text-, and link-equivalent.
render_hashes=[];links=[];blank=[];pagination=[]
intro=next(x[2]-1 for x in B.get_toc() if x[1].endswith('Introdução'))
for i,(a,b) in enumerate(zip(A,B)):
 x=a.get_pixmap(matrix=f.Matrix(2,2),alpha=False);y=b.get_pixmap(matrix=f.Matrix(2,2),alpha=False)
 assert x.samples==y.samples,('pixels',i+1)
 assert a.get_text()==b.get_text(),('text',i+1)
 la=[{k:v for k,v in l.items() if k not in ['xref','id']} for l in a.get_links()];lb=[{k:v for k,v in l.items() if k not in ['xref','id']} for l in b.get_links()];assert la==lb,('links',i+1)
 for link in b.get_links():
  if link['kind'] in [f.LINK_GOTO,f.LINK_NAMED]:assert 0<=link['page']<len(B),('bad_destination',i+1,link)
  if link['kind']==f.LINK_URI:assert link.get('uri') and '\n' not in link['uri']
  links.append(link['kind'])
 if not b.get_text().strip() and not b.get_images():blank.append(i+1)
 if i>=intro:
  header=b.get_text(clip=f.Rect(350,0,595,75)).strip();assert header==str(i-intro+1),('pagination',i+1,header);pagination.append(header)
 render_hashes.append(hashlib.sha256(y.samples).hexdigest())
assert not blank
# The six included external pages are visually identical except for report page numbers.
annex=[]
for i in range(1,7):
 a,b=OLD[-i],B[-i];rect=f.Rect(0,76,a.rect.width,a.rect.height)
 assert a.get_pixmap(matrix=f.Matrix(2,2),clip=rect,alpha=False).samples==b.get_pixmap(matrix=f.Matrix(2,2),clip=rect,alpha=False).samples,('annex changed',i)
 annex.append(len(B)-i+1)
# Named destinations used by lists, contents, citations, and cross-references.
names=B.resolve_names();checked_entries=0
for page in B:
 for link in page.get_links():
  if 'nameddest' in link:
   assert link['nameddest'] in names,link
   assert names[link['nameddest']]['page']==link['page']
for ext in ['toc','lof','lot']:
 for line in (build/('relatorio_final_pi2_v2.'+ext)).read_text().splitlines():
  match=re.search(r'\{(\d+)\}\{([^{}]+)\}%',line)
  if match:
   n,anchor=match.groups();assert anchor in names,(ext,anchor)
   assert names[anchor]['page']==intro+int(n)-1,(ext,n,anchor,names[anchor])
   checked_entries+=1
assert checked_entries>=100
# Embedded raster data retained (one redundant Olho Vivo figure removed).
def imagehashes(pdf):
 hashes=set()
 for p in pdf:
  for x in p.get_images():hashes.add((x[2],x[3],x[5],hashlib.sha256(pdf.xref_stream(x[0])).hexdigest()))
 return hashes
assert imagehashes(B)<=imagehashes(OLD)
# Compare original raster placement dimensions of the paired mobile screenshots.
geometry=[]
for oldn in [44,45]:
 page=OLD[oldn-1]
 for img in page.get_images():
  h=hashlib.sha256(OLD.xref_stream(img[0])).hexdigest()
  for newp in B:
   for im in newp.get_images():
    if hashlib.sha256(B.xref_stream(im[0])).hexdigest()==h:
     geometry.append(dict(old_page=oldn,new_page=newp.number+1,old_rects=[list(z) for z in page.get_image_rects(img[0])],new_rects=[list(z) for z in newp.get_image_rects(im[0])]))
# Active-source graph, cross-references, citations and appendix sequence.
files={}
for line in (build/'relatorio_final_pi2_v2.fls').read_text().splitlines():
 if line.startswith('INPUT '):
  p=Path(line[6:]);p=(p if p.is_absolute() else d/p).resolve()
  if p.suffix=='.tex' and p.is_file() and r in p.parents:files[str(p)]=p.read_text()
text='\n'.join(files.values());labels=collections.Counter(re.findall(r'\\label\{([^}]+)\}',text));refs=set(re.findall(r'\\(?:ref|pageref|autoref)\{([^}]+)\}',text));assert not(refs-set(labels)-{'LastPage'});assert all(v==1 for v in labels.values())
cites=set()
for match in re.findall(r'\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}',text):cites.update(x.strip() for x in match.split(','))
main=(d/'relatorio_final_pi2_v2.tex').read_text();prior=(c/'antes/relatorio_final_pi2_v2.tex').read_text()
getbib=lambda s:s.split('\\begin{thebibliography}',1)[1].split('\\end{thebibliography}',1)[0]
assert getbib(main)==getbib(prior)
keys=set(re.findall(r'\\bibitem\[[^\n]+?\]\{([^}]+)\}',main));assert not cites-keys
for command in ['autor','titulo','data','instituicao','local']:
 pattern=r'\\'+command+r'\{([^\n]*)\}'
 assert re.search(pattern,main).group(1)==re.search(pattern,prior).group(1),command
assert main.split('Este trabalho',1)[1].split('\\end{resumo}',1)[0]==prior.split('Este trabalho',1)[1].split('\\end{resumo}',1)[0]
toc=(build/'relatorio_final_pi2_v2.toc').read_text();app=re.findall(r'\\contentsline \{appendix\}\{\\chapternumberline \{([^}]+)\}',toc);assert app==list('ABCDEFGH')+['A'],app
# All pre-existing evidence files and PDFs remain intact; allow only requested editorial sources.
changed=[];missing=[]
for name,h in base['files'].items():
 p=r/name
 if not p.exists():missing.append(name)
 elif hashlib.sha256(p.read_bytes()).hexdigest()!=h:changed.append(name)
allowed={'docs/relatorio_final/relatorio_final_pi2_v2.tex','docs/relatorio_final/revisao-tecnico-cientifica-2026-11-02/notas-historicas.tex','docs/relatorio_final/README.md'}
assert not missing and set(changed)<=allowed,(missing,changed)
log=(build/'relatorio_final_pi2_v2.log').read_text();assert 'Overfull' not in log and 'undefined' not in log and 'Missing character' not in log
with pikepdf.open(out) as pdf:syntax=pdf.check_pdf_syntax();assert not syntax,syntax
result=dict(pages_before=168,pages_after=167,bytes_before=old.stat().st_size,bytes_compiled=src.stat().st_size,bytes_final=out.stat().st_size,md5=hashlib.md5(out.read_bytes()).hexdigest(),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),metadata_before=OLD.metadata,metadata_after=B.metadata,all_167_pages_pixel_identical_after_lossless_optimization_at_144dpi=True,text_and_links_identical_after_optimization=True,bookmarks=len(B.get_toc()),validated_list_and_contents_entries=checked_entries,named_destinations=len(names),internal_links=links.count(f.LINK_GOTO)+links.count(f.LINK_NAMED),external_links=links.count(f.LINK_URI),empty_pages=blank,pagination_checked_from_intro=len(pagination),appendices_and_annex=app,signed_annex_pages_preserved=sorted(annex),source_manifest_files=len(base['files']),changed_existing_files=changed,missing_files=missing,remaining_raster_images_identical=True,active_tex_files=len(files),labels=len(labels),references_resolved=len(refs),citation_keys=len(cites),bibliography_unchanged=True,overfull=0,underfull=log.count('Underfull'),warnings=re.findall(r'(?:Package|Class) .+ Warning:.*',log),pdf_syntax_errors=syntax,source_pdf_md5=hashlib.md5(old.read_bytes()).hexdigest(),raster_placement_checks=geometry,rendered_page_sha256=render_hashes)
(c/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['rendered_page_sha256','metadata_before','metadata_after','raster_placement_checks']},ensure_ascii=False,indent=2))
# Enlarged final previews.
for n in [4,5,6,7,8,21,22,45,53,57,58,59,99,106,162,167]:
 B[n-1].get_pixmap(matrix=f.Matrix(1.5,1.5),alpha=False).save(c/'visual'/f'final-{n:03}.png')
