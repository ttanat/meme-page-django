from django.db.models import Q, F
from django.contrib.auth import authenticate
from django.utils import timezone

from .models import Meme, Comment, User, Page
from notifications.models import Notification

from rest_framework import serializers

import os


class MemeSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Meme
        fields = ("username", "uuid", "caption", "url", "points", "num_comments")

    def get_url(self, obj):
        return obj.get_file_url()

    def to_representation(self, obj):
        representation = super().to_representation(obj)

        """
        Potential extra fields: is_gif, pname, pdname, dp_url, fallback
        """

        # Check if meme is GIF
        if obj.get_original_ext() == ".gif":
            representation["is_gif"] = True

        # Get page name and display name if meme is posted to a page and request is not sent from a page
        if not self.context["request"].query_params.get("p", "").startswith("page/") and obj.page_name:
            representation["pname"] = obj.page_name
            representation["pdname"] = obj.page_display_name or ""

        # Get image of user who posted meme
        try:
            representation["dp_url"] = obj.user_image.url
        except ValueError:
            pass

        # Get fallback URL if browser doesn't accept image/webp
        if ("image/webp" not in self.context["request"].headers.get("Accept", "") and
                os.path.splitext(obj.get_file_url().lower())[1] == ".webp"):
            representation["fallback"] = obj.original.url

        return representation


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
        representation = super().to_representation(obj)

        if not obj.deleted:
            # Get image associated with comment
            try:
                representation["image"] = obj.image.url
            except ValueError:
                pass

            # Get profile image of user who posted comment
            try:
                representation["dp_url"] = obj.user_image.url
            except ValueError:
                pass

        return representation


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
        representation = super().to_representation(obj)

        if not obj.deleted:
            # Get image associated with reply
            try:
                representation["image"] = obj.image.url
            except ValueError:
                pass

            # Get profile image of user who posted reply
            try:
                representation["dp_url"] = obj.user_image.url
            except ValueError:
                pass

        return representation


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
