from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from .models import Notification
from memes.models import User, MemeLike, CommentLike
from django.db.models import F
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType


meme_voted_signal = Signal(providing_args=["instance", "meme", "points"])


@receiver(meme_voted_signal, sender=MemeLike)
def notify_meme_like(sender, instance, meme, points, **kwargs):
    # Notify for every like up to 10 likes, every 25 likes up to 100 likes, then every 100 likes
    if points < 11 or (points < 101 and points % 25 == 0) or points % 100 == 0:
        # Create message
        s = 's' if points > 2 else ''
        username = User.objects.values_list("username", flat=True).get(id=instance.user_id)
        message = f"{username} {f'and {points - 1} other{s} ' if points > 1 else ''}liked your meme"

        Notification.objects.update_or_create(
            action="liked",
            recipient=meme.user,
            link=f"/m/{meme.uuid}",
            image=meme.small_thumbnail.url,
            content_type=ContentType.objects.get_for_model(sender),
            object_id=instance.id,
            defaults={
                "seen": False,
                "message": message,
                "timestamp": timezone.now()
            }
        )


comment_voted_signal = Signal(providing_args=["instance", "comment", "points"])


@receiver(comment_voted_signal, sender=CommentLike)
def notify_comment_like(sender, instance, comment, points, **kwargs):
    # Update or create notification if vote is a like (not dislike), same as above ^
    if points < 11 or (points < 101 and points % 25 == 0) or points % 100 == 0:
        # Create message
        s = 's' if points > 2 else ''
        username = User.objects.values_list("username", flat=True).get(id=instance.user_id)
        message = f"{username} {f'and {points - 1} other{s} ' if points > 1 else ''}liked your comment"

        Notification.objects.update_or_create(
            action="liked",
            recipient=comment.user,
            link=f"/m/{comment.meme_uuid}",
            content_type=ContentType.objects.get_for_model(sender),
            object_id=instance.id,
            defaults={
                "seen": False,
                "message": message,
                "timestamp": timezone.now()
            }
        )
