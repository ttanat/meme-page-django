from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views, api_profile

urlpatterns = [
    path("api/auth/user/", views.user_session, name="user_session"),
    path("api/m/<str:uuid>", views.meme_view, name="meme_view"),
    path("api/full_res/<str:obj>/<str:uuid>", views.full_res, name="full_res"),
    path("api/random", views.random, name="random"),

    path("api/likes/<str:obj>/", views.get_likes, name="get_likes"),
    path("api/like", views.like, name="like"),
    path("api/comment/<str:action>", views.comment, name="comment"),
    path("api/reply", views.reply, name="reply"),
    path("api/upload", views.upload, name="upload"),

    path("notifications", views.notifications, name="notifications"),

    path("api/page/<str:name>", views.page, name="page"),
    path("api/page/settings/<str:name>", views.page_settings, name="page_settings"),

    path("api/follow/<str:username>", views.follow, name="follow"),
    path("api/subscribe/<str:name>", views.subscribe, name="subscribe"),
    path("api/new_page", views.new_page, name="new_page"),
    path("api/update/<str:field>", views.update, name="update"),

    path("api/profile", api_profile.profile),
    path("api/user/<str:username>", api_profile.user_page),

    # path("logout", views.logout_view, name="logout"),
    path("api/register", views.register, name="register"),
    path("api/settings", views.user_settings, name="settings"),

    path("api/delete/<str:model>", views.delete, name="delete"),
    path("api/delete/<str:model>/<str:identifier>", views.delete, name="delete"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


    # path("something", SomethingDetailView.as_view(), name="something")