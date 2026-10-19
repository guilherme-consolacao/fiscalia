"""Request/worker-local scope. Unscoped access is reserved for management tasks."""
from contextlib import contextmanager
from contextvars import ContextVar
from django.db import models

_workspace_id = ContextVar('fiscalia_workspace_id', default=None)
_user_id = ContextVar('fiscalia_user_id', default=None)


def current_workspace_id():
    return _workspace_id.get() or 1


def current_user_id():
    return _user_id.get()


@contextmanager
def workspace_scope(workspace_id, user_id=None):
    workspace_token = _workspace_id.set(workspace_id)
    user_token = _user_id.set(user_id)
    try:
        yield
    finally:
        _user_id.reset(user_token)
        _workspace_id.reset(workspace_token)


class WorkspaceManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        workspace_id = _workspace_id.get()
        if workspace_id is not None:
            lookup = getattr(self.model, 'workspace_lookup', 'workspace_id')
            queryset = queryset.filter(**{lookup: workspace_id})
        return queryset


class PersonalManager(WorkspaceManager):
    def get_queryset(self):
        queryset = super().get_queryset()
        if _workspace_id.get() is not None:
            queryset = queryset.filter(user_id=_user_id.get())
        return queryset
