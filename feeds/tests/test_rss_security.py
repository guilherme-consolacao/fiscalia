from unittest.mock import patch, MagicMock
import requests
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from feeds.models import Workspace, Membership, Source, SourceCategory, NewsItem, NewsItemFollow, NewsItemRead, NewsItemAnalysis, NewsImportJob
from feeds.tenancy import workspace_scope
from feeds.validators import validate_public_url
from feeds.services.safe_http import resolve_public_address, PublicHTTPAdapter, fetch_url


class PublicFetchTests(TestCase):
    def test_rejects_local_credential_and_executable_urls(self):
        for url in ('file:///etc/passwd','javascript:alert(1)','http://127.0.0.1','http://[::1]','http://169.254.169.254','https://user:password@example.com','https://localhost','http://10.0.0.1','http://[::ffff:127.0.0.1]','https://example.com:8443'):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                validate_public_url(url)

    def test_rejects_mixed_dns_answers_and_pins_public_tls(self):
        def record(ip):
            return (2,1,6,'',(ip,443))
        with patch('feeds.services.safe_http.socket.getaddrinfo',return_value=[record('93.184.216.34'),record('127.0.0.1')]), self.assertRaises(requests.RequestException):
            resolve_public_address('https://example.com/rss')
        adapter = PublicHTTPAdapter()
        request = requests.Request('GET','https://example.com/rss').prepare()
        with patch('feeds.services.safe_http.socket.getaddrinfo',return_value=[record('93.184.216.34')]):
            pool = adapter.get_connection_with_tls_context(request,True)
        self.assertEqual(pool.host,'93.184.216.34')
        self.assertEqual(pool.assert_hostname,'example.com')
        self.assertEqual(pool.conn_kw['server_hostname'],'example.com')
        self.assertEqual(request.headers['Host'],'example.com')

    def test_redirect_to_internal_address_is_rejected(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.is_redirect = True
        response.url = 'https://example.com/rss'
        response.headers = {'Location':'http://127.0.0.1/admin'}
        with patch('feeds.services.safe_http.requests.Session') as factory:
            factory.return_value.__enter__.return_value.get.return_value = response
            with self.assertRaises(requests.RequestException):
                fetch_url('https://example.com/rss')

    def test_oversized_responses_are_bounded(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.is_redirect = False
        response.iter_content.return_value = [b'x'*(3*1024*1024+1)]
        with patch('feeds.services.safe_http.requests.Session') as factory:
            factory.return_value.__enter__.return_value.get.return_value = response
            with self.assertRaises(requests.RequestException):
                fetch_url('https://example.com/rss')


class SharedWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workspace = Workspace.objects.create(name='Compartilhado')
        cls.other = Workspace.objects.create(name='Privado')
        cls.users = [get_user_model().objects.create_user(username=f'person{i}@example.com') for i in range(3)]
        for user in cls.users[:2]:
            Membership.objects.create(workspace=cls.workspace,user=user,role='editor')
        Membership.objects.create(workspace=cls.other,user=cls.users[2],role='editor')
        with workspace_scope(cls.workspace.pk):
            cls.source = Source.objects.create(name='Fonte comum',url='https://example.com/rss',category=SourceCategory.objects.first())
            cls.item = NewsItem.objects.create(source=cls.source,title='Notícia comum',link='https://example.com/news',dedupe_key='same')
            NewsItemAnalysis.objects.create(news_item=cls.item,effective_date='2026-10-19')

    def test_shared_news_personal_reads_follows_and_foreign_ids(self):
        first, second, outsider = [Client() for _ in range(3)]
        for client,user in zip((first,second,outsider),self.users):
            client.force_login(user)
        first.post(reverse('feeds:toggle_news_read',args=[self.item.pk]))
        first.post(reverse('feeds:toggle_news_follow',args=[self.item.pk]))
        self.assertEqual(first.get(reverse('feeds:news')).context['unread_count'],0)
        self.assertEqual(second.get(reverse('feeds:news')).context['unread_count'],1)
        self.assertFalse(second.get(reverse('feeds:news')).context['news_items'][0].is_following_effective_date)
        self.assertNotContains(outsider.get(reverse('feeds:news')),'Notícia comum')
        for route in ('toggle_news_read','toggle_news_follow'):
            self.assertEqual(outsider.post(reverse('feeds:'+route,args=[self.item.pk])).status_code,404)
        self.assertEqual(outsider.post(reverse('feeds:delete_source',args=[self.source.pk])).status_code,404)

    def test_concurrent_requests_share_one_active_job_and_foreign_job_is_hidden(self):
        self.client.force_login(self.users[0])
        with patch('feeds.views.news.start_news_import_job') as start:
            self.client.post(reverse('feeds:refresh_news'))
            self.client.post(reverse('feeds:refresh_news'))
        self.assertEqual(start.call_count,1)
        job = NewsImportJob.all_objects.get(workspace=self.workspace)
        self.client.force_login(self.users[2])
        self.assertEqual(self.client.get(reverse('feeds:refresh_news_progress_status',args=[job.pk])).status_code,404)
