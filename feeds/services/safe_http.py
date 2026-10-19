"""Bounded public HTTP fetches with DNS-pinned connections and verified TLS."""
import ipaddress
import socket
import time
from urllib.parse import urlsplit, urljoin

import requests
from django.core.exceptions import ValidationError
from requests.adapters import HTTPAdapter

MAX_BYTES = 3 * 1024 * 1024
MAX_REDIRECTS = 3


from feeds.validators import validate_public_url


def resolve_public_address(url):
    try:
        parts = validate_public_url(url)
        addresses = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80), type=socket.SOCK_STREAM)
        if not addresses:
            raise ValueError('empty DNS answer')
        for record in addresses:
            address = ipaddress.ip_address(record[4][0])
            if not address.is_global or (address.version == 6 and address.ipv4_mapped and not address.ipv4_mapped.is_global):
                raise ValueError('non-public DNS answer')
        return parts, str(ipaddress.ip_address(addresses[0][4][0]))
    except (ValidationError, OSError, ValueError) as error:
        raise requests.RequestException('A fonte não possui um endereço público permitido.') from error


class PublicHTTPAdapter(HTTPAdapter):
    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        parts, address = resolve_public_address(request.url)
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(request, verify, cert)
        host_params['host'] = address
        if parts.scheme == 'https':
            pool_kwargs.update(assert_hostname=parts.hostname, server_hostname=parts.hostname)
        request.headers['Host'] = parts.netloc
        return self.poolmanager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)


def fetch_url(url, timeout=15, headers=None):
    deadline = time.monotonic() + min(max(float(timeout), 1), 45)
    with requests.Session() as session:
        session.trust_env = False
        session.mount('http://', PublicHTTPAdapter(max_retries=0))
        session.mount('https://', PublicHTTPAdapter(max_retries=0))
        for redirect_count in range(MAX_REDIRECTS + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise requests.Timeout('Tempo limite da fonte excedido.')
            # Validate before preparing the URL; the adapter resolves and pins
            # the public IP actually used to connect, including redirects.
            try:
                validate_public_url(url)
            except ValidationError as error:
                raise requests.RequestException('URL de fonte não permitida.') from error
            with session.get(url, timeout=(min(5, remaining), min(5, remaining)), headers=headers, stream=True, allow_redirects=False) as response:
                if response.is_redirect:
                    if redirect_count == MAX_REDIRECTS:
                        raise requests.TooManyRedirects('A fonte excedeu o limite de redirecionamentos.')
                    url = urljoin(response.url, response.headers['Location'])
                    continue
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_content(chunk_size=16384):
                    if time.monotonic() > deadline:
                        raise requests.Timeout('Tempo limite da fonte excedido.')
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise requests.RequestException('O conteúdo da fonte excedeu o limite de tamanho.')
                response._content = bytes(body)
                response._content_consumed = True
                return response
    raise requests.RequestException('Não foi possível buscar a fonte.')
