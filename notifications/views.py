from django.http import HttpResponseBadRequest
from django.core.paginator import Paginator

from .models import Notification
from memes.models import ModeratorInvite

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def nav_notifications(request):
    notifs = Notification.objects.filter(recipient=request.user, seen=False)
    to_send = notifs[:5]

    results = []
    for n in to_send:
        results.append({"link": n.link, "image": n.image.url if n.image else None, "message": n.message})
        n.seen = True

    response = {
        "count": notifs.count() + ModeratorInvite.objects.filter(invitee=request.user).count(),
        "results": results
    }

    Notification.objects.bulk_update(to_send, ["seen"])

    return Response(response)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
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
