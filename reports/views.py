from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F

from .models import Report
from memes.models import Meme, Comment, Page, User

from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class MemeReport(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if "uuid" not in request.POST or "reason" not in request.POST:
            return HttpResponseBadRequest()

        meme = get_object_or_404(Meme.objects.only("user"), uuid=request.POST["uuid"])
        if meme.user_id == request.user.id:
            return HttpResponseBadRequest("Cannot report yourself")

        Report.objects.create(
            reporter=request.user,
            content_object=meme,
            reason=request.POST["reason"],
            message=request.POST.get("message", "")
        )

        meme.num_reports = F("num_reports") + 1
        meme.save(update_fields=["num_reports"])

        return HttpResponse(status=201)

    def get(self, request):
        if "uuid" not in request.POST:
            return HttpResponseBadRequest()

        meme = get_object_or_404(Meme.objects.only("page"), uuid=uuid)

        # Only staff and moderators of page or admin can get reports for meme
        if not request.user.is_staff:
            if meme.page_id:
                page = get_object_or_404(Page.objects.only("id", "admin"), id=meme.page_id)
                if page.admin_id != request.user.id or not page.moderators.filter(id=request.user.id).exists():
                    return HttpResponse("Cannot get reports", status=403)
            else:
                return HttpResponse("Cannot get reports", status=403)

        reports = Report.objects.filter(content_object=meme).order_by("-id")

        return JsonResponse({
            "count": reports.count(),
            "reports": reports[:50]
        })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_num_meme_reports(request):
    """ Get number of reports for each meme with uuid in query params """

    if "uuid" not in request.query_params:
        return HttpResponseBadRequest()

    # Get list of uuids
    uuids = request.query_params.getlist("uuid")[:20]
    if not uuids:
        return JsonResponse([], safe=False)

    if "page" in request.query_params:
        # Get meme page that request is being sent from
        page = get_object_or_404(Page.objects.only("id", "admin"), name=request.query_params["page"])

        # Check that request is sent by moderator or admin of page or staff
        if (not request.user.is_staff and
                page.admin_id != request.user.id and
                    not page.moderators.filter(id=request.user.id).exists()):
            return HttpResponse("Cannot get reports", status=403)

        return Response(Meme.objects.filter(page=page, uuid__in=uuids).values("uuid", "num_reports"))

    # Staff can get number of reports without being in a specific meme page
    elif request.user.is_staff:
        return Response(Meme.objects.filter(uuid__in=uuids).values("uuid", "num_reports"))

    return HttpResponseBadRequest()
