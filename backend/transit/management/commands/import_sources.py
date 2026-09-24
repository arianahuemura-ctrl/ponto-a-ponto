from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from transit.importing import import_demo, import_collected, import_osm


class Command(BaseCommand):
    help = "Importa fontes locais em fonts para o SQLite; --download coleta novamente as fontes públicas."

    def add_arguments(self, parser):
        parser.add_argument("--download", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Importa explicitamente o cenário de demonstração",
        )
        parser.add_argument(
            "--directory", type=Path, default=settings.BASE_DIR / "fonts"
        )

    def handle(self, *args, **options):
        folder = options["directory"]
        try:
            if options["download"]:
                from fonts.collect import Collector

                if folder.resolve() != (settings.BASE_DIR / "fonts").resolve():
                    raise ValueError(
                        "Download disponível somente no diretório fonts do projeto"
                    )
                Collector(options["refresh"]).run()
            if options["demo"]:
                self.stdout.write(f"Demonstração: {import_demo(settings.BASE_DIR)}")
            if (folder / "collected.json").exists():
                self.stdout.write(f"Fontes externas: {import_collected(folder)}")
                from transit.models import SourceDocument

                for document in SourceDocument.objects.filter(status="error"):
                    self.stderr.write(
                        f"Fonte indisponível: {document.provider}: {document.metadata.get('error', '')}"
                    )
            if (folder / "osm.json").exists():
                self.stdout.write(f"OSM: {import_osm(folder / 'osm.json')}")
            if (
                not options["demo"]
                and not (folder / "collected.json").exists()
                and not (folder / "osm.json").exists()
            ):
                raise ValueError("Nenhum arquivo encontrado; execute com --download")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(str(exc)) from exc
