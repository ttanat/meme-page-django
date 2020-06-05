from django.contrib.auth.hashers import check_password
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from memes.models import User, Page
from rest_framework.decorators import api_view
from rest_framework.response import Response


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