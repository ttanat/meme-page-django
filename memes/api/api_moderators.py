from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.db import transaction, IntegrityError

from memes.models import Page, User, ModeratorInvite, Meme, Comment

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

    page = get_object_or_404(Page.objects.only("num_mods"), admin=request.user, name=name)

    current_pending_count = page.moderatorinvite_set.count() + page.num_mods
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
        if "username" not in request.GET:
            return HttpResponseBadRequest()

        page = get_object_or_404(Page.objects.only("num_mods"), admin=request.user, name=name)
        page.moderators.remove(*User.objects.filter(username__in=request.GET.getlist("username")))

        page.num_mods = F("num_mods") - 1
        page.save(update_fields=["num_mods"])

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
            "current": page.moderators.values_list("username", flat=True),
            "pending": page.moderatorinvite_set.values_list("invitee__username", flat=True)
        })

    return Response({"current": page.moderators.values_list("username", flat=True)})


""" For everyone except admin """


class HandleModeratorInvite(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """ Get invites for user """
        return Response(ModeratorInvite.objects.filter(invitee=request.user).values_list("page__name", flat=True))

    def put(self, request, name):
        """ Accept invite and become a moderator """

        page = get_object_or_404(Page.objects.only("display_name", "private", "num_mods"), name=name)

        with transaction.atomic():
            invite = get_object_or_404(ModeratorInvite.objects.only("id"), invitee=request.user, page=page)
            invite.delete()

            if page.num_mods >= 50:
                return HttpResponseBadRequest("Page has too many moderators already")
            else:
                if page.num_mods >= 49:
                    ModeratorInvite.objects.filter(page=page).delete()

                page.moderators.add(request.user)

                page.num_mods = F("num_mods") + 1
                page.save(update_fields=["num_mods"])

                # Send some data back for client to use
                return Response({
                    "dname": page.display_name,
                    "private": page.private
                })

        return HttpResponseBadRequest()


    def delete(self, request, name):
        """ For users deleting invite to moderate for a page """

        ModeratorInvite.objects.filter(invitee=request.user, page__name=name).delete()

        return HttpResponse(status=204)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def stop_moderating(self, request, name):
    """ For moderator to leave and stop being a moderator """
    """ name is page name """

    page = get_object_or_404(Page.objects.only("id"), moderators=request.user, name=name)
    page.moderators.remove(request.user)

    return HttpResponse(status=204)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def remove_meme(request, uuid):
    meme = get_object_or_404(
        Meme.objects.select_related("page").only(
            "user",
            "page_private",
            "page_name",
            "page_display_name",
            "page__admin_id",
            "page__num_posts"
        ),
        uuid=uuid
    )

    if not meme.page:
        return HttpResponseBadRequest()

    # Admin can remove all memes, mods can remove all memes except admin's
    if (request.user.id == meme.page.admin_id
            or meme.page.moderators.filter(id=request.user.id).exists() and meme.user_id != meme.page.admin_id):

        # Subtract one from total number of posts on page
        meme.page.num_posts = F("num_posts") - 1
        meme.page.save(update_fields=["num_posts"])

        # Remove page data
        meme.page = None
        meme.page_private = False
        meme.page_name = ""
        meme.page_display_name = ""
        meme.save(update_fields=("page", "page_private", "page_name", "page_display_name"))

        # Restore comments removed by moderator of page
        meme.comments.filter(deleted=2).update(deleted=0)

        return HttpResponse(status=204)

    if meme.user_id == meme.page.admin_id:
        return HttpResponse("Cannot remove admin's memes", status=403)

    return HttpResponseBadRequest()


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_comment(request, uuid):
    comment = get_object_or_404(
        Comment.objects.select_related("meme__page").only(
            "user",
            "meme__page__admin_id"
        ),
        uuid=uuid
    )

    if not comment.meme.page:
        return HttpResponseBadRequest()

    # ID of admin of page of meme that comment is posted on
    page_admin_id = comment.meme.page.admin_id

    # Admin can remove all comments, mods can remove all comments except admin's
    if (request.user.id == page_admin_id
            or (comment.meme.page.moderators.filter(id=request.user.id).exists() and comment.user_id != page_admin_id)):

        # Set comment deleted to "Removed by moderator"
        comment.deleted = 2
        comment.save(update_fields=["deleted"])

        return HttpResponse(status=204)

    if comment.user_id == page_admin_id:
        return HttpResponse("Cannot remove admin's comments", status=403)

    return HttpResponseBadRequest()
