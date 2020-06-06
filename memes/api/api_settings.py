from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from memes.models import User, Page
from memes.utils import SFT

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView


@api_view(("GET", "POST", "DELETE"))
def user_settings(request):
    user = request.user

    if request.method == "GET":
        return Response({
            "show_nsfw": user.show_nsfw,
            "email": user.email or ""
        })

    elif request.method == "POST":
        if "field" not in request.POST:
            return HttpResponseBadRequest()

        field = request.POST["field"]

        if field == "image":
            if not request.FILES or "image" not in request.FILES:
                return HttpResponseBadRequest()

            new_img = request.FILES["image"]
            if new_img.content_type not in SFT[:2]:
                return HttpResponseBadRequest("Supported media types: JPEG, PNG")

            user.image.delete()
            user.image.save(new_img.name, new_img)
            user.resize_img()

        elif field == "nsfw":
            user.show_nsfw = request.POST.get("show_nsfw") == "true"
            user.save(update_fields=["show_nsfw"])

        elif field == "email":
            if "email" not in request.POST:
                return HttpResponseBadRequest()

            email = request.POST["email"]
            if User.objects.filter(email=email).exists():
                return HttpResponseBadRequest("Email already in use")
            else:
                user.email = email
                user.save(update_fields=["email"])

        elif field == "password":
            old_password = request.POST.get("old_password")
            if not old_password or not user.check_password(old_password):
                return HttpResponseBadRequest("Password incorrect")

            password1 = request.POST.get("password1", "")
            # if len(password1) < 6:
            #     HttpResponseBadRequest("Password must be at least 6 characters")
            if password1 != request.POST.get("password2"):
                return HttpResponseBadRequest("Password does not match")
            else:
                # Change password
                user.set_password(password1)
                user.save(update_fields=["password"])

                return HttpResponse()

        else:
            return HttpResponseBadRequest()

        return HttpResponse()

    elif request.method == "DELETE":
        if "f" not in request.GET:
            return HttpResponseBadRequest()

        field = request.GET["f"]
        if field == "image":
            user.image.delete()
        elif field == "email":
            user.email = None
            user.save(update_fields=["email"])

        return HttpResponse(status=204)

    raise Http404


class PageSettings(APIView):
    def get_object(self, user, name, fields=None):
        return get_object_or_404(Page.objects.only(*fields), admin=user, name=name)

    def get(self, request, name):
        page = self.get_object(request.user, name, ("name", "display_name", "image", "cover", "description", "private", "permissions"))

        return Response({
            "name": page.name,
            "dname": page.display_name,
            "image": request.build_absolute_uri(page.image.url) if page.image else None,
            "cover": request.build_absolute_uri(page.cover.url) if page.cover else None,
            "description": page.description,
            "private": page.private,
            "permissions": page.permissions,
            "mods": User.objects.filter(moderating=page).values_list("username", flat=True),
            # "pending": page moderators pending
        })

    def post(self, request, name):
        if request.FILES:
            if "image" in request.FILES:
                page = self.get_object(request.user, name, ("name", "image"))
                img = request.FILES["image"]
                page.image.delete()
                page.image.save(img.name, img)
                page.resize_img()
            elif "cover" in request.FILES:
                page = self.get_object(request.user, name, ("name", "cover"))
                cover = request.FILES["cover"]
                page.cover.delete()
                page.cover.save(cover.name, cover)
                page.resize_cover()
            else:
                return HttpResponseBadRequest()
        else:
            page = self.get_object(request.user, name, ("display_name", "description", "private", "permissions"))
            page.display_name = request.POST.get("dname", "")[:32].strip()
            page.description = request.POST.get("description", "")[:150].strip()
            page.private = request.POST.get("private") == "true"
            page.permissions = request.POST.get("permissions") != "false"
            page.save()

        return HttpResponse()

    def delete(self, request, name):
        if "d" not in request.GET:
            return HttpResponseBadRequest()

        field = request.GET["d"]
        if field == "image":
            page = self.get_object(request.user, name, ["image"])
            page.image.delete()
        elif field == "cover":
            page = self.get_object(request.user, name, ["cover"])
            page.cover.delete()
        elif field == "mods":
            page = self.get_object(request.user.id, name, ["id"])
            page.moderators.remove(*User.objects.filter(username__in=request.GET.getlist("u")))
        elif field == "page":
            page = self.get_object(request.user.id, name, ["id"])
            page.delete()

        return HttpResponse(status=204)
