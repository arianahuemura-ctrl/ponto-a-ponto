"""Inventário de arquivos explícitos; não acessa automaticamente bancos ou usuários."""
import argparse,hashlib,json
from pathlib import Path

def inventory(root,items):
    root=Path(root).resolve();out=[]
    for item in items:
        rel=Path(item)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Use caminho relativo sem ..')
        p=root/rel
        if any(x.is_symlink() for x in [p,*p.parents] if x!=root.parent):raise ValueError('Symlink não admitido')
        if not p.is_file() or not p.resolve().is_relative_to(root):raise ValueError('Arquivo inválido')
        before=p.stat();h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
        after=p.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('Arquivo mudou durante hash')
        out.append({'arquivo':str(rel),'bytes':after.st_size,'sha256':h.hexdigest()})
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('raiz',type=Path);p.add_argument('saida',type=Path);p.add_argument('arquivos',nargs='+');a=p.parse_args()
    rows=inventory(a.raiz,a.arquivos);body=json.dumps({'schema':1,'arquivos':rows},ensure_ascii=False,indent=2)+'\n'
    seal=Path(str(a.saida)+'.sha256')
    if a.saida.exists() or seal.exists():p.error('Saída já existe')
    with a.saida.open('x') as f:f.write(body)
    with seal.open('x') as f:f.write(hashlib.sha256(body.encode()).hexdigest()+'\n')
