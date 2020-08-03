from rest_framework import serializers
from .models import Meme, Comment, User, Page, Notification
from django.utils import timezone
from django.db.models import Q, F
from django.contrib.auth import authenticate


class MemeSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    dp_url = serializers.SerializerMethodField()

    class Meta:
        model = Meme
        fields = ("username", "uuid", "caption", "content_type", "url", "points", "num_comments", "dp_url")

    def get_url(self, obj):
        return obj.get_file_url()

    def get_dp_url(self, obj):
        try:
            return obj.user.image.url # change to obj.small_image.url
        except ValueError:
            return ""


class FullMemeSerializer(MemeSerializer):
    pname = serializers.SerializerMethodField()
    pdname = serializers.SerializerMethodField()

    class Meta:
        model = Meme
        fields = ("username", "pname", "pdname", "uuid", "caption", "content_type", "url", "points", "num_comments", "dp_url")

    def get_pname(self, obj):
        return obj.page_name

    def get_pdname(self, obj):
        return obj.page_display_name


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
            return "" if obj.deleted else obj.user.image.url
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
            return obj.user.image.url
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

    class Meta:
        model = Meme
        fields = ("uuid", "url", "points", "content_type")

    def get_url(self, obj):
        return obj.get_thumbnail_url()


class UserMemesSerializer(ProfileMemesSerializer):
    class Meta:
        model = Meme
        fields = ("uuid", "url", "content_type")


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
