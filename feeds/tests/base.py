from django.contrib.auth import get_user_model
from django.test import TestCase
from feeds.models import Membership, Workspace
from feeds.tenancy import workspace_scope


class PortalTestCase(TestCase):
    """Existing feature regressions run as an authorized legacy-space admin."""
    @classmethod
    def _pre_setup(cls):
        super()._pre_setup()
        cls.portal_user, _ = get_user_model().objects.get_or_create(username='regression@example.com', defaults={'email':'regression@example.com'})
        Membership.objects.get_or_create(user=cls.portal_user, workspace_id=1, defaults={'role':'admin'})
        cls.client.force_login(cls.portal_user)
        cls._scope = workspace_scope(1, cls.portal_user.pk)
        cls._scope.__enter__()

    def _post_teardown(self):
        self._scope.__exit__(None, None, None)
        super()._post_teardown()
