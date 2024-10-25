from django.db import models, InternalError
from django.db.models import Q, CheckConstraint, UniqueConstraint
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.signals import post_delete
from django.dispatch import receiver

from memes.utils import resize_any_image

from secrets import token_urlsafe
import os, boto3, json


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
    banned = models.BooleanField(default=False)

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
        self.memes.update(user_image=self.small_image.name)
        self.comments.update(user_image=self.small_image.name)

    def delete_profile_image(self):
        self.image.delete(False)
        self.small_image.delete(False)
        self.save(update_fields=("image", "small_image"))
        self.memes.update(user_image="")
        self.comments.update(user_image="")


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
    return f"users/{instance.user.username}/original/{set_random_filename(filename)}"


class MemeManager(models.Manager):
    def get_queryset(self):
        # Always return unhidden memes
        return super().get_queryset().filter(hidden=False)


class AllMemesManager(models.Manager):
    def get_queryset(self):
        # Return all memes
        return super().get_queryset()


def empty_list():
    return []


def empty_json():
    return {}


class Meme(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memes")
    username = models.CharField(max_length=32, blank=False)
    user_image = models.ImageField(null=True, blank=True)
    private = models.BooleanField(default=False)

    # Page fields
    page = models.ForeignKey("Page", on_delete=models.SET_NULL, null=True, blank=True)
    page_private = models.BooleanField(default=False)
    page_name = models.CharField(max_length=32, blank=True)

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
    tags = ArrayField(models.CharField(max_length=64, blank=False), default=empty_list)
    tags_lower = ArrayField(models.CharField(max_length=64, blank=False), default=empty_list)
    num_views = models.PositiveIntegerField(default=0)

    report_labels = models.JSONField(default=empty_json)
    reviewed = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    objects = MemeManager()
    all_objects = AllMemesManager()

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["user", "upload_date"])]

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
        # Assign new name for large
        self.large.name = f"users/{self.username}/large/{set_random_filename('a.mp4' if is_gif else 'a.webp')}"
        # Assign new name for thumbnail
        self.thumbnail.name = f"users/{self.username}/thumbnail/{set_random_filename('a.webp')}"

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
            # Assign new thumbnail name
            self.thumbnail.name = f"users/{self.username}/thumbnail/{set_random_filename('a.webp')}"

            # Invoke async function to resize video
            client.invoke(
                FunctionName="resize_video_meme",
                InvocationType="Event",
                Payload=json.dumps({
                    "get_file_at": self.original.name,
                    "thumbnail_key": self.thumbnail.name,
                }),
                Qualifier="$LATEST"
            )

            is_mov = self.get_original_ext() == ".mov"
            if is_mov:
                self.original.name = f"{os.path.splitext(self.original.name)[0]}.mp4"

            # Save new thumbnail (and original) name
            self.save(update_fields=("original", "thumbnail") if is_mov else ["thumbnail"])

        else:
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="comments")
    username = models.CharField(max_length=32, blank=True)
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

    report_labels = models.JSONField(default=empty_json)
    reviewed = models.BooleanField(default=False)

    class Deleted(models.IntegerChoices):
        NO = 0, _("Not deleted")
        USER = 1, _("Deleted by user")
        MEME_OP = 2, _("Deleted by meme OP")
        MODERATOR = 3, _("Removed by moderator")
        STAFF = 4, _("Deleted by staff")
        USER_DELETED = 5, _("User deleted")

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
    point = models.SmallIntegerField()
    liked_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        constraints = [CheckConstraint(check=Q(point=1)|Q(point=-1), name="single_point_vote")]


class MemeLike(Like):
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=False, blank=False, related_name="likes")
    meme_uuid = models.CharField(max_length=11, blank=False)

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "meme"], name="unique_meme_vote")]
        indexes = [
            models.Index(fields=["user", "meme_uuid"]), # Used in api_views.join_votes_with_data and views.like (PUT request)
        ]

    def __str__(self):
        return f"{self.user.username} meme {self.meme_id} {'' if self.point == 1 else 'dis'}like"


class CommentLike(Like):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=False, blank=False, related_name="comment_likes")
    comment_uuid = models.CharField(max_length=11, blank=False)

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "comment"], name="unique_comment_vote")]
        indexes = [
            models.Index(fields=["user", "comment_uuid"]), # Used in api_views.join_votes_with_data and views.like (PUT request)
        ]

    def __str__(self):
        return f"{self.user.username} comment {self.comment_id} {'' if self.point == 1 else 'dis'}like"

