from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from memes.models import User, Page
from memes.utils import check_file_ext

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


@api_view(("GET", "POST", "DELETE"))
@permission_classes([IsAuthenticated])
def user_settings(request):
    user = request.user

    if request.method == "GET":
        return Response({
            # "show_nsfw": user.show_nsfw,
            "email": user.email
        })

    elif request.method == "POST":
        if "field" not in request.POST:
            return HttpResponseBadRequest()

        field = request.POST["field"]

        if field == "image":
            if not request.FILES or "image" not in request.FILES:
                return HttpResponseBadRequest()

            new_img = request.FILES["image"]
            if (new_img.content_type not in ("image/jpeg", "image/png")
                    or not check_file_ext(new_img.name, (".jpg", ".png", ".jpeg"))):
                return HttpResponseBadRequest("Supported media types: JPEG, PNG")

            user.add_profile_image(new_img)

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

        if request.GET["f"] == "image":
            user.delete_profile_image()

        return HttpResponse(status=204)

    raise Http404


class PageSettings(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, user, name, fields=None):
        return get_object_or_404(Page.objects.only(*fields), admin=user, name=name)

    def get(self, request, name):
        page = self.get_object(request.user, name, ("name", "display_name", "image", "cover", "description", "private", "permissions"))

        return Response({
            "name": page.name,
            "display_name": page.display_name,
            "image": page.image.url if page.image else None,
            "cover": page.cover.url if page.cover else None,
            "description": page.description,
            "private": page.private,
            "permissions": page.permissions,
        })

    def get_valid_update_fields(self):
        return ("display_name", "description", "private", "permissions")

    def update_fields_valid(self, update_fields):
        return all(field in ("display_name", "description", "private", "permissions") for field in update_fields)

    def post(self, request, name):
        if request.FILES:
            if "image" in request.FILES:
                page = self.get_object(request.user, name, ("name", "image"))
                img = request.FILES["image"]
                # Check valid image type
                if not check_file_ext(img.name, (".jpg", ".png", ".jpeg")):
                    return HttpResponseBadRequest()
                # Delete previous image
                page.image.delete()
                # Save new image
                page.image.save(img.name, img)
                # Resize new image
                page.resize_image()
            elif "cover" in request.FILES:
                page = self.get_object(request.user, name, ("name", "cover"))
                cover = request.FILES["cover"]
                # Check valid image type
                if not check_file_ext(cover.name, (".jpg", ".png", ".jpeg")):
                    return HttpResponseBadRequest()
                # Delete previous image
                page.cover.delete()
                # Save new image
                page.cover.save(cover.name, cover)
                # Resize new image
                page.resize_cover()
            else:
                return HttpResponseBadRequest()
        else:
            update_fields = request.POST.getlist("update_fields")

            if not update_fields or not self.update_fields_valid(update_fields):
                return HttpResponseBadRequest()

            page = self.get_object(request.user, name, update_fields)

            if "display_name" in update_fields:
                new_display_name = request.POST["display_name"][:32].strip()
                page.display_name = new_display_name

            if "description" in update_fields:
                page.description = request.POST["description"][:150].strip()

            if "private" in update_fields:
                new_private = request.POST["private"] == "true"
                page.private = new_private

            if "permissions" in update_fields:
                page.permissions = request.POST["permissions"] != "false"

            page.save()

            # Update cached values of all memes posted to this page (page_private)
            if "private" in update_fields:
                page.meme_set.update(page_private=new_private)

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
