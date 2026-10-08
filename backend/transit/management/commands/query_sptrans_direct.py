import json
import sqlite3
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import direct


class Command(BaseCommand):
    help='Consulta saídas, origens reversas ou o encontro A->B->C; resultado estrutural, sem previsões.'

    def add_arguments(self,parser):
        parser.add_argument('point',help='Origem na busca normal; destino na busca reversa.')
        parser.add_argument('other',nargs='?',help='Destino na busca normal; origem na reversa.')
        parser.add_argument('--reverse',action='store_true')
        parser.add_argument('--transfer',action='store_true',help='Uma baldeação no mesmo ponto; exige dois pontos.')
        parser.add_argument('--limit',type=int,default=16)
        parser.add_argument('--seconds',type=float,default=5)
        parser.add_argument('--database')

    def handle(self,*args,**o):
        try:
            if o['transfer']:
                if not o['other'] or o['reverse']:raise ValueError('--transfer exige origem e destino, sem --reverse.')
                result=direct.transfers(o['point'],o['other'],o['limit'],o['seconds'],o['database'])
            else:result=direct.lookup(o['point'],o['reverse'],o['other'],o['limit'],o['database'])
        except (ValueError,KeyError,OSError,sqlite3.Error) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(json.dumps(result,ensure_ascii=False,indent=2))
