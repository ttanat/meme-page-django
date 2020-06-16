from django.http import HttpResponse, Http404, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F, Q
from django.utils import timezone
# from django.views.decorators.cache import cache_page

from .models import Page, Meme, Comment, Like, Category, Tag, User
from .utils import UOC, SFT, CATEGORIES

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
        Meme.objects.select_related("user", "page").only(
            "user__username",
            "page__name",
            "page__display_name",
            "uuid",
            "caption",
            "content_type",
            "file",
            # "thumbnail",
            "points",
            "num_comments",
            "user__image",
            "page__private",
            "page__admin_id",
            # "num_views"
        ),
        uuid=uuid,
        hidden=False
    )
    # page_id automatically selected

    # Only show memes from private pages to admin and subscribers
    if meme.page and meme.page.private:
        if (not request.user.is_authenticated or
                (meme.page.admin_id != request.user.id and not request.user.subscriptions.filter(id=meme.page_id).exists())):
            return HttpResponse(status=403)

    # if request.user.is_authenticated:
    #     meme.views.add(request.user)
    # meme.num_views = F("num_views") + 1
    # meme.save(update_fields=["num_views"])

    return Response({
        "username": meme.user.username,
        "pname": meme.page.name if meme.page else None,
        "pdname": meme.page.display_name if meme.page else None,
        "uuid": meme.uuid,
        "caption": meme.caption,
        "content_type": meme.content_type,
        "url": request.build_absolute_uri(meme.file.url),
        "points": meme.points,
        "num_comments": meme.num_comments,
        "dp_url": request.build_absolute_uri(meme.user.image.url) if meme.user.image else None,
        "tags": meme.tags.values_list("name", flat=True)
    })


@api_view(["GET"])
def full_res(request, obj, uuid):
    if obj == "m":
        meme = get_object_or_404(Meme.objects.only("file", "content_type"), uuid=uuid, hidden=False)
        return JsonResponse({
            "url": request.build_absolute_uri(meme.file.url),
            "isVid": meme.content_type.startswith("video/")
        })
    elif obj == "c":
        comment = get_object_or_404(Comment.objects.select_related("meme").only("image", "meme__uuid"), uuid=uuid)
        return JsonResponse({
            "url": request.build_absolute_uri(comment.image.url),
            "m_uuid": comment.meme.uuid
        })

    raise Http404


@api_view(["GET"])
def random(request):
    queryset = Meme.objects.filter(hidden=False).filter(Q(page=None)|Q(page__private=False))
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
        return Response(Like.objects.filter(user=request.user, meme__uuid__in=uuids).annotate(uuid=F("meme__uuid")).values("uuid", "point"))
    elif obj == "c":
        return Response(Like.objects.filter(user=request.user, comment__uuid__in=uuids).annotate(uuid=F("comment__uuid")).values("uuid", "point"))

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
            meme = get_object_or_404(Meme, uuid=uuid)
            obj, created = Like.objects.update_or_create(user=request.user, meme=meme, defaults={"point": point, "liked_on": timezone.now()})
            return HttpResponse(status=201 if created else 200)
        elif request.method == "DELETE":
            Like.objects.filter(user=request.user, meme__uuid=uuid).delete()
            return HttpResponse(status=204)
    elif type_ == "c":
        if request.method == "PUT":
            comment = get_object_or_404(Comment.objects.prefetch_related("meme"), uuid=uuid)
            obj, created = Like.objects.update_or_create(user=request.user, comment=comment, defaults={"point": point, "liked_on": timezone.now()})
            return HttpResponse(status=201 if created else 200)
        elif request.method == "DELETE":
            Like.objects.filter(user=request.user, comment__uuid=uuid).delete()
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
            meme=meme,
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

        Comment.objects.filter(user=request.user, uuid=uuid, deleted=False).update(content=content, edited=True)

        return HttpResponse()

    elif request.method == "DELETE" and action == "delete":
        """ Delete comments and replies """
        if "u" in request.GET:
            Comment.objects.filter(user=request.user, uuid=request.GET["u"]).update(deleted=True)
            # c = Comment.objects.only("deleted").get(user=request.user, uuid=request.GET.get("u"))
            # c.deleted = True
            # c.save()

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
        meme=reply_to.meme,
        reply_to=reply_to,
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
            if category_name not in CATEGORIES:
                return JsonResponse({"success": False, "message": "Category not found"})
            # category = get_object_or_404(Category, name=category_name)
            category = Category.objects.get_or_create(name=category_name)[0]    # Change this before production

        if content_type not in SFT or (content_type == "video/quicktime" and not file.name.endswith(".mov")):
            return JsonResponse({"success": False, "message": "Unsupported file type"})

        if page_name:
            page = get_object_or_404(Page.objects.only("admin_id", "permissions"), name=page_name)
            if page.admin_id != request.user.id:
                if not page.permissions:
                    return JsonResponse({"success": False, "message": "Only admin of this page can post"})
                if not page.subscribers.filter(id=request.user.id).exists():
                    return JsonResponse({"success": False, "message": "Must be subscribed to post"})

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

        meme = Meme.objects.create(
            user=request.user,
            page=page,
            file=file,
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
