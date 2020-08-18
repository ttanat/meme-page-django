from django.db import models
from django.db.models import Q, CheckConstraint, UniqueConstraint
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class View(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.content_object} viewed on {self.timestamp}"


def default_JSON():
    return {}


class TagUse(models.Model):
    lower_name = models.CharField(max_length=64, blank=False)
    day = models.DateField(auto_now_add=True)
    count = models.PositiveIntegerField(default=0)
    variants = models.JSONField(default=default_JSON)

    class Meta:
        constraints = [
            CheckConstraint(check=Q(lower_name__regex="^[a-z][a-z0-9_]*$"), name="lowercase_tag_chars_valid"),
            UniqueConstraint(fields=["lower_name", "day"], name="unique_tag_name_day")
        ]

    def __str__(self):
        return f"#{self.lower_name} | {self.day} | {self.count} post{'s' if self.count > 1 else ''}"


class Trending(models.Model):
    data = models.JSONField(default=default_JSON)
    day = models.DateField(auto_now_add=True, unique=True)

    def __str__(self):
        return f"Trending data - {self.day}"
