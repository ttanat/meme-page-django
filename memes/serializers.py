from rest_framework import serializers
from .models import Meme, Comment, User, Page, Notification
from django.utils import timezone
from django.db.models import Q, F
from django.contrib.auth import authenticate


class MemeSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    pname = serializers.CharField(default=None)
    pdname = serializers.CharField(default=None)
    url = serializers.SerializerMethodField()
    points = serializers.IntegerField()
    num_comments = serializers.IntegerField()
    dp_url = serializers.SerializerMethodField()

    class Meta:
        model = Meme
        fields = ("username", "pname", "pdname", "uuid", "caption", "content_type", "url", "points", "num_comments", "dp_url")

    def get_url(self, obj):
        return self.context["request"].build_absolute_uri(obj.file.url)

    def get_dp_url(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.user.image.url)
        except ValueError:
            return ""


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
            return "" if obj.deleted else self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return ""

    def get_dp_url(self, obj):
        try:
            return "" if obj.deleted else self.context["request"].build_absolute_uri(obj.user.image.url)
        except ValueError:
            return ""


class CommentFullSerializer(CommentSerializer):
    points = serializers.IntegerField()

    class Meta:
        model = Comment
        fields = ("uuid", "username", "post_date", "edited", "content", "image", "points", "dp_url", "num_replies")


class ReplySerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    content = serializers.SerializerMethodField()
    points = serializers.IntegerField()
    dp_url = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("uuid", "username", "post_date", "edited", "content", "image", "points", "dp_url")

    def get_content(self, obj):
        return "" if obj.deleted else obj.content

    def get_image(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return ""

    def get_dp_url(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.user.image.url)
        except ValueError:
            return ""


class SearchUserSerializer(serializers.ModelSerializer):
    dp_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("username", "dp_url", "bio", "num_memes")

    def get_dp_url(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return ""


class SearchPageSerializer(serializers.ModelSerializer):
    dp_url = serializers.SerializerMethodField()
    num_subscribers = serializers.IntegerField()

    class Meta:
        model = Page
        fields = ("name", "display_name", "dp_url", "description", "num_subscribers")

    def get_dp_url(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return ""


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("link", "seen", "message", "timestamp")


class ProfileMemesSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Meme
        fields = ("uuid", "url", "points", "content_type")

    def get_url(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.thumbnail.url)
        except ValueError:
            return self.context["request"].build_absolute_uri(obj.file.url)


class UserMemesSerializer(ProfileMemesSerializer):
    class Meta:
        model = Meme
        fields = ("uuid", "url", "content_type")


class ProfileCommentsSerializer(serializers.ModelSerializer):
    m_uuid = serializers.CharField()
    image = serializers.SerializerMethodField()
    rt = serializers.CharField(default=None)

    class Meta:
        model = Comment
        fields = ("content", "uuid", "m_uuid", "image", "rt")

    def get_image(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return ""


class ProfileFollowersSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("username", "image")

    def get_image(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return ""
