from pathlib import Path
import subprocess, os, hashlib, json, tempfile
r=Path('/home/avale/Projetos/maua_bus_map-relatorio'); os.chdir(r)
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='relatorio'
ref='refs/auditoria/relatorio-20261102-original-tecnico-cientifica'
assert subprocess.run(['git','show-ref','--verify','--quiet',ref]).returncode==1
out=Path('/tmp/pap-revisao-relatorio-20261102')
def git(*args,env=None): return subprocess.check_output(['git',*args],env=env)
status=git('status','--porcelain=v1','-uall'); diff=git('diff','--binary')
index_path=Path(git('rev-parse','--git-path','index').decode().strip())
before=hashlib.sha256(index_path.read_bytes()).hexdigest()
env=os.environ.copy(); env['GIT_INDEX_FILE']=str(out/'original.index')
git('read-tree','HEAD',env=env)
git('add','--all','--','docs/relatorio_final','docs/imagens',env=env)
pdf='docs/relatorio_final/PaP_relatorio_2026-11-02_ARTESP_revisado.pdf'
git('add','-f','--',pdf,env=env)
# Preserve all documentary PDFs (including signed originals) even when ignored.
for p in (r/'docs/relatorio_final/avaliacoes_externas').rglob('*.pdf'):
 git('add','-f','--',str(p.relative_to(r)),env=env)
tree=git('write-tree',env=env).decode().strip()
git('update-ref',ref,tree,'0'*40)
assert before==hashlib.sha256(index_path.read_bytes()).hexdigest()
assert status==git('status','--porcelain=v1','-uall')
manifest={'reference':ref,'tree':tree,'head':git('rev-parse','HEAD').decode().strip(),'branch':'relatorio','original_index_sha256':before,'baseline_pdf':pdf,'baseline_pdf_sha256':hashlib.sha256((r/pdf).read_bytes()).hexdigest(),'preserved_files':{}}
for p in (r/'docs/relatorio_final').rglob('*'):
 if p.is_file() and (p.suffix in ('.tex','.csv','.json','.geojson','.png','.jpg','.docx') or 'avaliacoes_externas' in str(p)):
  manifest['preserved_files'][str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'baseline.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
(out/'status-original.txt').write_bytes(status);(out/'alteracoes-preexistentes.patch').write_bytes(diff)
print(json.dumps({k:v for k,v in manifest.items() if k!='preserved_files'},indent=2))
