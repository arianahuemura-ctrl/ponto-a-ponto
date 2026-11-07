from pathlib import Path
import pymupdf as f,pikepdf,hashlib,json,re,collections
from PIL import Image
r=Path('/home/avale/Projetos/maua_bus_map-relatorio');d=r/'docs/relatorio_final';c=r/'.cache/setup/capturas-atuais-20261102';build=c/'build';audit=d/'atualizacao-capturas-2026-11-02'
src=build/'relatorio_final_pi2_v2.pdf';out=d/'PaP_relatorio_2026-11-02_capturas_atualizadas.pdf';old=d/'PaP_relatorio_2026-11-02_revisao_editorial.pdf'
assert not out.exists(),'Do not overwrite previous deliverable'
pikepdf.settings.set_flate_compression_level(9)
with pikepdf.open(src) as pdf:
 pdf.remove_unreferenced_resources();pdf.save(out,compress_streams=True,recompress_flate=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)
A=f.open(src);B=f.open(out);OLD=f.open(old)
assert len(A)==len(B)==167 and len(OLD)==167
assert A.metadata==B.metadata and A.get_toc()==B.get_toc()
for k in ['title','author','subject','keywords']:assert B.metadata[k]==OLD.metadata[k] and B.metadata[k]
assert len(B.metadata['author'].split(';'))==8
intro=next(x[2]-1 for x in B.get_toc() if x[1].endswith('Introdução'))
links=[];blank=[];render_hashes=[];thin=[]
for i,(a,b) in enumerate(zip(A,B)):
 x=a.get_pixmap(matrix=f.Matrix(2,2),alpha=False);y=b.get_pixmap(matrix=f.Matrix(2,2),alpha=False)
 assert x.samples==y.samples,('pixels',i+1)
 assert a.get_text()==b.get_text(),('text',i+1)
 clean=lambda p:[{k:v for k,v in l.items() if k not in ['xref','id']} for l in p.get_links()]
 assert clean(a)==clean(b),('links',i+1)
 for link in b.get_links():
  if link['kind'] in [f.LINK_GOTO,f.LINK_NAMED]:assert 0<=link['page']<len(B)
  if link['kind']==f.LINK_URI:assert link.get('uri') and '\n' not in link['uri']
  links.append(link['kind'])
 if not b.get_text().strip() and not b.get_images():blank.append(i+1)
 if i>=intro:
  header=b.get_text(clip=f.Rect(350,0,595,75)).strip();assert header==str(i-intro+1),('pagination',i+1,header)
  if len(b.get_text().strip())<100 and not b.get_images():thin.append(i+1)
 render_hashes.append(hashlib.sha256(y.samples).hexdigest())
assert not blank and not thin,(blank,thin)
for i in range(1,7):
 a,b=OLD[-i],B[-i];rect=f.Rect(0,76,a.rect.width,a.rect.height)
 assert a.get_pixmap(matrix=f.Matrix(2,2),clip=rect,alpha=False).samples==b.get_pixmap(matrix=f.Matrix(2,2),clip=rect,alpha=False).samples,('annex',i)
names=B.resolve_names();entries=0
for page in B:
 for link in page.get_links():
  if 'nameddest' in link:assert link['nameddest'] in names and names[link['nameddest']]['page']==link['page']
for ext in ['toc','lof','lot']:
 for line in (build/('relatorio_final_pi2_v2.'+ext)).read_text().splitlines():
  m=re.search(r'\{(\d+)\}\{([^{}]+)\}%',line)
  if m:
   n,anchor=m.groups();assert anchor in names and names[anchor]['page']==intro+int(n)-1,(ext,n,anchor);entries+=1
files={};inputs=set()
for line in (build/'relatorio_final_pi2_v2.fls').read_text().splitlines():
 if line.startswith('INPUT '):
  p=Path(line[6:]);p=(p if p.is_absolute() else d/p).resolve()
  if p.is_file() and r in p.parents:
   inputs.add(p)
   if p.suffix=='.tex':files[str(p)]=p.read_text()
