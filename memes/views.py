from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
# from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
# from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import F, Q, Count, Sum, Exists, OuterRef, Subquery, IntegerField
# from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.exceptions import PermissionDenied
# from django.views.decorators.http import require_http_methods
# from django.views.decorators.cache import cache_page

from .models import *
from .utils import UOC, SFT, CATEGORIES
from datetime import timedelta
from time import perf_counter
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
def meme_view(request, uuid):
    """ Page for individual meme with comments """

    # if uuid == "random":
    #     queryset = Meme.objects.filter(hidden=False).filter(Q(page=None)|Q(page__private=False))
    #     n = randint(0, queryset.count() - 1)
    #     uuid = queryset.values("uuid")[n]

    meme = get_object_or_404(Meme.objects.select_related("user", "page"), uuid=uuid)

    if meme.page and meme.page.private:
        if not request.user.is_authenticated or (not request.user.subscriptions.filter(id=meme.page_id).exists() and meme.page.admin != request.user):
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
        return JsonResponse({"url": request.build_absolute_uri(meme.file.url), "isVid": meme.content_type[:6] == "video/"})
    elif obj == "c":
        url = get_object_or_404(Comment.objects.only("image"), uuid=uuid).image.url
        return JsonResponse({"url": request.build_absolute_uri(url)})

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
    if obj == "m":
        return Response(Like.objects.filter(user=request.user, meme__uuid__in=uuids).annotate(uuid=F("meme__uuid")).values("uuid", "point"))
    elif obj == "c":
        return Response(Like.objects.filter(user=request.user, comment__uuid__in=uuids).annotate(uuid=F("comment__uuid")).values("uuid", "point"))

    raise Http404


@api_view(("PUT", "DELETE"))
def like(request):
    uuid = request.GET["u"]
    type0 = request.GET["t"]
    point = 1 if request.GET["v"] == "l" else -1

    if type0 == "m":
        if request.method == "PUT":
            meme = get_object_or_404(Meme, uuid=uuid)
            obj, created = Like.objects.update_or_create(user=request.user, meme=meme, defaults={"point": point, "liked_on": timezone.now()})
            return HttpResponse(status=201 if created else 200)
        elif request.method == "DELETE":
            Like.objects.filter(user=request.user, meme__uuid=uuid).delete()
            return HttpResponse(status=204)
    elif type0 == "c":
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
        content = request.POST.get("content", "")[:150].strip()
        image = request.FILES.get("image")
        if not content and not image:
            return HttpResponseBadRequest()

        meme = get_object_or_404(Meme, uuid=request.POST["uuid"])

        new_comment = Comment.objects.create(
            user=request.user,
            meme=meme,
            content=content,
            image=image
        )

        return JsonResponse({"uuid": new_comment.uuid})

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
        Comment.objects.filter(user=request.user, uuid=request.GET.get("u")).update(deleted=True)
        # c = Comment.objects.only("deleted").get(user=request.user, uuid=request.GET.get("u"))
        # c.deleted = True
        # c.save()

        return HttpResponse(status=204)

    raise Http404


@api_view(["POST"])
def reply(request):
    """ Reply to comments """
    c_uuid = request.POST["c_uuid"]
    content = request.POST.get("content", "")[:150].strip()
    image = request.FILES.get("image")
    if not content and not image:
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
    c_embedded = request.POST["embed_caption"] == "true"
    nsfw = request.POST["nsfw"] == "true"
    content_type = file.content_type if file else None
    category_name = request.POST.get("category")

    if file:
        if category_name:
            if category_name not in CATEGORIES:
                return JsonResponse({"success": False, "message": "Category not found."})
            # category = get_object_or_404(Category, name=category_name)
            category = Category.objects.get_or_create(name=category_name)[0]    # Change this before production

        if content_type not in SFT or (content_type == "video/quicktime" and not file.name.endswith(".mov")):
            return JsonResponse({"success": False, "message": "Unsupported file type."})

        if page_name:
            page = get_object_or_404(Page, name=page_name)
            if page.admin != request.user:
                if not page.permissions:
                    return JsonResponse({"success": False, "message": "Only admin of this page can post."})
                if not page.subscribers.filter(id=request.user.id).exists():
                    return JsonResponse({"success": False, "message": "Must be subscribed to post."})

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
    
    return JsonResponse({"success": False, "message": "Error: No file uploaded."})


@api_view(["GET"])
def notifications(request):
    n = Notification.objects.filter(recipient=request.user)
    return render(request, "memes/notifications.html", {"notifications": n})


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
            "admin": page.adm,
            "moderators": page.moderators.values_list("username", flat=True)
        }
    }

    if request.user.is_authenticated:
        response["is_subscribed"] = page.subscribers.filter(id=request.user.id).exists()
        response["is_page_admin"] = page.admin == request.user

    # Prevent loading memes if page is private and user is not subscribed or page admin
    response["show"] = not page.private or response.get("is_subscribed") or response.get("is_page_admin")

    return Response(response)


