from django.dispatch import receiver, Signal
from django.db import transaction
from django.db.models import F
from django.core.signals import request_finished

from .models import View, TagUse
from memes.models import Meme


meme_viewed_signal = Signal(providing_args=["user", "meme"])


@receiver(meme_viewed_signal, sender=Meme)
def add_meme_view(sender, user, meme, **kwargs):
    meme.num_views = F("num_views") + 1
    meme.save(update_fields=["num_views"])

    View.objects.create(user=user if user.is_authenticated else None, content_object=meme)


upload_signal = Signal(providing_args=["instance", "tags"])


@receiver(upload_signal, sender=Meme)
def add_tags_use(sender, instance, tags: list, **kwargs):
    # Limit 20 tags
    tags = tags[:20]
    # Create dictionary for easier usage
    d = {t.lower(): t for t in tags}
    # Create data for tags
    TagUse.objects.bulk_create(
        [TagUse(lower_name=t, day=instance.upload_date) for t in d.keys()],
        ignore_conflicts=True
    )

    # Get data for tags
    taguses = TagUse.objects.select_for_update().filter(lower_name__in=list(d.keys()), day=instance.upload_date)

    with transaction.atomic():
        for taguse in taguses:
            # Increment count for tag (case-insensitive, in count column)
            taguse.count = F("count") + 1

            # Increment count for tag (case-sensitive, in JSON field)
            variant = d[taguse.lower_name]
            if variant in taguse.variants:
                taguse.variants[variant] += 1
            else:
                taguse.variants[variant] = 1

        TagUse.objects.bulk_update(taguses, ["count", "variants"])
