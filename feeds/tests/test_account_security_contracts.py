from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone
from feeds.models import AuthRateLimit, Membership, Workspace
from feeds.services.auth_rate_limit import allow_auth_attempt
from feeds.tests.scenarios import WorkspaceScenario


class AccountSecurityContracts(WorkspaceScenario):
    def signup_data(self, **changes):
        return {**{'first_name':'Pessoa', 'email':'new-account@example.com', 'workspace_name':'Espaço privado', 'password1':'Example-strong-7419!', 'password2':'Example-strong-7419!'}, **changes}

    def test_registration_invalid_inputs_create_no_partial_identity_or_workspace(self):
        before = (get_user_model().objects.count(), Workspace.objects.count(), Membership.objects.count())
        cases = [{'first_name':''}, {'email':'bad'}, {'workspace_name':''}, {'password1':'123456', 'password2':'123456'}, {'password2':'different'}]
        for changes in cases:
            with self.subTest(changes=changes):
                response = Client().post(reverse('feeds:signup'), self.signup_data(**changes))
                self.assertTrue(response.context['form'].errors)
                self.assertEqual((get_user_model().objects.count(), Workspace.objects.count(), Membership.objects.count()), before)

    def test_registration_rolls_back_user_if_workspace_cannot_be_created(self):
        with patch('feeds.views.accounts.Workspace.objects.create', side_effect=IntegrityError('simulated conflict')):
            response = Client().post(reverse('feeds:signup'), self.signup_data())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='new-account@example.com').exists())

    def test_registration_rejects_duplicate_email_on_a_legacy_username(self):
        get_user_model().objects.create_user(username='legacy-person', email='new-account@example.com')
        response = Client().post(reverse('feeds:signup'), self.signup_data(email='NEW-ACCOUNT@example.com'))
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(get_user_model().objects.filter(email__iexact='new-account@example.com').count(), 1)

    def test_disabled_user_and_user_without_membership_cannot_log_in(self):
        user = get_user_model().objects.create_user(username='no-access@example.com', password='Example-strong-7419!')
        browser = Client()
        response = browser.post(reverse('feeds:login'), {'username':user.username, 'password':'Example-strong-7419!'})
        self.assertEqual(response.context['form'].non_field_errors().as_data()[0].code, 'invalid_login')
        self.assertNotIn('_auth_user_id', browser.session)
        user.is_active = False
        user.save(update_fields=['is_active'])
        Membership.objects.create(workspace=self.space, user=user)
        self.assertEqual(browser.post(reverse('feeds:login'), {'username':user.username, 'password':'Example-strong-7419!'}).status_code, 200)
        self.assertNotIn('_auth_user_id', browser.session)

    def test_expired_session_and_inactive_identity_lose_access(self):
        session = self.client.session
        session.set_expiry(-1)
        session.save()
        self.assertEqual(self.client.get('/').status_code, 302)
        self.client.force_login(self.users['admin'])
        self.users['admin'].is_active = False
        self.users['admin'].save(update_fields=['is_active'])
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_login_rejects_external_next_urls_and_logout_flushes_scope(self):
        browser = Client()
        for target in ('https://evil.example/path', '//evil.example', 'http://evil.example'):
            with self.subTest(target=target):
                response = browser.post(reverse('feeds:login'), {'username':self.users['admin'].username.upper(), 'password':'Scenario-password-7419!', 'next':target})
                self.assertEqual(response.url, '/')
                browser.post(reverse('feeds:logout'))
                self.assertNotIn('workspace_id', browser.session)
                self.assertNotIn('_auth_user_id', browser.session)

    def test_registration_throttle_stops_validation_and_has_no_side_effects(self):
        with patch('feeds.views.accounts.allow_auth_attempt', return_value=False), patch('feeds.forms.accounts.SignupForm.is_valid') as validate:
            response = Client().post(reverse('feeds:signup'), self.signup_data())
        self.assertEqual(response.status_code, 429)
        validate.assert_not_called()
        self.assertFalse(get_user_model().objects.filter(username='new-account@example.com').exists())

    def test_rate_limit_is_ip_and_action_specific_ignores_forwarded_for_and_expires(self):
        request = RequestFactory().post('/', REMOTE_ADDR='192.0.2.1', HTTP_X_FORWARDED_FOR='203.0.113.5')
        now = timezone.now()
        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=now):
            self.assertTrue(allow_auth_attempt(request, 'login', 2, 900))
            self.assertTrue(allow_auth_attempt(request, 'login', 2, 900))
            request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.9'
            self.assertFalse(allow_auth_attempt(request, 'login', 2, 900))
            self.assertTrue(allow_auth_attempt(request, 'signup', 2, 900))
            request.META['REMOTE_ADDR'] = '192.0.2.2'
            self.assertTrue(allow_auth_attempt(request, 'login', 2, 900))
        request.META['REMOTE_ADDR'] = '192.0.2.1'
        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=now + timedelta(seconds=901)):
            self.assertTrue(allow_auth_attempt(request, 'login', 2, 900))
        self.assertEqual(AuthRateLimit.objects.count(), 3)

    def test_admin_login_and_portal_share_the_account_lockout(self):
        user = get_user_model().objects.create_superuser(username='platform-admin', password='Example-strong-7419!')
        browser = Client()
        now = timezone.now()
        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=now):
            for _ in range(4):
                self.assertEqual(browser.post(reverse('admin:login'), {'username':user.username, 'password':'wrong'}).status_code, 200)
            response = browser.post(reverse('feeds:login'), {'username':user.username.upper(), 'password':'wrong'}, REMOTE_ADDR='192.0.2.10')
            self.assertEqual(response.status_code, 429)
            response = browser.post(reverse('admin:login'), {'username':user.username, 'password':'Example-strong-7419!'}, REMOTE_ADDR='192.0.2.11')
            self.assertEqual(response.status_code, 429)
            self.assertIn('Retry-After', response)
            self.assertNotIn('_auth_user_id', browser.session)

        with patch('feeds.services.auth_rate_limit.timezone.now', return_value=now + timedelta(minutes=15)):
            response = browser.post(reverse('admin:login'), {'username':user.username, 'password':'Example-strong-7419!'})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(int(browser.session['_auth_user_id']), user.pk)

    def test_no_workspace_page_handles_all_session_states(self):
        self.assertEqual(Client().get(reverse('feeds:no_workspace')).url, reverse('feeds:login'))
        self.assertEqual(self.client.get(reverse('feeds:no_workspace')).url, '/')
        Membership.objects.filter(user=self.users['admin']).update(active=False)
        self.assertEqual(self.client.get(reverse('feeds:no_workspace')).status_code, 403)
