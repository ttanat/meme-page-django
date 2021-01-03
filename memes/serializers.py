from django.db.models import Q, F
from django.contrib.auth import authenticate
from django.utils import timezone

from .models import Meme, Comment, User, Page
from notifications.models import Notification

from rest_framework import serializers

import os
from datetime import timedelta
from urllib.parse import urlparse


class MemeSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Meme
        fields = ("username", "uuid", "caption", "url", "points", "num_comments")

    def get_url(self, obj):
        # If meme was uploaded less than 15 seconds ago, use original URL (in case it hasn't finished resizing)
        if timezone.now() - timedelta(seconds=15) < obj.upload_date:
            return obj.original.url

        return obj.get_file_url()

    def to_representation(self, obj):
        ret = super().to_representation(obj)

        """
        Potential extra fields: is_gif, pname, pdname, dp_url, fallback
        """

        # Check if meme is GIF
        if obj.get_original_ext() == ".gif":
            ret["is_gif"] = True

        # Get page name and display name if meme is posted to a page and request is not sent from a page
        if not self.context["request"].query_params.get("p", "").startswith("p/") and obj.page_name:
            ret["pname"] = obj.page_name
            ret["pdname"] = obj.page_display_name or ""

        # Get image of user who posted meme
        try:
            ret["dp_url"] = obj.user_image.url
        except ValueError:
            pass

        # Get fallback URL if browser doesn't accept image/webp
        if ("image/webp" not in self.context["request"].headers.get("Accept", "") and
                os.path.splitext(urlparse(ret["url"]).path)[1].lower() == ".webp"):
            ret["fallback"] = obj.original.url

        return ret


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("uuid", "username", "post_date", "edited", "content", "points", "num_replies")

    def get_username(self, obj):
        return "" if obj.deleted else obj.username

    def get_content(self, obj):
        return "" if obj.deleted else obj.content

    def to_representation(self, obj):
        ret = super().to_representation(obj)

        if not obj.deleted:
            # Get image associated with comment
            try:
                ret["image"] = obj.image.url
            except ValueError:
                pass

            # Get profile image of user who posted comment
            try:
                ret["dp_url"] = obj.user_image.url
            except ValueError:
                pass

        return ret


class ReplySerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("uuid", "username", "post_date", "edited", "content", "points")

    def get_username(self, obj):
        return "" if obj.deleted else obj.username

    def get_content(self, obj):
        return "" if obj.deleted else obj.content

    def to_representation(self, obj):
        ret = super().to_representation(obj)

        if not obj.deleted:
            # Get image associated with reply
            try:
                ret["image"] = obj.image.url
            except ValueError:
                pass

            # Get profile image of user who posted reply
            try:
                ret["dp_url"] = obj.user_image.url
            except ValueError:
                pass

        return ret


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
