import json
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import city_connections


class Command(BaseCommand):
    help = 'Prepara componentes estruturais; execute materialize_sptrans_connections para persistir trajetos.'

    def add_arguments(self, p):
        p.add_argument('--direct-database')
        p.add_argument('--graph-database')
        p.add_argument('--walk-database',help='Artefato de distâncias por rede pedestre local.')
        p.add_argument('--database')

    def handle(self, *args, **o):
        try:
            result=city_connections.build(source=o['direct_database'], graph_source=o['graph_database'],
                target=o['database'], progress=self.stderr.write, walk_source=o['walk_database'])
        except (ValueError, KeyError, OSError, sqlite3.Error) as e:
            raise CommandError(str(e)) from e
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
