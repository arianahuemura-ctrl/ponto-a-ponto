from pathlib import Path
import subprocess as sp,hashlib,json,re,shutil
r=Path('/home/avale/Projetos/maua_bus_map-relatorio');d=r/'docs/relatorio_final';c=r/'.cache/setup/video-definitivo-20261103';old=d/'PaP_relatorio_2026-11-02_capturas_atualizadas.pdf';src=c/'build/relatorio_final_pi2_v2.pdf';out=d/'PaP_relatorio_2026-11-03_video_definitivo.pdf';assert not out.exists()
def run(args):return sp.check_output(args,stderr=sp.STDOUT).decode()
def h(p,a):
 with p.open('rb') as f:return hashlib.file_digest(f,a).hexdigest()
assert h(old,'sha256')=='7a93bb8d7e2820a72a261e435585b8ee75403e82a8556181e4d272a18f3bd77d'
sp.run(['mutool','clean','-gggg','-z',str(src),str(out)],check=True)
for name,p in [('before',old),('compiled',src),('final',out)]:
 sp.run(['pdftotext','-layout',str(p),str(c/f'{name}.txt')],check=True)
 with (c/f'{name}-render.log').open('w') as log:sp.run(['mutool','draw','-r','100','-s','5',str(p)],stdout=log,stderr=sp.STDOUT,check=True)
 (c/f'{name}-pdfinfo.txt').write_text(run(['pdfinfo',str(p)]))
a=(c/'before.txt').read_text().split('\f');b=(c/'final.txt').read_text().split('\f');assert len(a)==len(b)==168;assert a[1:]==b[1:];assert 'rSvuIWx8QAg' in b[0];assert 'provisória' not in b[0]
def renderhash(name):return re.findall(r'page .*? (\d+) ([0-9a-f]{32})',(c/f'{name}-render.log').read_text())
ha,hb,hc=map(renderhash,['before','compiled','final']);assert len(ha)==len(hb)==len(hc)==167;assert ha[1:]==hc[1:];assert hb==hc
uris=run(['mutool','show',str(out),'grep']);assert 'https://www.youtube.com/watch?v=rSvuIWx8QAg' in uris;assert 'FDWkiNMvt4A' not in uris
(c/'links-video.txt').write_text('\n'.join(x for x in uris.splitlines() if 'rSvuIWx8QAg' in x))
log=(c/'build/relatorio_final_pi2_v2.log').read_text();assert not re.search(r'Overfull|undefined references|Missing character',log)
sp.run(['mutool','draw','-q','-r','100','-o',str(c/'capa.png'),str(out),'1'],check=True)
v={'pages':167,'bytes':out.stat().st_size,'md5':h(out,'md5'),'sha256':h(out,'sha256'),'url':'https://www.youtube.com/watch?v=rSvuIWx8QAg','page_2_to_167_text_and_pixels_unchanged':True,'lossless_optimization_all_pages_pixels_identical_100dpi':True,'clickable_url_present':True,'old_pdf_unchanged':True,'online_access_not_verified':'Web tool could not fetch YouTube page','underfull_count':log.count('Underfull'),'build_exit':0}
(c/'validacao.json').write_text(json.dumps(v,ensure_ascii=False,indent=2));print(json.dumps(v,ensure_ascii=False,indent=2))
