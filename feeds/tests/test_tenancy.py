from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from feeds.models import Workspace, Source, SourceCategory, Tag, NewsItem, NewsItemAnalysis, NewsImportJob, DashboardWeeklySummary
from feeds.tenancy import workspace_scope


class WorkspaceIsolationTests(TestCase):
    def test_scopes_isolate_queries_defaults_and_related_analysis(self):
        first = Workspace.objects.create(name='Primeiro grupo')
        second = Workspace.objects.create(name='Segundo grupo')
        category = SourceCategory.objects.first()
        for workspace in (first, second):
            with workspace_scope(workspace.pk):
                source = Source.objects.create(name=workspace.name, url='https://example.com/rss', category=category)
                Tag.objects.create(name='Mesmo nome')
                item = NewsItem.objects.create(source=source, title=workspace.name, link='https://example.com/news', dedupe_key='same')
                NewsItemAnalysis.objects.create(news_item=item)
                NewsImportJob.objects.create()
                DashboardWeeklySummary.objects.create(week_start='2026-10-19', week_end='2026-10-25')
        with workspace_scope(first.pk):
            self.assertEqual(list(Source.objects.values_list('name', flat=True)), [first.name])
            for model in (Tag, NewsItem, NewsItemAnalysis, NewsImportJob, DashboardWeeklySummary):
                self.assertEqual(model.objects.count(), 1)
            with workspace_scope(second.pk):
                self.assertEqual(NewsItem.objects.get().title, second.name)
            self.assertEqual(NewsItem.objects.get().title, first.name)
        with workspace_scope(-1):
            self.assertFalse(Source.objects.exists())

    def test_source_cannot_be_attached_to_another_workspace(self):
        workspace = Workspace.objects.create(name='Isolado')
        source = Source.all_objects.first()
        with workspace_scope(workspace.pk):
            with self.assertRaises(ValidationError):
                NewsItem.objects.create(source=source, title='Falha', link='https://example.com', dedupe_key='cross')
