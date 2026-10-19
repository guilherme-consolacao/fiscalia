from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class LegacyMigrationTests(TransactionTestCase):
    available_apps = None

    def test_existing_news_tags_sources_and_preferences_are_preserved(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old = [node for node in latest if node[0] != 'feeds']
        old.append(('feeds', '0015_source_tags_and_analysis_score_boost'))
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            User = apps.get_model('auth','User')
            user = User.objects.create(username='legacy-admin',email='legacy@example.com',is_staff=True,is_active=True)
            Source = apps.get_model('feeds','Source')
            category = apps.get_model('feeds','SourceCategory').objects.first()
            source = Source.objects.create(name='Acervo antigo',url='https://example.com/legacy',category=category)
            tag = apps.get_model('feeds','Tag').objects.create(name='Legado')
            source.tags.add(tag)
            news = apps.get_model('feeds','NewsItem').objects.create(source=source,title='Notícia preservada',link='https://example.com/legacy-news',dedupe_key='legacy',is_read=True)
            apps.get_model('feeds','NewsItemFollow').objects.create(news_item=news)
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            saved = apps.get_model('feeds','NewsItem').objects.get(pk=news.pk)
            self.assertEqual(saved.title,'Notícia preservada')
            self.assertEqual(saved.workspace_id,1)
            self.assertTrue(apps.get_model('feeds','Source').objects.get(pk=source.pk).tags.filter(pk=tag.pk).exists())
            self.assertTrue(apps.get_model('feeds','Membership').objects.filter(user_id=user.pk,workspace_id=1,role='admin').exists())
            self.assertTrue(apps.get_model('feeds','NewsItemRead').objects.filter(user_id=user.pk,news_item_id=news.pk).exists())
            self.assertTrue(apps.get_model('feeds','NewsItemFollow').objects.filter(user_id=user.pk,news_item_id=news.pk).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
