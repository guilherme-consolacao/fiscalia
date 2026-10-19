from django.conf import settings
from django.db import models
from feeds.tenancy import PersonalManager, current_user_id


class NewsItemRead(models.Model):
    workspace_lookup = 'news_item__workspace_id'
    objects = PersonalManager()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=current_user_id)
    news_item = models.ForeignKey('feeds.NewsItem', on_delete=models.CASCADE, related_name='read_by')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'news_item'], name='unique_user_news_read')]
