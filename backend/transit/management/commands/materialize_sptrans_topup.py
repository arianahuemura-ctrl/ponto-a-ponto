import json
import math
import sqlite3
from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from django.utils import timezone
from transit.sptrans import topup_materialized as topup,staged_materialized as staged

class Command(BaseCommand):
    help='Completa vagas até cinco rotas por par com custo até quatro.'
    def add_arguments(self,p):
        p.add_argument('--max-cost',type=int,choices=(4,),default=4)
        p.add_argument('--workers',type=int,choices=range(1,17),default=4)
        p.add_argument('--min-free-gib',type=float,default=20)
    def handle(self,*args,**options):
        reserve=options['min_free_gib']
        if not math.isfinite(reserve) or reserve<0:raise CommandError('Reserva inválida.')
        try:
            result=topup.build(workers=options['workers'],min_free_gib=reserve,progress=self.stdout.write)
            if result['complete']:
                self.stdout.write('Conferindo integridade do banco completo...')
                with sqlite3.connect(staged.database_path()) as db:
                    if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Falha de integridade.')
                result['integrity']='ok'
            report=settings.BASE_DIR/'artifacts/benchmarks'/f'topup-through-4-{timezone.localdate():%Y%m%d}.json'
            report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2))
            self.stdout.write(json.dumps(result,ensure_ascii=False))
        except (OSError,ValueError,RuntimeError,sqlite3.Error) as error:raise CommandError(str(error)) from error
