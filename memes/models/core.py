from django.db import models
from django.db.models import Q, CheckConstraint, UniqueConstraint
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
# from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _

from secrets import token_urlsafe
from PIL import Image
from io import BytesIO
import os, ffmpeg, boto3, json


client = boto3.client('lambda', region_name=settings.AWS_S3_REGION_NAME)


def set_uuid():
    return token_urlsafe(8)


# Gets random string from set_uuid() then add extension from current filename
def set_random_filename(current):
    return f"{set_uuid()}{os.path.splitext(current)[1]}"


def user_directory_path_profile(instance, filename):
    return f"users/{instance.username}/profile/{set_random_filename(filename)}"


class User(AbstractUser):
    num_memes = models.PositiveIntegerField(default=0)
    clout = models.IntegerField(default=0)
    bio = models.CharField(max_length=64, blank=True)
    follows = models.ManyToManyField(settings.AUTH_USER_MODEL, symmetrical=False, related_name="followers")
    num_followers = models.PositiveIntegerField(default=0)
    num_following = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to=user_directory_path_profile, null=True, blank=True)
    nsfw = models.BooleanField(default=False)
    show_nsfw = models.BooleanField(default=False)
    num_views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.username}"

    def resize_image(self):
        client.invoke(
            FunctionName="resize_profile_pic",
            InvocationType="Event",
            Payload=json.dumps({"name": self.image.name}),
            Qualifier="$LATEST"
        )

    def delete(self, *args, **kwargs):
        self.image.delete()
        super().delete(*args, **kwargs)


