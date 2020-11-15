from django.http import HttpResponse, Http404, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F, Q
# from django.views.decorators.cache import cache_page
from django.utils import timezone

from .models import Page, Meme, Comment, MemeLike, CommentLike, Category, Tag, User, Profile
from analytics.signals import meme_viewed_signal, upload_signal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from datetime import timedelta
from random import randint
import re, os


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
            "points",
            "num_comments",
            "num_views"
        ),
        uuid=uuid
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
        "username": meme.username,
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
        meme = get_object_or_404(Meme.objects.only("original", "large"), uuid=uuid)
        # Get original file if large is webp
        if os.path.splitext(meme.large.name)[1].lower() == ".webp":
            url = meme.original.url
        else:
            url = meme.get_file_url()

        return JsonResponse({"url": url})

    elif obj == "c":
        comment = get_object_or_404(Comment.objects.only("image", "meme_uuid"), uuid=uuid)
        if not comment.image:
            return HttpResponseBadRequest()

        return JsonResponse({
            "url": comment.image.url,
            "meme_uuid": comment.meme_uuid
        })

    raise Http404


@api_view(["GET"])
def random(request):
    queryset = Meme.objects.filter(page_private=False)
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

    if not uuid or len(uuid) != 11 or not type_ or vote not in ("l", "d"):
        return HttpResponseBadRequest()

    point = 1 if vote == "l" else -1

    if type_ == "m":
        if request.method == "PUT":
            try:
                # Change like to dislike or vice versa
                obj = MemeLike.objects.only("id").get(user=request.user, meme_uuid=uuid)
                if obj.point != point:
                    obj.point = point
                    obj.save(update_fields=["point"])

                    return HttpResponse()
            except MemeLike.DoesNotExist:
                # Maximum 200 likes/dislikes per hour
                if MemeLike.objects.filter(user=request.user, point=point, liked_on__gt=timezone.now()-timedelta(hours=1)).count() >= 200:
                    return HttpResponseBadRequest(f"Too many {'' if point == 1 else 'dis'}likes")

                # Create a like/dislike
                m = get_object_or_404(Meme.objects.only("id"), uuid=uuid)
                MemeLike.objects.create(user=request.user, meme=m, meme_uuid=uuid, point=point)

                return HttpResponse(status=201)

        elif request.method == "DELETE":
            # Delete a like/dislike
            MemeLike.objects.filter(user=request.user, meme_uuid=uuid).delete()

            return HttpResponse(status=204)

    elif type_ == "c":
        if request.method == "PUT":
            try:
                # Change like to dislike or vice versa
                obj = CommentLike.objects.only("id").get(user=request.user, comment_uuid=uuid)
                if obj.point != point:
                    obj.point = point
                    obj.save(update_fields=["point"])

                    return HttpResponse()
            except CommentLike.DoesNotExist:
                # Maximum 200 likes/dislikes per hour
                if CommentLike.objects.filter(user=request.user, point=point, liked_on__gt=timezone.now()-timedelta(hours=1)).count() >= 200:
                    return HttpResponseBadRequest(f"Too many {'' if point == 1 else 'dis'}likes")

                # Create a like/dislike
                c = get_object_or_404(Comment.objects.only("id"), uuid=uuid)
                CommentLike.objects.create(user=request.user, comment=c, comment_uuid=uuid, point=point)

                return HttpResponse(status=201)

        elif request.method == "DELETE":
            # Delete a like/dislike
            CommentLike.objects.filter(user=request.user, comment_uuid=uuid).delete()

            return HttpResponse(status=204)

    return HttpResponseBadRequest()


