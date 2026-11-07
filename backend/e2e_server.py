"""Servidor para testes: SQLite descartável, sem alterar avaliações de usuários."""

import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="mbm-e2e-") as directory:
    os.environ["MBM_DATABASE"] = str(Path(directory) / "test.sqlite3")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mbm.settings")
    import django

    django.setup()
    from django.core.management import call_command

    call_command("migrate", verbosity=0)
    from django.contrib.auth import get_user_model
    from transit.models import Simulation
    from transit.importing import import_demo
    from django.conf import settings
    settings.PAP_USABILITY_DB = Path(directory) / "telemetry.sqlite3"
    settings.PAP_RESEARCH_DB = Path(directory) / "research.sqlite3"
    import_demo(settings.BASE_DIR)

    # Credenciais exclusivamente do servidor efêmero de testes.
    get_user_model().objects.create_superuser(
        "test-admin", password="temporary-e2e-password"
    )
    Simulation.objects.create(pk=1, enabled=True, running=False, seconds=28800)
    call_command("runserver", "127.0.0.1:18081", use_reloader=False)
