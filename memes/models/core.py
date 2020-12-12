from django.db import models, InternalError
from django.db.models import Q, CheckConstraint, UniqueConstraint
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
# from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.signals import post_delete
from django.dispatch import receiver

from memes.utils import check_valid_file_ext, resize_any_image

from secrets import token_urlsafe
from io import BytesIO
import os, ffmpeg, boto3, json


client = boto3.client('lambda', region_name=settings.AWS_S3_REGION_NAME)


def set_uuid():
    return token_urlsafe(8)


# Gets random string from set_uuid() then add extension from current filename
def set_random_filename(current):
    return f"{token_urlsafe(5)}{os.path.splitext(current)[1].lower()}"


def user_directory_path_profile(instance, filename):
    return f"users/{instance.username}/profile/{set_random_filename(filename)}"


class User(AbstractUser):
    image = models.ImageField(upload_to=user_directory_path_profile, null=True, blank=True)
    small_image = models.ImageField(upload_to=user_directory_path_profile, null=True, blank=True)
    follows = models.ManyToManyField(settings.AUTH_USER_MODEL, symmetrical=False, related_name="followers", through="Following")
    nsfw = models.BooleanField(default=False)
    show_nsfw = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username}"

    def add_profile_image(self, file):
        # Delete existing images
        if self.image:
            self.image.delete(False)
        if self.small_image:
            self.small_image.delete(False)

        # Save new profile image
        self.image.save(file.name, file, False)
        # Save name of new profile image
        self.small_image.name = user_directory_path_profile(self, file.name)
        self.save(update_fields=("image", "small_image"))

        # Resize new images
        client.invoke(
            FunctionName="resize_profile_image",
            InvocationType="Event",
            Payload=json.dumps({
                "image_key": self.image.name,
                "small_image_key": self.small_image.name,
            }),
            Qualifier="$LATEST"
        )

        # Update all memes and comments
        self.meme_set.update(user_image=self.small_image.name)
        self.comment_set.update(user_image=self.small_image.name)

    def delete_profile_image(self):
        self.image.delete()
        self.small_image.delete()
        self.meme_set.update(user_image="")
        self.comment_set.update(user_image="")


@receiver(post_delete, sender=User)
def delete_user_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)
    if instance.small_image:
        instance.small_image.delete(False)


class Following(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    date_followed = models.DateTimeField(auto_now_add=True)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    num_memes = models.PositiveIntegerField(default=0)
    clout = models.IntegerField(default=0)
    bio = models.CharField(max_length=64, blank=True)
    num_followers = models.PositiveIntegerField(default=0)
    num_following = models.PositiveIntegerField(default=0)
    num_views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} profile"


def original_meme_path(instance, filename):
    return f"users/{instance.user.username}/memes/original/{set_random_filename(filename)}"


class MemeManager(models.Manager):
    def get_queryset(self):
        # Always return unhidden memes
        return super().get_queryset().filter(hidden=False)


class Meme(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    username = models.CharField(max_length=32, blank=False)
    user_image = models.ImageField(null=True, blank=True)

    # Page fields
    page = models.ForeignKey("Page", on_delete=models.SET_NULL, null=True, blank=True)
    page_private = models.BooleanField(default=False)
    page_name = models.CharField(max_length=32, blank=True)
    page_display_name = models.CharField(max_length=32, blank=True)

    # Store original file
    original = models.FileField(upload_to=original_meme_path, null=False, blank=False)
    # Full size (960x960 for images, 720x720 for video) for desktop (WEBP/MP4)
    large = models.FileField(null=True, blank=True)
    # Thumbnail (400x400) (WEBP)
    thumbnail = models.ImageField(null=True, blank=True)

    uuid = models.CharField(max_length=11, default=set_uuid, unique=True)
    dank = models.BooleanField(default=False)
    caption = models.CharField(max_length=100, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    num_likes = models.PositiveIntegerField(default=0)
    num_dislikes = models.PositiveIntegerField(default=0)
    points = models.IntegerField(default=0)
    num_comments = models.PositiveIntegerField(default=0)
    nsfw = models.BooleanField(default=False)
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField("Tag", related_name="memes")
    # tags_list = ArrayField(models.CharField(max_length=64, blank=False), blank=True)

    num_reports = models.PositiveIntegerField(default=0)
    num_views = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True)
    hidden = models.BooleanField(default=False)

    objects = MemeManager()

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.id}"

    def get_thumbnail_url(self):
        try:
            return self.thumbnail.url
        except ValueError:
            return self.original.url

        raise InternalError()

    def get_file_url(self):
        try:
            return self.large.url
        except ValueError:
            return self.original.url

        raise InternalError()

    def get_original_ext(self):
        return os.path.splitext(self.original.name)[1].lower()

    def resize_image(self):
        # Check if original file is a GIF
        is_gif = self.get_original_ext() == ".gif"
        prefix = f"users/{self.username}/memes"
        # Assign new name for large
        self.large.name = f"{prefix}/large/{set_random_filename('a.mp4' if is_gif else 'a.webp')}"
        # Assign new name for thumbnail
        self.thumbnail.name = f"{prefix}/thumbnail/{set_random_filename('a.webp')}"

        # Invoke async function to resize GIF or image
        client.invoke(
            FunctionName="resize_gif_meme" if is_gif else "resize_image_meme",
            InvocationType="Event",
            Payload=json.dumps({
                "get_file_at": self.original.name,
                "large_key": self.large.name,
                "thumbnail_key": self.thumbnail.name,
            })
        )

        # Save fields after invoking function to buy some time
        self.save(update_fields=("large", "thumbnail"))

    def resize_video(self):
        response = client.invoke(
            FunctionName="check_video_meme",
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "get_file_at": self.original.name,
            }),
            Qualifier="$LATEST"
        )

        response = json.loads(response["Payload"].read())

        if response.get("statusCode") == 200:
            # Assign new large and thumbnail names
            self.large.name = f"users/{self.username}/memes/large/{set_random_filename('a.mp4')}"
            self.thumbnail.name = f"users/{self.username}/memes/thumbnail/{set_random_filename('a.webp')}"

            # Invoke async function to resize video
            client.invoke(
                FunctionName="resize_video_meme",
                InvocationType="Event",
                Payload=json.dumps({
                    "get_file_at": self.original.name,
                    "large_key": self.large.name,
                    "thumbnail_key": self.thumbnail.name,
                }),
                Qualifier="$LATEST"
            )

            # Save fields after invoking function to buy some time
            self.save(update_fields=("large", "thumbnail"))

            return

        self.delete()
        if response.get("statusCode") == 418:
            raise ValidationError(response.get("errorMessage"))

        raise InternalError()

    def resize_file(self):
        if self.get_original_ext() in (".jpg", ".png", ".jpeg", ".gif"):
            self.resize_image()
        elif self.get_original_ext() in (".mp4", ".mov"):
            self.resize_video()
        else:
            raise InternalError("Invalid file type")


