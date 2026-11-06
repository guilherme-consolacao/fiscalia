"""Fail-closed entry point for production. Infrastructure supplies the secrets."""
import os
os.environ['APP_ENV'] = 'production'
os.environ['DEBUG'] = 'False'
from .settings import *  # noqa: F403,E402

MIDDLEWARE = [MIDDLEWARE[0], 'whitenoise.middleware.WhiteNoiseMiddleware', *MIDDLEWARE[1:]]
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
SECURE_REDIRECT_EXEMPT = [r'^saude/$']
TRUST_RENDER_CLIENT_IP = env.bool('TRUST_RENDER_CLIENT_IP', default=False)
