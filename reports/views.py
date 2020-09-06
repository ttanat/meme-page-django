from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F

from .models import Report
from memes.models import Meme, Comment, Page, User

from rest_framework.views import APIView
from rest_framework.decorators import permission_classes
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

        return HttpResponse(status=201)

    def get(self, request):
        if "uuid" not in request.POST:
            return HttpResponseBadRequest()

        meme = get_object_or_404(Meme.objects.only("page"), uuid=uuid)

        # Only staff and moderators of page can get reports for meme
        if not request.user.is_staff:
            if meme.page_id:
                page = get_object_or_404(Page.objects.only("id"), id=meme.page_id)
                if not page.moderators.filter(id=request.user.id).exists():
                    return HttpResponse("Cannot get reports", status=403)
            else:
                return HttpResponse("Cannot get reports", status=403)

        reports = Report.objects.filter(content_object=meme).order_by("-id")

        return JsonResponse({
            "count": reports.count(),
            "reports": reports[:50]
        })
