from rest_framework import serializers
# from .models import Meme, Comment, Like, User, Page, Notification, Tag
from .models import Meme, Comment, Like, User, Page, Tag
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
            return None


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    dp_url = serializers.SerializerMethodField()
    num_replies = serializers.IntegerField()

    class Meta:
        model = Comment
        fields = ("uuid", "username", "post_date", "edited", "content", "image", "dp_url", "num_replies")

    def get_username(self, obj):
        return "" if obj.deleted else obj.username

    def get_content(self, obj):
        return "" if obj.deleted else obj.content

    def get_image(self, obj):
        try:
            return None if obj.deleted else self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return None

    def get_dp_url(self, obj):
        try:
            return "" if obj.deleted else  self.context["request"].build_absolute_uri(obj.user.image.url)
        except ValueError:
            return None


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
            return None

    def get_dp_url(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.user.image.url)
        except ValueError:
            return None


class SearchUserSerializer(serializers.ModelSerializer):
    dp_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("username", "dp_url", "bio", "num_memes")

    def get_dp_url(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return None


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
            return None


# class NotificationSerializer(serializers.ModelSerializer):
#     # description = serializers.SerializerMethodField()

#     class Meta:
#         model = Notification
#         fields = ("description", "timestamp")

#     # def get_message(self, obj):
#     #     return obj.message if obj.message else f"{obj}"


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
    url = serializers.SerializerMethodField()
    rt = serializers.CharField(default=None)

    class Meta:
        model = Comment
        fields = ("content", "uuid", "m_uuid", "url", "rt")

    def get_url(self, obj):
        try:
            return self.context["request"].build_absolute_uri(obj.image.url)
        except ValueError:
            return None