text='\n'.join(files.values());labels=collections.Counter(re.findall(r'\\label\{([^}]+)\}',text));refs=set(re.findall(r'\\(?:ref|pageref|autoref)\{([^}]+)\}',text));assert not(refs-set(labels)-{'LastPage'});assert all(v==1 for v in labels.values())
cites=set()
for m in re.findall(r'\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}',text):cites.update(x.strip() for x in m.split(','))
main=(d/'relatorio_final_pi2_v2.tex').read_text();prior=(c/'relatorio_final_pi2_v2.tex').read_text()
getbib=lambda s:s.split('\\begin{thebibliography}',1)[1].split('\\end{thebibliography}',1)[0]
assert getbib(main)==getbib(prior)
assert not cites-set(re.findall(r'\\bibitem\[[^\n]+?\]\{([^}]+)\}',main))
for command in ['autor','titulo','data','instituicao','local']:
 pat=r'\\'+command+r'\{([^\n]*)\}';assert re.search(pat,main).group(1)==re.search(pat,prior).group(1)
assert main.split('Este trabalho',1)[1].split('\\end{resumo}',1)[0]==prior.split('Este trabalho',1)[1].split('\\end{resumo}',1)[0]
toc=(build/'relatorio_final_pi2_v2.toc').read_text();app=re.findall(r'\\contentsline \{appendix\}\{\\chapternumberline \{([^}]+)\}',toc);assert app==list('ABCDEFGH')+['A']
base=json.loads((c/'baseline.json').read_text());changed=[];missing=[]
for name,h in base['files'].items():
 p=r/name
 if not p.exists():missing.append(name)
 elif hashlib.sha256(p.read_bytes()).hexdigest()!=h:changed.append(name)
allowed={'docs/relatorio_final/relatorio_final_pi2_v2.tex','docs/relatorio_final/legibilidade_ferroviaria_20261102.tex','docs/relatorio_final/README.md'}
assert not missing and set(changed)<=allowed,(missing,changed)
# Verify all new screenshots are embedded at original resolution and pixels.
image_hashes=set()
for page in B:
 for im in page.get_images():
  pix=f.Pixmap(B,im[0])
  if pix.colorspace and pix.colorspace.n==3:image_hashes.add((pix.width,pix.height,hashlib.sha256(pix.samples).hexdigest()))
captures=[];post_requests=[]
folder=d/'capturas/2026-11-02-interface-atual'
for manifest in sorted(folder.glob('manifest-*.json')):
 m=json.loads(manifest.read_text());post_requests += [q for q in m['requests'] if q['method']!='GET']
 for shot in m['captures']:
  p=folder/shot['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==shot['sha256']
  im=Image.open(p).convert('RGB');assert (im.width,im.height,hashlib.sha256(im.tobytes()).hexdigest()) in image_hashes,shot['file']
  assert p.resolve() in inputs;captures.append(shot['file'])
assert len(set(captures))==17 and not post_requests
log=(build/'relatorio_final_pi2_v2.log').read_text();assert 'Overfull' not in log and 'undefined' not in log and 'Missing character' not in log
with pikepdf.open(out) as pdf:syntax=pdf.check_pdf_syntax();assert not syntax
result=dict(pages_before=len(OLD),pages_after=len(B),bytes_before=old.stat().st_size,bytes_compiled=src.stat().st_size,bytes_final=out.stat().st_size,md5=hashlib.md5(out.read_bytes()).hexdigest(),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),metadata=B.metadata,metadata_bibliographic_unchanged=True,bookmarks=len(B.get_toc()),validated_contents_list_entries=entries,named_destinations=len(names),internal_links=links.count(f.LINK_GOTO)+links.count(f.LINK_NAMED),external_links=links.count(f.LINK_URI),http_availability_retested=False,blank_pages=blank,sparse_pages_without_images=thin,continuous_pagination=True,appendices_and_annex=app,six_signed_annex_pages_pixel_preserved=True,original_files_checked=len(base['files']),changed_existing_files=changed,missing_files=missing,new_screenshots_embedded_pixel_identical=sorted(set(captures)),non_get_api_requests=post_requests,active_tex_files=len(files),labels=len(labels),references_resolved=len(refs),citation_keys=len(cites),bibliography_unchanged=True,overfull=0,underfull=log.count('Underfull'),warnings=re.findall(r'(?:Package|Class) .+ Warning:.*',log),lossless_optimization_all_pages_pixel_text_links_identical_at_144dpi=True,pdf_syntax_errors=syntax,rendered_page_sha256=render_hashes)
(audit/'VALIDACAO.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['metadata','rendered_page_sha256','new_screenshots_embedded_pixel_identical']},ensure_ascii=False,indent=2))
