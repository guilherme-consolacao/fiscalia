from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from feeds.models import NewsImportJob, Workspace
from feeds.services.news_import_jobs import run_news_import_job


class Command(BaseCommand):
    help = 'Executa coletas pendentes de um espaço e recupera atualizações interrompidas.'

    def add_arguments(self, parser):
        parser.add_argument('--workspace', type=int, required=True)
        parser.add_argument('--recover-stale', action='store_true', help='Marca como falhas execuções sem atualização há mais de 30 minutos.')

    def handle(self, *args, **options):
        if not Workspace.objects.filter(pk=options['workspace']).exists():
            raise CommandError('Espaço não encontrado.')
        jobs = NewsImportJob.all_objects.filter(workspace_id=options['workspace'])
        if options['recover_stale']:
            count = jobs.filter(status='running', updated_at__lt=timezone.now()-timedelta(minutes=30)).update(status='failed',current_stage='failed',error_message='A execução foi interrompida. Inicie uma nova atualização.',finished_at=timezone.now())
            self.stdout.write(f'{count} execução(ões) interrompida(s) encerrada(s).')
        for job_id in jobs.filter(status='pending').values_list('pk',flat=True):
            run_news_import_job(job_id)
        self.stdout.write(self.style.SUCCESS('Fila processada.'))
