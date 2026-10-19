from django.db import models
from feeds.models.workspace import WorkspaceModel


class Tag(WorkspaceModel):
    COLOR_BLUE = 'blue'
    COLOR_GREEN = 'green'
    COLOR_RED = 'red'
    COLOR_YELLOW = 'yellow'
    COLOR_PURPLE = 'purple'
    COLOR_PINK = 'pink'
    COLOR_ORANGE = 'orange'
    COLOR_GRAY = 'gray'

    COLOR_CHOICES = [
        (COLOR_BLUE, 'Azul'),
        (COLOR_GREEN, 'Verde'),
        (COLOR_RED, 'Vermelho'),
        (COLOR_YELLOW, 'Amarelo'),
        (COLOR_PURPLE, 'Roxo'),
        (COLOR_PINK, 'Rosa'),
        (COLOR_ORANGE, 'Laranja'),
        (COLOR_GRAY, 'Cinza'),
    ]

    name = models.CharField('nome', max_length=50)
    color = models.CharField('cor', max_length=20, choices=COLOR_CHOICES, default=COLOR_BLUE)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workspace', 'name'], name='unique_workspace_tag_name')]
        ordering = ['-created_at']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name
