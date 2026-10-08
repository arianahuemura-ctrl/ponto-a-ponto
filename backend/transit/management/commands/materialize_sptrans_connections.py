from mbm import routing_config as config
import json
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import materialized_connections as materialized


class Command(BaseCommand):
    help='Materializa TOP 16/8 conexões físicas offline, com retomada por par/categoria.'

    def add_arguments(self,p):
        p.add_argument('--experimental',action='store_true',help='Heurísticas de cobertura/convergência; saída separada .materialized.heuristics.sqlite3.')
        p.add_argument('--source',help='Componentes gerados por build_sptrans_city_connections.')
        p.add_argument('--database',help='Saída física; padrão sptrans.materialized.sqlite3.')
        scope=p.add_mutually_exclusive_group(required=True)
        scope.add_argument('--pairs-file',help='JSON: lista de pares [A,B] ou objeto pairs com a/b.')
        scope.add_argument('--all',action='store_true',help='Percorre pares alcançáveis por até dois ônibus.')
        scope.add_argument('--origin',action='append',help='Gera todos os destinos alcançáveis destas origens.')
        p.add_argument('--seconds',type=float,default=config.ROUTE_SECONDS,help='Limite offline por categoria; pendências podem ser retomadas.')
        p.add_argument('--min-free-gib',type=float,default=config.MIN_FREE_GIB,help='Reserva mínima de disco para interromper e retomar.')

    def handle(self,*args,**o):
        try:
            if o['min_free_gib']<0:raise ValueError('Reserva de disco negativa.')
            if o['pairs_file']:
                with open(o['pairs_file']) as f:data=json.load(f)
                if isinstance(data,dict):data=data['pairs']
                pairs=[(p['a'],p['b']) if isinstance(p,dict) else tuple(p) for p in data]
                if any(len(p)!=2 for p in pairs):raise ValueError('Cada par deve ter origem e destino.')
            else:pairs=materialized.city_pairs(o['source'],o['origin'])
            result=materialized.materialize(pairs,source=o['source'],target=o['database'],
                seconds=o['seconds'],experimental=o['experimental'],min_free_bytes=o['min_free_gib']*1024**3,progress=self.stderr.write)
            if o['all']:
                with sqlite3.connect(result['database']) as db:
                    meta=materialized._read_meta(db)
                    meta['city_complete']=result['timed_out_categories']==0
                    db.execute('UPDATE materialization_meta SET value=? WHERE id=1',(json.dumps(meta),))
            self.stdout.write(json.dumps(result,ensure_ascii=False,indent=2))
        except (ValueError,KeyError,OSError,sqlite3.Error) as e:raise CommandError(str(e)) from e
