"""Fail-closed entry point for production. Infrastructure supplies the secrets."""
import os
os.environ['APP_ENV'] = 'production'
os.environ['DEBUG'] = 'False'
from .settings import *  # noqa: F403,E402
