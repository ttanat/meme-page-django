from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import F, Q

from memes.serializers import ProfileMemesSerializer, UserMemesSerializer, ProfileCommentsSerializer
from memes.models import User, Page, Meme, Comment

from rest_framework import viewsets, pagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.exceptions import ParseError


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """ Get info for profile page """

    return Response({
        "bio": request.user.bio,
        "clout": request.user.clout,
        "num_followers": request.user.num_followers,
        "num_following": request.user.num_following
    })


@api_view(["GET"])
def user_page(request, username):
    """ Get info for /user/username page """
    user = get_object_or_404(
        User.objects.only("image", "bio", "clout", "num_followers", "num_following"),
        username__iexact=username
    )

    return Response({
        "image": request.build_absolute_uri(user.image.url) if user.image else None,
        "is_following": request.user.follows.filter(pk=user.pk).exists() if request.user.is_authenticated else False,
        "bio": user.bio,
        "clout": user.clout,
        "num_followers": user.num_followers,
        "num_following": user.num_following,
        "moderating": Page.objects.filter(Q(admin=user)|Q(moderators=user)).annotate(dname=F("display_name")).values("name", "dname", "private")
    })


class ProfileMemesPagination(pagination.PageNumberPagination):
    page_size = 15

    def get_paginated_response(self, data):
        return Response({
            "next": self.get_next_link(),
            "results": data
        })


class ProfileMemesViewSet(viewsets.ReadOnlyModelViewSet):
    """ Get memes on profile page """
    model = Meme
    serializer_class = ProfileMemesSerializer
    pagination_class = ProfileMemesPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Meme.objects.filter(user=self.request.user)


class UserMemesViewSet(ProfileMemesViewSet):
    """ Get memes on /user/username page """
    serializer_class = UserMemesSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if "u" not in self.request.GET:
            raise ParseError

        return Meme.objects.filter(username=self.request.GET["u"], hidden=False, page_private=False).order_by("-id")

        """
        Intentionally leave out memes on private pages that both users are subscribed to because query is too complicated

        return Meme.objects.filter(username=self.request.GET["u"], hidden=False) \
                           .filter(Q(page_private=False)|Q(page__subscribers=self.request.user.id)).order_by("-id")
        """


class ProfileLikesViewSet(ProfileMemesViewSet):
    serializer_class = UserMemesSerializer

    def get_queryset(self):
        return Meme.objects.filter(likes__user=self.request.user, likes__point=1).order_by("-likes__id")


class ProfileCommentsViewSet(viewsets.ReadOnlyModelViewSet):
    model = Comment
    serializer_class = ProfileCommentsSerializer
    pagination_class = ProfileMemesPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.annotate(
            rt=F("reply_to__username")
        ).filter(user=self.request.user, deleted=False).order_by("-id")


@api_view(["GET"])
def follow(request, username):
    user = request.user
    if user.username == username:
        return HttpResponseBadRequest()

    user_to_follow = get_object_or_404(User.objects.only("id"), username=username)
    is_following = user.follows.filter(id=user_to_follow.id).exists()

    if is_following:
        user.follows.remove(user_to_follow)    # Unfollow
    else:
        user.follows.add(user_to_follow)    # Follow

    return JsonResponse({"following": not is_following})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_followers(request):
    followers = request.user.followers.only("username", "image").order_by("username")

    if "after" in request.GET:
        followers = followers.filter(username__gt=request.GET["after"])

    results = [
        {"username": u.username, "image": request.build_absolute_uri(u.image.url) if u.image else None}
        for u in followers[:25]
    ]

    return Response({
        "next": request.build_absolute_uri(f"?after={results[-1]['username']}") if followers.count() > 25 else None,
        "results": results
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_following(request):
    following = request.user.follows.only("username", "image").order_by("username")

    if "after" in request.GET:
        following = following.filter(username__gt=request.GET["after"])

    results = [
        {"username": u.username, "image": request.build_absolute_uri(u.image.url) if u.image else None}
        for u in following[:25]
    ]

    return Response({
        "next": request.build_absolute_uri(f"?after={results[-1]['username']}") if following.count() > 25 else None,
        "results": results
    })


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def remove_follower(request, username):
    u = get_object_or_404(User.objects.only("id"), username=username)
    # Cannot do request.user.followers.remove(u), causes IntegrityError
    u.follows.remove(request.user)

    return HttpResponse()
