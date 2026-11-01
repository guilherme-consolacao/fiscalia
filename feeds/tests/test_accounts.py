from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from feeds.models import Workspace, Membership


class AccountTests(TestCase):
    def signup(self, email='someone@example.com'):
        return self.client.post(reverse('feeds:signup'), {'first_name':'Pessoa', 'email':email, 'workspace_name':'Meu grupo', 'password1':'Strong-example-7419!', 'password2':'Strong-example-7419!', 'is_superuser':'true', 'role':'admin'})

    def test_registration_session_and_logout(self):
        self.assertEqual(self.signup().status_code, 302)
        user = get_user_model().objects.get(email='someone@example.com')
        self.assertTrue(user.check_password('Strong-example-7419!'))
        self.assertFalse(user.is_staff or user.is_superuser)
        membership = Membership.objects.get(user=user)
        self.assertEqual(membership.role, Membership.ADMIN)
        self.assertNotEqual(membership.workspace_id, 1)
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get(reverse('feeds:logout')).status_code, 405)
        self.client.post(reverse('feeds:logout'))
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertEqual(self.client.post(reverse('feeds:login'), {'username':user.email.upper(),'password':'wrong'}).status_code, 200)
        self.assertEqual(self.client.post(reverse('feeds:login'), {'username':user.email.upper(),'password':'Strong-example-7419!','next':'https://evil.example'}).url, '/')

    def test_invalid_duplicate_and_csrf(self):
        self.signup()
        other = Client()
        self.assertContains(other.post(reverse('feeds:signup'), {'first_name':'Outra','email':'SOMEONE@example.com','workspace_name':'Segundo','password1':'Strong-example-7419!','password2':'Strong-example-7419!'}), 'Não foi possível usar este e-mail')
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('feeds:signup'), {}).status_code, 403)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_separate_sessions_and_disabled_membership(self):
        self.signup()
        first_id = self.client.session['_auth_user_id']
        other = Client()
        other.post(reverse('feeds:signup'), {'first_name':'Outra','email':'another@example.com','workspace_name':'Outro grupo','password1':'Strong-example-7419!','password2':'Strong-example-7419!'})
        self.assertNotEqual(other.session['_auth_user_id'], first_id)
        Membership.objects.filter(user_id=first_id).update(active=False)
        self.assertRedirects(self.client.get('/'), reverse('feeds:no_workspace'), fetch_redirect_response=False)
        self.assertEqual(other.get('/').status_code, 200)

    def test_registered_person_joins_another_team_with_the_same_account(self):
        self.signup()
        user = get_user_model().objects.get(email='someone@example.com')
        initial = Membership.objects.get(user=user)
        password_hash = user.password
        team = Workspace.objects.create(name='Equipe compartilhada')
        owner = get_user_model().objects.create_user(username='owner@example.com')
        Membership.objects.create(workspace=team, user=owner, role=Membership.ADMIN)
        administrator = Client()
        administrator.force_login(owner)

        response = administrator.post(reverse('feeds:users'), {'email':user.email.upper(), 'role':Membership.EDITOR})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertEqual(user.password, password_hash)
        self.assertEqual(Membership.objects.get(workspace=team, user=user).role, Membership.EDITOR)
        initial.refresh_from_db()
        self.assertEqual(initial.role, Membership.ADMIN)
        self.assertTrue(initial.active)

        self.client.post(reverse('feeds:switch_workspace'), {'workspace_id':team.pk})
        response = self.client.get('/')
        self.assertEqual(response.wsgi_request.user.pk, user.pk)
        self.assertEqual(response.wsgi_request.workspace.pk, team.pk)
        self.client.post(reverse('feeds:logout'))
        self.assertEqual(self.client.post(reverse('feeds:login'), {'username':user.email, 'password':'Strong-example-7419!'}).status_code, 302)
