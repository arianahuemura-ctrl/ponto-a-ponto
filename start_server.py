
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
 
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
print('Mapa disponível em: http://localhost:8000')
print('Pressione Ctrl+C para encerrar.')
ThreadingHTTPServer(('127.0.0.1', 8000), SimpleHTTPRequestHandler).serve_forever()
 
