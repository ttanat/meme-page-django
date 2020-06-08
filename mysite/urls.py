"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from memes import api_views
from memes.api import api_profile
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
import notifications.urls

router = routers.DefaultRouter()
router.register("memes/pv", api_views.PrivateMemeViewSet, basename="Meme")
router.register("memes", api_views.MemeViewSet, basename="Meme")

router.register("comments", api_views.CommentFullViewSet, basename="Comment")
router.register("replies", api_views.ReplyViewSet, basename="Comment")

router.register("search/users", api_views.SearchUserViewSet)
router.register("search/pages", api_views.SearchPageViewSet)

router.register("profile/memes", api_profile.ProfileMemesViewSet, basename="Meme")
router.register("user_page/memes", api_profile.UserMemesViewSet, basename="Meme")
router.register("profile/likes", api_profile.ProfileLikesViewSet, basename="Meme")
router.register("profile/comments", api_profile.ProfileCommentsViewSet, basename="Comment")

router.register("notifications", api_views.NotificationViewSet, basename="Notification")

urlpatterns = [
    path("", include("memes.urls")),
    path('admin/', admin.site.urls),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(notifications.urls, namespace='notifications')),
]
