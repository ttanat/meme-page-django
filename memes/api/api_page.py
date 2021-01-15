from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F, Q
from django.db import transaction

from memes.models import Page, SubscribeRequest, User, InviteLink
from analytics.signals import page_view_signal

from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

import re
from string import ascii_letters


@api_view(["GET"])
def page(request, name):
    try:
        page = Page.objects.annotate(adm=F("admin__username")).defer("created", "nsfw").get(name=name)
    except Page.DoesNotExist:
        page_name = get_object_or_404(Page.objects.values_list("name", flat=True), name__iexact=name)
        return JsonResponse({"redirect": True, "name": page_name})

    response = {
        "page": {
            "name": page.name,
            "dname": page.display_name,
            "image": page.image.url if page.image else None,
            "cover": page.cover.url if page.cover else None,
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

        # Check if user has requested to subscribe to page
        if page.private and not response["is_subscribed"]:
            response["is_requested"] = SubscribeRequest.objects.filter(user=request.user, page=page).exists()

    # Prevent loading memes if page is private and user is not subscribed and user is not page admin
    response["show"] = (not page.private or response.get("is_subscribed") or page.admin_id == request.user.id
                            or page.moderators.filter(id=request.user.id).exists())

    if response["show"]:
        mods = [p for p in page.moderators.values_list("username", flat=True).order_by("date_joined")]
        mods.remove(page.adm)
        response["page"]["moderators"] = mods

    page_view_signal.send(sender=page.__class__, user=request.user, page=page)

    return Response(response)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscribe(request, name):
    page_to_sub = get_object_or_404(Page.objects.only("id", "admin_id", "private"), name=name)

    # Admins cannot subscribe to their own page
    if page_to_sub.admin_id == request.user.id:
        return HttpResponseBadRequest()

    is_subscribed = page_to_sub.subscribers.filter(id=request.user.id).exists()

    if is_subscribed:
        page_to_sub.subscribers.remove(request.user)    # Unsubscribe
    else:
        # If subscribing to a private page
        if page_to_sub.private:
            # Send a request to subscribe
            obj, created = SubscribeRequest.objects.get_or_create(user=request.user, page=page_to_sub)
            if not created:
                obj.delete()

            return JsonResponse({"requested": created})
        else:
            page_to_sub.subscribers.add(request.user)    # Subscribe

    return JsonResponse({"subscribed": not is_subscribed})


class HandleSubscribeRequest(APIView):
    """ Handle subscribe requests for private pages for admin and moderators """
    permission_classes = [IsAuthenticated]

    def get_page(self, user, name):
        return get_object_or_404(Page.objects.only("id"), moderators=user, name=name)

    def get(self, request, name):
        """ ID of request is sent too """
        page = get_object_or_404(Page.objects.only("admin_id"), moderators=request.user, name=name)

        reqs = SubscribeRequest.objects.annotate(username=F("user__username")) \
                                       .filter(page=page) \
                                       .values("id", "username", "timestamp") \
                                       .order_by("id")

        # Last ID of "subscribe request" sent (prevents showing duplicates)
        if "lid" in request.GET:
            reqs = reqs.filter(id__gt=request.GET["lid"])

        # Get first 25 requests
        results = reqs[:25]

        response = {
            # If there are more requests, get largest ID of results
            "lid": results[25]["id"] if reqs.count() > 25 else None,
            "results": results
        }

        # Tell client if user is admin
        if "lid" not in request.GET:
            response["is_admin"] = request.user.id == page.admin_id

        return Response(response)

    def put(self, request, name):
        """ Accept request and delete object """
        if "id" not in request.GET:
            return HttpResponseBadRequest()

        sub_req = get_object_or_404(SubscribeRequest.objects.only("user_id"), id=request.GET["id"])
        # Get user to add to subscribers
        user_to_add = User.objects.only("id").get(id=sub_req.user_id)
        # Add user to subscribers of page
        self.get_page(request.user, name).subscribers.add(user_to_add)
        # Delete the request
        sub_req.delete()

        return HttpResponse(status=204)

    def delete(self, request, name):
        """ Delete request without accepting """

        if "id" not in request.GET:
            return HttpResponseBadRequest()

        SubscribeRequest.objects.filter(id=request.GET["id"], page=self.get_page(request.user, name)).delete()

        return HttpResponse(status=204)


class HandleInviteLinkMods(APIView):
    """ Handle invite links for private pages for admin AND moderators """
    permission_classes = [IsAuthenticated]

    def get_page(self, user, identifier):
        return get_object_or_404(Page.objects.only("id"), moderators=user, name=identifier, private=True)

    def post(self, request, identifier):
        """ identifier is name of page to create link for """
        if "uses" not in request.POST:
            return HttpResponseBadRequest()

        page = self.get_page(request.user, identifier)

        if InviteLink.objects.filter(page=page).count() < 100:
            link = InviteLink.objects.create(page=page, uses=request.POST["uses"])

            return JsonResponse({"uuid": link.uuid, "uses": link.uses})

        return HttpResponseBadRequest()

    def get(self, request, identifier):
        """ Get invite links for page """
        page = self.get_page(request.user, identifier)

        return Response(InviteLink.objects.filter(page=page).values("uuid", "uses"))

    def delete(self, request, identifier):
        """ identifier is uuid of link to delete """
        InviteLink.objects.filter(uuid=identifier).filter(page__moderators=request.user).delete()

        return HttpResponse(status=204)


class HandleInviteLinkUser(APIView):
    """ Handle invite links for private pages for users """
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        """ Get page details when user goes to invite link """
        try:
            link = InviteLink.objects.select_related("page").only("page__name", "page__display_name", "page__image").get(uuid=uuid)
        except InviteLink.DoesNotExist:
            return JsonResponse({"valid": False})

        response = {"valid": True, "name": link.page.name}

        if link.page.display_name:
            response["dname"] = link.page.display_name

        if link.page.image:
            response["image"] = link.page.image.url

        return JsonResponse(response)

    def put(self, request, uuid):
        """ uuid of link to use to add user """
        link = get_object_or_404(
            InviteLink.objects.select_related("page").only("id", "page__id", "page__name", "page__admin_id", "uses"),
            uuid=uuid
        )

        # Don't subscribe admin to their own page and don't let a subscriber use a link
        if request.user.id == link.page.admin_id or link.page.subscribers.filter(id=request.user.id).exists():
            return JsonResponse({"name": link.page.name})

        with transaction.atomic():
            if link.uses < 1:
                # Delete if no uses left
                link.delete()
                return HttpResponseBadRequest("Link is no longer valid")
            else:
                # Subscribe user to page
                link.page.subscribers.add(request.user)
                if link.uses == 1:
                    # Delete now because no uses left
                    link.delete()
                else:
                    link.uses = F("uses") - 1
                    link.save(update_fields=["uses"])

                # Delete subscribe request for user on this page if it exists
                SubscribeRequest.objects.filter(user=request.user, page=link.page).delete()

                return JsonResponse({"name": link.page.name})

        return HttpResponseBadRequest()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def new_page(request):
    name = request.POST.get("name", "").strip()
    dname = request.POST.get("display_name", "")[:32].strip()
    private = request.POST.get("private") == "true"
    perm = request.POST.get("permissions") != "false"

    # Check name exists
    if not name:
        return JsonResponse({"success": False})
    # Check name length <= 32
    if len(name) > 32:
        return JsonResponse({"success": False, "message": "Maximum 32 characters"})
    # Check at least one letter [a-zA-Z] in name
    if not any(c in name for c in ascii_letters) or not re.search(".*[a-zA-Z].*", name):
        return JsonResponse({"success": False, "letter": "Name must have at least one letter"})
    # Check characters in name valid
    if not re.search("^[a-zA-Z0-9_]+$", name):
        return JsonResponse({"success": False, "message": "Letters, numbers, and underscores only"})
    # Check if user already has 3 pages
    if Page.objects.filter(admin=request.user).count() > 2:
        return JsonResponse({"success": False, "maximum": True})

    with transaction.atomic():
        # Check if page with same name (case-insensitive) already exists
        if Page.objects.filter(name__iexact=name).exists():
            return JsonResponse({"success": False, "taken": True})

        page = Page.objects.create(admin=request.user, name=name, display_name=dname, private=private, permissions=perm)

    page.moderators.add(request.user)

    return JsonResponse({"success": True, "name": name})
