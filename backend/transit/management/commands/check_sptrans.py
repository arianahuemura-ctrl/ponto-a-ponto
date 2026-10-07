from django.core.management.base import BaseCommand, CommandError
from transit.sptrans.client import client, APIError

class Command(BaseCommand):
    help = 'Verifica autenticação e acesso ao Olho Vivo sem revelar a credencial.'
    def handle(self,*args,**options):
        try:
            data=client.get('Posicao')
        except APIError as error:
            raise CommandError(str(error)) from None
        lines=data.get('l',[])
        self.stdout.write(self.style.SUCCESS(f"API acessível · referência {data.get('hr')} · {len(lines)} linhas · {sum(len(line.get('vs',[])) for line in lines)} veículos"))
