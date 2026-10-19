from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from feeds.tenancy import WorkspaceManager, current_workspace_id


class Workspace(models.Model):
    name = models.CharField('nome do espaço', max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    READER = 'reader'
    EDITOR = 'editor'
    ADMIN = 'admin'
    ROLE_CHOICES = [(READER, 'Leitor'), (EDITOR, 'Editor'), (ADMIN, 'Administrador')]
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField('perfil', max_length=12, choices=ROLE_CHOICES, default=READER)
    active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workspace', 'user'], name='unique_workspace_member')]


class WorkspaceModel(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, default=current_workspace_id)
    objects = WorkspaceManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if hasattr(self, 'source_id') and self.source_id:
            if self.source.workspace_id != self.workspace_id:
                raise ValidationError('A fonte deve pertencer ao mesmo espaço.')
        return super().save(*args, **kwargs)
