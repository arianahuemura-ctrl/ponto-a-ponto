"""Mesmos contratos de consulta; sem administração, avaliação ou explorador legado."""
from .urls import urlpatterns as development_patterns

urlpatterns = [pattern for pattern in development_patterns
               if not str(pattern.pattern).startswith("admin/") and str(pattern.pattern) not in {"admin/", "api/demo/evaluation/", "explorar/"}]
