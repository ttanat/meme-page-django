from django.urls import path

from . import views

urlpatterns = [
    path("meme", views.MemeReport.as_view(), name="meme"),
]
