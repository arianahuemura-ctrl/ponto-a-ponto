from django.core.management.base import BaseCommand
from django.conf import settings
from transit.sptrans.store import import_gtfs, database_path

class Command(BaseCommand):
    help = 'Indexa o GTFS da SPTrans em banco separado, sem modificar o cenário de Mauá.'
    def add_arguments(self, parser):
        parser.add_argument('--source', default=str(settings.BASE_DIR / 'fonts/sptrans_gtfs'))
    def handle(self, *args, **options):
        counts=import_gtfs(options['source'], database_path())
        self.stdout.write(self.style.SUCCESS(f'GTFS indexado: {counts}'))
