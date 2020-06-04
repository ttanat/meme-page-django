from .serializers import *
from rest_framework import viewsets, pagination, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import *
from .utils import CATEGORIES
from django.db.models import F, Q, Count, Sum
# from django.db.models.functions import Coalesce
from django.http import Http404
from django.core.exceptions import PermissionDenied
from re import findall
from django.shortcuts import get_object_or_404
# from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.exceptions import NotAuthenticated


class MemePagination(pagination.PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data):
        return Response({
            "next": self.get_next_link(),
            "results": data
        })


class MemeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MemeSerializer
    pagination_class = MemePagination

    def get_queryset(self):
        memes = Meme.objects.annotate(username=F("user__username")).filter(hidden=False)
        if not self.request.user.is_authenticated or (self.request.user.is_authenticated and not self.request.user.show_nsfw):
            memes = memes.filter(nsfw=False)
        pathname = self.request.query_params.get("p")

        # Don't show page name in container header if user is in a meme page
        if pathname[:5] != "page/":
            memes = memes.annotate(pname=F("page__name"), pdname=F("page__display_name"))
        # Don't show memes from private pages
        if pathname != "feed":
            memes = memes.exclude(page__private=True)

        if not pathname:
            return memes    # Currently just showing all memes
            # return memes.filter(uploaded__gte=timezone.now()-timedelta(3)).order_by("points")
        elif pathname == "feed":
            # Show memes from followed users and subscribed pages
            # Don't show memes from private pages that user is not subscribed to
            if self.request.user.is_authenticated:
                return memes.filter(Q(user__followers=self.request.user)|Q(page__subscribers=self.request.user)) \
                            .exclude(Q(page__private=True)&~Q(page__subscribers=self.request.user))
            raise NotAuthenticated()
        elif pathname == "all":
            return memes
        elif pathname[:5] == "page/":
            return memes.filter(page__name=pathname[5:])
        elif pathname[:7] == "browse/":
            if pathname[7:] not in CATEGORIES:
                raise Http404
            return memes.filter(category__name=pathname[7:])
        elif pathname == "search":
            query = self.request.query_params.get("q", "")[:64].strip()
            if query:
                tags = findall("#([a-zA-Z][a-zA-Z0-9_]*)", query)
                if tags:
                    q = Q()
                    for tag in tags:
                        q |= Q(tags__name__iexact=tag)

                    return memes.filter(q).distinct()[:15] # Return search by tags
                else:
                    return memes.filter(caption__icontains=query).distinct()[:15] # Return search by caption

        raise Http404


class PrivateMemeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MemeSerializer
    pagination_class = MemePagination

    def get_queryset(self):
        name = self.request.query_params.get("n")
        page = get_object_or_404(Page, name=name)
        if not page.subscribers.filter(pk=self.request.user.pk).exists() and page.admin != self.request.user:
            raise PermissionDenied
        return Meme.objects.annotate(username=F("user__username")).filter(page=page, hidden=False)


class CommentPagination(pagination.PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data):
        return Response({
            "next": self.get_next_link(),
            "results": data
        })


class CommentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommentSerializer
    pagination_class = CommentPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id"]
    ordering = ["-id"]

    def get_queryset(self):
        uuid = self.request.query_params.get("u")
        return Comment.objects.annotate(username=F("user__username"), num_replies=Count("replies", distinct=True)) \
                              .filter(reply_to__isnull=True, meme__uuid=uuid)


class CommentFullViewSet(CommentViewSet):
    serializer_class = CommentFullSerializer
    ordering_fields = ["id", "points"]

    def get_queryset(self):
        uuid = self.request.query_params.get("u")
        return Comment.objects.annotate(username=F("user__username"), num_replies=Count("replies", distinct=True)) \
                              .filter(reply_to__isnull=True, meme__uuid=uuid)


class ReplyPagination(CommentPagination):
    page_size = 10


class ReplyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReplySerializer
    pagination_class = ReplyPagination
    # ordering_fields = ["id"]
    # ordering = ["id"]

    def get_queryset(self):
        uuid = self.request.query_params["u"]
        return Comment.objects.annotate(username=F("user__username")).filter(reply_to__uuid=uuid).order_by("id")


class SearchListPagination(pagination.PageNumberPagination):
    page_size = 15

    def get_paginated_response(self, data):
        return Response({
            "next": self.get_next_link(),
            "results": data
        })


class SearchUserViewSet(viewsets.ReadOnlyModelViewSet):
    model = User
    queryset = User.objects.order_by("-num_memes")
    serializer_class = SearchUserSerializer
    pagination_class = SearchListPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["username"]


class SearchPageViewSet(viewsets.ReadOnlyModelViewSet):
    model = Page
    queryset = Page.objects.order_by("-num_subscribers").distinct()
    serializer_class = SearchPageSerializer
    pagination_class = SearchListPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "display_name"]


# class NotificationPagination(pagination.PageNumberPagination):
#     page_size = 20

#     def get_paginated_response(self, data):
#         return Response({
#             "count": self.page.paginator.count,
#             "results": data
#         })


# class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
#     # model = Notification
#     serializer_class = NotificationSerializer
#     pagination_class = NotificationPagination
#     # permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         return Notification.objects.filter(user=self.request.user).order_by("-id")
