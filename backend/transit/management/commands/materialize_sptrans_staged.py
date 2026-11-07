import json
import math
import sqlite3
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from django.utils import timezone
from transit.sptrans import staged_materialized as staged


class Command(BaseCommand):
    help='Materializa toda a rede por custo: zero primeiro, depois até um (ferroviário = 1/3).'

    def add_arguments(self,p):
        p.add_argument('--stages',nargs='+',type=int,choices=(0,1),default=[0,1])
        p.add_argument('--database',type=Path)
        p.add_argument('--walks',type=Path,help='Base pedestre verificada, necessária para preparar uma nova saída.')
        p.add_argument('--min-free-gib',type=float,default=20)
        p.add_argument('--workers',type=int,default=1,choices=range(1,33))
        p.add_argument('--short-walks',action='store_true',help='Inclui caminhadas de até 300 m e preserva suas vagas ao ampliar para custo um.')

    def handle(self,*args,**options):
        if not math.isfinite(options['min_free_gib']) or options['min_free_gib']<0:raise CommandError('Reserva de disco inválida.')
        path=options['database'] or staged.database_path()
        try:
            if options['walks']:staged.prepare(options['walks'],target=path,progress=self.stdout.write)
            if not path.exists():raise ValueError('Prepare a fonte com --walks CAMINHO antes de materializar.')
            for stage in sorted(set(options['stages'])):
                if options['workers']>1:
                    from transit.sptrans import staged_parallel
                    result=staged_parallel.build(stage,path,workers=options['workers'],min_free_gib=options['min_free_gib'],progress=self.stdout.write)
                else:
                    result=staged.build(stage,path,min_free_gib=options['min_free_gib'],progress=self.stdout.write)
                if options['short_walks']:
                    from transit.sptrans import short_walks,walking_slots
                    result['walking']=(walking_slots.reserve(path,progress=self.stdout.write,min_free_gib=options['min_free_gib']) if stage else short_walks.build(path,min_free_gib=options['min_free_gib']))
                    with sqlite3.connect(path) as db:
                        result['routes']=db.execute('SELECT sum(paths) FROM progress WHERE stage=?',(stage,)).fetchone()[0]
                    result['bytes']=path.stat().st_size
                with sqlite3.connect(path) as db:
                    if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Falha de integridade.')
                report=settings.BASE_DIR/'artifacts/benchmarks'/f'staged-cost-{stage}-{timezone.localdate():%Y%m%d}.json'
                report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2))
                self.stdout.write(json.dumps(result,ensure_ascii=False))
                if not result['complete']:raise ValueError('Etapa incompleta; a próxima não será iniciada.')
        except (OSError,ValueError,sqlite3.Error) as error:raise CommandError(str(error)) from error
