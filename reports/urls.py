from django.urls import path

from . import views

urlpatterns = [
    path("", views.create_report, name="create"),
    path("meme", views.MemeReport.as_view(), name="meme"),
    path("memes", views.get_num_meme_reports, name="num_meme_reports"),
]
