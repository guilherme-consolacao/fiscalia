from functools import wraps
from django.core.exceptions import PermissionDenied
from feeds.models import Membership


def workspace_roles(*roles):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            membership = getattr(request, 'membership', None)
            if not membership or not membership.active or membership.role not in roles:
                raise PermissionDenied('Seu perfil não permite esta ação neste espaço.')
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


editor_required = workspace_roles(Membership.EDITOR, Membership.ADMIN)
admin_required = workspace_roles(Membership.ADMIN)
