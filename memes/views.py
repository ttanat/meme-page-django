from django.http import HttpResponse, Http404, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F, Q
# from django.views.decorators.cache import cache_page

from .models import Page, Meme, Comment, MemeLike, CommentLike, Category, Tag, User
from analytics.signals import meme_viewed_signal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from datetime import timedelta
from random import randint
import re


@api_view(["GET"])
def meme_view(request, uuid):
    """ Page for individual meme with comments """

    meme = get_object_or_404(
        Meme.objects.select_related("user").only(
            "username",
            "user__image",
            "page_id",
            "page_name",
            "page_display_name",
            "page_private",
            "uuid",
            "caption",
            "content_type",
            "large",
            "medium",
            "points",
            "num_comments",
            "num_views"
        ),
        uuid=uuid,
        hidden=False
    )

    # Only show memes from private pages to admin, moderators, and subscribers
    if meme.page_private:
        # Check user is logged in and one of (subscriber, admin, moderator) <= in that order
        if not (request.user.is_authenticated and
                (request.user.subscriptions.filter(id=meme.page_id).exists() or
                    Page.objects.values_list("admin_id", flat=True).get(id=meme.page_id) == request.user.id or
                        request.user.moderating.filter(id=meme.page_id).exists())):
            return HttpResponse(status=403)

    meme_viewed_signal.send(sender=meme.__class__, user=request.user, meme=meme)

    return Response({
        "username": meme.user.username,
        "pname": meme.page_name,
        "pdname": meme.page_display_name,
        "uuid": meme.uuid,
        "caption": meme.caption,
        "content_type": meme.content_type,
        "url": meme.get_file_url(),
        "points": meme.points,
        "num_comments": meme.num_comments,
        "dp_url": meme.user.image.url if meme.user.image else None,
        "tags": meme.tags.values_list("name", flat=True)
    })


@api_view(["GET"])
def full_res(request, obj, uuid):
    if obj == "m":
        meme = get_object_or_404(Meme.objects.only("large", "medium"), uuid=uuid, hidden=False)
        return JsonResponse({
            "url": meme.get_file_url()
        })
    elif obj == "c":
        comment = get_object_or_404(Comment.objects.select_related("meme").only("image", "meme_uuid"), uuid=uuid)
        return JsonResponse({
            "url": comment.image.url,
            "meme_uuid": comment.meme_uuid
        })

    raise Http404


@api_view(["GET"])
def random(request):
    queryset = Meme.objects.filter(hidden=False, page_private=False)
    n = randint(0, queryset.count() - 1)
    response = queryset.values("uuid")[n]

    return JsonResponse(response)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_likes(request, obj):
    uuids = request.query_params.getlist("u")[:20]
    if not uuids:
        return JsonResponse([], safe=False)

    if obj == "m":
        return Response(MemeLike.objects.filter(user=request.user, meme_uuid__in=uuids).annotate(uuid=F("meme_uuid")).values("uuid", "point"))
    elif obj == "c":
        return Response(CommentLike.objects.filter(user=request.user, comment_uuid__in=uuids).annotate(uuid=F("comment_uuid")).values("uuid", "point"))

    raise Http404


@api_view(("PUT", "DELETE"))
@permission_classes([IsAuthenticated])
def like(request):
    uuid = request.GET.get("u")
    type_ = request.GET.get("t")
    vote = request.GET.get("v")

    if not uuid or not type_ or vote not in ("l", "d"):
        return HttpResponseBadRequest()

    point = 1 if vote == "l" else -1

    if type_ == "m":
        if request.method == "PUT":
            meme = get_object_or_404(Meme.objects.only("id"), uuid=uuid)
            try:
                obj = MemeLike.objects.only("meme_id").get(user=request.user, meme=meme, meme_uuid=uuid)
                if obj.point != point:
                    obj.point = point
                    obj.save(update_fields=["point"])

                    return HttpResponse()
            except MemeLike.DoesNotExist:
                MemeLike.objects.create(user=request.user, meme=meme, meme_uuid=uuid, point=point)

                return HttpResponse(status=201)

        elif request.method == "DELETE":
            MemeLike.objects.filter(user=request.user, meme_uuid=uuid).delete()

            return HttpResponse(status=204)

    elif type_ == "c":
        if request.method == "PUT":
            comment = get_object_or_404(Comment.objects.only("id"), uuid=uuid)
            try:
                obj = CommentLike.objects.only("comment_id").get(user=request.user, comment=comment, comment_uuid=uuid)
                if obj.point != point:
                    obj.point = point
                    obj.save(update_fields=["point"])

                    return HttpResponse()
            except CommentLike.DoesNotExist:
                CommentLike.objects.create(user=request.user, comment=comment, comment_uuid=uuid, point=point)

                return HttpResponse(status=201)

        elif request.method == "DELETE":
            CommentLike.objects.filter(user=request.user, comment_uuid=uuid).delete()

            return HttpResponse(status=204)

    return HttpResponseBadRequest()


