from mbm import routing_config as config
import json
import sqlite3
from django.core.management.base import BaseCommand,CommandError
from transit.sptrans import walk_artifacts

class Command(BaseCommand):
    help='Calcula caminhadas até o limite configurado entre paradas via rede OSRM foot local.'
    def add_arguments(self,p):
        p.add_argument('--router',required=True)
        p.add_argument('--network-id',required=True)
        p.add_argument('--graph-database')
        p.add_argument('--database')
        p.add_argument('--workers',type=int,default=config.WALK_WORKERS)
    def handle(self,*args,**o):
        try:
            result=walk_artifacts.build(o['router'],o['network_id'],source=o['graph_database'],
                target=o['database'],workers=o['workers'],progress=self.stderr.write)
        except (ValueError,OSError,sqlite3.Error,KeyError) as e:
            raise CommandError(str(e)) from e
        self.stdout.write(json.dumps(result,ensure_ascii=False,indent=2))
