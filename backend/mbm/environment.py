"""Configuração compartilhada: exemplo < arquivo local < ambiente do processo."""
import os
from pathlib import Path
from dotenv import dotenv_values


def load_environment(root=None, environ=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    environ = os.environ if environ is None else environ
    # Valores literais: não expanda referências usando um ambiente parcial.
    values = {**dotenv_values(root / '.env.example', interpolate=False),
              **dotenv_values(root / '.env', interpolate=False)}
    for key, value in values.items():
        if value is not None:
            environ.setdefault(key, value)
    return environ
