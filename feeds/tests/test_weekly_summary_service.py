import json
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch, MagicMock
import requests
from django.test import override_settings
from django.utils import timezone
from feeds.models import DashboardWeeklySummary, NewsItem, NewsItemAnalysis, NewsImportJob
from feeds.services import dashboard_weekly_summary as summaries
from feeds.tenancy import workspace_scope
from feeds.tests.scenarios import WorkspaceScenario
from feeds.tests.test_news import build_ai_settings, DummyJsonResponse


@override_settings(NEWS_AI=build_ai_settings())
class WeeklySummaryServiceTests(WorkspaceScenario):
    def setUp(self):
        super().setUp()
        self.job.status = 'completed'
        self.job.save(update_fields=['status'])
        self.week_start, self.week_end = summaries.get_current_week_range()
        closer = patch('feeds.services.dashboard_weekly_summary.close_old_connections')
        closer.start()
        self.addCleanup(closer.stop)

    def summary(self, **changes):
        defaults = {'week_end': self.week_end, 'status': 'running', 'started_at': timezone.now()}
        defaults.update(changes)
        return DashboardWeeklySummary.objects.create(week_start=self.week_start, **defaults)

    def response(self, content=None, **kwargs):
        content = content or {'overview': 'Visão da semana', 'main_changes': 'Mudanças fiscais', 'attention': 'Atenção aos prazos'}
        return DummyJsonResponse({'output_text': json.dumps(content)}, **kwargs)

    def test_week_boundary_uses_local_timezone(self):
        sunday_night = datetime(2026, 10, 19, 1, tzinfo=dt_timezone.utc)
        start, end = summaries.get_current_week_range(sunday_night)
        self.assertEqual((start.isoformat(), end.isoformat()), ('2026-10-12', '2026-10-18'))

    def test_worker_persists_provider_output_only_in_its_workspace(self):
        summary = self.summary()
        with workspace_scope(self.foreign_space.pk):
            foreign = self.summary()
            with patch('feeds.services.dashboard_weekly_summary.requests.post', return_value=self.response()) as post:
                summaries.run_dashboard_weekly_summary_job(summary.pk, summary.revision)
            self.assertIn(self.foreign_item.title, list(NewsItem.objects.values_list('title', flat=True)))
        summary.refresh_from_db()
        foreign.refresh_from_db()
        self.assertEqual(summary.status, 'completed')
        self.assertEqual(summary.news_count, 1)
        self.assertEqual(foreign.status, 'running')
        payload = post.call_args.kwargs['json']['input'][1]['content'][0]['text']
        self.assertIn(self.item.title, payload)
        self.assertNotIn(self.foreign_item.title, payload)

    def test_stale_revision_cannot_overwrite_newer_summary(self):
        summary = self.summary(revision=2, overview='Versão atual')
        with patch('feeds.services.dashboard_weekly_summary.requests.post') as post:
            summaries.run_dashboard_weekly_summary_job(summary.pk, 1)
        post.assert_not_called()
        summary.refresh_from_db()
        self.assertEqual(summary.overview, 'Versão atual')
        summaries._persist_summary_failure(summary.pk, 1, 'Falha antiga')
        summary.refresh_from_db()
        self.assertEqual(summary.status, 'running')

    def test_invalidation_clears_old_content_and_advances_revision(self):
        summary = self.summary(status='completed', overview='Antigo', main_changes='Antigas mudanças', attention='Antes')
        summaries.invalidate_current_week_summary()
        summary.refresh_from_db()
        self.assertEqual(summary.revision, 2)
        self.assertEqual(summary.status, 'pending')
        self.assertEqual(summary.overview, '')
        self.assertIsNone(summary.started_at)

    def test_empty_week_does_not_call_the_provider(self):
        self.item.published_at = timezone.now() - timedelta(days=40)
        self.item.save(update_fields=['published_at'])
        NewsItemAnalysis.objects.filter(news_item=self.item).update(effective_date=None)
        summary = self.summary()
        with patch('feeds.services.dashboard_weekly_summary.requests.post') as post:
            summaries.run_dashboard_weekly_summary_job(summary.pk, summary.revision)
        post.assert_not_called()
        summary.refresh_from_db()
        self.assertEqual(summary.status, 'completed')
        self.assertEqual(summary.news_count, 0)

    def test_no_news_is_ready_and_no_summary_or_worker_is_created(self):
        NewsItem.objects.all().delete()
        with patch('feeds.services.dashboard_weekly_summary.start_dashboard_weekly_summary_job') as start:
            payload = summaries.get_current_week_summary_state(start_async=True)
        self.assertTrue(payload['is_ready'])
        self.assertEqual(DashboardWeeklySummary.objects.count(), 0)
        start.assert_not_called()

    def test_active_import_prevents_generation_but_foreign_import_does_not(self):
        self.job.status = 'pending'
        self.job.save(update_fields=['status'])
        with patch('feeds.services.dashboard_weekly_summary.start_dashboard_weekly_summary_job') as start:
            state = summaries.get_current_week_summary_state(start_async=True)
            start.assert_not_called()
            self.assertIn('fontes estão sendo atualizadas', state['message'])
            self.job.status = 'completed'
            self.job.save(update_fields=['status'])
            summaries.get_current_week_summary_state(start_async=True)
            summaries.get_current_week_summary_state(start_async=True)
            self.assertEqual(start.call_count, 1)

    def test_failed_generation_is_not_restarted_by_every_status_poll(self):
        self.summary(status='failed', error_message='Limite de uso', finished_at=timezone.now())
        with patch('feeds.services.dashboard_weekly_summary.start_dashboard_weekly_summary_job') as start:
            for _ in range(3):
                state = summaries.get_current_week_summary_state(start_async=True)
        start.assert_not_called()
        self.assertEqual(state['status'], 'failed')
        self.assertFalse(state['is_loading'])

    def test_abandoned_running_summary_can_be_recovered(self):
        summary = self.summary(started_at=timezone.now() - timedelta(minutes=10))
        with patch('feeds.services.dashboard_weekly_summary.start_dashboard_weekly_summary_job') as start:
            summaries.get_current_week_summary_state(start_async=True)
        start.assert_called_once()
        summary.refresh_from_db()
        self.assertGreater(summary.started_at, timezone.now() - timedelta(minutes=1))
        self.assertEqual(summary.revision, 2)
        with patch('feeds.services.dashboard_weekly_summary.requests.post') as post:
            summaries.run_dashboard_weekly_summary_job(summary.pk, 1)
        post.assert_not_called()

    def test_failure_can_retry_after_cooldown_or_after_invalidation(self):
        summary = self.summary(status='failed', finished_at=timezone.now() - timedelta(minutes=16))
        with patch('feeds.services.dashboard_weekly_summary.start_dashboard_weekly_summary_job') as start:
            summaries.get_current_week_summary_state(start_async=True)
            self.assertEqual(start.call_count, 1)
            summaries.invalidate_current_week_summary()
            summaries.get_current_week_summary_state(start_async=True)
            self.assertEqual(start.call_count, 2)

    def test_provider_configuration_fails_before_http(self):
        settings_cases = [build_ai_settings(enabled=False), {**build_ai_settings(), 'PROVIDER': 'unsupported'}, {**build_ai_settings(), 'OPENAI_API_KEY': ''}]
        for ai in settings_cases:
            with self.subTest(ai=ai['PROVIDER'], enabled=ai['ENABLED']), override_settings(NEWS_AI=ai), patch('feeds.services.dashboard_weekly_summary.requests.post') as post:
                with self.assertRaises(summaries.DashboardWeeklySummaryConfigurationError):
                    summaries._generate_weekly_summary_with_llm({})
                post.assert_not_called()

    def test_provider_response_errors_and_rate_limits_are_classified(self):
        responses = [
            (DummyJsonResponse({'error': {'type':'insufficient_quota', 'code':'insufficient_quota', 'message':'quota'}}, status_code=429), summaries.DashboardWeeklySummaryQuotaError),
            (DummyJsonResponse({'error': {'type':'rate_limit_exceeded', 'message':'rate limit'}}, status_code=429), summaries.DashboardWeeklySummaryRateLimitError),
            (DummyJsonResponse({'error': {'message':'Unavailable'}}, status_code=503), summaries.DashboardWeeklySummaryProviderError),
            (DummyJsonResponse({'output_text':'not JSON'}), summaries.DashboardWeeklySummaryProviderError),
            (DummyJsonResponse({'output': []}), summaries.DashboardWeeklySummaryProviderError),
            (self.response({'overview':'only one field'}), summaries.DashboardWeeklySummaryProviderError),
        ]
        for response, error_type in responses:
            with self.subTest(status=response.status_code), patch('feeds.services.dashboard_weekly_summary.requests.post', return_value=response):
                with self.assertRaises(error_type):
                    summaries._generate_weekly_summary_with_llm({})
        with patch('feeds.services.dashboard_weekly_summary.requests.post', side_effect=requests.Timeout('timeout')):
            with self.assertRaises(summaries.DashboardWeeklySummaryProviderError):
                summaries._generate_weekly_summary_with_llm({})

    def test_normalization_strips_html_and_rejects_non_object_content(self):
        self.assertEqual(summaries._normalize_weekly_summary_result({'overview':'<b> Visão </b>', 'main_changes':'A\u00a0 B', 'attention':'Prazos'})['overview'], 'Visão')
        for content in ([], None, {'overview':'', 'main_changes':'B', 'attention':'C'}):
            with self.subTest(content=content), self.assertRaises(summaries.DashboardWeeklySummaryProviderError):
                summaries._normalize_weekly_summary_result(content)

    def test_payload_counts_all_news_but_bounds_provider_items(self):
        for number in range(30):
            NewsItem.objects.create(source=self.source, title=f'Informativo {number}', link=f'https://example.com/{number}', dedupe_key=str(number), published_at=timezone.now())
        payload = summaries._build_current_week_items_payload(self.week_start, self.week_end)
        self.assertEqual(payload['total_items'], 31)
        self.assertEqual(len(payload['items']), 25)
        self.assertEqual(payload['truncated_item_count'], 6)
        self.assertEqual(payload['high_relevance_count'], 1)
        self.assertNotIn(self.foreign_item.title, json.dumps(payload))

    def test_missing_summary_is_logged_and_does_not_call_provider(self):
        with self.assertLogs(summaries.logger, level='WARNING'), patch('feeds.services.dashboard_weekly_summary.requests.post') as post:
            summaries.run_dashboard_weekly_summary_job(999999, 1)
        post.assert_not_called()

    def test_worker_failure_is_persisted_and_reported_as_finished(self):
        summary = self.summary()
        with self.assertLogs(summaries.logger, level='WARNING'), patch('feeds.services.dashboard_weekly_summary._generate_weekly_summary_with_llm', side_effect=summaries.DashboardWeeklySummaryProviderError('Serviço indisponível')):
            summaries.run_dashboard_weekly_summary_job(summary.pk, summary.revision)
        summary.refresh_from_db()
        self.assertEqual(summary.status, 'failed')
        self.assertIsNotNone(summary.finished_at)
        self.assertEqual(summary.error_message, 'Serviço indisponível')
