import json
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import direct


class Command(BaseCommand):
    help='Gera conexões diretas e índice reverso de toda a cidade, percorrendo os padrões GTFS.'

    def add_arguments(self,parser):
        parser.add_argument('--graph-database',help='Grafo pré-processado com shapes/projeções.')
        parser.add_argument('--database',help='Saída; padrão <GTFS>.direct.sqlite3, substituição atômica.')

    def handle(self,*args,**options):
        try:
            result=direct.build(source=options['graph_database'],target=options['database'],progress=self.stderr.write)
        except (ValueError,KeyError,OSError,sqlite3.Error) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps(result,ensure_ascii=False,indent=2))
