from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
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

    def test_login_is_throttled_before_authentication(self):
        with patch('django.contrib.auth.forms.authenticate',return_value=None) as auth:
            for _ in range(10):
                self.client.post(reverse('feeds:login'), {'username':'security@example.com','password':'wrong'})
            response = self.client.post(reverse('feeds:login'), {'username':'security@example.com','password':'wrong'})
        self.assertEqual(response.status_code,429)
        self.assertEqual(auth.call_count,10)
        self.assertEqual(response['Retry-After'],'900')
        self.assertNotIn('127.0.0.1',AuthRateLimit.objects.get().key)

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_https_redirect_is_enabled_for_production(self):
        response = self.client.get('/entrar/')
        self.assertEqual(response.status_code,301)
        self.assertTrue(response.url.startswith('https://'))