@receiver(post_delete, sender=Meme)
def delete_meme_files(sender, instance, **kwargs):
    instance.original.delete(False)
    instance.large.delete(False)
    instance.thumbnail.delete(False)


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True, blank=False)

    class Meta:
        constraints = [CheckConstraint(check=Q(name__regex="^[a-zA-Z][a-zA-Z0-9_]*$"), name="tag_chars_valid")]

    def __str__(self):
        return f"{self.name}"


class Category(models.Model):

    class Name(models.TextChoices):
        MOVIES = "movies", _("Movies")
        TV = "tv", _("TV")
        GAMING = "gaming", _("Gaming")
        ANIMALS = "animals", _("Animals")
        INTERNET = "internet", _("Internet")
        SCHOOL = "school", _("School")
        ANIME = "anime", _("Anime")
        CELEBRITIES = "celebrities", _("Celebrities")
        SPORTS = "sports", _("Sports")
        FOOTBALL = "football", _("Football")
        NBA = "nba", _("NBA")
        NFL = "nfl", _("NFL")
        NEWS = "news", _("News")
        UNIVERSITY = "university", _("University")

    name = models.CharField(max_length=32, choices=Name.choices)

    def __str__(self):
        return f"{self.name}"


def user_directory_path_comments(instance, filename):
    return f"users/{instance.user.username}/comments/{set_random_filename(filename)}"


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=32, blank=False)
    user_image = models.ImageField(null=True, blank=True)

    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=False, blank=False, related_name="comments")
    meme_uuid = models.CharField(max_length=11, blank=False)

    """ For comments that are replies """
    # Root comment
    root = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    # Comment directly being replied to
    reply_to = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")

    uuid = models.CharField(max_length=11, default=set_uuid, unique=True)
    post_date = models.DateTimeField(auto_now_add=True)
    content = models.CharField(max_length=150, blank=True)
    image = models.ImageField(upload_to=user_directory_path_comments, null=True, blank=True)
    points = models.IntegerField(default=0)
    num_replies = models.PositiveIntegerField(default=0)
    edited = models.BooleanField(default=False)

    class Deleted(models.IntegerChoices):
        NO = 0, _("Not deleted"),
        USER = 1, _("Deleted by user")
        MEME_OP = 2, _("Deleted by meme OP")
        MODERATOR = 3, _("Removed by moderator")
        STAFF = 4, _("Deleted by staff")

    deleted = models.PositiveSmallIntegerField(default=0, choices=Deleted.choices)

    def __str__(self):
        return f"{self.user.username}: {self.content}"

    def resize_image(self):
        if self.image:
            dimension = 400 if self.reply_to else 480
            resize_any_image(self.image.name, (dimension, dimension))


@receiver(post_delete, sender=Comment)
def delete_comment_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    point = models.IntegerField()
    liked_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        constraints = [CheckConstraint(check=Q(point=1)|Q(point=-1), name="single_point_vote")]


class MemeLike(Like):
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=False, blank=False, related_name="likes")
    meme_uuid = models.CharField(max_length=11, blank=False)

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "meme"], name="unique_meme_vote")]

    def __str__(self):
        return f"{self.user.username} meme {self.meme_id} {'' if self.point == 1 else 'dis'}like"


class CommentLike(Like):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=False, blank=False, related_name="comment_likes")
    comment_uuid = models.CharField(max_length=11, blank=False)

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "comment"], name="unique_comment_vote")]

    def __str__(self):
        return f"{self.user.username} comment {self.comment_id} {'' if self.point == 1 else 'dis'}like"

