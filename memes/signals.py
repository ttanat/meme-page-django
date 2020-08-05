from django.db.models.signals import post_save, m2m_changed, pre_delete
from django.dispatch import receiver
from .models import Meme, MemeLike, CommentLike, Comment, User, Page, Profile
from notifications.models import Notification
from notifications.signals import meme_voted_signal, comment_voted_signal
from django.db.models import F
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType


@receiver(post_save, sender=User)
def register_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=Meme)
def upload_meme(sender, instance, created, **kwargs):
    if created:
        instance.resize_file()
        Profile.objects.filter(user_id=instance.user_id).update(num_memes=F("num_memes") + 1)

        if instance.page_id:
            Page.objects.filter(id=instance.page_id).update(num_posts=F("num_posts") + 1)


@receiver(pre_delete, sender=Meme)
def delete_meme(sender, instance, **kwargs):
    Profile.objects.filter(user_id=instance.user_id).update(num_memes=F("num_memes") - 1)

    if instance.page_id:
        Page.objects.filter(id=instance.page_id).update(num_posts=F("num_posts") - 1)


@receiver(post_save, sender=MemeLike)
def vote_meme(sender, instance, created, **kwargs):
    # Calculate point change
    change = instance.point if created else instance.point * 2

    like_created = created and instance.point == 1
    if like_created:
        # Extra fields selected to use when creating notification
        meme = Meme.objects.select_related("user") \
                           .only("points", "uuid", "small_thumbnail", "user__id") \
                           .get(id=instance.meme_id)
        uid = meme.user.id
    else:
        meme = Meme.objects.only("points", "user").get(id=instance.meme_id)
        uid = meme.user_id

    # Update points on meme and update clout on user who posted that
    new_points = meme.points + change    # Do this so no need to call .refresh_from_db()
    meme.points = F("points") + change
    meme.save(update_fields=["points"])
    Profile.objects.filter(user_id=uid).update(clout=F("clout") + change)

    # Notify if vote is a like and user is not liking their own meme
    if like_created and uid != instance.user_id:
        meme_voted_signal.send(sender=sender, instance=instance, meme=meme, points=new_points)


@receiver(post_save, sender=CommentLike)
def vote_comment(sender, instance, created, **kwargs):
    # Calculate point change
    change = instance.point if created else instance.point * 2

    like_created = created and instance.point == 1
    if like_created:
        comment = Comment.objects.select_related("user") \
                                 .only("points", "user__id", "meme_uuid") \
                                 .get(id=instance.comment_id)
        uid = comment.user.id
    else:
        comment = Comment.objects.only("points", "user").get(id=instance.comment_id)
        uid = comment.user_id

    # Update points on comment and update clout on user who posted that
    new_points = comment.points + change    # Do this so no need to call .refresh_from_db()
    comment.points = F("points") + change
    comment.save(update_fields=["points"])
    Profile.objects.filter(user_id=uid).update(clout=F("clout") + change)

    # Notify if vote is a like and user is not liking their own comment
    if like_created and uid != instance.user_id:
        comment_voted_signal.send(sender=sender, instance=instance, comment=comment, points=new_points)


@receiver(pre_delete, sender=MemeLike)
def unvote_meme(sender, instance, **kwargs):
    Meme.objects.filter(uuid=instance.meme_uuid).update(points=F("points") - instance.point)
    Profile.objects.filter(user_id=instance.meme.user_id).update(clout=F("clout") - instance.point)


@receiver(pre_delete, sender=CommentLike)
def unvote_comment(sender, instance, **kwargs):
    Comment.objects.filter(uuid=instance.comment_uuid).update(points=F("points") - instance.point)
    Profile.objects.filter(user_id=instance.comment.user_id).update(clout=F("clout") - instance.point)


@receiver(post_save, sender=Comment)
def comment_meme(sender, instance, created, **kwargs):
    if created:
        if instance.image:
            instance.resize_image()

        is_reply = not not instance.reply_to_id

        if is_reply:
            meme = Meme.objects.only("num_comments").get(id=instance.meme_id)
        else:
            meme = Meme.objects.select_related("user") \
                               .only("num_comments", "user__id", "small_thumbnail") \
                               .get(id=instance.meme_id)

        # Update number of comments
        meme.num_comments = F("num_comments") + 1
        meme.save(update_fields=["num_comments"])

        if is_reply:
            reply_to = Comment.objects.select_related("user").only("num_replies", "user__id").get(id=instance.reply_to_id)

            # Update number of replies
            reply_to.num_replies = F("num_replies") + 1
            reply_to.save(update_fields=["num_replies"])

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
        else:
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


@receiver(m2m_changed, sender=User.followers.through)
def follow_user(sender, instance, action, **kwargs):
    if action == "post_add":
        Profile.objects.filter(user=instance).update(num_following=F("num_following") + 1)

        for pk in kwargs["pk_set"]:
            followed_user = User.objects.only("id").get(id=pk)
            Profile.objects.filter(user=followed_user).update(num_followers=F("num_followers") + 1)
            Notification.objects.create(
                actor=instance,
                action="followed",
                recipient=followed_user,
                link=f"/user/{instance}",
                image=instance.image.url if instance.image else "",
                message=f"{instance} followed you",
                content_object=followed_user
            )
            break

    elif action == "post_remove":
        Profile.objects.filter(user=instance).update(num_following=F("num_following") - 1)

        for pk in kwargs["pk_set"]:
            Profile.objects.filter(user_id=pk).update(num_followers=F("num_followers") - 1)
            Notification.objects.filter(actor=instance, action="followed", recipient_id=pk).delete()
            break


@receiver(m2m_changed, sender=Page.subscribers.through)
def subscribe_page(sender, instance, action, **kwargs):
    if action == "post_add":
        instance.num_subscribers = F("num_subscribers") + 1
        instance.save(update_fields=["num_subscribers"])

        for pk in kwargs["pk_set"]:
            new_sub = User.objects.only("id", "image").get(id=pk)
            Notification.objects.create(
                actor=new_sub,
                action="subscribed",
                recipient=instance.admin,
                link=f"/user/{new_sub}",
                image=new_sub.image.url if new_sub.image else "",
                message=f"{new_sub} subscribed to {instance}",
                content_object=instance
            )
            break

    elif action == "post_remove":
        instance.num_subscribers = F("num_subscribers") - 1
        instance.save(update_fields=["num_subscribers"])

        for pk in kwargs["pk_set"]:
            Notification.objects.filter(
                actor_id=pk,
                action="subscribed",
                recipient_id=instance.admin_id,
                content_type=ContentType.objects.get_for_model(User),
                object_id=instance.id
            ).delete()
            break
