from django.urls import reverse
from django.test import Client
from feeds.models import NewsItemAnalysis
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
        self.assertContains(response, 'aria-label="Alternar espaço"')

    def test_styles_use_release_version_for_browser_cache_invalidation(self):
        for name in ('index','news','sources','tags','users','login','signup'):
            with self.subTest(name=name):
                client = Client() if name in ('login', 'signup') else self.client
                response = client.get(reverse('feeds:' + name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '.css?v=')