@api_view(("POST", "DELETE"))
@permission_classes([IsAuthenticated])
def comment(request, action):
    if request.method == "POST" and action == "post":
        """ Post new comments only """
        uuid = request.POST.get("uuid")
        content = request.POST.get("content", "")[:150].strip()
        image = request.FILES.get("image")
        if not uuid or (not content and not image):
            return HttpResponseBadRequest()

        meme = get_object_or_404(Meme, uuid=uuid)

        comment = Comment.objects.create(
            user=request.user,
            username=request.user.username,
            meme=meme,
            meme_uuid=uuid,
            content=content,
            image=image
        )

        return JsonResponse({"uuid": comment.uuid})

    elif request.method == "POST" and action == "edit":
        """ Edit comments and replies """
        uuid = request.POST.get("uuid")
        content = request.POST.get("content", "")[:150].strip()
        if not content or not uuid:
            return HttpResponseBadRequest()

        Comment.objects.filter(user=request.user, uuid=uuid, deleted=0).update(content=content, edited=True)

        return HttpResponse()

    elif request.method == "DELETE" and action == "delete":
        """ Delete comments and replies """
        if "u" not in request.GET:
            return HttpResponseBadRequest()

        c = get_object_or_404(Comment.objects.only("image"), user=request.user, uuid=request.GET["u"], deleted=0)

        # Delete image if exists and set deleted to true
        if c.image:
            c.image.delete()
        c.deleted = 1

        c.save(update_fields=["deleted"])

        return HttpResponse(status=204)

    raise Http404


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reply(request):
    """ Reply to comments """
    c_uuid = request.POST.get("c_uuid")
    content = request.POST.get("content", "")[:150].strip()
    image = request.FILES.get("image")
    if not c_uuid or (not content and not image):
        return HttpResponseBadRequest()

    reply_to = get_object_or_404(Comment.objects.select_related("meme"), uuid=c_uuid, deleted=False)

    new_reply = Comment.objects.create(
        user=request.user,
        username=request.user.username,
        meme=reply_to.meme,
        meme_uuid=reply_to.meme.uuid,
        reply_to=reply_to,
        reply_to_uuid=c_uuid,
        content=content,
        image=image
    )

    return JsonResponse({"uuid": new_reply.uuid})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload(request):
    page = category = None
    page_name = request.POST.get("page")
    file = request.FILES.get("file")
    caption = request.POST.get("caption", "")[:100]
    c_embedded = request.POST.get("embed_caption") == "true"
    nsfw = request.POST.get("nsfw") == "true"
    content_type = file.content_type if file else None
    category_name = request.POST.get("category")

    if file:
        if category_name:
            if category_name not in Category.Name.values:
                return JsonResponse({"success": False, "message": "Category not found"})
            # category = get_object_or_404(Category, name=category_name)
            category = Category.objects.get_or_create(name=category_name)[0]    # Change this before deployment

        if (content_type not in Meme.ContentType.values
                or (content_type == "video/quicktime" and not file.name.endswith(".mov"))):
            return JsonResponse({"success": False, "message": "Unsupported file type"})

        if page_name:
            page = get_object_or_404(Page.objects.only("admin_id", "private", "permissions"), name=page_name)
            # User must be admin or subscriber or moderator to post to page
            if not (page.admin_id == request.user.id
                        or (page.permissions and page.subscribers.filter(id=request.user.id).exists())
                            or page.moderators.filter(id=request.user.id).exists()):
                return JsonResponse({"success": False, "message": "Cannot post to this page"})

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

        meme = Meme.objects.create(
            user=request.user,
            username=request.user.username,
            page=page,
            page_private=page.private if page else False,
            page_name=page.name if page else "",
            page_display_name=page.display_name if page else "",
            original=file,
            caption=caption,
            caption_embedded=c_embedded,
            content_type=content_type,
            nsfw=nsfw,
            category=category,
            ip_address=ip
        )

        tag_names = re.findall("#([a-zA-Z][a-zA-Z0-9_]*)", request.POST.get("tags"))[:20]
        if tag_names:
            Tag.objects.bulk_create([Tag(name=t) for t in tag_names], ignore_conflicts=True)
            meme.tags.add(*Tag.objects.filter(name__in=tag_names))

        if request.POST.get("is_profile_page"):
            return JsonResponse({"success": True, "uuid": meme.uuid}, status=201)
        else:
            return JsonResponse({"success": True}, status=201)

    return JsonResponse({"success": False, "message": "Error: No file uploaded"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update(request, field):
    """ Update bio for user or description for page """
    if field == "bio":
        if "new_val" not in request.POST:
            return HttpResponseBadRequest()

        new_bio = request.POST["new_val"][:150].strip()

        if request.user.bio != new_bio:
            request.user.bio = new_bio
            request.user.save(update_fields=["bio"])

        return JsonResponse({"new_val": new_bio})

    elif field == "description":
        if "name" not in request.POST or "new_val" not in request.POST:
            return HttpResponseBadRequest()

        new_description = request.POST["new_val"][:150].strip()
        page = get_object_or_404(Page.objects.only("admin_id", "description"), name=request.POST["name"])

        if request.user.id == page.admin_id and page.description != new_description:
            page.description = new_description
            page.save(update_fields=["description"])

            return JsonResponse({"new_val": new_description})

    return HttpResponseBadRequest()


@api_view(["DELETE", "POST"])
def delete(request, model, identifier=None):
    # Use get instead of filter so that files are deleted too
    if model == "meme":
        Meme.objects.get(user=request.user, uuid=identifier).delete()
    else:
        password = request.POST.get("password")
        if password and request.user.check_password(password):
            if model == "page":
                Page.objects.get(admin=request.user, name=identifier).delete()
            elif model == "user":
                request.user.delete()
        else:
            return HttpResponseBadRequest("Password incorrect")

    return HttpResponse(status=204)
