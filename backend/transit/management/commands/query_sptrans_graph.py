import json
import sqlite3
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import graph


class Command(BaseCommand):
    help = 'Consulta rotas e custo temporal para 0, 1 e 2 baldeações no índice persistente.'

    def add_arguments(self, parser):
        parser.add_argument('origin')
        parser.add_argument('destination')
        parser.add_argument('--database')
        parser.add_argument('--at', help='ISO 8601 com fuso, por exemplo 2026-10-07T08:00:00-03:00')
        parser.add_argument('--transfers', type=int, nargs='+', default=[0,1,2], choices=[0,1,2])
        parser.add_argument('--access-meters', type=float, default=0)
        parser.add_argument('--egress-meters', type=float, default=0)
        parser.add_argument('--max-candidates', type=int, default=10000)
        parser.add_argument('--query-seconds', type=float, default=5)

    def handle(self, *args, **options):
        try:
            result=graph.query(options['origin'],options['destination'],
                now=datetime.fromisoformat(options['at']) if options['at'] else None,
                transfers=options['transfers'],path=options['database'],
                access_seconds=options['access_meters']/graph.walking.WALK_METERS_PER_SECOND,
                egress_seconds=options['egress_meters']/graph.walking.WALK_METERS_PER_SECOND,
                max_candidates=options['max_candidates'],query_seconds=options['query_seconds'])
        except (ValueError, OSError, sqlite3.Error) as e:
            raise CommandError(str(e)) from e
        self.stdout.write(json.dumps(result,ensure_ascii=False,indent=2))
