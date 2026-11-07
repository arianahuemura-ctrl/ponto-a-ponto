"""Lifecycle local, sem daemon do sistema; estado privado fora do repositório."""
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
STATE = Path.home() / '.cache' / 'pap-public' / IDENTIFIER


def identity(pid):
    try:
        proc = Path(f'/proc/{pid}')
        args = proc.joinpath('cmdline').read_bytes()
        stamp = proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19]
        return stamp if b'mbm.public_wsgi:application' in args else None
    except (OSError, IndexError):
        return None


def alive(record):
    return identity(record['pid']) == record['started']


def docker_output(*args):
    return subprocess.run(['docker', *args], capture_output=True, text=True,
                          timeout=10, check=True)


def discover_host():
    """Only running Cloudflare containers explicitly forwarding to this instance."""
    try:
        ids=docker_output('ps','--filter','status=running','--format','{{.ID}}').stdout.split()
        hosts=set()
        for cid in ids:
            raw=docker_output('inspect','--format',
                '{{json .Config.Image}}|{{json .Args}}|{{.State.StartedAt}}',cid).stdout.strip()
            image,args,started=raw.split('|',2)
            if not json.loads(image).startswith('cloudflare/cloudflared'):continue
            args=json.loads(args)
            targets={'http://127.0.0.1:8001','http://localhost:8001'}
            if not any((arg=='--url' and i+1<len(args) and args[i+1].rstrip('/') in targets)
                       or (arg.startswith('--url=') and arg[6:].rstrip('/') in targets)
                       for i,arg in enumerate(args)):continue
            log=docker_output('logs','--since',started,'--tail','1000',cid)
            found=re.findall(r'https://([a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com)\b',log.stdout+'\n'+log.stderr)
            if not found:raise SystemExit('Túnel encontrado, mas a URL ainda não apareceu. Aguarde e execute start_public.sh novamente.')
            hosts.add(found[-1])
        if len(hosts)>1:raise SystemExit('Há vários túneis para 8001. Defina PAP_PUBLIC_HOST explicitamente; nada foi interrompido.')
        return next(iter(hosts),None)
    except (OSError,subprocess.SubprocessError,ValueError):
        print('Não foi possível consultar túneis Docker; usando PAP_PUBLIC_HOST ou a configuração pública existente.')
        return None


def running_host(record):
    # Read only the host; never print or persist the process environment.
    if not record or not alive(record):return None
    for item in Path(f"/proc/{record['pid']}/environ").read_bytes().split(b'\0'):
        if item.startswith(b'PAP_PUBLIC_HOST='):return item.split(b'=',1)[1].decode()
    return ''


def desired_host(record):
    explicit=os.environ.get('PAP_PUBLIC_HOST','').strip().lower()
    host=explicit or discover_host() or running_host(record) or ''
    if host and (len(host)>253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+',host)):
        raise SystemExit('PAP_PUBLIC_HOST inválido: informe somente o domínio, sem https:// ou caminho. Nada foi interrompido.')
    return host


def main():
    os.umask(0o077)
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE.chmod(0o700)
    pidfile = STATE / 'process.json'
    with (STATE / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = json.loads(pidfile.read_text()) if pidfile.exists() else None
        if sys.argv[1] == 'stop':
            if not record or not alive(record):
                print('Instância pública já está parada. Desenvolvimento preservado.')
                pidfile.unlink(missing_ok=True)
                return
            os.kill(record['pid'], signal.SIGTERM)
            for _ in range(350):
                if not alive(record):
                    pidfile.unlink(missing_ok=True)
                    print('Instância pública interrompida. Porta 8000 preservada.')
                    return
                time.sleep(.1)
            raise SystemExit('Encerramento ainda em andamento; execute stop_public.sh novamente.')
        host=desired_host(record)
        if record and alive(record):
            if running_host(record)==host:
                print('Instância pública já ativa; domínio permitido:',host or 'somente localhost')
                return
            print('Atualizando domínio público para:',host)
            os.kill(record['pid'],signal.SIGTERM)
            for _ in range(350):
                if not alive(record):break
                time.sleep(.1)
            else:raise SystemExit('Encerramento ainda em andamento; tente novamente. Túnel preservado.')
            pidfile.unlink(missing_ok=True)
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', 8001))
            except OSError:
                raise SystemExit('Porta 8001 ocupada; nenhum processo foi interrompido.')
        if not (ROOT / 'frontend/dist/index.html').is_file():
            raise SystemExit('Compile o React antes: npm --prefix frontend run build')
        env = os.environ.copy()
        env['PAP_PUBLIC_HOST'] = host
        env['DJANGO_SETTINGS_MODULE'] = 'mbm.public_settings'
        env['DJANGO_DEBUG'] = '0'
        env['PAP_PUBLIC_SECRET_KEY'] = env.get('PAP_PUBLIC_SECRET_KEY') or secrets.token_urlsafe(64)
        env['DJANGO_SECRET_KEY'] = env['PAP_PUBLIC_SECRET_KEY']
        env['PYTHONPATH'] = str(ROOT / 'backend') + os.pathsep + str(ROOT)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        # Limite de requisições pedestres usa SQLite temporário próprio, sem tocar bases anteriores.
        temp = STATE / 'tmp'
        temp.mkdir(exist_ok=True, mode=0o700)
        env['TMPDIR'] = str(temp)
        subprocess.run([sys.executable, str(ROOT / 'backend/manage.py'), 'check'],
                       cwd=ROOT, env=env, check=True)
        with (STATE / 'gunicorn.log').open('ab') as log:
            process = subprocess.Popen([
                sys.executable, '-m', 'gunicorn', '--chdir', str(ROOT),
                '--config', str(ROOT / 'scripts/gunicorn_public.py'),
                'mbm.public_wsgi:application',
            ], cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log,
               stderr=subprocess.STDOUT, start_new_session=True)
        stamp = None
        for _ in range(100):
            stamp = identity(process.pid)
            if stamp is not None or process.poll() is not None:
                break
            time.sleep(.02)
        record = {'pid': process.pid, 'started': stamp}
        if stamp is None:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=35)
            raise SystemExit(f'Falha ao identificar o processo; consulte {STATE / "gunicorn.log"}')
        pidfile.write_text(json.dumps(record))
        opener = build_opener(ProxyHandler({}))
        for _ in range(100):
            if process.poll() is not None:
                pidfile.unlink(missing_ok=True)
                raise SystemExit(f'Gunicorn não iniciou. Consulte {STATE / "gunicorn.log"}')
            try:
                with opener.open('http://127.0.0.1:8001/api/health/', timeout=1) as response:
                    if response.status == 200:
                        print('PaP público pronto em http://127.0.0.1:8001; DEBUG=False.')
                        print('Domínio permitido:', env.get('PAP_PUBLIC_HOST') or 'somente localhost (defina PAP_PUBLIC_HOST antes do túnel)')
                        print('Log privado:', STATE / 'gunicorn.log')
                        return
            except OSError:
                time.sleep(.2)
        process.terminate()
        process.wait(timeout=35)
        pidfile.unlink(missing_ok=True)
        raise SystemExit('Instância não ficou pronta; processo público encerrado.')


if __name__ == '__main__':
    main()
