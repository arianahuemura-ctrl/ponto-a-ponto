import json
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import graph


class Command(BaseCommand):
    help = 'Enriquece candidatos com trajetos a pé verificados, em lote limitado ou por arquivo JSONL.'

    def add_arguments(self, parser):
        parser.add_argument('--database')
        parser.add_argument('--limit', type=int, default=0, help='Máximo de consultas ao roteador a pé; padrão 0.')
        parser.add_argument('--origin', action='append', help='Restringir às saídas deste ponto; pode repetir.')
        parser.add_argument('--file', help='JSONL: origin, destination e result (resposta de walking.route).')

    def handle(self, *args, **options):
        path = options['database'] or graph.graph_path()
        try:
            with graph.connection(path):
                pass
            count=0
            if options['file']:
                with open(options['file'], encoding='utf-8') as stream, sqlite3.connect(path) as db:
                    db.row_factory=sqlite3.Row
                    for line in stream:
                        if not line.strip():
                            continue
                        row=json.loads(line)
                        graph.put_walk(db,str(row['origin']),str(row['destination']),row['result'])
                        count+=1
            result=graph.verify_walks(path,limit=options['limit'],origins=options['origin'])
        except (ValueError, OSError, sqlite3.Error, KeyError) as e:
            raise CommandError(str(e)) from e
        self.stdout.write(json.dumps({'imported':count,'checked':result},ensure_ascii=False))