class Following(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    date_followed = models.DateTimeField(auto_now_add=True)


def original_meme_path(instance, filename):
    return f"users/{instance.user.username}/memes/original/{set_random_filename(filename)}"


class Meme(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    username = models.CharField(max_length=32, blank=False)
    page = models.ForeignKey("Page", on_delete=models.SET_NULL, null=True, blank=True)
    private_page = models.BooleanField()

    # Store original file
    original = models.FileField(upload_to=original_meme_path, null=False, blank=False)

    # Full size (960x960) for desktop (WEBP/MP4)
    large = models.FileField(null=True, blank=True)
    # Medium size (640x640) for mobile (WEBP/MP4)
    medium = models.FileField(null=True, blank=True)

    # Thumbnail (480x480) for profile and video and gif memes (WEBP)
    thumbnail = models.ImageField(null=True, blank=True)
    # Small thumbnail (320x320) for mobile thumbnails (WEBP)
    small_thumbnail = models.ImageField(null=True, blank=True)

    class ContentType(models.TextChoices):
        JPEG = "image/jpeg", _("JPEG")
        PNG = "image/png", _("PNG")
        GIF = "image/gif", _("GIF")
        MP4 = "video/mp4", _("MP4")
        MOV = "video/quicktime", _("MOV")

    content_type = models.CharField(max_length=15, blank=False, choices=ContentType.choices)

    uuid = models.CharField(max_length=11, default=set_uuid, unique=True)
    dank = models.BooleanField(default=False)
    caption = models.CharField(max_length=100, blank=True)
    caption_embedded = models.BooleanField(default=False)
    upload_date = models.DateTimeField(auto_now_add=True)
    points = models.IntegerField(default=0)
    num_comments = models.PositiveIntegerField(default=0)
    nsfw = models.BooleanField(default=False)
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField("Tag", related_name="memes")
    # tags_list = ArrayField(models.CharField(max_length=64, blank=False), blank=True)

    num_views = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True)
    hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.id}"

    def invoke_resize_function(self, func_name: str) -> list:
        """
        func_name: name of AWS lambda function

        Invoke resize function for image/gif/video then return response payload
        """
        response = client.invoke(
            FunctionName=func_name,
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "file_key": self.original.name,
                "path": f"users/{self.username}/memes"
            }),
            Qualifier="$LATEST"
        )

        return json.loads(response["Payload"].read())

    def resize_file(self):
        if self.content_type in ("image/jpeg", "image/png"):
            payload = self.invoke_resize_function("resize_meme")

            for obj in payload:
                getattr(self, obj["size"]).name = f"users/{self.username}/memes/{obj['size']}/{obj['fname']}.webp"
        else:
            payload = self.invoke_resize_function("resize_video_meme")

            for obj in payload:
                getattr(self, obj["size"]).name = f"users/{self.username}/memes/{obj['size']}/{obj['fname']}.{obj['ext']}"

        self.save(update_fields=("large", "medium", "thumbnail", "small_thumbnail"))

    # def resize_video(self):
    #     old_path = self.file.path
    #     path_to_dir = os.path.split(old_path)[0]
    #     new_path = os.path.join(path_to_dir, f"{set_uuid()}.mp4")

    #     self.file.name = f"{os.path.split(self.file.name)[0]}/{new_fname}"

    #     file = ffmpeg.input(old_path)
    #     if self.content_type == "image/gif":
    #         file.output(new_path, movflags="faststart", video_bitrate="0", crf="25", format="mp4", vcodec="libx264", pix_fmt="yuv420p", vf="scale=trunc(iw/2)*2:trunc(ih/2)*2")
    #     elif self.content_type[:6] == "video/" and self.file.size > 102400:    # Resize if video is more than 100 kb
    #         file.output(new_path, movflags="faststart", vcodec="libx264", crf="33", format="mp4", pix_fmt="yuv420p")
    #     file.run()

    #     if self.content_type == "video/quicktime":
    #         self.content_type = "video/mp4"
    #         self.save(update_fields=("file", "content_type"))
    #     else:
    #         self.save(update_fields=["file"])

    #     os.remove(old_path)

    def delete(self, *args, **kwargs):
        self.original.delete()
        self.large.delete()
        self.medium.delete()
        self.thumbnail.delete()
        self.small_thumbnail.delete()
        super().delete(*args, **kwargs)


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
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=False, blank=False, related_name="comments")
    reply_to = models.ForeignKey("Comment", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.CharField(max_length=150, blank=True)
    mention = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="mention")
    uuid = models.CharField(max_length=11, default=set_uuid, unique=True)
    points = models.IntegerField(default=0)
    num_replies = models.PositiveIntegerField(default=0)
    post_date = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to=user_directory_path_comments, null=True, blank=True)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [CheckConstraint(check=~Q(content="", image=None, deleted=False), name="content_image_both_not_empty")]

    def __str__(self):
        return f"{self.user.username}: {self.content}"

    def resize_image(self):
        img = Image.open(self.image.path)
        n = 400 if self.reply_to else 480
        if img.height > n or img.width > n:
            img.thumbnail((n, n))
            img.save(self.image.path)

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete()
        super().delete(*args, **kwargs)


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    point = models.IntegerField()
    liked_on = models.DateTimeField(auto_now=True)
    # UUID of meme or comment
    uuid = models.CharField(max_length=11, blank=False)

    class Meta:
        abstract = True
        constraints = [CheckConstraint(check=Q(point=1)|Q(point=-1), name="single_point_vote")]


class MemeLike(Like):
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=False, blank=False, related_name="likes")

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "meme"], name="unique_meme_vote")]

    def __str__(self):
        return f"{self.user.username} meme {self.meme_id} {'' if self.point == 1 else 'dis'}like"


class CommentLike(Like):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=False, blank=False, related_name="comment_likes")

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "comment"], name="unique_comment_vote")]

    def __str__(self):
        return f"{self.user.username} comment {self.comment_id} {'' if self.point == 1 else 'dis'}like"


# class Report(models.Model):
#     reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     meme = models.ForeignKey(Meme, on_delete=models.SET_NULL, null=True)
#     comment = models.ForeignKey(Comment, on_delete=models.SET_NULL, null=True)
#     page = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True)
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reported_user")
#     reason = models.CharField(max_length=64, blank=False)
#     message = models.CharField(max_length=500, blank=True)
