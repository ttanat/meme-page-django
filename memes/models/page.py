from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator

from secrets import token_urlsafe
from PIL import Image

from .core import Meme, Comment, set_random_filename


def page_directory_path(instance, filename):
    return f"pages/{instance.name}/{set_random_filename(filename)}"


class Page(models.Model):
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    moderators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="moderating", through="Moderator")
    subscribers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="subscriptions")
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

    def __str__(self):
        return f"{self.name}"

    def resize_img(self):
        img = Image.open(self.image.path)
        if img.height > 200 or img.width > 200:
            img.thumbnail((200, 200))
            img.save(self.image.path)

    def resize_cover(self):
        cover = Image.open(self.cover.path)
        if cover.height > 150 or cover.width > 2000:
            cover.thumbnail((2000, 150))
            cover.save(self.cover.path)

    def delete(self, *args, **kwargs):
        self.image.delete()
        self.cover.delete()
        super().delete(*args, **kwargs)


class Moderator(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=32, blank=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    link = models.URLField(max_length=64, blank=False)
    seen = models.BooleanField(default=False)
    image = models.URLField(max_length=128, blank=True, default="")
    message = models.CharField(max_length=128, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    target_meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=True, blank=True)
    target_comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    target_page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.message}"


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
    uses = models.PositiveSmallIntegerField(default=1, validators=[MaxValueValidator(100), MinValueValidator(1)])
    timestamp = models.DateTimeField(auto_now_add=True)

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
