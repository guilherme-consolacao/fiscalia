"""Shared data for integration tests; no provider or external HTTP calls."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from feeds.models import Membership, Workspace, Source, SourceCategory, Tag, NewsItem, NewsItemAnalysis, NewsImportJob
from feeds.tenancy import workspace_scope


class WorkspaceScenario(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.space = Workspace.objects.create(name='Equipe de teste')
        cls.foreign_space = Workspace.objects.create(name='Outra equipe')
        cls.users = {}
        cls.memberships = {}
        for role in ('reader', 'editor', 'admin'):
            user = get_user_model().objects.create_user(username=f'{role}@example.com', email=f'{role}@example.com', password='Scenario-password-7419!')
            cls.users[role] = user
            cls.memberships[role] = Membership.objects.create(workspace=cls.space, user=user, role=role)
        cls.outsider = get_user_model().objects.create_user(username='outside@example.com')
        cls.foreign_member = Membership.objects.create(workspace=cls.foreign_space, user=cls.outsider, role='admin')
        cls.category = SourceCategory.objects.first()
        for prefix, space in (('', cls.space), ('foreign_', cls.foreign_space)):
            with workspace_scope(space.pk):
                source = Source.objects.create(name=space.name, url='https://example.com/rss', category=cls.category)
                tag = Tag.objects.create(name='Tributos', color='blue')
                source.tags.add(tag)
                item = NewsItem.objects.create(source=source, title=f'Notícia {space.name}', link='https://example.com/news', dedupe_key='same', published_at=timezone.now())
                NewsItemAnalysis.objects.create(news_item=item, status='completed', impact_level='high', importance_score=90, effective_date=timezone.localdate())
                job = NewsImportJob.objects.create(status='pending')
            for name, obj in (('source', source), ('tag', tag), ('item', item), ('job', job)):
                setattr(cls, prefix + name, obj)

    def setUp(self):
        self.scope = workspace_scope(self.space.pk, self.users['admin'].pk)
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)
        self.client.force_login(self.users['admin'])

    def role_client(self, role):
        client = Client()
        client.force_login(self.users[role])
        return client
