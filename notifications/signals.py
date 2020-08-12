from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from .models import Notification
from memes.models import User, MemeLike, CommentLike, Comment, Meme, Page
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


comment_posted_signal = Signal(providing_args=["instance"])


@receiver(comment_posted_signal, sender=Comment)
def notify_comment(sender, instance, **kwargs):
    # If instance is a reply
    if instance.reply_to_id:
        # Update number of replies
        Comment.objects.filter(id=instance.reply_to_id).update(num_replies=F("num_replies") + 1)

        reply_to = Comment.objects.select_related("user").only("num_replies", "user__id").get(id=instance.reply_to_id)
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
        meme = Meme.objects.select_related("user").only("user__id", "small_thumbnail").get(id=instance.meme_id)
        if meme.user.id != instance.user_id:
            actor = User.objects.only("username").get(id=instance.user_id)
            Notification.objects.create(
                actor=actor,
                action="commented",
                recipient=meme.user,
                link=f"/m/{instance.meme_uuid}",
                image=meme.small_thumbnail.url,
                message=f"{actor.username} commented on your meme",
                content_object=meme
            )


follow_user_signal = Signal(providing_args=["instance", "action"])


@receiver(follow_user_signal, sender=User.followers.through)
def notify_follow(sender, instance, action, **kwargs):
    if action == "post_add":
        Notification.objects.create(
            actor=instance,
            action="followed",
            recipient=kwargs["followed_user"],
            link=f"/user/{instance.username}",
            image=instance.image.url if instance.image else "",
            message=f"{instance.username} followed you",
            content_object=kwargs["followed_user"]
        )
    elif action == "post_remove":
        Notification.objects.filter(
            actor=instance,
            action="followed",
            recipient_id=kwargs["recipient_id"]
        ).delete()


subscribe_page_signal = Signal(providing_args=["instance", "action"])


@receiver(subscribe_page_signal, sender=Page.subscribers.through)
def notify_subscribe(sender, instance, action, **kwargs):
    if action == "post_add":
        new_sub = User.objects.only("username", "image").get(id=kwargs["new_sub_pk"])
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
            actor_id=kwargs["actor_pk"],
            action="subscribed",
            recipient_id=instance.admin_id,
            object_id=instance.id
        ).delete()
