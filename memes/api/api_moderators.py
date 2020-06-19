from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.db import IntegrityError

from memes.models import Page, User, ModeratorInvite

from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly


""" For page admin """


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_moderators(request, name):
    """ Invite users in new_mods to moderate for page"""
    usernames = request.POST.getlist("new_mods")[:50]
    if not usernames:
        return HttpResponseBadRequest()

    page = get_object_or_404(Page.objects.only("id"), admin=request.user, name=name)
    # page = get_object_or_404(Page.objects.only("id", "num_mods"), admin=request.user, name=name)

    current_pending_count = page.moderatorinvite_set.count() + page.moderators.count() # + page.num_mods
    if current_pending_count + len(usernames) > 50:
        return HttpResponseBadRequest("Can only have 50 moderators")

    users = User.objects.only("id").filter(username__in=usernames)

    try:
        ModeratorInvite.objects.bulk_create([ModeratorInvite(invitee=user, page=page) for user in users])
    except IntegrityError:
        return HttpResponseBadRequest("Moderator(s) already exist")

    return Response(users.values_list("username", flat=True))


class PendingModeratorsAdmin(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, name):
        """ For admin deleting pending moderation invites to users """
        if "username" not in request.GET:
            return HttpResponseBadRequest()

        usernames = request.GET.getlist("username")
        page = get_object_or_404(Page.objects.only("id"), admin=request.user, name=name)
        ModeratorInvite.objects.filter(page=page, invitee__username__in=usernames).delete()

        return HttpResponse(status=204)


class CurrentModerators(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    """ For page admin """
    def delete(self, request, name):
        """ For admin deleting current moderators """
        if "usernames" not in request.GET:
            return HttpResponseBadRequest()

        usernames = request.GET["usernames"]
        page = get_object_or_404(Page.objects.only("id"), admin=request.user, name=name)
        # page = get_object_or_404(Page.objects.only("id", "num_mods"), admin=request.user, name=name)
        page.moderators.remove(*User.objects.filter(username__in=usernames))
        # page.num_mods = F("num_mods") - 1
        # page.save(update_fields=["num_mods"])

        return HttpResponse(status=204)


""" For everyone """


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_moderators(request, name):
    """
    If admin, get pending invites and all moderators (dictionary)
    If any other user, get all moderators (list)
    """

    page = get_object_or_404(Page.objects.only("admin_id"), name=name)

    if request.user.id == page.admin_id:
        return Response({
            "pending": page.moderatorinvite_set.values_list("invitee__username", flat=True),
            "current": page.moderators.values_list("username", flat=True)
        })
    else:
        return Response(page.moderators.values_list("username", flat=True))


""" For everyone except admin """


class HandleModeratorInvite(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """ Get invites for user """
        return Response(ModeratorInvite.objects.filter(invitee=request.user).values_list("page__name", flat=True))

    def put(self, request, name):
        """ Accept invite and become a moderator """

        page = get_object_or_404(Page.objects.only("id"), name=name)
        # page = get_object_or_404(Page.objects.only("id", "num_mods"), name=name)
        invite = get_object_or_404(ModeratorInvite.objects.only("id"), invitee=request.user, page=page)
        page.moderators.add(request.user)
        invite.delete()
        # with transaction.atomic():
        #     if page.num_mods >= 100:
        #         return HttpResponseBadRequest("Page has too many moderators already")
        #     else:
        #         if page.num_mods >= 99:
        #             ModeratorInvite.objects.filter(page=page).delete()

        #         page.moderators.add(request.user)
        #         page.num_mods = F("num_mods") + 1
        #         page.save(update_fields=["num_mods"])
        #         invite.delete()

        #         return HttpResponse()

        # return HttpResponseBadRequest()

        return HttpResponse()

    def delete(self, request, name):
        """ For users deleting invite to moderate for a page """

        # page = get_object_or_404(Page.objects.only("num_mods"), name=name)
        ModeratorInvite.objects.filter(invitee=request.user, page__name=name).delete()
        # ModeratorInvite.objects.filter(invitee=request.user, page=page).delete()
        # page.num_mods = F("num_mods") - 1
        # page.save(update_fields=["num_mods"])

        return HttpResponse(status=204)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def stop_moderating(self, request, name):
    """ For moderator to leave and stop being a moderator """
    """ name is page name """

    page = get_object_or_404(Page.objects.only("id"), moderators=request.user, name=name)
    page.moderators.remove(request.user)

    return HttpResponse(status=204)
