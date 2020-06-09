from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F

from memes.models import Page, SubscribeRequest, User

from rest_framework.decorators import api_view
from rest_framework.response import Response


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

        # Check if user has requested to subscribe to page
        if page.private and not response["is_subscribed"]:
            response["sub_req_exists"] = SubscribeRequest.objects.filter(user=request.user, page=page).exists()

    # Prevent loading memes if page is private and user is not subscribed or page admin
    response["show"] = not page.private or response.get("is_subscribed") or page.admin_id == request.user.id

    if response["show"]:
        response["page"]["moderators"] = page.moderators.values_list("username", flat=True)

    return Response(response)


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


# name only used in GET
@api_view(("GET", "PUT", "DELETE"))
def subscribe_request(request, name):
    """ Handle subscribe requests for private pages """

    page = get_object_or_404(Page.objects.only("id"), admin=request.user, name=name)

    if request.method == "GET":
        """ ID of request is sent too """

        reqs = SubscribeRequest.objects.annotate(username=F("user__username")) \
                                .filter(page=page) \
                                .values("id", "username", "timestamp") \
                                .order_by("id")

        # Last ID of "subscribe request" sent (prevents showing duplicates)
        if "lid" in request.GET:
            reqs = reqs.filter(id__gt=request.GET["lid"])

        # Get first 25 requests
        results = reqs[:25]

        return Response({
            # If there are more requests, get largest ID of results
            "lid": results[25]["id"] if reqs.count() > 25 else None,
            "results": results
        })

    elif request.method == "PUT":
        """ Accept request and delete object """

        if "id" not in request.GET:
            return HttpResponseBadRequest()

        sub_req = get_object_or_404(
            SubscribeRequest.objects.only("user_id"),
            id=request.GET["id"]
        )

        # Get user to add to subscribers
        user_to_add = User.objects.only("id").get(id=sub_req.user_id)

        # Add user to subscribers of page
        page.subscribers.add(user_to_add)

        # Delete the request
        sub_req.delete()

        return HttpResponse(status=204)

    elif request.method == "DELETE":
        """ Delete request without accepting """

        if "id" not in request.GET:
            return HttpResponseBadRequest()

        SubscribeRequest.objects.filter(id=request.GET["id"], page=page).delete()

        return HttpResponse(status=204)


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