import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from feeds.models import Membership, Source, Tag, NewsItem, NewsItemRead, NewsItemFollow, NewsItemReminderNotification
from feeds.tenancy import workspace_scope
from feeds.tests.scenarios import WorkspaceScenario


class PortalAccessContracts(WorkspaceScenario):
    def routes(self):
        return [
            ('index', [], 'read'), ('news', [], 'read'),
            ('dashboard_weekly_summary_status', [], 'read'), ('effective_date_reminders', [], 'read'),
            ('sources', [], 'edit'), ('tags', [], 'edit'), ('users', [], 'admin'),
            ('edit_user', [self.memberships['reader'].pk], 'admin'),
            ('refresh_news_progress', [self.job.pk], 'edit'),
            ('refresh_news_progress_status', [self.job.pk], 'edit'),
        ]

    def mutations(self):
        return [
            ('create_source', [], 'edit'), ('update_source', [self.source.pk], 'edit'),
            ('delete_source', [self.source.pk], 'edit'), ('toggle_source_status', [self.source.pk], 'edit'),
            ('create_tag', [], 'edit'), ('update_tag', [self.tag.pk], 'edit'), ('delete_tag', [self.tag.pk], 'edit'),
            ('refresh_news', [], 'edit'), ('toggle_news_read', [self.item.pk], 'read'),
            ('toggle_news_follow', [self.item.pk], 'read'), ('bulk_update_news_read', [], 'read'),
            ('dismiss_effective_date_reminder', [], 'read'), ('switch_workspace', [], 'read'),
            ('exemplo_post', [], 'read'),
        ]

    def test_every_private_route_requires_a_session(self):
        anonymous = Client()
        for name, args, _ in self.routes() + self.mutations():
            with self.subTest(route=name):
                response = anonymous.get(reverse('feeds:' + name, args=args))
                self.assertIn(response.status_code, (302, 401))
                if response.status_code == 302:
                    self.assertTrue(response.url.startswith(reverse('feeds:login')))
                self.assertEqual(anonymous.get(reverse('feeds:' + name, args=args), HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code, 401)

    def test_read_page_permissions_cover_all_three_roles(self):
        for role in ('reader', 'editor', 'admin'):
            client = self.role_client(role)
            with patch('feeds.services.dashboard_weekly_summary.start_dashboard_weekly_summary_job'):
                for name, args, requirement in self.routes():
                    allowed = requirement == 'read' or role == 'admin' or requirement == 'edit' and role == 'editor'
                    with self.subTest(role=role, route=name):
                        self.assertEqual(client.get(reverse('feeds:' + name, args=args)).status_code, 200 if allowed else 403)

    def test_mutations_reject_get_and_require_csrf(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.users['admin'])
        for name, args, _ in self.mutations() + [('logout', [], 'read')]:
            with self.subTest(route=name):
                self.assertEqual(self.client.get(reverse('feeds:' + name, args=args)).status_code, 405)
                self.assertEqual(strict.post(reverse('feeds:' + name, args=args), {}).status_code, 403)

    def test_reader_cannot_mutate_sources_tags_or_accounts(self):
        reader = self.role_client('reader')
        for name, args, permission in self.mutations():
            if permission == 'edit':
                with self.subTest(route=name):
                    self.assertEqual(reader.post(reverse('feeds:' + name, args=args), {}).status_code, 403)
        self.assertEqual(reader.post(reverse('feeds:users'), {'email': self.outsider.username, 'role': 'admin'}).status_code, 403)
        self.assertEqual(reader.post(reverse('feeds:edit_user', args=[self.memberships['reader'].pk]), {'role': 'admin', 'confirm': 'on', 'active': 'on'}).status_code, 403)
        self.memberships['reader'].refresh_from_db()
        self.assertEqual(self.memberships['reader'].role, 'reader')

    def test_foreign_identifiers_are_rejected_for_every_object_action(self):
        payload = {'name': 'Alterado', 'url': 'https://example.com/changed', 'category': self.category.pk, 'color': 'blue', 'role': 'reader', 'confirm': 'on'}
        routes = [('update_source', self.foreign_source.pk), ('delete_source', self.foreign_source.pk), ('toggle_source_status', self.foreign_source.pk), ('update_tag', self.foreign_tag.pk), ('delete_tag', self.foreign_tag.pk), ('toggle_news_read', self.foreign_item.pk), ('toggle_news_follow', self.foreign_item.pk), ('edit_user', self.foreign_member.pk)]
        for name, pk in routes:
            with self.subTest(route=name):
                self.assertEqual(self.client.post(reverse('feeds:' + name, args=[pk]), payload).status_code, 404)
        for name in ('refresh_news_progress', 'refresh_news_progress_status', 'finalize_refresh_news_job'):
            with self.subTest(route=name):
                self.assertEqual(self.client.get(reverse('feeds:' + name, args=[self.foreign_job.pk])).status_code, 404)
        self.foreign_source.refresh_from_db()
        self.assertEqual(self.foreign_source.name, self.foreign_space.name)

    def test_tampered_session_falls_back_to_owned_active_membership(self):
        session = self.client.session
        session['workspace_id'] = self.foreign_space.pk
        session.save()
        response = self.client.get('/')
        self.assertEqual(response.wsgi_request.workspace, self.space)
        self.assertNotContains(response, self.foreign_space.name)

    def test_bulk_read_never_updates_foreign_news_or_another_person(self):
        response = self.client.post(reverse('feeds:bulk_update_news_read'), {'bulk_action': 'mark_read', 'selected_news_ids': [str(self.item.pk), str(self.foreign_item.pk), 'bad', str(self.item.pk)]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NewsItemRead.objects.filter(news_item=self.item).exists())
        with workspace_scope(self.space.pk, self.users['reader'].pk):
            self.assertFalse(NewsItemRead.objects.exists())
        with workspace_scope(self.foreign_space.pk, self.users['admin'].pk):
            self.assertFalse(NewsItemRead.objects.exists())

    def test_personal_reminders_cannot_be_dismissed_by_a_colleague(self):
        self.client.post(reverse('feeds:toggle_news_follow', args=[self.item.pk]))
        reminders = self.client.get(reverse('feeds:effective_date_reminders')).json()['notifications']
        self.assertEqual(len(reminders), 1)
        reminder = NewsItemReminderNotification.objects.get()
        reader = self.role_client('reader')
        self.assertEqual(reader.post(reverse('feeds:dismiss_effective_date_reminder'), {'notification_id': reminder.pk}).status_code, 404)
        self.assertEqual(reader.get(reverse('feeds:effective_date_reminders')).json()['notifications'], [])
        self.assertEqual(self.client.post(reverse('feeds:dismiss_effective_date_reminder'), data=json.dumps({'notification_id': reminder.pk}), content_type='application/json').status_code, 200)
        self.assertEqual(self.client.get(reverse('feeds:effective_date_reminders')).json()['notifications'], [])

    def test_unfollowing_removes_only_own_reminders(self):
        reader = self.role_client('reader')
        for client in (self.client, reader):
            client.post(reverse('feeds:toggle_news_follow', args=[self.item.pk]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            client.get(reverse('feeds:effective_date_reminders'))
        self.client.post(reverse('feeds:toggle_news_follow', args=[self.item.pk]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertFalse(NewsItemFollow.objects.exists())
        self.assertFalse(NewsItemReminderNotification.objects.exists())
        with workspace_scope(self.space.pk, self.users['reader'].pk):
            self.assertEqual(NewsItemFollow.objects.count(), 1)
            self.assertEqual(NewsItemReminderNotification.objects.count(), 1)

    def test_xss_payloads_are_escaped_in_news_and_feedback(self):
        self.item.title = '<img src=x onerror=alert(1)>'
        self.item.save(update_fields=['title'])
        response = self.client.get(reverse('feeds:news'))
        self.assertContains(response, '&lt;img src=x onerror=alert(1)&gt;')
        self.assertNotContains(response, '<img src=x onerror=alert(1)>')

    def test_example_api_handles_valid_invalid_and_non_object_json(self):
        url = reverse('feeds:exemplo_post')
        response = self.client.post(url, data=json.dumps({'mensagem': 'Olá'}), content_type='application/json')
        self.assertEqual(response.json()['dados_recebidos'], 'Olá')
        for payload in ('[1]', 'null', '{bad', '"text"'):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post(url, data=payload, content_type='application/json').status_code, 400)


class WorkspaceCrudContracts(WorkspaceScenario):
    def test_source_validation_is_atomic_for_invalid_categories_tags_and_urls(self):
        duplicate = Source.objects.create(name='URL ocupada', url='https://example.com/used', category=self.category)
        base = {'name': 'Outra fonte', 'url': 'https://example.com/other', 'category': self.category.pk, 'tags': [self.tag.pk]}
        cases = [{'name': ''}, {'url': 'javascript:alert(1)'}, {'url': 'http://127.0.0.1/feed'}, {'category': 'not-a-number'}, {'category': 999999}, {'tags': [self.foreign_tag.pk]}, {'url': duplicate.url}, {'name': 'x' * 300}]
        for change in cases:
            with self.subTest(change=change):
                self.client.post(reverse('feeds:create_source'), {**base, **change})
                self.assertEqual(Source.objects.count(), 2)
                self.client.post(reverse('feeds:update_source', args=[self.source.pk]), {**base, **change})
                self.source.refresh_from_db()
                self.assertEqual(self.source.name, self.space.name)
                self.assertEqual(list(self.source.tags.all()), [self.tag])

    def test_source_create_edit_toggle_delete_and_cascade_are_scoped(self):
        data = {'name': 'Nova fonte', 'url': 'https://example.com/new', 'category': self.category.pk, 'tags': [self.tag.pk, self.tag.pk]}
        self.assertEqual(self.client.post(reverse('feeds:create_source'), data).status_code, 302)
        source = Source.objects.get(name='Nova fonte')
        self.assertEqual(source.tags.count(), 1)
        self.client.post(reverse('feeds:update_source', args=[source.pk]), {**data, 'name': 'Editada', 'tags': []})
        source.refresh_from_db()
        self.assertEqual(source.name, 'Editada')
        self.assertEqual(source.tags.count(), 0)
        self.client.post(reverse('feeds:toggle_source_status', args=[source.pk]), {})
        source.refresh_from_db()
        self.assertFalse(source.active)
        self.client.post(reverse('feeds:toggle_source_status', args=[source.pk]), {'active': 'on'})
        self.client.post(reverse('feeds:delete_source', args=[source.pk]))
        self.assertFalse(Source.objects.filter(pk=source.pk).exists())
        self.assertTrue(Source.all_objects.filter(pk=self.foreign_source.pk).exists())

    def test_tag_validation_and_case_insensitive_duplicate_names(self):
        for data in ({'name': '', 'color': 'blue'}, {'name': '<script>', 'color': 'blue'}, {'name': 'Nova', 'color': 'invalid'}, {'name': 'TRIBUTOS', 'color': 'green'}, {'name': 'x' * 300, 'color': 'blue'}):
            with self.subTest(data=data):
                self.client.post(reverse('feeds:create_tag'), data)
                self.assertEqual(Tag.objects.count(), 1)
        self.client.post(reverse('feeds:create_tag'), {'name': 'Nova Tag', 'color': 'red'})
        tag = Tag.objects.get(name='Nova Tag')
        self.client.post(reverse('feeds:update_tag', args=[tag.pk]), {'name': 'Renomeada', 'color': 'green'})
        tag.refresh_from_db()
        self.assertEqual((tag.name, tag.color), ('Renomeada', 'green'))
        self.client.post(reverse('feeds:delete_tag', args=[tag.pk]))
        self.assertEqual(Tag.objects.count(), 1)

    def test_team_form_rejects_missing_inactive_duplicate_and_invalid_role(self):
        for data in ({'email': 'missing@example.com', 'role': 'reader'}, {'email': self.users['reader'].email, 'role': 'admin'}, {'email': self.outsider.username, 'role': 'root'}):
            with self.subTest(data=data):
                response = self.client.post(reverse('feeds:users'), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
                self.assertEqual(Membership.objects.filter(workspace=self.space).count(), 3)
        self.outsider.is_active = False
        self.outsider.save(update_fields=['is_active'])
        self.assertTrue(self.client.post(reverse('feeds:users'), {'email': self.outsider.username, 'role': 'reader'}).context['form'].errors)

    def test_role_change_requires_confirmation_and_last_admin_is_retained(self):
        reader = self.memberships['reader']
        response = self.client.post(reverse('feeds:edit_user', args=[reader.pk]), {'role': 'editor', 'active': 'on'})
        self.assertTrue(response.context['form'].errors)
        reader.refresh_from_db()
        self.assertEqual(reader.role, 'reader')
        for role, active in (('reader', 'on'), ('admin', '')):
            with self.subTest(role=role, active=active):
                response = self.client.post(reverse('feeds:edit_user', args=[self.memberships['admin'].pk]), {'role': role, 'active': active, 'confirm': 'on'})
                self.assertContains(response, 'Mantenha pelo menos um administrador')

    def test_deactivating_a_member_revokes_the_existing_session(self):
        reader = self.role_client('reader')
        self.client.post(reverse('feeds:edit_user', args=[self.memberships['reader'].pk]), {'role': 'reader', 'confirm': 'on'})
        self.assertRedirects(reader.get('/'), reverse('feeds:no_workspace'), fetch_redirect_response=False)
        self.assertEqual(reader.get(reverse('feeds:no_workspace')).status_code, 403)
