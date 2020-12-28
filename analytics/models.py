from django.db import models
from django.db.models import Q, CheckConstraint
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField

from memes.models import Meme


class View(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.content_object} viewed on {self.timestamp}"


def empty_list():
    return []


class Trending(models.Model):
    data = ArrayField(models.CharField(max_length=64, blank=False), default=empty_list)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trending data - {self.timestamp}"
