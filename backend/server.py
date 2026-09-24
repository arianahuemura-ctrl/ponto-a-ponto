from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import webbrowser

FRONTEND_ROOT = Path(__file__).resolve().parents[1] / 'frontend'
HOST = '127.0.0.1'
DEFAULT_PORT = 8000
MAX_PORT_ATTEMPTS = 10


def main():
    os.chdir(FRONTEND_ROOT)
    server = None
    for port in range(DEFAULT_PORT, DEFAULT_PORT + MAX_PORT_ATTEMPTS):
        try:
            server = ThreadingHTTPServer((HOST, port), SimpleHTTPRequestHandler)
            break
        except OSError:
            continue

    if server is None:
        raise RuntimeError(f'Não foi possível encontrar uma porta livre entre {DEFAULT_PORT} e {DEFAULT_PORT + MAX_PORT_ATTEMPTS - 1}.')

    url = f'http://{HOST}:{server.server_port}'
    print(f'Mapa disponível em: {url}')
    print('Pressione Ctrl+C para encerrar.')
    webbrowser.open(url)
    server.serve_forever()


if __name__ == '__main__':
    main()
