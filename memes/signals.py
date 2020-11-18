from django.db.models.signals import post_save, m2m_changed, pre_delete
from django.dispatch import receiver
from .models import Meme, MemeLike, CommentLike, Comment, User, Page, Profile
from notifications.models import Notification
from notifications.signals import (
    meme_voted_signal,
    comment_voted_signal,
    comment_posted_signal,
    follow_user_signal,
    subscribe_page_signal
)
from django.db.models import F
from django.utils import timezone


@receiver(post_save, sender=User)
def register_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=Meme)
def upload_meme(sender, instance, created, **kwargs):
    if created:
        Profile.objects.filter(user_id=instance.user_id).update(num_memes=F("num_memes") + 1)
        instance.resize_file()

        if instance.page_id:
            Page.objects.filter(id=instance.page_id).update(num_posts=F("num_posts") + 1)


@receiver(pre_delete, sender=Meme)
def delete_meme(sender, instance, **kwargs):
    Profile.objects.filter(user_id=instance.user_id).update(num_memes=F("num_memes") - 1)

    if instance.page_id:
        Page.objects.filter(id=instance.page_id).update(num_posts=F("num_posts") - 1)


@receiver(post_save, sender=MemeLike)
def vote_meme(sender, instance, created, **kwargs):
    """
    Update fields when new vote is created or when vote is changed

    Scenarios: like created, dislike created, like changed to dislike, dislike changed to like
    """
    like_created = created and instance.point == 1
    if like_created:
        # Extra fields selected to use when creating notification
        meme = Meme.objects.select_related("user") \
                           .only("num_likes", "points", "uuid", "thumbnail", "user__id") \
                           .get(id=instance.meme_id)
        uid = meme.user.id
    else:
        # Select both num_likes and num_dislikes even if scenario is 'dislike created' (good enough)
        meme = Meme.objects.only("num_likes", "num_dislikes", "points", "user").get(id=instance.meme_id)
        uid = meme.user_id

    # Calculate point change
    change = instance.point if created else instance.point * 2

    new_points = meme.points + change    # Do this so no need to call .refresh_from_db()
    # Update points on meme
    meme.points = F("points") + change
    # Update num_likes and/or num_dislikes field on meme
    if instance.point == 1:
        # Set field to update
        field = "num_likes"
        # Update num_likes
        meme.num_likes = F("num_likes") + 1
        if not created:
            meme.num_dislikes = F("num_dislikes") - 1
    elif instance.point == -1:
        # Set field to update
        field = "num_dislikes"
        # Update num_dislikes
        meme.num_dislikes = F("num_dislikes") + 1
        if not created:
            meme.num_likes = F("num_likes") - 1

    meme.save(update_fields=(field, "points") if created else ("num_likes", "num_dislikes", "points"))

    # Update clout on user who posted that
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
    field = "num_likes" if instance.point == 1 else "num_dislikes"
    Meme.objects.filter(uuid=instance.meme_uuid) \
                .update(**{"points": F("points") - instance.point, field: F(field) - 1})
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

        # Update number of comments
        Meme.objects.filter(id=instance.meme_id).update(num_comments=F("num_comments") + 1)

        comment_posted_signal.send(sender=sender, instance=instance)


@receiver(m2m_changed, sender=User.followers.through)
def follow_user(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove"):
        change = 1 if action == "post_add" else -1
        Profile.objects.filter(user=instance).update(num_following=F("num_following") + change)

        for pk in kwargs["pk_set"]:
            Profile.objects.filter(user_id=pk).update(num_followers=F("num_followers") + change)
            follow_user_signal.send(sender=sender, instance=instance, action=action, pk=pk)
            break


@receiver(m2m_changed, sender=Page.subscribers.through)
def subscribe_page(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove"):
        change = 1 if action == "post_add" else -1
        Page.objects.filter(id=instance.id).update(num_subscribers=F("num_subscribers") + change)

        for pk in kwargs["pk_set"]:
            subscribe_page_signal.send(sender=sender, instance=instance, action=action, pk=pk)
            break


@receiver(m2m_changed, sender=Page.moderators.through)
def add_page_mod(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove"):
        change = 1 if action == "post_add" else -1
        Page.objects.filter(id=instance.id).update(num_mods=F("num_mods") + change)
