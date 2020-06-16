from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from secrets import token_urlsafe
# from .utils import CATEGORIES
from PIL import Image
from io import BytesIO
import os, ffmpeg
# from django.core.files import File
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator


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
    private = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username}"

    def resize_img(self):
        img = Image.open(self.image.path)
        if img.height > 200 or img.width > 200:
            img.thumbnail((200, 200))
            img.save(self.image.path)

    def delete(self, *args, **kwargs):
        self.image.delete()
        super().delete(*args, **kwargs)


def user_directory_path(instance, filename):
    return f"users/{instance.user.username}/memes/{set_random_filename(filename)}"


def user_directory_path_thumbnails(instance, filename):
    return f"users/{instance.user.username}/memes/thumbnails/{set_random_filename(filename)}"


def user_directory_path_small_thumbnails(instance, filename):
    return f"users/{instance.user.username}/memes/small_thumbnails/{set_random_filename(filename)}"


class Meme(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey("Page", on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to=user_directory_path, null=False, blank=False)
    uuid = models.CharField(max_length=11, default=set_uuid, unique=True)
    thumbnail = models.FileField(upload_to=user_directory_path_thumbnails, null=True, blank=True)
    small_thumbnail = models.FileField(upload_to=user_directory_path_small_thumbnails, null=True, blank=True)
    dank = models.BooleanField(default=False)
    caption = models.CharField(max_length=100, blank=True)
    caption_embedded = models.BooleanField(default=False)
    content_type = models.CharField(max_length=64, blank=False)
    upload_date = models.DateTimeField(auto_now=False, default=timezone.now)
    points = models.IntegerField(default=0)
    num_comments = models.PositiveIntegerField(default=0)
    nsfw = models.BooleanField(default=False)
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True, blank=True)
    # tags = models.ManyToManyField("Tag", related_name="memes")
    # tags_list = models.ArrayField(ArrayField(models.CharField(max_length=64, blank=False), blank=True))
    ip_address = models.GenericIPAddressField(null=True)
    is_seen = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="seen")
    # ^ Replace with views
    hidden = models.BooleanField(default=False)
    # views = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="viewed")
    # num_views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.id}"

    def resize_file(self):
        if self.content_type in ("image/jpeg", "image/png"):
            self.resize_image()
        else:
            # Videos and GIFs get processed here
            self.resize_video()

    def resize_image(self):
        if self.file.size > 51200:
            img = Image.open(self.file.path).convert("RGB")
            icc_profile = img.info.get("icc_profile")
            if img.height > 960 or img.width > 960:
                img.thumbnail((960, 960))

            if self.content_type == "image/jpeg":
                img.save(self.file.path, icc_profile=icc_profile, optimize=True, quality=70, format="JPEG")
            else:
                new_path = f"{os.path.splitext(self.file.path)[0]}.jpg"
                fname = os.path.split(new_path)[1]
                f = BytesIO()
                img.save(f, icc_profile=icc_profile, optimize=True, quality=70, format="JPEG")
                if f.tell() < self.file.size:
                    self.file.delete()
                    self.file.save(fname, ContentFile(f.getvalue()))
                f.close()

            if img.height > 480 or img.width > 480:
                # Create thumbnail
                img.thumbnail((480, 480))
                f = BytesIO()
                img.save(f, icc_profile=icc_profile, optimize=True, quality=70, format="JPEG")
                name, ext = os.path.splitext(os.path.split(self.file.path)[1])
                self.thumbnail.save(f"{name}_t{ext}", ContentFile(f.getvalue()))
                f.close()

                # Create small thumbnail
                f = BytesIO()
                img.thumbnail((240, 240))
                img.save(f, icc_profile=icc_profile, optimize=True, quality=70, format="JPEG")
                self.small_thumbnail.save(f"{name}_st{ext}", ContentFile(f.getvalue()))
                f.close()

            img.close()

    def resize_video(self):
        old_path = self.file.path
        path_to_dir = os.path.split(old_path)[0]
        new_path = os.path.join(path_to_dir, f"{set_uuid()}.mp4")

        self.file.name = f"{os.path.split(self.file.name)[0]}/{new_fname}"

        file = ffmpeg.input(old_path)
        if self.content_type == "image/gif":
            file.output(new_path, movflags="faststart", video_bitrate="0", crf="25", format="mp4", vcodec="libx264", pix_fmt="yuv420p", vf="scale=trunc(iw/2)*2:trunc(ih/2)*2")
        elif self.content_type[:6] == "video/" and self.file.size > 102400:    # Resize if video is more than 100 kb
            file.output(new_path, movflags="faststart", vcodec="libx264", crf="33", format="mp4", pix_fmt="yuv420p")
        file.run()

        if self.content_type == "video/quicktime":
            self.content_type = "video/mp4"
            self.save(update_fields=("file", "content_type"))
        else:
            self.save(update_fields=["file"])

        os.remove(old_path)

    def delete(self, *args, **kwargs):
        self.small_thumbnail.delete()
        self.thumbnail.delete()
        self.file.delete()
        super().delete(*args, **kwargs)


