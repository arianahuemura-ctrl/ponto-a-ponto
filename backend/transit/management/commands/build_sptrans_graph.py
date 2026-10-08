from mbm import routing_config as config
import json
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import graph


class Command(BaseCommand):
    help = 'Constrói índices persistentes de ônibus e candidatos a caminhada, sem chamadas externas.'

    def add_arguments(self, parser):
        parser.add_argument('--database', help='SQLite de saída; padrão: <GTFS>.routing.sqlite3')
        parser.add_argument('--walk-radius', type=float, default=config.WALK_LIMIT_METERS)

    def handle(self, *args, **options):
        try:
            result = graph.build(target=options['database'], walk_radius=options['walk_radius'], progress=self.stderr.write)
        except (ValueError, OSError, sqlite3.Error) as e:
            raise CommandError(str(e)) from e
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
