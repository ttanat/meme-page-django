from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views
from .api import api_auth, api_notifications, api_profile, api_page, api_moderators, api_settings

urlpatterns = [
    # Authentication
    path("api/auth/user/", api_auth.user_session, name="user_session"),
    path("api/register", api_auth.register, name="register"),
    # path("logout", api_auth.logout_view, name="logout"),

    # Notifications
    path("api/notifications/nav", api_notifications.nav_notifications, name="nav_notifications"),
    path("api/notifications", api_notifications.notifications, name="notifications"),

    path("api/m/<str:uuid>", views.meme_view, name="meme_view"),
    path("api/full_res/<str:obj>/<str:uuid>", views.full_res, name="full_res"),
    path("api/random", views.random, name="random"),

    path("api/likes/<str:obj>/", views.get_likes, name="get_likes"),
    path("api/like", views.like, name="like"),
    path("api/comment/<str:action>", views.comment, name="comment"),
    path("api/reply", views.reply, name="reply"),
    path("api/upload", views.upload, name="upload"),

    # Profile
    path("api/profile", api_profile.profile),
    path("api/user/<str:username>", api_profile.user_page),

    # Follow/unfollow user
    path("api/follow/<str:username>", views.follow, name="follow"),
    # Update profile bio or page description
    path("api/update/<str:field>", views.update, name="update"),

    # Page
    path("api/page/<str:name>", api_page.page, name="page"),
    path("api/subscribe/<str:name>", api_page.subscribe, name="subscribe"),
    path("api/subscribe_request/<str:name>", api_page.HandleSubscribeRequest.as_view(), name="subscribe_request"),
    # Invite links for private pages
    path("api/invite/admin/<str:identifier>", api_page.HandleInviteLinkAdmin.as_view(), name="admin_invite"),
    path("api/invite/<str:uuid>", api_page.HandleInviteLinkUser.as_view(), name="invite"),
    # Create new page
    path("api/new_page", api_page.new_page, name="new_page"),
    # Moderators
    path("api/mods/invite/<str:name>", api_moderators.invite_moderators, name="invite_moderators"),
    path("api/mods/pending/<str:name>", api_moderators.PendingModeratorsAdmin.as_view(), name="pending_moderators"),
    path("api/mods/current/<str:name>", api_moderators.CurrentModerators.as_view(), name="current_moderators"),
    path("api/mods/handle_invite/<str:name>", api_moderators.HandleModeratorInvite.as_view(), name="handle_invite_moderators"),
    path("api/mods/leave/<str:name>", api_moderators.stop_moderating, name="leave_moderators"),

    # Settings
    path("api/settings", api_settings.user_settings, name="settings"),
    path("api/page/<str:name>/settings", api_settings.PageSettings.as_view(), name="page_settings"),

    # Delete stuff
    path("api/delete/<str:model>", views.delete, name="delete"),
    path("api/delete/<str:model>/<str:identifier>", views.delete, name="delete"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
