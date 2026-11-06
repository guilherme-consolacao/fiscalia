from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TestCase, Client, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from feeds.models import Membership, Workspace, Source, AuthRateLimit
from feeds.tenancy import workspace_scope


class SecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='security@example.com',password='Strong-password-2964!', is_staff=True)
        cls.workspace = Workspace.objects.create(name='Segurança')
        Membership.objects.create(user=cls.user, workspace=cls.workspace, role='admin')

    def test_queries_without_workspace_are_closed(self):
        self.assertFalse(Source.objects.exists())
        self.assertTrue(Source.all_objects.exists())
        with workspace_scope(-1):
            self.assertFalse(Source.objects.exists())

    def test_csrf_protects_authenticated_example_api(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('feeds:exemplo_post'), data='{}',content_type='application/json').status_code,403)

    def test_invalid_json_and_dates_do_not_break_services(self):
        self.client.force_login(self.user)
        for payload in ('[]','null','"text"','{"notification_id":"invalid"}'):
            self.assertEqual(self.client.post(reverse('feeds:dismiss_effective_date_reminder'),data=payload,content_type='application/json').status_code,400)
        self.assertEqual(self.client.get(reverse('feeds:news'), {'effective_date_from':'2026-99-99'}).status_code,200)
        self.assertEqual(self.client.post(reverse('feeds:switch_workspace'), {'workspace_id':'invalid'}).status_code,400)

    def test_platform_admin_does_not_accept_workspace_staff(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/').status_code,403)

    def test_security_headers_and_private_cache(self):
        self.client.force_login(self.user)
        response = self.client.get('/')
        self.assertEqual(response['Cache-Control'],'private, no-store')
        self.assertEqual(response['X-Frame-Options'],'DENY')
        self.assertEqual(response['X-Content-Type-Options'],'nosniff')
        self.assertIn("object-src 'none'",response['Content-Security-Policy'])
        self.assertNotIn('unpkg',response['Content-Security-Policy'])

    def test_fifth_failure_blocks_correct_password_for_a_full_window(self):
        url = reverse('feeds:login')
        now = timezone.now()
        password = 'Strong-password-2964!'
        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=now):
            for attempt in range(4):
                response = self.client.post(url, {'username':' SECURITY@example.com ', 'password':'wrong'}, REMOTE_ADDR=f'192.0.2.{attempt + 1}')
                self.assertEqual(response.status_code, 200)

        fifth = now + timedelta(minutes=14)
        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=fifth):
            response = self.client.post(url, {'username':self.user.username, 'password':'wrong'}, REMOTE_ADDR='192.0.2.5')
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response['Retry-After'], '900')

        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=fifth + timedelta(seconds=899)), \
                patch('django.contrib.auth.forms.authenticate') as authenticate:
            response = self.client.post(url, {'username':self.user.username, 'password':password}, REMOTE_ADDR='192.0.2.6')
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response['Retry-After'], '1')
            authenticate.assert_not_called()
            self.assertNotIn('_auth_user_id', self.client.session)

        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=fifth + timedelta(minutes=15)):
            response = self.client.post(url, {'username':self.user.username, 'password':password}, REMOTE_ADDR='192.0.2.6')
            self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.assertTrue(all(self.user.username not in key and '192.0.2.' not in key for key in AuthRateLimit.objects.values_list('key', flat=True)))

    def test_success_resets_the_failure_sequence(self):
        url = reverse('feeds:login')
        for _ in range(2):
            for _ in range(4):
                self.assertEqual(self.client.post(url, {'username':self.user.username, 'password':'wrong'}).status_code, 200)
            self.assertEqual(self.client.post(url, {'username':self.user.username, 'password':'Strong-password-2964!'}).status_code, 302)
            self.client.post(reverse('feeds:logout'))

    def test_expired_observation_window_starts_a_new_failure_sequence(self):
        url = reverse('feeds:login')
        now = timezone.now()
        data = {'username':self.user.username, 'password':'wrong'}
        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=now):
            for _ in range(4):
                self.assertEqual(self.client.post(url, data).status_code, 200)
        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=now + timedelta(minutes=15)):
            self.assertEqual(self.client.post(url, data).status_code, 200)

    def test_unknown_and_known_accounts_have_the_same_failure_responses(self):
        responses = []
        for address, username in enumerate((self.user.username, 'not-registered@example.com'), start=1):
            sequence = []
            for _ in range(6):
                response = self.client.post(reverse('feeds:login'), {'username':username, 'password':'wrong'}, REMOTE_ADDR=f'192.0.2.{address}')
                error = response.context['form'].non_field_errors().as_data()[0]
                sequence.append((response.status_code, error.message))
            responses.append(sequence)
        self.assertEqual(responses[0], responses[1])
        self.assertEqual([code for code, _ in responses[0]], [200, 200, 200, 200, 429, 429])

    def test_origin_limit_applies_across_accounts_and_login_routes(self):
        with patch('django.contrib.auth.forms.authenticate', return_value=None) as authenticate:
            for attempt in range(10):
                response = self.client.post(reverse('feeds:login'), {'username':f'test-{attempt}', 'password':'wrong'}, HTTP_X_FORWARDED_FOR=f'192.0.2.{attempt + 1}')
                self.assertEqual(response.status_code, 200)
            response = self.client.post(reverse('admin:login'), {'username':'different', 'password':'wrong'}, HTTP_X_FORWARDED_FOR='198.51.100.1')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(authenticate.call_count, 10)

    def test_login_csrf_rejection_does_not_consume_attempts(self):
        browser = Client(enforce_csrf_checks=True)
        for name in ('feeds:login', 'admin:login'):
            self.assertEqual(browser.post(reverse(name), {'username':self.user.username, 'password':'wrong'}).status_code, 403)
        self.assertFalse(AuthRateLimit.objects.exists())

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_https_redirect_is_enabled_for_production(self):
        response = self.client.get('/entrar/')
        self.assertEqual(response.status_code,301)
        self.assertTrue(response.url.startswith('https://'))


class ConcurrentLoginTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_parallel_requests_get_only_five_password_checks_for_one_account(self):
        start = Barrier(8, timeout=10)

        def post(attempt):
            try:
                start.wait()
                response = Client().post(reverse('feeds:login'), {'username':'parallel@example.com', 'password':'wrong'}, REMOTE_ADDR=f'192.0.2.{attempt + 1}')
                return response.status_code
            finally:
                connections.close_all()

        with patch('django.contrib.auth.forms.authenticate', return_value=None) as authenticate, ThreadPoolExecutor(max_workers=8) as pool:
            self.assertCountEqual(pool.map(post, range(8)), [200] * 4 + [429] * 4)
            self.assertEqual(authenticate.call_count, 5)
