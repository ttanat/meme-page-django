from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F

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
    usernames = request.POST.getlist("new_mods")
    if not usernames:
        return HttpResponseBadRequest()

    page = get_object_or_404(Page.objects.only("id"), admin=request.user, name=name)
    # page = get_object_or_404(Page.objects.only("id", "num_mods"), admin=request.user, name=name)

    current_pending_count = ModeratorInvite.objects.filter(page=page).count() # + page.num_mods
    if current_pending_count + len(usernames) > 50:
        return HttpResponseBadRequest("Can only have 50 moderators")

    users = User.objects.only("id").filter(username__in=usernames)

    ModeratorInvite.objects.bulk_create(
        [ModeratorInvite(invitee=user, page=page) for user in users],
        ignore_conflicts=True
    )

    return HttpResponse()


class PendingModeratorsAdmin(APIView):
    permission_classes = [IsAuthenticated]

    def get_page(self, user, name):
        return get_object_or_404(Page.objects.only("id"), admin=user, name=name)

    def get(self, request, name):
        """ For admin seeing pending moderation invites to users """
        page = get_object_or_404(Page.objects.only("admin_id"), admin=request.user, name=name)

        if request.user.id != page.admin_id:
            return HttpResponseBadRequest()

        invites = ModeratorInvite.objects.filter(page=page) \
                                         .annotate(username=F("invitee__username")) \
                                         .values_list("username", flat=True)

        return Response(invites)

    def delete(self, request, name):
        """ For admin deleting pending moderation invites to users """
        if "usernames" not in request.GET:
            return HttpResponseBadRequest()

        usernames = request.GET["usernames"]
        page = self.get_page(request.user, name)
        ModeratorInvite.objects.filter(page=page, invitee__username__in=usernames).delete()

        return HttpResponse(status=204)


""" For everyone (GET request) or page admin (DELETE request) """


class CurrentModerators(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    """ For everyone """
    def get(self, request, name):
        """ Get invites for user """

        # TODO: fix this
        return Response(
            Page.objects.filter(name=name).annotate(username=F("moderators__username")).values_list("username", flat=True)
        )


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



""" For everyone except admin """


class HandleModeratorInvite(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """ Get invites for user """
        return Response(ModeratorInvite.objects.annotate(pname=F("page__name")).filter(invitee=request.user).values("pname"))

    def put(self, request, name):
        """ Accept invite and become a moderator """

        page = get_object_or_404(Page.objects.only("id"), name=name)
        # page = get_object_or_404(Page.objects.only("id", "num_mods"), name=name)
        invite = get_object_or_404(ModeratorInvite.objects.only("id"), invitee=request.user, page=page)
        page.moderators.add(request.user)
        # with transaction.atomic():
        #     if page.num_mods >= 100:
        #         return HttpResponseBadRequest("Page has too many moderators already")
        #     else:
        #         if page.num_mods >= 99:
        #             ModeratorInvite.objects.filter(page=page).delete()

        #         page.moderators.add(request.user)
        #         page.num_mods = F("num_mods") + 1
        #         page.save(update_fields=["num_mods"])

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
