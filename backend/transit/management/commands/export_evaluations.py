import json
from django.core.management.base import BaseCommand
from transit.models import Evaluation


class Command(BaseCommand):
    help = "Exporta observações da demonstração em JSON, sem disponibilizá-las publicamente."

    def handle(self, *args, **options):
        rows = [
            {
                "id": e.pk,
                "created_at": e.created_at.isoformat(),
                "scenario": e.scenario,
                "notes": e.notes,
            }
            for e in Evaluation.objects.order_by("pk")
        ]
        self.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2))
