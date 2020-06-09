from django.http import HttpResponse, Http404, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.db.models import F, Q
from django.utils import timezone
# from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator

from .models import *
from .utils import UOC, SFT, CATEGORIES
from datetime import timedelta
from random import randint
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
import re
from rest_framework_simplejwt.tokens import RefreshToken


@api_view(["GET"])
def user_session(request):
    user = request.user
    if user.is_authenticated:
        return Response({
            "username": user.username,
            "image": request.build_absolute_uri(user.image.url) if user.image else None,
            "moderating": Page.objects.filter(Q(admin=user)|Q(moderators=user)).annotate(dname=F("display_name")).values("name", "dname", "private"),
            "subscriptions": user.subscriptions.annotate(dname=F("display_name")).values("name", "dname", "private")
        })

    return HttpResponse(status=401)


@api_view(["GET"])
def nav_notifications(request):
    notifs = Notification.objects.filter(recipient=request.user, seen=False)
    to_send = notifs[:5]

    # Must force evaluation of queryset before updating
    response = {
        "count": notifs.count(),
        "list": [n for n in to_send.values("link", "image", "message")]
    }

    for n in to_send:
        n.seen = True

    Notification.objects.bulk_update(to_send, ["seen"])

    return Response(response)


@api_view(["GET"])
def notifications(request):
    notifs = Notification.objects.filter(recipient=request.user).order_by("-timestamp")

    p = Paginator(notifs, 20)
    if "page" not in request.GET:
        return HttpResponseBadRequest()
    page_num = request.GET["page"]

    current_page = p.get_page(page_num)
    objs = current_page.object_list
    to_send = [n for n in objs.values("link", "seen", "message", "timestamp")]

    for obj in objs:
        obj.seen = True

    Notification.objects.bulk_update(objs, ["seen"])

    return Response({
        "next": current_page.next_page_number() if current_page.has_next() else None,
        "results": to_send
    })


@api_view(["GET"])
def meme_view(request, uuid):
    """ Page for individual meme with comments """

    meme = get_object_or_404(Meme.objects.select_related("user", "page"), uuid=uuid)

    if meme.page and meme.page.private:
        if (not request.user.is_authenticated or
                (not request.user.subscriptions.filter(id=meme.page_id).exists() and meme.page.admin_id != request.user.id)):
            return HttpResponse(status=403)

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
        meme = get_object_or_404(Meme.objects.only("file", "content_type"), uuid=uuid)
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
def page(request, name):
    page = get_object_or_404(Page.objects.annotate(adm=F("admin__username")), name__iexact=name)

    response = {
        "page": {
            "name": page.name,
            "dname": page.display_name,
            "image": request.build_absolute_uri(page.image.url) if page.image else None,
            "cover": request.build_absolute_uri(page.cover.url) if page.cover else None,
            "description": page.description,
            "private": page.private,
            "permissions": page.permissions,
            "subs": page.num_subscribers,
            "num_posts": page.num_posts,
            "admin": page.adm
        }
    }

    if request.user.is_authenticated:
        response["is_subscribed"] = page.subscribers.filter(id=request.user.id).exists()

    # Prevent loading memes if page is private and user is not subscribed or page admin
    response["show"] = not page.private or response.get("is_subscribed") or page.admin_id == request.user.id

    if response["show"]:
        response["page"]["moderators"] = page.moderators.values_list("username", flat=True)

    return Response(response)


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
def subscribe(request, name):
    page_to_sub = get_object_or_404(Page.objects.only("id", "admin_id", "private"), name=name)
    is_subscribed = page_to_sub.subscribers.filter(id=request.user.id).exists()

    if is_subscribed:
        page_to_sub.subscribers.remove(request.user)    # Unsubscribe
        return JsonResponse({"subscribed": not is_subscribed})
    else:
        if page_to_sub.admin_id != request.user.id:
            # If subscribing to a private page
            if page_to_sub.private:
                # Send a request to subscribe
                obj, created = SubscribeRequest.objects.get_or_create(user=request.user, page=page_to_sub)
                if not created:
                    obj.delete()
            else:
                page_to_sub.subscribers.add(request.user)    # Subscribe

            return JsonResponse({"subscribed": not is_subscribed})

    return HttpResponseBadRequest()


@api_view(["POST"])
def new_page(request):
    name = request.POST.get("name", "")[:32].strip()
    if not name:
        return JsonResponse({"success": False})
    elif any(c not in UOC for c in name):
        return JsonResponse({"success": False, "message": "Letters, numbers, and underscores only"})
    elif Page.objects.filter(name__iexact=name).exists():
        return JsonResponse({"success": False, "taken": True})
    elif Page.objects.filter(admin=request.user).count() > 2:
        return JsonResponse({"success": False, "maximum": True})

    dname = request.POST.get("display_name", "")[:32].strip()
    private = request.POST.get("private") == "true"
    perm = request.POST.get("permissions") != "false"

    Page.objects.create(admin=request.user, name=name, display_name=dname, description="", private=private, permissions=perm)
    # Page.objects.create(admin=request.user, name=name, display_name=dname, private=private, permissions=perm)

    return JsonResponse({"success": True, "name": name})


@api_view(["POST"])
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


def logout_view(request):
    # Blacklist token
    pass


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    # refresh_token = RefreshToken.for_user(User.objects.get(username='bob'))
    # return JsonResponse({
    #     "registered": True,
    #     "refresh": f"{refresh_token}",
    #     "access": f"{refresh_token.access_token}"
    # })
    username = request.POST.get("username")
    email = request.POST.get("email")
    password1 = request.POST.get("password1")

    if not username or not email or not password1:
        error = "Username" if not username else "Email" if not email else "Password"
        return JsonResponse({"message": f"{error} cannot be blank", "field": error[0].lower()})
    if len(username) > 32:
        return JsonResponse({"message": "Maximum 32 characters", "field": "u"})
    if any(c not in UOC for c in username):
        return JsonResponse({"message": "Invalid username", "field": "u"})
    if not re.search("^\S+@\S+\.[a-zA-Z]+$", email):
        return JsonResponse({"message": "Please enter a valid email", "field": "e"})
    # if len(password1) < 6:
        # return JsonResponse({"message": "Password must be at least 6 characters", "field": "p"})
    if password1 != request.POST.get("password2"):
        return JsonResponse({"message": "Password does not match", "field": "p2"})
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"message": "Username already taken", "field": "u", "taken": True})
    if User.objects.filter(email=email).exists():
        return JsonResponse({"message": "Email already in use", "field": "e"})

    user = None
    try:
        user = User.objects.create_user(username, email, password1)
        if user is not None:
            refresh_token = RefreshToken.for_user(user)
            return JsonResponse({
                "registered": True,
                "refresh": f"{refresh_token}",
                "access": f"{refresh_token.access_token}"
            })
    except IntegrityError:
        return JsonResponse({"message": "User already exists"})

    return JsonResponse({"message": "Unexpected error occurred"})


@api_view(["DELETE", "POST"])
def delete(request, model, identifier=None):
    # Use get instead of filter so that files are deleted too
    if model == "meme":
        Meme.objects.get(user=request.user, uuid=identifier).delete()
    elif model == "page":
        Page.objects.get(admin=request.user, name=identifier).delete()
    elif model == "account":
        password = request.POST.get("password")
        if password and request.user.check_password(password):
            request.user.delete()
        else:
            return HttpResponseBadRequest("Password incorrect")

    return HttpResponse(status=204)
