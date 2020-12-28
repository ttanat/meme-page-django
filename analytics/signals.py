from django.dispatch import receiver, Signal
from django.db.models import F

from .models import View
from memes.models import Meme


meme_viewed_signal = Signal(providing_args=["user", "meme"])


@receiver(meme_viewed_signal, sender=Meme)
def add_meme_view(sender, user, meme, **kwargs):
    meme.num_views = F("num_views") + 1
    meme.save(update_fields=["num_views"])

    View.objects.create(user=user if user.is_authenticated else None, content_object=meme)
