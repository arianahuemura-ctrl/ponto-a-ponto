from pathlib import Path
import json,hashlib,shutil,subprocess,re,difflib
import pymupdf as fitz
R=Path('/home/avale/Projetos/maua_bus_map');D=Path('/home/avale/Projetos/maua_bus_map-relatorio/docs/relatorio_final');A=D/'auditoria-artesp-maua-2026-11-02';P=Path(__file__).parent
pdf=A/'build/PaP_relatorio_2026-11-02_ARTESP.pdf';doc=fitz.open(pdf);texts=[p.get_text() for p in doc];text=' '.join(' '.join(texts).split())
log=pdf.with_suffix('.log').read_text();assert not re.search(r'Overfull|There were undefined references|Citation .*undefined|Reference .*undefined',log)
assert all(s in text for s in ['337','705','427','359','Capuava','Guapituba','99,666','95,5 min','20261007','busca parcial','Tabela 5'])
aux=pdf.with_suffix('.aux').read_text();assert r'\newlabel{tab:objetivos-atendimento}{{5}' in aux
review=sorted({2,31,32,44,45,*[i for i,t in enumerate(texts) if any(k in t for k in ['3.1 Ampliação','Tabela 9','retorno funcional','4 CONSIDERAÇÕES','705 viagens','A.6 Ampliação','staged_adapter.progressive'])]})
(A/'revisao-visual').mkdir(exist_ok=True)
for i in review:
 doc[i].get_pixmap(matrix=fitz.Matrix(1.2,1.2),alpha=False).save(A/'revisao-visual'/f'pagina-{i+1}.png')
out=D/pdf.name;shutil.copy2(pdf,out)
hashes={}
for p in [out,D/'PaP_relatorio_2026-11-02_multimodal.pdf',Path('/home/avale/Documentos/univesp/PI2/entrega-2026-11-01/PaP_relatorio_2026-11-01.pdf')]:
 hashes[str(p)]={a:hashlib.file_digest(p.open('rb'),a).hexdigest() for a in ['md5','sha256']}
assert list(hashes.values())[-1]['md5']=='fcf136604ea3aa13ea58bd884cc628b1'
(A/'pdf-text.txt').write_text('\n\f\n'.join(texts))
for name in ['validate_temporal.py','temporal-validation.json','capture-live.cjs','live-capture.json','captura-maua-bras-consulta.png','captura-maua-bras-mapa.png','captura-maua-bras-texto.txt','video-avaliacao.txt','finalize.py','latexmk.log']:
 shutil.copy2(P/name,A/name)
for name in ['summary.json','audit.py']:shutil.copy2(R/'artifacts/benchmarks/maua-artesp-20261102'/name,A/name)
code=A/'codigo-consultado';code.mkdir(exist_ok=True)
sources=list((R/'backend/transit/sptrans').glob('*.py'))+[R/'backend/mbm/routing_config.py',R/'backend/transit/management/commands/import_artesp.py']
source_hashes={}
for source in sources:
 relative=source.relative_to(R);target=code/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);source_hashes[str(relative)]=hashlib.sha256(source.read_bytes()).hexdigest()
(A/'codigo-sha256.json').write_text(json.dumps(source_hashes,indent=2)+'\n')
(A/'codigo-alteracoes-locais.diff').write_bytes(subprocess.check_output(['git','diff','HEAD','--','backend/transit/sptrans','backend/mbm/routing_config.py'],cwd=R))
(A/'revisoes.txt').write_text('Aplicação: '+subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()+'\nRelatório: '+subprocess.check_output(['git','rev-parse','HEAD'],cwd=D,text=True).strip()+'\nAmbas com alterações locais preservadas. Sem commit automático.\n')
validation={'pdf':str(out),'pages':len(doc),'hashes':hashes,'review_pages':[i+1 for i in review],'unresolved_references':False,'overfull_boxes':False,'table_5_number_preserved':True,'original_reference_unchanged':True,'real_query_count':14,'returned_journeys_temporally_checked':41,'artesp_legs_checked':34,'public_capture':'Actual server time, 02/11/2026 02:19 -03, partial-search warning preserved','video':'Narrative assessment and real captures prepared; original MP4 and subtitles unchanged','commit_created':False}
(A/'validacao-final.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
(A/'hashes-finais.json').write_text(json.dumps(hashes,indent=2)+'\n')
source=D/'relatorio_final_pi2_v2.tex';old=(A/'antes'/source.name).read_text();new=source.read_text()
(A/'alteracoes-localizadas.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='antes/relatorio_final_pi2_v2.tex',tofile='relatorio_final_pi2_v2.tex')))
pres=json.loads((A/'preservacao.json').read_text());pres['source_after_sha256']=hashlib.sha256(new.encode()).hexdigest();(A/'preservacao.json').write_text(json.dumps(pres,indent=2)+'\n')
readme=D/'README.md';intro=f'''# Ampliação ARTESP em Mauá — 2 de novembro de 2026

PDF atual: [{out.name}]({out.name}), {len(doc)} páginas.
MD5: `{hashes[str(out)]['md5']}`.

Confirmadas no GTFS original 337 paradas, 16 linhas ou variantes e 705/427/359
viagens programadas distintas em dia útil/sábado/domingo. Ao fim de semana,
324 paradas constam na programação. Capuava, Mauá e Guapituba são adicionais.
Foram examinadas 14 consultas temporais e preservada uma captura real da
interface pública com ônibus 157 e CPTM L10; seu aviso de busca parcial foi mantido.

Resumo, Metodologia, Resultados, Tabela 5, Considerações Finais e apêndice de
integração atualizados; ajuste pontual da delimitação para distinguir os três
estágios. Fontes, respostas, capturas, validação e hashes:
[auditoria-artesp-maua-2026-11-02](auditoria-artesp-maua-2026-11-02/).
O vídeo não foi modificado; avaliação e plano de substituição visual em
[video-avaliacao.txt](auditoria-artesp-maua-2026-11-02/video-avaliacao.txt).
Versões anteriores preservadas. Nenhum commit automático.

---

'''
previous=readme.read_text();assert not previous.startswith('# Ampliação ARTESP');readme.write_text(intro+previous)
print(json.dumps(validation,ensure_ascii=False,indent=2))
