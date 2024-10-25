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


def join_votes_with_data(data: list, user_id: int, object_name: str) -> list:
    """
    Get likes/dislikes for memes or comments in data then add to data
    """
    assert object_name in ("meme", "comment")

    # Get meme or comment uuids from data
    uuids = [obj["uuid"] for obj in data]
    # Get votes for those memes/comments for that user
    if object_name == "meme":
        votes = MemeLike.objects.filter(user_id=user_id, meme_uuid__in=uuids).values("meme_uuid", "point")
    else:
        votes = CommentLike.objects.filter(user_id=user_id, comment_uuid__in=uuids).values("comment_uuid", "point")
    # Add "vote" key and point (1 or -1) value to meme/comment in data
    indexes = {uuid: i for i, uuid in enumerate(uuids)}
    for vote in votes:
        i = indexes[vote[f"{object_name}_uuid"]]
        data[i]["vote"] = vote["point"]

    return data


class MemePagination(pagination.PageNumberPagination):
    page_size = 20

    def add_before_query_param(self):
        """ Check if should add "before" query parameter """
        return self.get_next_link() and "before" not in self.request.query_params and "page" not in self.request.query_params

    def get_next_meme_link(self, uuid):
        """
        Add "before" query param to prevent duplicates
        e.g. new memes uploaded before loading next page will cause duplicates
        """
        if self.request.query_params.get("p") and self.add_before_query_param():
            # Get upload or post date of first object
            before = Meme.objects.values_list("upload_date", flat=True).get(uuid=uuid)
            # Add "before" query param to next link
            return f"{self.get_next_link()}&{urlencode({'before': before})}"

        return self.get_next_link()

    def get_paginated_response(self, data):
        if self.request.user.is_authenticated:
            data = join_votes_with_data(data, self.request.user.id, "meme")

        return Response({
            "next": self.get_next_meme_link(data[0]["uuid"]) if data else None,
            "results": data
        })


class MemeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MemeSerializer
    pagination_class = MemePagination

    def get_before(self, memes):
        """ Get memes before certain datetime """
        if "before" in self.request.query_params:
            return memes.filter(upload_date__lte=parse_datetime(self.request.query_params["before"]))

        # Don't get memes uploaded within past minute (allow time for files to get resized)
        return memes.filter(upload_date__lt=timezone.now()-timedelta(minutes=1))

    def get_meme_queryset(self, before=True):
        """ Select correct fields and filter memes before certain datetime """
        memes = Meme.objects.only(
            "username",
            "user_image",
            "page_name",
            "original",
            "large",
            "upload_date",
            "uuid",
            "caption",
            "points",
            "num_comments"
        )

        return self.get_before(memes) if before else memes

    def get_queryset(self):
        memes = self.get_meme_queryset().filter(private=False)

        # if (not self.request.user.is_authenticated or
        #         (self.request.user.is_authenticated and not self.request.user.show_nsfw)):
        #     memes = memes.filter(nsfw=False)

        pathname = self.request.query_params.get("p", "")

        # Don't show memes from private pages
        if pathname != "feed":
            memes = memes.filter(page_private=False)

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

        elif pathname.startswith("browse/"):
            category_name = pathname.partition("browse/")[2]

            if category_name not in Category.Name.values:
                raise NotFound

            return memes.filter(category__name=category_name)

        elif pathname == "search":
            query = self.request.query_params.get("q", "")[:64].strip()
            if query:
                tags = [t.lower() for t in re.findall("#([a-zA-Z][a-zA-Z0-9_]*)", query)]
                if tags:
                    return memes.filter(tags_lower__contains=tags)

                return memes.filter(caption__icontains=query).distinct() # Return search by caption

        raise NotFound


class PageMemeViewSet(MemeViewSet):
    def get_page_name(self):
        pname = self.request.query_params.get("name", "")
        if not re.search("^[a-zA-Z0-9_]{1,32}$", pname):
            raise NotFound

        return pname

    def get_queryset(self):
        page = get_object_or_404(Page.objects.only("id"), name=self.get_page_name(), private=False)

        return self.get_meme_queryset().filter(page=page)


class PrivatePageMemeViewSet(PageMemeViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        page = get_object_or_404(Page.objects.only("admin"), name=self.get_page_name(), private=True)

        if (page.admin_id != self.request.user.id
                and not page.subscribers.filter(id=self.request.user.id).exists()
                    and not page.moderators.filter(id=self.request.user.id).exists()):
            raise PermissionDenied

        return self.get_meme_queryset().filter(page=page)


class CommentPagination(pagination.PageNumberPagination):
    page_size = 20

    def add_before_query_param(self):
        """ Check if should add "before" query parameter """
        return self.get_next_link() and "before" not in self.request.query_params and "page" not in self.request.query_params

    def get_next_comment_link(self, datetime):
        return f"{self.get_next_link()}&{urlencode({'before': datetime})}" \
               if self.add_before_query_param() else self.get_next_link()

    def get_paginated_response(self, data):
        if self.request.user.is_authenticated:
            data = join_votes_with_data(data, self.request.user.id, "comment")

        return Response({
            "next": self.get_next_comment_link(data[0]["post_date"]) if data else None,
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

        comments = Comment.objects.only(
            "uuid",
            "username",
            "user_image",
            "post_date",
            "edited",
            "content",
            "image",
            "points",
            "num_replies"
        ).filter(root__isnull=True, meme_uuid=self.request.query_params["u"])

        return comments.filter(post_date__lte=parse_datetime(self.request.query_params["before"])) \
               if "before" in self.request.query_params else comments


class ReplyPagination(CommentPagination):
    page_size = 10

    def get_paginated_response(self, data):
        if self.request.user.is_authenticated:
            data = join_votes_with_data(data, self.request.user.id, "comment")

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

        return Comment.objects.only(
            "uuid",
            "username",
            "user_image",
            "post_date",
            "edited",
            "content",
            "image",
            "points"
        ).filter(root_id=comment_id).order_by("id")


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
                           .only("username", "image", "profile__bio", "profile__clout") \
                           .order_by("-profile__clout")
    serializer_class = SearchUserSerializer
    pagination_class = SearchListPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["username"]


class SearchPageViewSet(viewsets.ReadOnlyModelViewSet):
    model = Page
    queryset = Page.objects.only("name", "display_name", "image", "description", "num_subscribers") \
                           .order_by("-num_subscribers")
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
