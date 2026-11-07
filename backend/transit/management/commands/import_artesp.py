"""Merge ARTESP into a new catalogue without modifying the active source."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from transit.sptrans import merged_gtfs, store


class Command(BaseCommand):
    help='Importa um ZIP GTFS ARTESP em uma nova base combinada com a SPTrans.'

    def add_arguments(self,p):
        p.add_argument('--archive',required=True,type=Path)
        p.add_argument('--database',required=True,type=Path)
        p.add_argument('--base',type=Path)
        p.add_argument('--report',type=Path)

    def handle(self,*args,**options):
        try:
            report=merged_gtfs.merge(options['base'] or store.database_path(),options['archive'],options['database'],progress=lambda message,**kw:self.stdout.write(message))
            if options['report']:
                options['report'].write_text(json.dumps(report,ensure_ascii=False,indent=2))
            self.stdout.write(json.dumps(report,ensure_ascii=False))
        except (OSError,ValueError) as error:
            raise CommandError(str(error)) from error
