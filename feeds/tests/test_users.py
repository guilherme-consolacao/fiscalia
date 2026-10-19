from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from feeds.models import Workspace, Membership, Source


class MembershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.space = Workspace.objects.create(name='Grupo um')
        cls.other = Workspace.objects.create(name='Grupo dois')
        cls.admin = get_user_model().objects.create_user(username='admin@example.com', email='admin@example.com')
        cls.reader = get_user_model().objects.create_user(username='reader@example.com', email='reader@example.com')
        cls.admin_access = Membership.objects.create(workspace=cls.space, user=cls.admin, role='admin')
        cls.reader_access = Membership.objects.create(workspace=cls.space, user=cls.reader)
        cls.other_access = Membership.objects.create(workspace=cls.other, user=cls.reader, role='admin')

    def test_permissions_apply_to_direct_requests_and_menu(self):
        self.client.force_login(self.reader)
        for route in ('users','sources','tags'):
            self.assertEqual(self.client.get(reverse('feeds:'+route)).status_code, 403)
        for route in ('create_source','create_tag','refresh_news'):
            self.assertEqual(self.client.post(reverse('feeds:'+route), {}).status_code, 403)
        response = self.client.get('/')
        self.assertNotContains(response, 'Gerenciar equipe')
        self.assertNotContains(response, 'Configurar Fontes')

    def test_edit_and_deactivation_take_effect_on_open_session(self):
        self.client.force_login(self.admin)
        reader_client = Client()
        reader_client.force_login(self.reader)
        response = self.client.post(reverse('feeds:edit_user',args=[self.reader_access.pk]), {'role':'editor','active':'on','confirm':'on'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(reader_client.get(reverse('feeds:sources')).status_code,200)
        self.client.post(reverse('feeds:edit_user',args=[self.reader_access.pk]), {'role':'reader','confirm':'on'})
        response = reader_client.get('/')
        self.assertNotEqual(response.wsgi_request.workspace.pk, self.space.pk)

    def test_cannot_edit_foreign_member_or_remove_last_admin(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse('feeds:edit_user',args=[self.other_access.pk]), {'role':'admin','active':'on','confirm':'on'}).status_code,404)
        response = self.client.post(reverse('feeds:edit_user',args=[self.admin_access.pk]), {'role':'reader','confirm':'on'})
        self.assertContains(response,'Mantenha pelo menos um administrador')
        self.admin_access.refresh_from_db()
        self.assertTrue(self.admin_access.active)
        self.assertEqual(self.admin_access.role,'admin')

    def test_admin_can_share_only_own_workspace_and_switch_is_validated(self):
        user = get_user_model().objects.create_user(username='new@example.com',email='new@example.com')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse('feeds:users'),{'email':user.email,'role':'editor'}).status_code,302)
        self.assertEqual(Membership.objects.get(user=user).workspace,self.space)
        self.assertEqual(self.client.post(reverse('feeds:switch_workspace'),{'workspace_id':self.other.pk}).status_code,404)
        self.client.force_login(self.reader)
        self.assertEqual(self.client.post(reverse('feeds:switch_workspace'),{'workspace_id':self.other.pk}).status_code,302)
        self.assertContains(self.client.get('/'),'Grupo dois')
