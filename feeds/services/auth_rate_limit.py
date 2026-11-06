import logging
from datetime import timedelta
from ipaddress import ip_address
from math import ceil
from unicodedata import normalize

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from feeds.models import AuthRateLimit


logger = logging.getLogger(__name__)
LOGIN_FAILURE_LIMIT = 5
LOGIN_WINDOW_SECONDS = 900


def allow_auth_attempt(request, action, limit, seconds):
    return not auth_attempt_retry_after(request, action, limit, seconds)


def auth_attempt_retry_after(request, action, limit, seconds):
    origin = request.META.get('REMOTE_ADDR', '')
    if getattr(settings, 'TRUST_RENDER_CLIENT_IP', False):
        # Enable only when the Render edge replaces this header on ingress.
        try:
            origin = str(ip_address(request.META.get('HTTP_CF_CONNECTING_IP', '')))
        except ValueError:
            pass
    key = salted_hmac('auth-rate-limit', action + ':' + origin).hexdigest()
    now = timezone.now()
    expires = now + timedelta(seconds=seconds)
    AuthRateLimit.objects.get_or_create(key=key, defaults={'expires_at':expires})
    AuthRateLimit.objects.filter(key=key, expires_at__lte=now).update(hits=0, expires_at=expires)
    if AuthRateLimit.objects.filter(key=key, hits__lt=limit).update(hits=F('hits') + 1):
        return 0
    return _retry_after(AuthRateLimit.objects.get(key=key).expires_at, now)


def validate_login_attempt(username, validate):
    identifier = normalize('NFKC', username).casefold()
    key = salted_hmac('auth-login-account', identifier, algorithm='sha256').hexdigest()
    window = timedelta(seconds=LOGIN_WINDOW_SECONDS)

    with transaction.atomic():
        # Write first for SQLite, then lock the account's bucket on PostgreSQL.
        AuthRateLimit.objects.bulk_create(
            [AuthRateLimit(key=key, expires_at=timezone.now())], ignore_conflicts=True,
        )
        bucket = AuthRateLimit.objects.select_for_update().get(pk=key)
        now = timezone.now()
        if bucket.expires_at <= now:
            bucket.hits = 0
            bucket.expires_at = now + window
        if bucket.hits >= LOGIN_FAILURE_LIMIT:
            return _retry_after(bucket.expires_at, now)

        try:
            validate()
        except ValidationError as error:
            failure = error
            bucket.hits += 1
            if bucket.hits == LOGIN_FAILURE_LIMIT:
                bucket.expires_at = timezone.now() + window
        else:
            failure = None
            bucket.hits = 0
            bucket.expires_at = now
        bucket.save(update_fields=['hits', 'expires_at'])

    if bucket.hits == LOGIN_FAILURE_LIMIT:
        logger.warning('Bloqueio temporário de login após cinco falhas.')
        return _retry_after(bucket.expires_at, timezone.now())
    if failure is not None:
        raise failure
    return 0


def _retry_after(expires_at, now):
    return max(1, ceil((expires_at - now).total_seconds()))
