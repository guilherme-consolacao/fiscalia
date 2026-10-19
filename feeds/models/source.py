from django.db import models

from feeds.models.source_category import SourceCategory
from feeds.models.workspace import WorkspaceModel
from feeds.validators import validate_public_url


class Source(WorkspaceModel):
    name = models.CharField('nome', max_length=150)
    url = models.URLField('URL do feed RSS', max_length=500, validators=[validate_public_url])
    description = models.TextField('descrição', blank=True)
    category = models.ForeignKey(
        SourceCategory,
        verbose_name='categoria',
        on_delete=models.PROTECT,
        related_name='sources',
    )
    tags = models.ManyToManyField(
        'feeds.Tag',
        verbose_name='tags de score',
        related_name='sources',
        blank=True,
    )
    active = models.BooleanField('ativa', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workspace', 'url'], name='unique_workspace_source_url')]
        ordering = ['name']
        verbose_name = 'Fonte RSS'
        verbose_name_plural = 'Fontes RSS'

    def __str__(self):
        return self.name
