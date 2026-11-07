"""A porta pública nunca escuta na LAN; somente cloudflared local pode encaminhar."""
bind = "127.0.0.1:8001"
workers = 1
worker_class = "gthread"
threads = 4
timeout = 120
graceful_timeout = 30
forwarded_allow_ips = "127.0.0.1,::1"
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
accesslog = "-"
# Não registrar query string: pode conter localização ou destino do passageiro.
access_log_format = '%(t)s %(m)s %(U)s %(s)s %(L)s'
errorlog = "-"
capture_output = True
