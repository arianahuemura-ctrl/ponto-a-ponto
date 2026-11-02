import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from transit.sptrans import short_walks


class Command(BaseCommand):
    help = 'Materializa caminhadas verificadas até 300 m apenas em pares com vagas.'

    def add_arguments(self, parser):
        parser.add_argument('--min-free-gib', type=float, default=20)

    def handle(self, *args, **options):
        try:
            result = short_walks.build(min_free_gib=options['min_free_gib'])
        except (OSError, ValueError) as error:
            raise CommandError(str(error)) from error
        report = settings.BASE_DIR/'artifacts/benchmarks'/f'short-walks-{timezone.localdate():%Y%m%d}.json'
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2))
        self.stdout.write(json.dumps(result, ensure_ascii=False))
