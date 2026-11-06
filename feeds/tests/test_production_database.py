import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connections
from django.test import Client, SimpleTestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from feeds.models import Membership, NewsImportJob, Workspace


class ProductionDatabaseTests(SimpleTestCase):
    def load_settings(self, url):
        env = {
            **os.environ, 'ALLOWED_HOSTS': 'portal.example.com', 'PYTHONUTF8': '1',
            'SECRET_KEY': 'production-check-only-fake-key-76313c9a66d24af0aa095743', 'DATABASE_URL': url,
        }
        return subprocess.run(
            [sys.executable, '-c', 'from config.production import DATABASES; '
             'db = DATABASES["default"]; print(db["ENGINE"], db["OPTIONS"]["sslmode"])'],
            cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, encoding='utf-8', timeout=15,
        )

    def test_production_requires_postgres_host_and_verified_tls(self):
        for url in ('sqlite:///:memory:', 'postgresql:///fiscalia', 'postgresql://db.example/fiscalia?sslmode=disable'):
            with self.subTest(url=url):
                result = self.load_settings(url)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Produção exige', result.stderr)

    def test_production_defaults_to_tls_with_hostname_validation(self):
        result = self.load_settings('postgresql://db.example/fiscalia?channel_binding=require')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'django.db.backends.postgresql verify-full')


class ProductionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.team = Workspace.objects.create(name='Equipe concorrente')
        self.admins = []
        for index in range(2):
            user = get_user_model().objects.create_user(username=f'pg-admin-{index}')
            membership = Membership.objects.create(workspace=self.team, user=user, role=Membership.ADMIN)
            browser = Client()
            browser.force_login(user)
            self.admins.append((browser, membership))

    def concurrent_posts(self, requests):
        start = Barrier(len(requests), timeout=10)

        def post(request):
            browser, url, data = request
            try:
                start.wait()
                return browser.post(url, data)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(requests)) as pool:
            return list(pool.map(post, requests))

    @skipUnlessDBFeature('has_select_for_update')
    def test_simultaneous_demotions_keep_one_active_administrator(self):
        responses = self.concurrent_posts([
            (browser, reverse('feeds:edit_user', args=[member.pk]), {'role': Membership.EDITOR, 'active': 'on', 'confirm': 'on'})
            for browser, member in self.admins
        ])
        self.assertCountEqual([response.status_code for response in responses], [200, 302])
        self.assertEqual(self.team.memberships.filter(active=True, role=Membership.ADMIN).count(), 1)

    @skipUnlessDBFeature('has_select_for_update')
    def test_simultaneous_refresh_requests_share_one_job(self):
        with patch('feeds.views.news.start_news_import_job') as start_job:
            responses = self.concurrent_posts([
                (browser, reverse('feeds:refresh_news'), {}) for browser, _ in self.admins
            ])
        job = NewsImportJob.all_objects.get(workspace=self.team)
        self.assertEqual([response.url for response in responses], [reverse('feeds:refresh_news_progress', args=[job.pk])] * 2)
        start_job.assert_called_once_with(job.pk)
