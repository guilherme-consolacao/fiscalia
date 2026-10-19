from django.urls import reverse
from django.test import Client
from feeds.models import NewsItemAnalysis, Membership, Workspace
from feeds.tests.scenarios import WorkspaceScenario


class CompactLayoutContracts(WorkspaceScenario):
    def test_advanced_filters_start_closed_and_preserve_active_selection(self):
        response = self.client.get(reverse('feeds:news'))
        self.assertContains(response, '<details class="news-advanced-filters">')
        cases = [{'status':'unread'}, {'source':self.source.pk}, {'relevance':'high'}, {'effective_date_from':'2026-10-01'}, {'effective_date_to':'2026-10-31'}]
        for params in cases:
            with self.subTest(params=params):
                self.assertContains(self.client.get(reverse('feeds:news'), params), '<details class="news-advanced-filters" open>')

    def test_duplicate_source_and_ai_summary_is_not_rendered_twice(self):
        self.item.summary = 'Resumo idêntico de validação'
        self.item.save(update_fields=['summary'])
        NewsItemAnalysis.objects.filter(news_item=self.item).update(summary=self.item.summary)
        response = self.client.get(reverse('feeds:news'))
        self.assertContains(response, self.item.summary, count=1)
        self.assertNotContains(response, 'Resumo da fonte')

    def test_distinct_source_summary_remains_available_in_details(self):
        self.item.summary = 'Resumo original da fonte'
        self.item.save(update_fields=['summary'])
        NewsItemAnalysis.objects.filter(news_item=self.item).update(summary='Resumo analítico complementar')
        response = self.client.get(reverse('feeds:news'))
        self.assertContains(response, '<summary>Resumo da fonte</summary>')
        self.assertContains(response, self.item.summary)
        self.assertContains(response, 'Resumo analítico complementar')

    def test_search_and_each_selection_have_accessible_names(self):
        response = self.client.get(reverse('feeds:news'))
        self.assertContains(response, '<span class="visually-hidden">Pesquisar informativos</span>')
        self.assertContains(response, f'Selecionar {self.item.title}')
        self.assertContains(response, 'aria-controls="workspace-options"')

    def test_styles_use_release_version_for_browser_cache_invalidation(self):
        for name in ('index','news','sources','tags','users','login','signup'):
            with self.subTest(name=name):
                client = Client() if name in ('login', 'signup') else self.client
                response = client.get(reverse('feeds:' + name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '.css?v=')

    def test_account_and_team_identity_only_offer_active_memberships(self):
        user = self.users['admin']
        user.first_name = 'Ana'
        user.last_name = 'Silva'
        user.save(update_fields=['first_name', 'last_name'])
        second = Workspace.objects.create(name='Equipe de revisão')
        inactive = Workspace.objects.create(name='Equipe desativada')
        Membership.objects.create(workspace=second, user=user, role='reader')
        Membership.objects.create(workspace=inactive, user=user, role='editor', active=False)
        response = self.client.get(reverse('feeds:index'))
        self.assertContains(response, 'Minha conta')
        self.assertContains(response, 'Ana Silva')
        self.assertContains(response, user.email)
        self.assertContains(response, 'Seu papel nesta equipe')
        self.assertContains(response, 'Administrador')
        self.assertContains(response, second.name)
        self.assertNotContains(response, inactive.name)
        self.assertNotContains(response, self.foreign_space.name)

        response = self.client.post(reverse('feeds:switch_workspace'), {'workspace_id':second.pk}, follow=True)
        self.assertEqual(response.wsgi_request.user.pk, user.pk)
        self.assertEqual(response.wsgi_request.workspace.pk, second.pk)
        self.assertContains(response, user.email)
        self.assertContains(response, '<dd>Leitor</dd>')
        self.assertNotContains(response, 'Gerenciar equipe atual')

    def test_single_team_shows_current_choice_and_keeps_exit_in_account_menu(self):
        response = self.client.get(reverse('feeds:index'))
        self.assertContains(response, 'class="workspace-option is-current" disabled aria-current="true"')
        self.assertContains(response, 'Fontes, tags e informativos pertencem à equipe selecionada.')
        self.assertContains(response, 'Ao trocar de equipe, você continua na mesma conta.')
        self.assertContains(response, 'Sair da conta')
        self.assertNotContains(response, 'id="workspace-switch"')
