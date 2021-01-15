from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views
from .api import api_auth, api_profile, api_page, api_moderators, api_settings

urlpatterns = [
    # Authentication
    path("auth/user/", api_auth.user_session, name="user_session"),
    path("register", api_auth.register, name="register"),
    # path("logout", api_auth.logout_view, name="logout"),

    path("m/<str:uuid>", views.meme_view, name="meme_view"),
    path("full_res/<str:obj>/<str:uuid>", views.full_res, name="full_res"),

    path("like", views.like, name="like"),
    path("comment/<str:action>", views.comment, name="comment"),
    path("reply", views.reply, name="reply"),
    path("upload", views.upload, name="upload"),

    # Profile
    path("profile", api_profile.profile),
    path("user/<str:username>", api_profile.user_page),
    # Follow/unfollow user
    path("follow/<str:username>", api_profile.follow, name="follow"),
    # Followers and following in profile page
    path("profile/followers/", api_profile.get_followers),
    path("profile/following/", api_profile.get_following),
    # Remove follower
    path("remove_follower/<str:username>", api_profile.remove_follower),

    # Update profile bio or page description
    path("update/<str:field>", views.update, name="update"),

    # Page
    path("page/<str:name>", api_page.page, name="page"),
    path("subscribe/<str:name>", api_page.subscribe, name="subscribe"),
    path("subscribe_request/<str:name>", api_page.HandleSubscribeRequest.as_view(), name="subscribe_request"),
    # Invite links for private pages
    path("invite/for-mods/<str:identifier>", api_page.HandleInviteLinkMods.as_view(), name="admin_invite"),
    path("invite/<str:uuid>", api_page.HandleInviteLinkUser.as_view(), name="invite"),
    # Create new page
    path("new_page", api_page.new_page, name="new_page"),
    # Moderators
    path("mods/invite/<str:name>", api_moderators.invite_moderators, name="invite_moderators"),
    path("mods/pending/<str:name>", api_moderators.PendingModeratorsAdmin.as_view(), name="pending_moderators"),
    path("mods/current/<str:name>", api_moderators.CurrentModerators.as_view(), name="current_moderators"),
    path("mods/get_mods/<str:name>", api_moderators.get_moderators, name="get_moderators"),
    path("mods/handle_invite", api_moderators.HandleModeratorInvite.as_view(), name="get_invite_moderators"),
    path("mods/handle_invite/<str:name>", api_moderators.HandleModeratorInvite.as_view(), name="handle_invite_moderators"),
    path("mods/leave/<str:name>", api_moderators.stop_moderating, name="leave_moderators"),
    # Remove meme from page
    path("mods/remove/meme/<str:uuid>", api_moderators.remove_meme, name="remove_meme"),
    # Remove comment
    path("mods/remove/comment/<str:uuid>", api_moderators.remove_comment, name="remove_comment"),

    # Settings
    path("settings", api_settings.user_settings, name="settings"),
    path("page/<str:name>/settings", api_settings.PageSettings.as_view(), name="page_settings"),

    # Delete stuff
    path("delete/<str:model>", views.delete, name="delete"),
    path("delete/<str:model>/<str:identifier>", views.delete, name="delete"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
