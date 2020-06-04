from django.db.models.signals import post_save, m2m_changed, pre_delete
from django.dispatch import receiver
from .models import Meme, Like, Comment, User, Page
from django.db.models import F
from notifications.signals import notify


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
    # Create notification if vote is like
    if created and instance.point == 1:
        if instance.meme:
            if instance.meme.user_id != instance.user_id:
                notify.send(
                    sender=instance.user,
                    recipient=instance.meme.user,
                    verb="liked",
                    action_object=instance.meme,
                    description=f"{instance.user.username} liked your meme",
                    link=f"/m/{instance.meme.uuid}",
                    public=False
                )
        elif instance.comment:
            if instance.comment.user_id != instance.user_id:
                notify.send(
                    sender=instance.user,
                    recipient=instance.comment.user,
                    verb="liked",
                    action_object=instance.comment,
                    description=f"{instance.user.username} liked your comment",
                    link=f"/m/{instance.comment.meme.uuid}",
                    public=False
                )

    # Calculate point change
    change = instance.point if created else instance.point * 2

    # Update points on meme/comment and update clout on user who posted that
    if instance.meme:
        instance.meme.points = F("points") + change
        instance.meme.save(update_fields=["points"])

        instance.meme.user.clout = F("clout") + change
        instance.meme.user.save(update_fields=["clout"])

    elif instance.comment:
        instance.comment.points = F("points") + change
        instance.comment.save(update_fields=["points"])

        instance.comment.user.clout = F("clout") + change
        instance.comment.user.save(update_fields=["clout"])


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
        if instance.reply_to:
            if instance.reply_to.user_id != instance.user_id:
                pass
                # Notification.objects.create(recipient=instance.reply_to.user, comment=instance)
        else:
            if instance.meme.user_id != instance.user_id:
                pass
                # Notification.objects.create(recipient=instance.meme.user, comment=instance)

        # Update number of comments
        instance.meme.num_comments = F("num_comments") + 1
        instance.meme.save(update_fields=["num_comments"])

        if instance.image:
            instance.resize_image()


@receiver(m2m_changed, sender=User.followers.through)
def follow_user(sender, instance, action, **kwargs):
    if action == "post_add":
        instance.num_following = F("num_following") + 1
        instance.save(update_fields=["num_following"])
        for pk in kwargs["pk_set"]:
            User.objects.filter(id=pk).update(num_followers=F("num_followers") + 1)
            # Notification.objects.get_or_create(recipient=User.objects.get(id=pk), follower=instance)
            break
    elif action == "post_remove":
        instance.num_following = F("num_following") - 1
        instance.save(update_fields=["num_following"])
        for pk in kwargs["pk_set"]:
            User.objects.filter(id=pk).update(num_followers=F("num_followers") - 1)
            # Notification.objects.filter(recipient=User.objects.get(id=pk), follower=instance).delete()
            break


@receiver(m2m_changed, sender=Page.subscribers.through)
def subscribe_page(sender, instance, action, **kwargs):
    if action == "post_add":
        instance.num_subscribers = F("num_subscribers") + 1
        instance.save(update_fields=["num_subscribers"])
        # for pk in kwargs["pk_set"]:
        #     Notification.objects.get_or_create(recipient=instance.admin, subscriber=kwargs["model"].objects.get(id=pk), page=instance)
        #     break
    elif action == "post_remove":
        instance.num_subscribers = F("num_subscribers") - 1
        instance.save(update_fields=["num_subscribers"])
        # for pk in kwargs["pk_set"]:
        #     break
