from django.db import models


class AuthRateLimit(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    hits = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
