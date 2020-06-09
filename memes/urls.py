from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views
from .api import api_profile, api_page, api_settings

urlpatterns = [
    path("api/auth/user/", views.user_session, name="user_session"),

    path("api/notifications/nav", views.nav_notifications, name="nav_notifications"),
    path("api/notifications", views.notifications, name="notifications"),

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
    path("api/subscribe_request/<str:name>", api_page.subscribe_request, name="subscribe_request"),
    path("api/new_page", api_page.new_page, name="new_page"),

    path("api/register", views.register, name="register"),
    # path("logout", views.logout_view, name="logout"),

    # Settings
    path("api/settings", api_settings.user_settings, name="settings"),
    path("api/page/<str:name>/settings", api_settings.PageSettings.as_view(), name="page_settings"),

    # Delete stuff
    path("api/delete/<str:model>", views.delete, name="delete"),
    path("api/delete/<str:model>/<str:identifier>", views.delete, name="delete"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
