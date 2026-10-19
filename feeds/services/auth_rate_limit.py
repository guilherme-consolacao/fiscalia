from datetime import timedelta
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac
from feeds.models import AuthRateLimit


def allow_auth_attempt(request, action, limit, seconds):
    # Only REMOTE_ADDR is trusted; forwarded headers require a separately
    # configured reverse proxy. Raw IPs and credentials are never stored.
    key = salted_hmac('auth-rate-limit', action + ':' + request.META.get('REMOTE_ADDR', '')).hexdigest()
    now = timezone.now()
    expires = now + timedelta(seconds=seconds)
    AuthRateLimit.objects.get_or_create(key=key, defaults={'expires_at':expires})
    AuthRateLimit.objects.filter(key=key, expires_at__lte=now).update(hits=0, expires_at=expires)
    AuthRateLimit.objects.filter(key=key).update(hits=F('hits')+1)
    return AuthRateLimit.objects.get(key=key).hits <= limit
