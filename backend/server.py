from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

FRONTEND_ROOT = Path(__file__).resolve().parents[1] / 'frontend'


def main():
    os.chdir(FRONTEND_ROOT)
    print('Mapa disponível em: http://127.0.0.1:8000')
    print('Pressione Ctrl+C para encerrar.')
    ThreadingHTTPServer(('127.0.0.1', 8000), SimpleHTTPRequestHandler).serve_forever()


if __name__ == '__main__':
    main()
