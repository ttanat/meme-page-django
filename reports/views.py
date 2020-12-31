from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from .models import Report
from .utils import get_moderation_labels, analyze_labels
from memes.models import Meme, Comment, Page, User

from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_report(request):
    """ Report meme, comment, page, or user """

    if request.POST.keys() < {"reportObject", "objectUid", "reason"}:
        return HttpResponseBadRequest()
    if request.POST["reason"] not in ("spam", "nudity", "shocking", "private", "discrimination", "dangerous", "illegal", "other"):
        return HttpResponseBadRequest()
    if request.POST["reason"] == "other" and not request.POST.get("info", "").strip():
        return HttpResponseBadRequest()

    # Get object that user is reporting
    obj_name = request.POST["reportObject"]
    if obj_name == "meme":
        to_report = get_object_or_404(Meme.objects.only("user", "original", "report_labels", "hidden"), uuid=request.POST["objectUid"])
    elif obj_name in ("comment", "reply"):
        to_report = get_object_or_404(Comment.objects.only("user", "image", "report_labels", "deleted"), uuid=request.POST["objectUid"])
    elif obj_name == "page":
        to_report = get_object_or_404(Page.objects.only("admin", "banned"), name=request.POST["objectUid"])
    elif obj_name == "user":
        to_report = get_object_or_404(User.objects.only("banned"), username=request.POST["objectUid"])
    else:
        return HttpResponseBadRequest()

    # Prevent reporting hidden/deleted/banned objects
    if obj_name == "meme" and to_report.hidden:
        return HttpResponseBadRequest()
    elif obj_name in ("comment", "reply") and to_report.deleted:
        return HttpResponseBadRequest()
    elif obj_name in ("user", "page") and to_report.banned:
        return HttpResponseBadRequest()

    # Prevent reporting oneself
    if obj_name in ("meme", "comment", "reply") and to_report.user_id == request.user.id:
        return HttpResponseBadRequest()
    elif obj_name == "page" and to_report.admin_id == request.user.id:
        return HttpResponseBadRequest()
    elif obj_name == "user" and to_report.id == request.user.id:
        return HttpResponseBadRequest()

    # Create report
    report = Report.objects.create(
        reporter=request.user,
        content_object=to_report,
        reason=request.POST["reason"],
        info=request.POST.get("info", "").strip()[:500].strip()
    )

    # Automatically hide/delete/ban depending on number of reports
    report_count = Report.objects.filter(
        content_type=ContentType.objects.get_for_model(to_report),
        object_id=to_report.id
    ).distinct("reporter").count()
    if report_count > 100:
        if obj_name in ("user", "page"):
            to_report.banned = True
            to_report.save(update_fields=["banned"])
    if report_count > 10:
        if obj_name == "meme":
            to_report.hidden = True
            to_report.save(update_fields=["hidden"])
        elif obj_name in ("comment", "reply"):
            to_report.deleted = 4
            to_report.save(update_fields=["deleted"])

    if obj_name in ("meme", "comment", "reply") and not to_report.report_labels:
        labels = get_moderation_labels(to_report)
        if labels is not None:  # Labels will be None if object is comment/reply without image
            to_report.report_labels = labels
            analysis = analyze_labels(labels)
            if analysis["hide"]:
                if obj_name == "meme":
                    to_report.hidden = True
                    to_report.save(update_fields=("report_labels", "hidden"))
                else:
                    to_report.deleted = 4
                    to_report.save(update_fields=("report_labels", "deleted"))
            else:
                to_report.save(update_fields=["report_labels"])

    return HttpResponse()


class MemeReport(APIView):
    permission_classes = [IsAuthenticated]

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
