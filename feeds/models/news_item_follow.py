from django.db import models
from django.conf import settings
from feeds.tenancy import PersonalManager, current_user_id

from feeds.models.news_item import NewsItem


class NewsItemFollow(models.Model):
    workspace_lookup = 'news_item__workspace_id'
    objects = PersonalManager()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, default=current_user_id)
    news_item = models.ForeignKey(
        NewsItem,
        verbose_name='informativo',
        on_delete=models.CASCADE,
        related_name='follows',
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['news_item', 'user'], name='unique_user_news_follow')]
        verbose_name = 'Acompanhamento de Informativo'
        verbose_name_plural = 'Acompanhamentos de Informativos'

    def __str__(self):
        return f'Acompanhamento - {self.news_item.title}'
