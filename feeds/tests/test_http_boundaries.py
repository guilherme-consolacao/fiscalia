from unittest.mock import MagicMock, patch
import requests
from django.test import SimpleTestCase
from feeds.services.safe_http import fetch_url, resolve_public_address
from feeds.validators import validate_public_url
from django.core.exceptions import ValidationError


class PublicHttpBoundaryTests(SimpleTestCase):
    def response(self, redirect=False):
        response = MagicMock()
        response.__enter__.return_value = response
        response.url = 'https://example.com/rss'
        response.is_redirect = redirect
        response.iter_content.return_value = [b'<rss/>']
        response.headers = {'Location':'/next'} if redirect else {}
        return response

    def test_success_returns_bounded_body_and_disables_environment_proxies(self):
        response = self.response()
        with patch('feeds.services.safe_http.requests.Session') as factory:
            session = factory.return_value.__enter__.return_value
            session.get.return_value = response
            result = fetch_url('https://example.com/rss', headers={'Accept':'application/xml'})
        self.assertEqual(result._content, b'<rss/>')
        self.assertTrue(result._content_consumed)
        self.assertFalse(session.trust_env)
        self.assertEqual(session.get.call_args.kwargs['allow_redirects'], False)
        self.assertEqual(session.get.call_args.kwargs['timeout'], (5, 5))

    def test_relative_public_redirect_is_resolved_and_revalidated(self):
        with patch('feeds.services.safe_http.requests.Session') as factory:
            session = factory.return_value.__enter__.return_value
            session.get.side_effect = [self.response(True), self.response()]
            fetch_url('https://example.com/rss')
        self.assertEqual([call.args[0] for call in session.get.call_args_list], ['https://example.com/rss','https://example.com/next'])

    def test_redirect_loop_is_limited_to_four_requests(self):
        with patch('feeds.services.safe_http.requests.Session') as factory:
            session = factory.return_value.__enter__.return_value
            session.get.return_value = self.response(True)
            with self.assertRaises(requests.TooManyRedirects):
                fetch_url('https://example.com/rss')
        self.assertEqual(session.get.call_count, 4)

    def test_timeout_before_connect_and_during_streaming(self):
        with patch('feeds.services.safe_http.time.monotonic', side_effect=[0, 20]), patch('feeds.services.safe_http.requests.Session') as factory:
            with self.assertRaises(requests.Timeout):
                fetch_url('https://example.com/rss', timeout=1)
            factory.return_value.__enter__.return_value.get.assert_not_called()
        with patch('feeds.services.safe_http.time.monotonic', side_effect=[0, 0, 20]), patch('feeds.services.safe_http.requests.Session') as factory:
            factory.return_value.__enter__.return_value.get.return_value = self.response()
            with self.assertRaises(requests.Timeout):
                fetch_url('https://example.com/rss', timeout=1)

    def test_http_failure_does_not_parse_or_return_an_error_body(self):
        response = self.response()
        response.raise_for_status.side_effect = requests.HTTPError('503')
        with patch('feeds.services.safe_http.requests.Session') as factory:
            factory.return_value.__enter__.return_value.get.return_value = response
            with self.assertRaises(requests.HTTPError):
                fetch_url('https://example.com/rss')
        response.iter_content.assert_not_called()

    def test_empty_dns_answers_and_resolution_failures_are_safe_errors(self):
        for side_effect, result in ((None, []), (OSError('dns unavailable'), None)):
            with self.subTest(error=side_effect), patch('feeds.services.safe_http.socket.getaddrinfo', side_effect=side_effect, return_value=result), self.assertRaises(requests.RequestException):
                resolve_public_address('https://example.com/rss')

    def test_url_edge_cases_reject_credentials_controls_and_non_public_hosts(self):
        urls = ['https://example.com:bad/rss','https://[invalid]/rss','https://example.com\\@127.0.0.1/','https://example.com/\nheader','http://localhost.','http://service.local','http://db.internal','https://singlehost','http://0.0.0.0','http://[fe80::1]','https://user@example.com']
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValidationError):
                validate_public_url(url)

    def test_valid_urls_keep_query_and_standard_ports(self):
        for url in ['https://example.com/rss?a=1&b=2','https://example.com:443/rss','http://example.com:80/rss','https://[2606:4700:4700::1111]/rss']:
            with self.subTest(url=url):
                self.assertIn(validate_public_url(url).scheme, ('http','https'))
