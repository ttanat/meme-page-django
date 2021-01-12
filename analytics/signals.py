from django.dispatch import receiver, Signal
from django.db.models import F

from .models import View
from memes.models import Meme, Profile, Page


meme_viewed_signal = Signal(providing_args=["user", "meme"])


@receiver(meme_viewed_signal, sender=Meme)
def add_meme_view(sender, user, meme, **kwargs):
    meme.num_views = F("num_views") + 1
    meme.save(update_fields=["num_views"])

    View.objects.create(user=user if user.is_authenticated else None, content_object=meme)


profile_view_signal = Signal(providing_args=["user", "profile"])


@receiver(profile_view_signal, sender=Profile)
def add_profile_view(sender, user, profile, **kwargs):
    profile.num_views = F("num_views") + 1
    profile.save(update_fields=["num_views"])

    View.objects.create(user=user if user.is_authenticated else None, content_object=profile)


page_view_signal = Signal(providing_args=["user", "page"])


@receiver(page_view_signal, sender=Page)
def add_page_view(sender, user, page, **kwargs):
    page.num_views = F("num_views") + 1
    page.save(update_fields=["num_views"])

    View.objects.create(user=user if user.is_authenticated else None, content_object=page)
