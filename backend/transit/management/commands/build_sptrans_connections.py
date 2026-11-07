import csv
import json
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import graph, catalog, costs


class Command(BaseCommand):
    help = 'Instala o artefato conexões e materializa os 16/8/4 menores trajetos dos pares solicitados.'

    def add_arguments(self,parser):
        parser.add_argument('--database')
        parser.add_argument('--pair',nargs=2,action='append',metavar=('ORIGEM','DESTINO'))
        parser.add_argument('--pairs-file',help='CSV com colunas origin,destination; processado incrementalmente.')
        parser.add_argument('--seconds',type=float,default=60,help='Limite por par/categoria; cancelamentos são marcados incompletos.')
        parser.add_argument('--force',action='store_true')
        parser.add_argument('--profiles',help='CSV de perfis históricos de circulação, com procedência.')

    def handle(self,*args,**options):
        try:
            path=catalog.install(options['database'])
            with sqlite3.connect(path,timeout=30) as db:
                db.row_factory=sqlite3.Row
                if options['profiles']:
                    count=costs.import_profiles(db,options['profiles']);db.commit()
                    self.stdout.write(json.dumps({'profiles_imported':count}))
                def pairs():
                    yield from options['pair'] or []
                    if options['pairs_file']:
                        with open(options['pairs_file'],encoding='utf-8-sig',newline='') as f:
                            for row in csv.DictReader(f):yield str(row['origin']),str(row['destination'])
                for origin,destination in pairs():
                    result=catalog.build_pair(db,origin,destination,options['seconds'],options['force'])
                    db.commit();self.stdout.write(json.dumps(result,ensure_ascii=False))
                self.stdout.write(json.dumps({'database':str(path),'counts':{t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]
                    for t in ('connection_segments','connection_pairs','connections','historical_profiles')},
                    'walking_coverage':json.loads(db.execute('SELECT value FROM graph_meta').fetchone()[0]).get('walk_status_counts',{})},ensure_ascii=False))
        except (ValueError,KeyError,OSError,sqlite3.Error) as e:
            raise CommandError(str(e)) from e
