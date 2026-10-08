import json
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import city_connections


class Command(BaseCommand):
    help = 'Retorna as 16/8/4 conexões estruturais mais curtas com 1/2/3 ônibus.'

    def add_arguments(self, p):
        p.add_argument('origin')
        p.add_argument('destination')
        p.add_argument('--database')

    def handle(self, *args, **o):
        try:
            result=city_connections.query(o['origin'], o['destination'], path=o['database'])
        except (ValueError, KeyError, OSError, sqlite3.Error) as e:
            raise CommandError(str(e)) from e
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
