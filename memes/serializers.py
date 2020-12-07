from django.db.models import Q, F
from django.contrib.auth import authenticate
from django.utils import timezone

from .models import Meme, Comment, User, Page
from notifications.models import Notification

from rest_framework import serializers

import os


class MemeSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    dp_url = serializers.SerializerMethodField()

    class Meta:
        model = Meme
        fields = ("username", "uuid", "caption", "url", "points", "num_comments", "dp_url")

    def get_url(self, obj):
        return obj.get_file_url()

    def get_dp_url(self, obj):
        try:
            return obj.user.small_image.url
        except ValueError:
            return ""

    def to_representation(self, obj):
        representation = super().to_representation(obj)

        # Check if meme is GIF
        if obj.get_original_ext() == ".gif":
            representation["is_gif"] = True

        # Get page name and display name if meme is posted to a page and request is not sent from a page
        if not self.context["request"].query_params.get("p", "").startswith("page/") and obj.page_name:
            representation["pname"] = obj.page_name
            representation["pdname"] = obj.page_display_name or ""

        # Get fallback URL if browser doesn't accept image/webp
        if ("image/webp" not in self.context["request"].headers.get("Accept", "") and
                os.path.splitext(obj.get_file_url().lower())[1] == ".webp"):
            representation["fallback"] = obj.original.url

        return representation


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    dp_url = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("uuid", "username", "post_date", "edited", "content", "image", "dp_url", "num_replies")

    def get_username(self, obj):
        return "" if obj.deleted else obj.username

    def get_content(self, obj):
        return "" if obj.deleted else obj.content

    def get_image(self, obj):
        try:
            return "" if obj.deleted else obj.image.url
        except ValueError:
            return ""

    def get_dp_url(self, obj):
        try:
            return "" if obj.deleted else obj.user.small_image.url
        except ValueError:
            return ""


class CommentFullSerializer(CommentSerializer):
    points = serializers.IntegerField()

    class Meta:
        model = Comment
        fields = ("uuid", "username", "post_date", "edited", "content", "image", "points", "dp_url", "num_replies")


class ReplySerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    dp_url = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("uuid", "username", "post_date", "edited", "content", "image", "points", "dp_url")

    def get_username(self, obj):
        return "" if obj.deleted else obj.username

    def get_content(self, obj):
        return "" if obj.deleted else obj.content

    def get_image(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return ""

    def get_dp_url(self, obj):
        try:
            return obj.user.small_image.url
        except ValueError:
            return ""


class SearchUserSerializer(serializers.ModelSerializer):
    dp_url = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    num_memes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("username", "dp_url", "bio", "num_memes")

    def get_dp_url(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return ""

    def get_bio(self, obj):
        return obj.profile.bio

    def get_num_memes(self, obj):
        return obj.profile.num_memes


class SearchPageSerializer(serializers.ModelSerializer):
    dp_url = serializers.SerializerMethodField()
    num_subscribers = serializers.IntegerField()

    class Meta:
        model = Page
        fields = ("name", "display_name", "dp_url", "description", "num_subscribers")

    def get_dp_url(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return ""


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("link", "seen", "message", "timestamp")


class ProfileMemesSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()

    class Meta:
        model = Meme
        fields = ("uuid", "url", "points", "file_ext")

    def get_url(self, obj):
        return obj.get_thumbnail_url()

    def get_file_ext(self, obj):
        return obj.get_original_ext()


class UserMemesSerializer(ProfileMemesSerializer):
    class Meta:
        model = Meme
        fields = ("uuid", "url", "file_ext")


class ProfileCommentsSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    rt = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("content", "uuid", "meme_uuid", "image", "rt")

    def get_image(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return ""

    def get_rt(self, obj):
        return obj.rt or ""
