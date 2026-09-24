# Entrada compatível para iniciar o servidor Django de desenvolvimento.
import os
import sys
from pathlib import Path


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mbm.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(
        [sys.argv[0], "runserver", *(sys.argv[1:] or ["127.0.0.1:8000"])]
    )


if __name__ == "__main__":
    main()
