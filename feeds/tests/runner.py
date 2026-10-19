from unittest.mock import patch
import ipaddress
import socket
from django.test.runner import DiscoverRunner


class IsolatedTestRunner(DiscoverRunner):
    """A missing HTTP mock fails the suite instead of consuming provider quota."""
    def run_tests(self, test_labels, **kwargs):
        original_connect = socket.socket.connect
        blocked = []

        def connect_local(sock, address):
            # Windows event loops can create a loopback socket pair for IPC.
            host = address[0] if isinstance(address, tuple) else None
            try:
                local = host == 'localhost' or host is not None and ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = False
            if local or sock.family == getattr(socket, 'AF_UNIX', None):
                return original_connect(sock, address)
            blocked.append(True)
            raise AssertionError('Conexão externa bloqueada nos testes.')

        with patch('requests.sessions.Session.request', side_effect=AssertionError('HTTP externo bloqueado nos testes.')) as http, patch('socket.socket.connect', new=connect_local):
            failures = super().run_tests(test_labels, **kwargs)
            if http.call_count or blocked:
                raise RuntimeError(f'Testes tentaram usar a rede: HTTP={http.call_count}, sockets={len(blocked)}. Adicione respostas simuladas explícitas.')
            return failures
