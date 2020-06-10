from django.db.models.signals import post_save, m2m_changed, pre_delete
from django.dispatch import receiver
from .models import Meme, Like, Comment, User, Page, Notification
from django.db.models import F
# from notifications.signals import notify
from django.utils import timezone


@receiver(post_save, sender=Meme)
def upload_meme(sender, instance, created, **kwargs):
    if created:
        instance.resize_file()
        instance.user.num_memes = F("num_memes") + 1
        instance.user.save(update_fields=["num_memes"])

        if instance.page:
            instance.page.num_posts = F("num_posts") + 1
            instance.page.save(update_fields=["num_posts"])


@receiver(pre_delete, sender=Meme)
def delete_meme(sender, instance, **kwargs):
    instance.user.num_memes = F("num_memes") - 1
    instance.user.save(update_fields=["num_memes"])

    if instance.page:
        instance.page.num_posts = F("num_posts") - 1
        instance.page.save(update_fields=["num_posts"])


@receiver(post_save, sender=Like)
def vote(sender, instance, created, **kwargs):
    # Calculate point change
    change = instance.point if created else instance.point * 2

    # Update points on meme/comment and update clout on user who posted that
    if instance.meme:
        new_points = instance.meme.points + change    # Do this so no need to call .refresh_from_db()

        instance.meme.points = F("points") + change
        instance.meme.save(update_fields=["points"])

        instance.meme.user.clout = F("clout") + change
        instance.meme.user.save(update_fields=["clout"])

    elif instance.comment:
        new_points = instance.comment.points + change    # Do this so no need to call .refresh_from_db()

        instance.comment.points = F("points") + change
        instance.comment.save(update_fields=["points"])

        instance.comment.user.clout = F("clout") + change
        instance.comment.user.save(update_fields=["clout"])

    # Update or create notification if vote is a like (not dislike)
    if created and instance.point == 1:
        if instance.meme and instance.meme.user_id != instance.user_id:
            if new_points < 11 or (new_points < 101 and new_points % 25 == 0) or new_points % 100 == 0:
                s = 's' if new_points > 2 else ''
                message = f"{instance.user} {f'and {new_points - 1} other{s} ' if new_points > 1 else ''}liked your meme"

                Notification.objects.update_or_create(
                    action="liked",
                    recipient=instance.meme.user,
                    link=f"/m/{instance.meme.uuid}",
                    image=instance.meme.small_thumbnail.url,
                    target_meme=instance.meme,
                    defaults={
                        "seen": False,
                        "message": message,
                        "timestamp": timezone.now()
                    }
                )

        elif instance.comment and instance.comment.user_id != instance.user_id:
            if new_points < 11 or (new_points < 101 and new_points % 25 == 0) or new_points % 100 == 0:
                    s = 's' if new_points > 2 else ''
                    message = f"{instance.user} {f'and {new_points - 1} other{s} ' if new_points > 1 else ''}liked your comment"

                    Notification.objects.update_or_create(
                        action="liked",
                        recipient=instance.comment.user,
                        link=f"/m/{instance.comment.meme.uuid}",
                        target_comment=instance.comment,
                        defaults={
                            "seen": False,
                            "message": message,
                            "timestamp": timezone.now()
                        }
                    )


@receiver(pre_delete, sender=Like)
def unvote(sender, instance, **kwargs):
    if instance.meme:
        instance.meme.points = F("points") - instance.point
        instance.meme.save(update_fields=["points"])

        instance.meme.user.clout = F("clout") - instance.point
        instance.meme.user.save(update_fields=["clout"])

    elif instance.comment:
        instance.comment.points = F("points") - instance.point
        instance.comment.save(update_fields=["points"])

        instance.comment.user.clout = F("clout") - instance.point
        instance.comment.user.save(update_fields=["clout"])


@receiver(post_save, sender=Comment)
def comment_meme(sender, instance, created, **kwargs):
    if created:
        if instance.image:
            instance.resize_image()

        # Update number of comments
        instance.meme.num_comments = F("num_comments") + 1
        instance.meme.save(update_fields=["num_comments"])

        if instance.reply_to:
            if instance.reply_to.user_id != instance.user_id:
                Notification.objects.create(
                    actor=instance.user,
                    action="replied",
                    recipient=instance.comment.reply_to.user,
                    link=f"/m/{instance.comment.meme.uuid}",
                    image=instance.user.image.url if instance.user.image else "",
                    message=f"{instance.user} replied to your comment",
                    target_comment=instance.comment
                )
        else:
            if instance.meme.user_id != instance.user_id:
                Notification.objects.create(
                    actor=instance.user,
                    action="commented",
                    recipient=instance.comment.meme.user,
                    link=f"/m/{instance.comment.meme.uuid}",
                    image=instance.user.image.url if instance.user.image else "",
                    message=f"{instance.user} commented on your meme",
                    target_comment=instance.comment
                )


@receiver(m2m_changed, sender=User.followers.through)
def follow_user(sender, instance, action, **kwargs):
    if action == "post_add":
        instance.num_following = F("num_following") + 1
        instance.save(update_fields=["num_following"])

        for pk in kwargs["pk_set"]:
            followed_user = User.objects.only("num_followers").get(id=pk)
            followed_user.num_followers = F("num_followers") + 1
            followed_user.save(update_fields=["num_followers"])

            Notification.objects.create(
                actor=instance,
                action="followed",
                recipient=followed_user,
                link=f"/user/{instance}",
                image=instance.image.url if instance.image else "",
                message=f"{instance} followed you"
            )

            break

    elif action == "post_remove":
        instance.num_following = F("num_following") - 1
        instance.save(update_fields=["num_following"])

        for pk in kwargs["pk_set"]:
            unfollowed_user = User.objects.only("num_followers").get(id=pk)
            unfollowed_user.num_followers = F("num_followers") - 1
            unfollowed_user.save(update_fields=["num_followers"])

            Notification.objects.filter(
                actor=instance,
                action="followed",
                recipient=unfollowed_user
            ).delete()

            break


@receiver(m2m_changed, sender=Page.subscribers.through)
def subscribe_page(sender, instance, action, **kwargs):
    if action == "post_add":
        instance.num_subscribers = F("num_subscribers") + 1
        instance.save(update_fields=["num_subscribers"])

        for pk in kwargs["pk_set"]:
            new_sub = User.objects.only("id").get(id=pk)
            Notification.objects.create(
                actor=new_sub,
                action="subscribed",
                recipient=instance.admin,
                link=f"/user/{new_sub}",
                image=new_sub.image.url if new_sub.image else "",
                message=f"{new_sub} subscribed to {instance}",
                target_page=instance
            )

            break

    elif action == "post_remove":
        instance.num_subscribers = F("num_subscribers") - 1
        instance.save(update_fields=["num_subscribers"])

        for pk in kwargs["pk_set"]:
            old_sub = User.objects.only("id").get(id=pk)
            Notification.objects.filter(
                actor=old_sub,
                action="subscribed",
                recipient_id=instance.admin_id,
                target_page=instance
            ).delete()

            break
