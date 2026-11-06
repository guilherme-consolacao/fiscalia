from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from uuid import uuid4
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone
from feeds.models import NewsImportJob, NewsItem, Membership, NewsItemAnalysis
from feeds.services import news_import_jobs as jobs
from feeds.services.news_import import NewsImportResult
from feeds.services.news_analysis import NewsAnalysisBatchExecutionResult
from feeds.tenancy import workspace_scope
from feeds.tests.scenarios import WorkspaceScenario


class ImportWorkerContracts(WorkspaceScenario):
    def test_worker_claims_once_and_restores_callers_workspace(self):
        def importer(progress_callback):
            self.assertEqual(list(NewsItem.objects.values_list('pk', flat=True)), [self.item.pk])
            progress_callback('rss_start', total_sources=1, analysis_enabled=False)
            return NewsImportResult(created_count=2, source_count=1)
        with workspace_scope(self.foreign_space.pk), patch('feeds.services.news_import_jobs.import_news_items', side_effect=importer) as execute:
            jobs.run_news_import_job(self.job.pk)
            jobs.run_news_import_job(self.job.pk)
            self.assertEqual(NewsItem.objects.get().pk, self.foreign_item.pk)
        self.assertEqual(execute.call_count, 1)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'completed')
        self.assertEqual(self.job.imported_created_count, 2)
        self.assertIsNotNone(self.job.finished_at)

    def test_failure_marks_job_terminal_without_exposing_exception(self):
        with patch('feeds.services.news_import_jobs.import_news_items', side_effect=RuntimeError('sensitive-internal-detail')), self.assertLogs(jobs.logger, level='ERROR'):
            jobs.run_news_import_job(self.job.pk)
        self.job.refresh_from_db()
        self.assertEqual((self.job.status, self.job.current_stage), ('failed', 'failed'))
        self.assertNotIn('sensitive-internal-detail', self.job.error_message)
        self.assertIsNotNone(self.job.finished_at)

    def test_missing_job_is_logged_without_import(self):
        with patch('feeds.services.news_import_jobs.import_news_items') as importer, self.assertLogs(jobs.logger, level='WARNING'):
            jobs.run_news_import_job(uuid4())
        importer.assert_not_called()

    def test_background_thread_is_configured_without_running_network(self):
        with patch('feeds.services.news_import_jobs.Thread') as thread:
            worker = jobs.start_news_import_job(self.job.pk)
        thread.assert_called_once()
        self.assertTrue(thread.call_args.kwargs['daemon'])
        self.assertEqual(thread.call_args.kwargs['args'], (self.job.pk,))
        worker.start.assert_called_once()
        with patch('feeds.services.news_import_jobs.connections.close_all') as close, \
                patch('feeds.services.news_import_jobs.run_news_import_job', side_effect=RuntimeError('falha')) as run:
            with self.assertRaises(RuntimeError):
                thread.call_args.kwargs['target'](self.job.pk)
        run.assert_called_once_with(self.job.pk)
        close.assert_called_once()

    def test_only_one_pending_or_running_job_is_allowed_per_workspace(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            NewsImportJob.objects.create(status='running')
        self.assertEqual(NewsImportJob.objects.count(), 1)
        self.job.status = 'completed'
        self.job.save(update_fields=['status'])
        self.assertEqual(NewsImportJob.objects.create(status='pending').workspace_id, self.space.pk)

    def test_reporter_progress_and_terminal_messages_are_bounded(self):
        reporter = jobs.NewsImportJobReporter(self.job)
        reporter.mark_started()
        reporter.handle_event('unknown_event', ignored=True)
        reporter.handle_event('rss_start', total_sources=2, analysis_enabled=True)
        reporter.handle_event('rss_progress', processed_sources=1, total_sources=2, source_name='Fonte', created_count=2, existing_count=1, error_count=0, skipped_count=0, queued_analysis_count=3)
        self.job.refresh_from_db()
        self.assertEqual(self.job.rss_progress_percent, 50)
        reporter.handle_event('analysis_start', total_items=3, analysis_enabled=True)
        reporter.handle_event('analysis_progress', processed_count=2, total_count=3, updated_count=1, failed_count=1, skipped_count=0, halted=True)
        self.job.refresh_from_db()
        self.assertIn('interrompida', self.job.stage_title)
        self.assertEqual(self.job.analysis_progress_percent, 66)
        self.job.rss_processed_sources = 50
        self.assertEqual(self.job.rss_progress_percent, 100)
        self.job.analysis_processed_items = 50
        self.assertEqual(self.job.analysis_progress_percent, 100)
        reporter.mark_completed(NewsImportResult(created_count=2, source_count=2, analysis_failure_count=1))
        self.job.refresh_from_db()
        self.assertTrue(self.job.is_finished)
        self.assertIn('sem análise', self.job.stage_message)


class ManagementCommandContracts(WorkspaceScenario):
    def command(self, name, **kwargs):
        output = StringIO()
        call_command(name, stdout=output, **kwargs)
        return output.getvalue()

    def test_admin_bootstrap_is_idempotent_and_does_not_grant_platform_staff(self):
        user = self.users['reader']
        for _ in range(2):
            self.command('grant_workspace_admin', username=user.username, workspace=self.space.pk)
        access = Membership.objects.get(workspace=self.space, user=user)
        user.refresh_from_db()
        self.assertEqual(access.role, 'admin')
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(Membership.objects.filter(workspace=self.foreign_space, user=user).count(), 0)

    def test_admin_bootstrap_refuses_missing_or_inactive_accounts_and_spaces(self):
        for username, workspace in (('absent', self.space.pk), (self.users['reader'].username, 999999)):
            with self.subTest(username=username), self.assertRaises(CommandError):
                self.command('grant_workspace_admin', username=username, workspace=workspace)
        self.users['reader'].is_active = False
        self.users['reader'].save(update_fields=['is_active'])
        with self.assertRaises(CommandError):
            self.command('grant_workspace_admin', username=self.users['reader'].username, workspace=self.space.pk)

    def test_commands_require_an_explicit_existing_workspace(self):
        for command in ('backfill_news_analysis', 'process_news_jobs'):
            with self.subTest(command=command):
                with self.assertRaises(CommandError):
                    self.command(command)
                with self.assertRaises(CommandError):
                    self.command(command, workspace=999999)
        with self.assertRaises(CommandError):
            self.command('backfill_news_analysis', workspace=self.space.pk, limit=-1)

    def test_queue_command_executes_only_pending_jobs_in_selected_workspace(self):
        with patch('feeds.management.commands.process_news_jobs.run_news_import_job') as execute:
            self.command('process_news_jobs', workspace=self.space.pk)
        execute.assert_called_once_with(self.job.pk)

    def test_queue_recovery_does_not_modify_other_workspaces_or_recent_jobs(self):
        stale = timezone.now() - timedelta(minutes=40)
        NewsImportJob.all_objects.filter(pk__in=[self.job.pk, self.foreign_job.pk]).update(status='running', updated_at=stale)
        with patch('feeds.management.commands.process_news_jobs.run_news_import_job') as execute:
            output = self.command('process_news_jobs', workspace=self.space.pk, recover_stale=True)
        self.assertIn('1 execução', output)
        execute.assert_not_called()
        self.job.refresh_from_db()
        self.foreign_job.refresh_from_db()
        self.assertEqual(self.job.status, 'failed')
        self.assertEqual(self.foreign_job.status, 'running')
        self.assertIsNotNone(self.job.finished_at)

    def test_backfill_honors_workspace_limit_batching_and_provider_stop(self):
        for i in range(4):
            NewsItem.objects.create(source=self.source, title=f'Pendente {i}', link=f'https://example.com/{i}', dedupe_key=str(i))
        service = MagicMock(batch_size=1)
        service.analyze_news_items.return_value = NewsAnalysisBatchExecutionResult(updated_count=1)
        with patch('feeds.management.commands.backfill_news_analysis.build_news_analysis_service', return_value=(service, '')):
            self.command('backfill_news_analysis', workspace=self.space.pk, limit=2)
        self.assertEqual(service.analyze_news_items.call_count, 2)
        self.assertTrue(all(item.workspace_id == self.space.pk for call in service.analyze_news_items.call_args_list for item in call.args[0]))
        service.reset_mock()
        service.analyze_news_items.return_value = NewsAnalysisBatchExecutionResult(halted=True, halted_pending_count=3, halt_reason='Limite simulado')
        with patch('feeds.management.commands.backfill_news_analysis.build_news_analysis_service', return_value=(service, '')):
            output = self.command('backfill_news_analysis', workspace=self.space.pk)
        self.assertEqual(service.analyze_news_items.call_count, 1)
        self.assertIn('interrompido', output)

    def test_backfill_does_not_analyze_when_disabled_or_already_current(self):
        with patch('feeds.management.commands.backfill_news_analysis.build_news_analysis_service', return_value=(None, 'Desativada')):
            self.assertIn('Desativada', self.command('backfill_news_analysis', workspace=self.space.pk))
        NewsItemAnalysis.objects.filter(news_item=self.item).update(pipeline_version='v1', status='completed')
        service = MagicMock(batch_size=5)
        with patch('feeds.management.commands.backfill_news_analysis.build_news_analysis_service', return_value=(service, '')):
            self.command('backfill_news_analysis', workspace=self.space.pk)
        service.analyze_news_items.assert_not_called()
