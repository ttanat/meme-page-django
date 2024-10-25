from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F, Q

from memes.serializers import ProfileMemesSerializer, UserMemesSerializer, ProfileCommentsSerializer
from memes.models import User, Page, Meme, Comment, Profile
from analytics.signals import profile_view_signal

from rest_framework import viewsets, pagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.exceptions import ParseError, NotFound


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """ Get info for profile page """
    return Response(Profile.objects.values("bio", "clout", "num_followers", "num_following").get(user=request.user))


@api_view(["GET"])
def user_page(request, username):
    """ Get info for /u/username page """
    try:
        user = User.objects.only("image", "banned", "is_active").get(username=username)
        profile = Profile.objects.only("bio", "clout", "num_followers", "num_following").get(user=user)
    except User.DoesNotExist:
        username = get_object_or_404(User.objects.values_list("username", flat=True), username__iexact=username)
        return JsonResponse({"redirect": True, "username": username})

    profile_view_signal.send(sender=profile.__class__, user=request.user, profile=profile)

    if user.banned:
        return JsonResponse({"banned": True})
    if not user.is_active:
        return JsonResponse({"deleted": True})

    return Response({
        "image": user.image.url if user.image else None,
        "is_following": request.user.follows.filter(pk=user.pk).exists() if request.user.is_authenticated else False,
        "bio": profile.bio,
        "clout": profile.clout,
        "num_followers": profile.num_followers,
        "num_following": profile.num_following,
        "moderating": Page.objects.filter(moderators=user).annotate(dname=F("display_name")).values("name", "dname", "private")
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
        memes = Meme.objects.only("uuid", "thumbnail", "points", "original") \
                           .filter(user=self.request.user, private=False) \
                           .order_by("-id")

        if "offset" in self.request.query_params:
            offset = int(self.request.query_params["offset"])
            assert offset > 0

            return memes[offset:offset+self.pagination_class.page_size]

        return memes


class UserMemesViewSet(ProfileMemesViewSet):
    """ Get memes on /u/username page """
    serializer_class = UserMemesSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if "u" not in self.request.GET:
            raise ParseError

        user = get_object_or_404(User.objects.only("banned", "is_active"), username=self.request.GET["u"])
        if user.banned or not user.is_active:
            raise NotFound

        return Meme.objects.only("uuid", "original", "thumbnail") \
                           .filter(user=user, private=False, page_private=False) \
                           .order_by("-id")

        """
        Intentionally leave out memes on private pages that both users are subscribed to because query is too complicated

        return Meme.objects.filter(user=user) \
                           .filter(Q(page_private=False)|Q(page__subscribers=self.request.user.id)).order_by("-id")
        """


class ProfileLikesViewSet(ProfileMemesViewSet):
    serializer_class = UserMemesSerializer

    def get_queryset(self):
        return Meme.objects.only("uuid", "original", "thumbnail") \
                           .filter(likes__user=self.request.user, likes__point=1) \
                           .order_by("-likes__id")


class ProfilePrivateMemesViewSet(ProfileMemesViewSet):
    serializer_class = UserMemesSerializer

    def get_queryset(self):
        return Meme.objects.only("uuid", "original", "thumbnail") \
                           .filter(user=self.request.user, private=True) \
                           .order_by("-id")


class ProfileCommentsViewSet(viewsets.ReadOnlyModelViewSet):
    model = Comment
    serializer_class = ProfileCommentsSerializer
    pagination_class = ProfileMemesPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.annotate(
            rt=F("reply_to__username")
        ).filter(user=self.request.user, deleted=False).order_by("-id")


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def follow(request, username):
    if request.user.username.lower() == username.lower():
        return HttpResponseBadRequest("Cannot follow yourself. smh")

    user_to_follow = get_object_or_404(User.objects.only("id"), username=username)
    is_following = request.user.follows.filter(id=user_to_follow.id).exists()

    if is_following:
        request.user.follows.remove(user_to_follow)    # Unfollow
    else:
        # Limit number that user can follow
        if Profile.objects.values_list("num_following", flat=True).get(user=request.user) >= 1000:
            return HttpResponseBadRequest("Cannot follow more than 1000 users")

        request.user.follows.add(user_to_follow)    # Follow

    return JsonResponse({"following": not is_following})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_followers(request):
    followers = request.user.followers.only("username", "image").order_by("username")

    if "after" in request.GET:
        followers = followers.filter(username__gt=request.GET["after"])

    results = [
        {"username": u.username, "image": u.image.url if u.image else None}
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
        {"username": u.username, "image": u.image.url if u.image else None}
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
