from django.db import models
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver

from secrets import token_urlsafe
from PIL import Image

from .core import Meme, Comment, set_random_filename
import boto3, json


client = boto3.client('lambda', region_name=settings.AWS_S3_REGION_NAME)


def page_directory_path(instance, filename):
    return f"pages/{instance.name}/{set_random_filename(filename)}"


class Page(models.Model):
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    moderators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="moderating", through="Moderator")
    subscribers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="subscriptions", through="Subscriber")
    created = models.DateTimeField(auto_now_add=True)

    name = models.CharField(max_length=32, blank=False, unique=True)
    display_name = models.CharField(max_length=32, blank=True)
    image = models.ImageField(upload_to=page_directory_path, null=True, blank=True)
    cover = models.ImageField(upload_to=page_directory_path, null=True, blank=True)
    description = models.CharField(max_length=300, blank=True, default="")
    nsfw = models.BooleanField(default=False)
    private = models.BooleanField(default=False)
    # True if subscribers can post / False if only admin can post
    permissions = models.BooleanField(default=True)

    num_mods = models.PositiveSmallIntegerField(default=0)
    num_subscribers = models.PositiveIntegerField(default=0)
    num_posts = models.PositiveIntegerField(default=0)
    num_views = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(name__regex="^[a-zA-Z0-9_]+$"), name="page_name_chars_valid")]

    def __str__(self):
        return f"{self.name}"

    def resize_image(self):
        if self.image:
            client.invoke(
                FunctionName="resize_any_image",
                InvocationType="Event",
                Payload=json.dumps({
                    "file_key": self.image.name,
                    "dimensions": (200, 200),
                }),
                Qualifier="$LATEST"
            )

    def resize_cover(self):
        if self.cover:
            client.invoke(
                FunctionName="resize_any_image",
                InvocationType="Event",
                Payload=json.dumps({
                    "file_key": self.cover.name,
                    "dimensions": (2000, 150),
                }),
                Qualifier="$LATEST"
            )


@receiver(post_delete, sender=Page)
def delete_page_image_and_cover(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)
    if instance.cover:
        instance.cover.delete(False)


class Moderator(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)


class Subscriber(models.Model):
    subscriber = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)


class SubscribeRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.user} wants to join {self.page}"


def get_invite_link():
    return token_urlsafe(5)


class InviteLink(models.Model):
    """ Let page admins create links to join their private page """
    uuid = models.CharField(max_length=7, default=get_invite_link)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    uses = models.PositiveSmallIntegerField(default=1)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(uses__lte=100)&models.Q(uses__gt=0), name="invite_link_use_limit")]

    def __str__(self):
        return f"Invite link for {self.page}"


class ModeratorInvite(models.Model):
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.invitee} invited to moderate for {self.page}"
