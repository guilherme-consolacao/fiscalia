import ipaddress
from urllib.parse import urlsplit
from django.core.exceptions import ValidationError


def validate_public_url(url):
    try:
        parts = urlsplit(url)
        hostname = parts.hostname or ''
        valid_port = parts.port in (None, 80 if parts.scheme == 'http' else 443)
    except ValueError as error:
        raise ValidationError('Informe uma URL pública HTTP ou HTTPS válida.') from error
    if parts.scheme not in ('http', 'https') or not hostname or parts.username is not None or parts.password is not None or not valid_port or '\\' in url or any(ord(c) < 33 for c in url):
        raise ValidationError('Use uma URL pública HTTP ou HTTPS, sem credenciais e sem porta personalizada.')
    if hostname.lower().rstrip('.').endswith(('.localhost', '.local', '.internal')) or hostname.lower().rstrip('.') == 'localhost':
        raise ValidationError('Endereços locais não são permitidos.')
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if '.' not in hostname:
            raise ValidationError('Informe um endereço público completo.')
    else:
        if not address.is_global or (address.version == 6 and address.ipv4_mapped and not address.ipv4_mapped.is_global):
            raise ValidationError('Endereços de rede interna não são permitidos.')
    return parts