# class View(models.Model):
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     meme = models.ForeignKey(Meme, on_delete=models.CASCADE)
#     viewed_on = models.DateTimeField(auto_now=False, default=timezone.now)


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True, blank=False)
    meme = models.ManyToManyField(Meme, related_name="tags")

    def __str__(self):
        return f"{self.name}"


class Category(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.name}"


def user_directory_path_comments(instance, filename):
    return f"users/{instance.user.username}/comments/{set_random_filename(filename)}"


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL)
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=False, blank=False, related_name="comments")
    reply_to = models.ForeignKey("Comment", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.CharField(max_length=150, blank=True)
    mention = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="mention")
    uuid = models.CharField(max_length=11, default=set_uuid, unique=True)
    points = models.IntegerField(default=0)
    # num_replies = models.PositiveIntegerField(default=0)
    post_date = models.DateTimeField(auto_now=False, default=timezone.now)
    image = models.ImageField(upload_to=user_directory_path_comments, null=True, blank=True)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    class Meta:
        constraints = [models.CheckConstraint(check=~models.Q(content=None, image=None), name="content_image_both_not_null")]

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
    point = models.SmallIntegerField()
    # ^ Change to IntegerField
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=True, blank=True, related_name="likes")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="comment_likes")
    liked_on = models.DateTimeField(auto_now=False, default=timezone.now)

    class Meta:
        # abstract = True
        constraints = [
            models.UniqueConstraint(fields=["user", "meme", "comment"], name="unique_vote"),
            models.CheckConstraint(check=models.Q(point=1)|models.Q(point=-1), name="single_vote") # single_point_vote
        ]

    def __str__(self):
        return f"{self.user.username} {'meme' if self.meme else 'comment'} {'' if self.point == 1 else 'dis'}like"


# class MemeLike(Like):
#     meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=False, blank=False, related_name="likes")

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=["user", "meme"], name="unique_meme_vote"),
#             models.CheckConstraint(check=models.Q(point=1)|models.Q(point=-1), name="single_point_vote")
#         ]

#     def __str__(self):
#         return f"{self.user.username} meme {'' if self.point == 1 else 'dis'}like"


# class CommentLike(Like):
#     comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=False, blank=False, related_name="c_likes")

#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=["user", "comment"], name="unique_comment_vote"),
#             models.CheckConstraint(check=models.Q(point=1)|models.Q(point=-1), name="single_point_vote")
#         ]

#     def __str__(self):
#         return f"{self.user.username} comment {'' if self.point == 1 else 'dis'}like"


def page_directory_path(instance, filename):
    return f"pages/{instance.name}/{set_random_filename(filename)}"


class Page(models.Model):
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    moderators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="moderating")
    # moderators = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="moderating", through="Moderator")
    subscribers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="subscriptions")
    created = models.DateTimeField(auto_now=False, default=timezone.now)
    name = models.CharField(max_length=32, blank=False, unique=True)
    display_name = models.CharField(max_length=32, blank=True)
    image = models.ImageField(upload_to=page_directory_path, null=True, blank=True)
    cover = models.ImageField(upload_to=page_directory_path, null=True, blank=True)
    description = models.CharField(max_length=150, blank=True, default="")
    # description = models.CharField(max_length=200, blank=True, default="")
    # description2 = models.CharField(max_length=300, blank=True, default="")
    nsfw = models.BooleanField(default=False)
    private = models.BooleanField(default=False)
    # True if subscribers can post / False if only admin can post
    permissions = models.BooleanField(default=True)
    # num_mods = models.PositiveSmallIntegerField(default=0)
    num_subscribers = models.PositiveIntegerField(default=0)
    num_posts = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name}"

    # def get_display_name(self):
    #     return f"{self.display_name}" if self.display_name else f"{self.name}"

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


# class Moderator(models.Model):
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     page = models.ForeignKey(Page, on_delete=models.CASCADE)
#     date_joined = models.DateTimeField(auto_now=False, default=timezone.now)


class Notification(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=32, blank=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    link = models.URLField(max_length=64, blank=False)
    seen = models.BooleanField(default=False)
    image = models.URLField(max_length=128, blank=True, default="")
    message = models.CharField(max_length=128, blank=True)
    timestamp = models.DateTimeField(auto_now=False, default=timezone.now)

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
    timestamp = models.DateTimeField(auto_now=False, default=timezone.now)

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
    timestamp = models.DateTimeField(auto_now=False, default=timezone.now)

    def __str__(self):
        return f"Invite link for {self.page}"


class ModeratorInvite(models.Model):
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now=False, default=timezone.now)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.invitee} invited to moderate for {self.page}"


# class Report(models.Model):
#     reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     meme = models.ForeignKey(Meme, on_delete=models.SET_NULL, null=True)
#     comment = models.ForeignKey(Comment, on_delete=models.SET_NULL, null=True)
#     page = models.ForeignKey(Page, on_delete=models.SET_NULL, null=True)
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reported_user")
#     reason = models.CharField(max_length=64, blank=False)
#     message = models.CharField(max_length=500, blank=True)
