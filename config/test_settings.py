"""Deterministic settings for the automated suite; never used for deployment."""
import os
os.environ.setdefault('SECRET_KEY', 'test-only-key-not-for-deployment-683517097db1a2e68283d6c9')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('DEBUG', 'False')
from .settings import *  # noqa: F403,E402

NEWS_AI['ENABLED'] = False
NEWS_AI['OPENAI_API_KEY'] = 'test-key-not-real'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
