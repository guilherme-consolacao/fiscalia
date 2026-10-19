from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from feeds.models import Membership, Workspace


class Command(BaseCommand):
    help = 'Concede administração de um espaço a uma conta existente. Uso exclusivo do operador local da plataforma.'

    def add_arguments(self, parser):
        parser.add_argument('--workspace', type=int, required=True)
        parser.add_argument('--username', required=True)

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options['username'], is_active=True).first()
        workspace = Workspace.objects.filter(pk=options['workspace']).first()
        if not user or not workspace:
            raise CommandError('Conta ativa ou espaço não encontrado.')
        Membership.objects.update_or_create(user=user, workspace=workspace, defaults={'role':'admin', 'active':True})
        self.stdout.write(self.style.SUCCESS('Administrador do espaço definido.'))
