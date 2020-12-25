from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from .models import Notification
from memes.models import User, MemeLike, CommentLike, Comment, Meme, Page
from django.db.models import F
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType


"""
This file (and probably other signals.py files too) is evaluated twice
on first server startup using "python manage.py runserver"
so get_for_model is called twice for each model
"""


meme_voted_signal = Signal(providing_args=["instance", "meme", "points"])
memelike_content_type = ContentType.objects.get_for_model(MemeLike)


@receiver(meme_voted_signal, sender=MemeLike)
def notify_meme_like(sender, instance, meme, points, **kwargs):
    # Notify for every like up to 10 likes, every 25 likes up to 100 likes, then every 100 likes
    if points < 11 or (points < 101 and points % 25 == 0) or points % 100 == 0:
        # Create message
        s = 's' if points > 2 else ''
        username = User.objects.values_list("username", flat=True).get(id=instance.user_id)
        message = f"{username} {f'and {points - 1} other{s} ' if points > 1 else ''}liked your meme"

        Notification.objects.update_or_create(
            recipient=meme.user,
            link=f"/m/{meme.uuid}",
            content_type=memelike_content_type,
            defaults={
                "action": "liked",  # Faster to update to same value than compare when finding in db
                "image": meme.thumbnail.url,  # Faster to update to same value than compare when finding in db
                "seen": False,
                "message": message,
                "timestamp": timezone.now(),
                "object_id": instance.id,
            }
        )


comment_voted_signal = Signal(providing_args=["instance", "comment", "points"])
commentlike_content_type = ContentType.objects.get_for_model(CommentLike)


@receiver(comment_voted_signal, sender=CommentLike)
def notify_comment_like(sender, instance, comment, points, **kwargs):
    # Update or create notification if vote is a like (not dislike), same as above ^
    if points < 11 or (points < 101 and points % 25 == 0) or points % 100 == 0:
        # Create message
        s = 's' if points > 2 else ''
        username = User.objects.values_list("username", flat=True).get(id=instance.user_id)
        message = f"{username} {f'and {points - 1} other{s} ' if points > 1 else ''}liked your comment"

        # Will combine number of likes for all of user's comments on same meme
        Notification.objects.update_or_create(
            recipient=comment.user,
            link=f"/m/{comment.meme_uuid}",
            content_type=commentlike_content_type,
            defaults={
                "action": "liked",  # Faster to update to same value than compare when finding in db
                "seen": False,
                "message": message,
                "timestamp": timezone.now(),
                "object_id": instance.id,
            }
        )


comment_posted_signal = Signal(providing_args=["instance"])


@receiver(comment_posted_signal, sender=Comment)
def notify_comment(sender, instance, **kwargs):
    # If instance is a reply
    if instance.root_id:
        # Update number of replies on root comment
        Comment.objects.filter(id=instance.root_id).update(num_replies=F("num_replies") + 1)

        # Get comment that was directly replied to
        reply_to = Comment.objects.select_related("user").only("num_replies", "user__id").get(id=instance.reply_to_id)
        # Get user who posted reply
        actor = User.objects.only("image", "username").get(id=instance.user_id)
        if reply_to.user.id != instance.user_id:
            Notification.objects.create(
                actor=actor,
                action="replied",
                recipient=reply_to.user,
                link=f"/m/{instance.meme_uuid}",
                image=actor.image.url if actor.image else "",
                message=f"{actor.username} replied to your comment",
                content_object=reply_to
            )
    # If instance is a top level comment
    else:
        meme = Meme.objects.select_related("user").only("user__id", "thumbnail").get(id=instance.meme_id)
        if meme.user.id != instance.user_id:
            actor = User.objects.only("username").get(id=instance.user_id)
            Notification.objects.create(
                actor=actor,
                action="commented",
                recipient=meme.user,
                link=f"/m/{instance.meme_uuid}",
                image=meme.thumbnail.url,
                message=f"{actor.username} commented on your meme",
                content_object=meme
            )


follow_user_signal = Signal(providing_args=["instance", "action", "pk"])


@receiver(follow_user_signal, sender=User.followers.through)
def notify_follow(sender, instance, action, pk, **kwargs):
    if action == "post_add":
        followed_user = User.objects.only("id").get(id=pk)
        Notification.objects.create(
            actor=instance,
            action="followed",
            recipient=followed_user,
            link=f"/user/{instance.username}",
            image=instance.image.url if instance.image else "",
            message=f"{instance.username} followed you",
            content_object=followed_user
        )
    elif action == "post_remove":
        Notification.objects.filter(
            actor=instance,
            action="followed",
            recipient_id=pk
        ).delete()


subscribe_page_signal = Signal(providing_args=["instance", "action", "pk"])


@receiver(subscribe_page_signal, sender=Page.subscribers.through)
def notify_subscribe(sender, instance, action, pk, **kwargs):
    if action == "post_add":
        new_sub = User.objects.only("username", "image").get(id=pk)
        page_admin = User.objects.only("id").get(id=instance.admin_id)
        Notification.objects.create(
            actor=new_sub,
            action="subscribed",
            recipient=page_admin,
            link=f"/user/{new_sub.username}",
            image=new_sub.image.url if new_sub.image else "",
            message=f"{new_sub.username} subscribed to {instance.name}",
            content_object=instance
        )
    elif action == "post_remove":
        Notification.objects.filter(
            actor_id=pk,
            action="subscribed",
            recipient_id=instance.admin_id,
            object_id=instance.id
        ).delete()
