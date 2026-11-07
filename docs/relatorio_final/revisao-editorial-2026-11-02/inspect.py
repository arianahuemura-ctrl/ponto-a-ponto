from pathlib import Path
import pymupdf as f,hashlib,json,collections
r=Path('/home/avale/Projetos/maua_bus_map-relatorio');c=r/'.cache/setup/editorial-20261102';paths={'before':r/'docs/relatorio_final/PaP_relatorio_2026-11-02_revisao_tecnico_cientifica.pdf','compiled':c/'build/relatorio_final_pi2_v2.pdf'};result={}
for key,path in paths.items():
 d=f.open(path);toc=d.get_toc();sections=[]
 for name in ['Fundamentação teórica','Fluxo implementado e evidência visual','Evolução e propostas de continuidade','Registro histórico da arquitetura em 28 de outubro']:
  j=next(i for i,t in enumerate(toc) if t[1].endswith(name));level,title,pg=toc[j];end=next(t[2] for t in toc[j+1:] if t[0]<=level);sections.append(dict(name=name,start=pg,end=end-1,pages=end-pg))
 images={};references=collections.Counter()
 for n,page in enumerate(d,1):
  for im in page.get_images(full=True):
   x=im[0];references[x]+=1
   if x not in images:images[x]=dict(width=im[2],height=im[3],colorspace=im[5],smask=im[1],decoded_sha256=hashlib.sha256(d.xref_stream(x)).hexdigest(),encoded_bytes=len(d.xref_stream_raw(x)),pages=[])
   if n not in images[x]['pages']:images[x]['pages'].append(n)
 dup=collections.defaultdict(list)
 for x,im in images.items():dup[(im['width'],im['height'],im['colorspace'],im['decoded_sha256'])].append(x)
 result[key]=dict(path=str(path),pages=len(d),bytes=path.stat().st_size,metadata=d.metadata,toc=toc,sections=sections,images=images,references=dict(references),duplicate_image_objects=[v for v in dup.values() if len(v)>1])
 print(key,len(d),'pages',path.stat().st_size,'bytes',[(x['name'],x['pages']) for x in sections]);print('duplicates:',result[key]['duplicate_image_objects'])
(c/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
# Thumbnail contact sheets of complete compiled PDF; later inspect relevant full-size pages.
d=f.open(paths['compiled']);from PIL import Image,ImageDraw
out=c/'visual';out.mkdir(exist_ok=True)
for start in range(0,len(d),24):
 sheet=Image.new('RGB',(1000,1500),'#b0b0b0');draw=ImageDraw.Draw(sheet)
 for i in range(start,min(start+24,len(d))):
  pix=d[i].get_pixmap(matrix=f.Matrix(.34,.34),alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((240,225));x=(i-start)%4*250+(250-im.width)//2;y=(i-start)//4*250+22;sheet.paste(im,(x,y));draw.text(((i-start)%4*250+8,(i-start)//4*250+4),str(i+1),fill='black')
 sheet.save(out/f'contact-{start+1:03}.jpg',quality=88)
print('Contact sheets ready')
