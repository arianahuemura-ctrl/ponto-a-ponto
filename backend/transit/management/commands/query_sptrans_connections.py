import json
import sqlite3
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import graph, catalog, connection_planner, walking


class Command(BaseCommand):
    help = 'Consulta o catálogo 16/8/4 e refina até cinco alternativas; --stream emite NDJSON.'

    def add_arguments(self,p):
        p.add_argument('origin');p.add_argument('destination');p.add_argument('--database')
        p.add_argument('--at',help='Instante ISO 8601 com fuso; com --at o modo é offline.')
        p.add_argument('--offline',action='store_true',help='Não consultar Olho Vivo.')
        p.add_argument('--stream',action='store_true');p.add_argument('--structure',action='store_true')
        p.add_argument('--access-meters',type=float,default=0);p.add_argument('--egress-meters',type=float,default=0)
        p.add_argument('--max-transfers',type=int,choices=[0,1,2],default=2)

    def handle(self,*args,**o):
        try:
            path=o['database'] or graph.graph_path()
            if o['structure']:
                with graph.connection(path) as db:
                    rows,meta=catalog.candidates(db,o['origin'],o['destination'])
                    result={'origem':o['origin'],'destino':o['destination'],'trajetos':[catalog.describe(db,r) for r in rows],'catalog':meta}
                self.stdout.write(json.dumps(result,ensure_ascii=False,indent=2));return
            kwargs={'now':datetime.fromisoformat(o['at']) if o['at'] else None,'path':path,
                'access_seconds':o['access_meters']/walking.WALK_METERS_PER_SECOND,
                'egress_seconds':o['egress_meters']/walking.WALK_METERS_PER_SECOND,
                'operational':not(o['offline'] or o['at']),'max_transfers':o['max_transfers']}
            result=None
            for result in connection_planner.progressive(o['origin'],o['destination'],**kwargs):
                if o['stream']:self.stdout.write(json.dumps(result,ensure_ascii=False))
            if not o['stream']:self.stdout.write(json.dumps(result,ensure_ascii=False,indent=2))
        except (ValueError,KeyError,OSError,sqlite3.Error) as e:
            raise CommandError(str(e)) from e
