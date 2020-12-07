from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.http import QueryDict
from django.utils.dateparse import parse_datetime
# from django.utils import timezone

from .serializers import *
from .models import *

from rest_framework import viewsets, pagination, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotAuthenticated, ParseError, PermissionDenied, NotFound

import re
from urllib.parse import urlencode


def add_before_query_param(self_):
    """ Check if should add "before" query parameter """
    return self_.get_next_link() and "before" not in self_.request.query_params and "page" not in self_.request.query_params


def get_next_meme_link(self_, uuid):
    """
    Add "before" query param to prevent duplicates
    e.g. new memes uploaded before loading next page will cause duplicates
    """
    if self_.request.query_params.get("p") and add_before_query_param(self_):
        # Get upload or post date of first object
        before = Meme.objects.values_list("upload_date", flat=True).get(uuid=uuid)
        # Add "before" query param to next link
        return f"{self_.get_next_link()}&{urlencode({'before': before})}"

    return self_.get_next_link()


class MemePagination(pagination.PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data):
        return Response({
            "next": get_next_meme_link(self, data[0]["uuid"]) if data else None,
            "results": data
        })


class MemeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MemeSerializer
    pagination_class = MemePagination

    def get_queryset(self):
        memes = Meme.objects.defer(
            "thumbnail",
            "upload_date",
            "nsfw",
            "num_reports",
            "num_views",
            "ip_address",
            "hidden",
            "page_id",
            "page_private"
        )

        if (not self.request.user.is_authenticated or
                (self.request.user.is_authenticated and not self.request.user.show_nsfw)):
            memes = memes.filter(nsfw=False)

        pathname = self.request.query_params.get("p", "")

        # Get memes before certain datetime
        if pathname and "before" in self.request.query_params:
            memes = memes.filter(upload_date__lte=parse_datetime(self.request.query_params["before"]))

        # Don't show memes from private pages
        if pathname != "feed":
            memes = memes.exclude(page_private=True)

        if not pathname:
            return memes    # Currently just showing all memes
            # return memes.filter(upload_date__gte=timezone.now()-timedelta(3)).order_by("points")

        elif pathname == "feed":
            # Show memes from followed users and subscribed pages
            # Don't show memes from private pages that user is not subscribed to
            if self.request.user.is_authenticated:
                return memes.filter(Q(user__followers=self.request.user)|Q(page__subscribers=self.request.user)) \
                            .exclude(Q(page_private=True)&~Q(page__subscribers=self.request.user)).distinct()

            raise NotAuthenticated()

        elif pathname == "all":
            return memes

        elif pathname.startswith("page/"):
            pname = pathname.partition("page/")[2]

            if not pname or not re.search("^[a-zA-Z0-9_]+$", pname):
                raise NotFound

            return memes.filter(page_name=pname).defer("page_name", "page_display_name")

        elif pathname.startswith("browse/"):
            category_name = pathname.partition("browse/")[2]

            if category_name not in Category.Name.values:
                raise NotFound

            return memes.filter(category__name=category_name)

        elif pathname == "search":
            query = self.request.query_params.get("q", "")[:64].strip()
            if query:
                tags = re.findall("#([a-zA-Z][a-zA-Z0-9_]*)", query)
                if tags:
                    q = Q()
                    for tag in tags:
                        q |= Q(tags__name__iexact=tag)

                    return memes.filter(q).distinct() # Return search by tags
                else:
                    return memes.filter(caption__icontains=query).distinct() # Return search by caption

        raise NotFound


class PrivateMemeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MemeSerializer
    pagination_class = MemePagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if "n" not in self.request.query_params:
            raise ParseError

        page = get_object_or_404(Page.objects.only("id", "admin_id"), name=self.request.query_params["n"])

        if (not page.subscribers.filter(id=self.request.user.id).exists()
                and page.admin_id != self.request.user.id
                    and not page.moderators.filter(id=self.request.user.id).exists()):
            raise PermissionDenied

        return Meme.objects.filter(page=page)


def get_next_comment_link(self_, datetime):
    return f"{self_.get_next_link()}&{urlencode({'before': datetime})}" \
           if add_before_query_param(self_) else self_.get_next_link()


class CommentPagination(pagination.PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data):
        return Response({
            "next": get_next_comment_link(self, data[0]["post_date"]) if data else None,
            "results": data
        })


class CommentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommentSerializer
    pagination_class = CommentPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id"]
    ordering = ["-id"]

    def get_queryset(self):
        if "u" not in self.request.query_params:
            raise ParseError

        comments = Comment.objects.filter(root__isnull=True, meme_uuid=self.request.query_params["u"])

        return comments.filter(post_date__lte=parse_datetime(self.request.query_params["before"])) \
               if "before" in self.request.query_params else comments


class ReplyPagination(CommentPagination):
    page_size = 10

    def get_paginated_response(self, data):
        return Response({
            "next": self.get_next_link(),
            "results": data
        })


class ReplyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReplySerializer
    pagination_class = ReplyPagination

    def get_queryset(self):
        if "u" not in self.request.query_params:
            raise ParseError

        comment_id = Comment.objects.values_list("id", flat=True).get(uuid=self.request.query_params["u"])

        return Comment.objects.filter(root_id=comment_id).order_by("id")


class SearchListPagination(pagination.PageNumberPagination):
    page_size = 15

    def get_paginated_response(self, data):
        return Response({
            "next": self.get_next_link(),
            "results": data
        })


class SearchUserViewSet(viewsets.ReadOnlyModelViewSet):
    model = User
    queryset = User.objects.select_related("profile") \
                           .only("username", "image", "profile__bio", "profile__num_memes") \
                           .order_by("-profile__num_memes")
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


class NotificationPagination(pagination.PageNumberPagination):
    page_size = 20

    def get_paginated_response(self, data):
        return Response({
            "next": self.get_next_link(),
            "results": data
        })


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    model = Notification
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by("-timestamp")