@api_view(("POST", "PUT", "DELETE"))
@permission_classes([IsAuthenticated])
def comment(request, action):
    if request.method == "POST" and action == "post":
        """ Post new comments only """
        uuid = request.POST.get("uuid")
        content = request.POST.get("content", "")[:150].strip()
        image = request.FILES.get("image")
        if not uuid or (not content and not image):
            return HttpResponseBadRequest()

        if image and not image.name.endswith((".jpg", ".png", ".jpeg")):
            return HttpResponseBadRequest()

        meme = get_object_or_404(Meme.objects.only("id"), uuid=uuid)

        comment = Comment.objects.create(
            user=request.user,
            username=request.user.username,
            meme=meme,
            meme_uuid=uuid,
            content=content,
            image=image
        )

        return JsonResponse({"uuid": comment.uuid})

    elif request.method == "PUT" and action == "edit":
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

        # Delete image if exists
        if c.image:
            c.image.delete()
        # Set deleted to true
        c.deleted = 1
        c.save(update_fields=["deleted"])

        return HttpResponse(status=204)

    raise Http404


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reply(request):
    """ Reply to comments """
    root_uuid = request.POST.get("root_uuid")
    reply_to_uuid = request.POST.get("reply_to_uuid")
    content = request.POST.get("content", "")[:150].strip()
    image = request.FILES.get("image")

    if not root_uuid or not reply_to_uuid or (not content and not image):
        return HttpResponseBadRequest()

    if image and not image.name.endswith((".jpg", ".png", ".jpeg")):
        return HttpResponseBadRequest()

    root = get_object_or_404(
        Comment.objects.select_related("meme").only("meme__id", "meme_uuid"),
        uuid=root_uuid,
        deleted=False
    )

    reply_to = get_object_or_404(
        Comment.objects.only("id"),
        uuid=reply_to_uuid,
        deleted=False
    )

    new_reply = Comment.objects.create(
        user=request.user,
        username=request.user.username,
        meme=root.meme,
        meme_uuid=root.meme_uuid,
        root=root,
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
    nsfw = request.POST.get("nsfw") == "true"
    content_type = file.content_type if file else None
    category_name = request.POST.get("category")

    if file:
        # Check upload limits (50 per hour and 200 per day)
        past_upload = Meme.objects.filter(user=request.user).aggregate(
            hour=Count("upload_date", filter=Q(upload_date__gt=timezone.now()-timedelta(hours=1))),
            day=Count("upload_date", filter=Q(upload_date__gt=timezone.now()-timedelta(days=1)))
        )
        if past_upload["hour"] >= 50:
            return JsonResponse({"success": False, "message": "Upload limit is 50 per hour"})
        if past_upload["day"] >= 200:
            return JsonResponse({"success": False, "message": "Upload limit is 200 per day"})

        if category_name:
            if category_name not in Category.Name.values:
                return JsonResponse({"success": False, "message": "Category not found"})
            # category = get_object_or_404(Category, name=category_name)
            category = Category.objects.get_or_create(name=category_name)[0]    # Change this before deployment

        # Check content type and file extension is valid
        if (content_type not in Meme.ContentType.values
                or not file.name.lower().endswith((".jpg", ".png", ".jpeg", ".mp4", ".mov", ".gif"))):
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
            content_type=content_type,
            nsfw=nsfw,
            category=category,
            ip_address=ip
        )

        tag_names = re.findall("#([a-zA-Z][a-zA-Z0-9_]*)", request.POST.get("tags"))[:20]
        if tag_names:
            # Remove duplicates
            tag_names = list(dict.fromkeys(tag_names))
            Tag.objects.bulk_create([Tag(name=t) for t in tag_names], ignore_conflicts=True)
            meme.tags.add(*Tag.objects.filter(name__in=tag_names))

            upload_signal.send(sender=meme.__class__, instance=meme, tags=tag_names)

        if request.POST.get("is_profile_page"):
            response = {"success": True, "uuid": meme.uuid}
            if meme.content_type.startswith("video/"):
                response["thumbnail"] = meme.get_thumbnail_url()

            return JsonResponse(response, status=201)
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

        Profile.objects.filter(user=request.user).update(bio=new_bio)

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
                
                # Remove following
                request.user.follows.remove(*request.user.follows.all())    # Using .clear() instead of remove will not send signal

                # Remove subscriptions
                for page in request.user.subscriptions.all():
                    page.subscribers.remove(request.user)
                # Have to do multiple queries like this instead of
                # request.user.subscriptions.remove(*request.user.subscriptions.all()) because of notify_subscribe signal

                # Delete all of user's memes
                request.user.meme_set.all().delete()

                # Get all of user's comments
                comments = request.user.comment_set.all()
                # Decrement number of comments by 1 on memes before deleting comments
                # (only by 1 even if user commented on meme multiple times) (good enough)
                Meme.objects.filter(id__in=comments.values_list("meme_id", flat=True)).update(num_comments=F("num_comments") - 1)
                # Delete all of user's comments
                comments.delete()

                # Delete user
                request.user.delete()
        else:
            return HttpResponseBadRequest("Password incorrect")

    return HttpResponse(status=204)
