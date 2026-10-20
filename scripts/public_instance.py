"""Lifecycle local, sem daemon do sistema; estado privado fora do repositório."""
import fcntl
import hashlib
import json
import os
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
        if record and alive(record):
            print('Instância pública já está ativa em 127.0.0.1:8001. Para mudar o domínio, pare e reinicie.')
            return
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', 8001))
            except OSError:
                raise SystemExit('Porta 8001 ocupada; nenhum processo foi interrompido.')
        if not (ROOT / 'frontend/dist/index.html').is_file():
            raise SystemExit('Compile o React antes: npm --prefix frontend run build')
        env = os.environ.copy()
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
