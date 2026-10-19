from django.db.models import Exists, OuterRef
from feeds.models import NewsItem, NewsItemRead


def personal_news():
    return NewsItem.objects.annotate(user_has_read=Exists(NewsItemRead.objects.filter(news_item_id=OuterRef('pk'))))
