from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
from django.db import IntegrityError, transaction
from django.utils import timezone
from feeds.models import Source, Tag, NewsItem, NewsItemAnalysis, NewsItemRead, NewsItemFollow, NewsItemReminderNotification
from feeds.tenancy import workspace_scope, current_workspace_id, current_user_id
from feeds.services.news_analysis import _normalize_analysis_result
from feeds.tests.scenarios import WorkspaceScenario


class DomainContracts(WorkspaceScenario):
    def test_nested_scope_restores_both_identity_and_workspace_after_exception(self):
        before = (current_workspace_id(), current_user_id())
        with self.assertRaises(RuntimeError):
            with workspace_scope(self.foreign_space.pk, self.outsider.pk):
                raise RuntimeError('interrupted worker')
        self.assertEqual((current_workspace_id(), current_user_id()), before)

    def test_copied_and_thread_contexts_do_not_leak_between_tasks(self):
        expected = [(self.space.pk, self.users['admin'].pk), (self.foreign_space.pk, self.outsider.pk)]
        contexts = []
        for pair in expected:
            with workspace_scope(*pair):
                contexts.append(copy_context())
        self.assertEqual([(context.run(current_workspace_id), context.run(current_user_id)) for context in contexts], expected)
        def worker(pair):
            with workspace_scope(*pair):
                return current_workspace_id(), current_user_id()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(worker, expected)), expected)

    def test_workspace_constraints_allow_shared_names_only_across_spaces(self):
        for action in (lambda: Source.objects.create(name='Duplicada', url=self.source.url, category=self.category), lambda: Tag.objects.create(name=self.tag.name)):
            with self.assertRaises(IntegrityError), transaction.atomic():
                action()
        with workspace_scope(self.foreign_space.pk):
            self.assertEqual(Source.objects.get().url, self.source.url)
            self.assertEqual(Tag.objects.get().name, self.tag.name)

    def test_news_deduplication_key_is_per_source(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            NewsItem.objects.create(source=self.source, title='Duplicada', link='https://example.com/x', dedupe_key=self.item.dedupe_key)
        source = Source.objects.create(name='Outra', url='https://example.com/other', category=self.category)
        self.assertEqual(NewsItem.objects.create(source=source, title='Outra', link='https://example.com/x', dedupe_key=self.item.dedupe_key).source, source)

    def test_personal_preferences_are_unique_per_person_and_news(self):
        for model in (NewsItemRead, NewsItemFollow):
            model.objects.create(news_item=self.item)
            with self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.create(news_item=self.item)
            with workspace_scope(self.space.pk, self.users['reader'].pk):
                self.assertFalse(model.objects.exists())
                model.objects.create(news_item=self.item)
        self.assertEqual(NewsItemRead.objects.count(), 1)
        self.assertEqual(NewsItemFollow.objects.count(), 1)

    def test_deleting_source_cascades_its_analysis_and_preferences_only(self):
        today = timezone.localdate()
        NewsItemRead.objects.create(news_item=self.item)
        NewsItemFollow.objects.create(news_item=self.item)
        NewsItemReminderNotification.objects.create(news_item=self.item, effective_date=today, reminder_date=today, days_before=0)
        self.source.delete()
        for model in (NewsItem, NewsItemAnalysis, NewsItemRead, NewsItemFollow, NewsItemReminderNotification):
            self.assertFalse(model.objects.exists())
        with workspace_scope(self.foreign_space.pk):
            self.assertEqual(NewsItem.objects.count(), 1)
            self.assertEqual(NewsItemAnalysis.objects.count(), 1)

    def test_analysis_normalization_handles_malformed_and_extreme_provider_fields(self):
        cases = [(None, None), ('invalid', None), (-20, 0), (1000, 100), ('75', 75), (float('inf'), None)]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                result = _normalize_analysis_result({'summary':'<b>Resumo</b>', 'importance_score':raw, 'impact_level':'INVALID', 'effective_date':'2026-99-99', 'keywords':['ICMS','icms','','PIS','COFINS','ISS','IBS','Extra']})
                self.assertEqual(result.importance_score, expected)
                self.assertEqual(result.summary, 'Resumo')
                self.assertEqual(result.impact_level, '')
                self.assertIsNone(result.effective_date)
                self.assertEqual(result.keywords, ['ICMS','PIS','COFINS','ISS','IBS'])

    def test_analysis_display_does_not_repeat_the_date_and_ignores_corrupt_matches(self):
        analysis = self.item.analysis
        analysis.effective_date_label = analysis.effective_date.strftime('%d/%m/%Y')
        self.assertEqual(analysis.effective_date_display, analysis.effective_date_label)
        analysis.tag_score_matches = [None, {'name':'Invalid','occurrences':'bad','boost':5}, {'name':'Negative','occurrences':-1,'boost':5}, {'name':'ICMS','color':'blue','occurrences':2,'boost':10}]
        analysis.tag_score_boost = 10
        self.assertEqual(len(analysis.tag_score_matches_display), 1)
        self.assertIn('ICMS (2x, +10)', analysis.score_tooltip_text)
        self.assertIn('Bônus total: +10', analysis.score_tooltip_text)