@api_view(("GET", "POST", "DELETE"))
def page_settings(request, name):
    page = get_object_or_404(Page, admin=request.user, name=name)
    if request.method == "GET":
        return Response({
            "name": page.name,
            "dname": page.display_name,
            "image": request.build_absolute_uri(page.image.url) if page.image else None,
            "cover": request.build_absolute_uri(page.cover.url) if page.cover else None,
            "description": page.description,
            "private": page.private,
            "permissions": page.permissions,
            "mods": page.moderators.values_list("username", flat=True),
            # "pending": page moderators pending
        })
    elif request.method == "POST":
        if request.FILES:
            if request.FILES.get("image"):
                img = request.FILES["image"]
                page.image.delete()
                page.image.save(img.name, img)
                page.resize_img()
            elif request.FILES.get("cover"):
                cover = request.FILES["cover"]
                page.cover.delete()
                page.cover.save(cover.name, cover)
                page.resize_cover()
            else:
                return HttpResponseBadRequest()
        else:
            page.display_name = request.POST.get("dname", "")[:32].strip()
            page.description = request.POST.get("description", "")[:150].strip()
            page.private = request.POST.get("private") == "true"
            page.permissions = request.POST.get("permissions") != "false"
            page.save(update_fields=("display_name", "description", "private", "permissions"))

        return HttpResponse()
    elif request.method == "DELETE":
        field = request.GET.get("d")
        if field == "image":
            page.image.delete()
        elif field == "cover":
            page.cover.delete()
        elif field == "mods":
            page.moderators.remove(*User.objects.filter(username__in=request.GET.getlist("u")))
        elif field == "page":
            page.delete()

        return HttpResponse(status=204)


@api_view(["GET"])
def follow(request, username):
    user = request.user
    if user.username == username:
        return HttpResponseBadRequest()

    user_to_follow = get_object_or_404(User.objects.only("id", "num_followers"), username=username)
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
        new_bio = request.POST["new_val"][:150].strip()
        if request.user.bio != new_bio:
            request.user.bio = new_bio
            request.user.save(update_fields=["bio"])

        return JsonResponse({"new_val": new_bio})

    elif field == "description":
        new_description = request.POST["new_val"][:150].strip()
        name = request.POST["name"]

        page = get_object_or_404(Page.objects.only("admin_id", "description"), name=name)
        if request.user.id == page.admin_id:
            if page.description != new_description:
                page.description = new_description
                page.save(update_fields=["description"])

                return JsonResponse({"new_val": new_description})

    return HttpResponseBadRequest()


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False})

    raise Http404


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    # refresh_token = RefreshToken.for_user(User.objects.get(username='bob'))
    # return JsonResponse({
    #     "registered": True,
    #     "refresh": f"{refresh_token}",
    #     "access": f"{refresh_token.access_token}"
    # })
    username = request.POST["username"]
    email = request.POST["email"]
    password1 = request.POST["password1"]

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
    if password1 != request.POST["password2"]:
        return JsonResponse({"message": "Password does not match", "field": "p2"})
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"message": "Username already taken", "field": "u", "taken": True})
    if User.objects.filter(email=email).exists():
        return JsonResponse({"message": "Email is already being used with another account", "field": "e"})

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
        return JsonResponse({"message": "User already exists."})

    return JsonResponse({"message": "Unexpected error occurred."})


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


@api_view(("GET", "POST", "DELETE"))
def user_settings(request):
    user = request.user

    if request.method == "GET":
        return Response({
            "show_nsfw": user.show_nsfw,
            "email": user.email or ""
        })

    elif request.method == "POST":
        field = request.POST["field"]

        if field == "image" and request.FILES:
            new_img = request.FILES["image"]
            if new_img.content_type not in SFT[:2]:
                return HttpResponseBadRequest("Supported media types: JPEG, PNG")
            user.image.delete()
            user.image.save(new_img.name, new_img)
            user.resize_img()

        elif field == "nsfw":
            user.show_nsfw = request.POST["show_nsfw"] == "true"
            user.save(update_fields=["show_nsfw"])

        elif field == "email":
            email = request.POST["email"]
            if User.objects.filter(email=email).exists():
                return HttpResponseBadRequest("Email is already being used with another account")
            else:
                user.email = email
                user.save(update_fields=["email"])

        elif field == "password":
            password1 = request.POST["password1"]
            if password1 != request.POST["password2"]:
                return HttpResponseBadRequest("Password does not match")
            # elif len(password1) < 6:
            #     return HttpResponseBadRequest("Password must be at least 6 characters")
            elif check_password(request.POST["old_password"], user.password):
                user.password = make_password(password1)
                user.save(update_fields=["password"])
            else:
                return HttpResponseBadRequest("Password incorrect")

        return HttpResponse()

    elif request.method == "DELETE":
        field = request.GET["f"]
        if field == "image":
            user.image.delete()
        elif field == "email":
            user.email = None
            user.save(update_fields=["email"])

        return HttpResponse(status=204)

    raise Http404


@api_view(["DELETE", "POST"])
def delete(request, model, identifier=None):
    # Use get instead of filter so that files are deleted too
    if model == "meme":
        Meme.objects.get(user=request.user, uuid=identifier).delete()
    elif model == "page":
        Page.objects.get(admin=request.user, name=identifier).delete()
    elif model == "account":
        user = request.user
        if check_password(request.POST["password"], user.password):
            user.delete()
        else:
            return HttpResponseBadRequest("Password incorrect")

    return HttpResponse(status=204)
