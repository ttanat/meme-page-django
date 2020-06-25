# Generated by Django 3.0 on 2020-06-25 17:08

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import memes.models.core
import memes.models.page


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('num_memes', models.PositiveIntegerField(default=0)),
                ('clout', models.IntegerField(default=0)),
                ('bio', models.CharField(blank=True, max_length=64)),
                ('num_followers', models.PositiveIntegerField(default=0)),
                ('num_following', models.PositiveIntegerField(default=0)),
                ('image', models.ImageField(blank=True, null=True, upload_to=memes.models.core.user_directory_path_profile)),
                ('nsfw', models.BooleanField(default=False)),
                ('show_nsfw', models.BooleanField(default=False)),
                ('private', models.BooleanField(default=False)),
                ('follows', models.ManyToManyField(related_name='followers', to=settings.AUTH_USER_MODEL)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(blank=True, max_length=150)),
                ('uuid', models.CharField(default=memes.models.core.set_uuid, max_length=11, unique=True)),
                ('points', models.IntegerField(default=0)),
                ('num_replies', models.PositiveIntegerField(default=0)),
                ('post_date', models.DateTimeField(auto_now_add=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to=memes.models.core.user_directory_path_comments)),
                ('edited', models.BooleanField(default=False)),
                ('deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Meme',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=memes.models.core.user_directory_path)),
                ('uuid', models.CharField(default=memes.models.core.set_uuid, max_length=11, unique=True)),
                ('thumbnail', models.FileField(blank=True, null=True, upload_to=memes.models.core.user_directory_path_thumbnails)),
                ('small_thumbnail', models.FileField(blank=True, null=True, upload_to=memes.models.core.user_directory_path_small_thumbnails)),
                ('dank', models.BooleanField(default=False)),
                ('caption', models.CharField(blank=True, max_length=100)),
                ('caption_embedded', models.BooleanField(default=False)),
                ('content_type', models.CharField(max_length=64)),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('points', models.IntegerField(default=0)),
                ('num_comments', models.PositiveIntegerField(default=0)),
                ('nsfw', models.BooleanField(default=False)),
                ('ip_address', models.GenericIPAddressField(null=True)),
                ('hidden', models.BooleanField(default=False)),
                ('num_views', models.PositiveIntegerField(default=0)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='memes.Category')),
            ],
            options={
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='Moderator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=32, unique=True)),
                ('display_name', models.CharField(blank=True, max_length=32)),
                ('image', models.ImageField(blank=True, null=True, upload_to=memes.models.page.page_directory_path)),
                ('cover', models.ImageField(blank=True, null=True, upload_to=memes.models.page.page_directory_path)),
                ('description', models.CharField(blank=True, default='', max_length=300)),
                ('nsfw', models.BooleanField(default=False)),
                ('private', models.BooleanField(default=False)),
                ('permissions', models.BooleanField(default=True)),
                ('num_mods', models.PositiveSmallIntegerField(default=0)),
                ('num_subscribers', models.PositiveIntegerField(default=0)),
                ('num_posts', models.PositiveIntegerField(default=0)),
                ('admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('moderators', models.ManyToManyField(related_name='moderating', through='memes.Moderator', to=settings.AUTH_USER_MODEL)),
                ('subscribers', models.ManyToManyField(related_name='subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='SubscribeRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.Page')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=32)),
                ('link', models.URLField(max_length=64)),
                ('seen', models.BooleanField(default=False)),
                ('image', models.URLField(blank=True, default='', max_length=128)),
                ('message', models.CharField(blank=True, max_length=128)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
                ('target_comment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='memes.Comment')),
                ('target_meme', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='memes.Meme')),
                ('target_page', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='memes.Page')),
            ],
            options={
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='ModeratorInvite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('invitee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.Page')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.AddField(
            model_name='moderator',
            name='page',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.Page'),
        ),
        migrations.AddField(
            model_name='moderator',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='MemeLike',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point', models.IntegerField()),
                ('liked_on', models.DateTimeField(auto_now_add=True)),
                ('meme', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='memes.Meme')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='meme',
            name='page',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='memes.Page'),
        ),
        migrations.AddField(
            model_name='meme',
            name='tags',
            field=models.ManyToManyField(related_name='memes', to='memes.Tag'),
        ),
        migrations.AddField(
            model_name='meme',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='InviteLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(default=memes.models.page.get_invite_link, max_length=7)),
                ('uses', models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MaxValueValidator(100), django.core.validators.MinValueValidator(1)])),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.Page')),
            ],
        ),
        migrations.CreateModel(
            name='Following',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_followed', models.DateTimeField(auto_now_add=True)),
                ('follower', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='follower', to=settings.AUTH_USER_MODEL)),
                ('following', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='following', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CommentLike',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point', models.IntegerField()),
                ('liked_on', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comment_likes', to='memes.Comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='comment',
            name='meme',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='memes.Meme'),
        ),
        migrations.AddField(
            model_name='comment',
            name='mention',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mention', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='reply_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='memes.Comment'),
        ),
        migrations.AddField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='memelike',
            constraint=models.UniqueConstraint(fields=('user', 'meme'), name='unique_meme_vote'),
        ),
        migrations.AddConstraint(
            model_name='commentlike',
            constraint=models.UniqueConstraint(fields=('user', 'comment'), name='unique_comment_vote'),
        ),
        migrations.AddConstraint(
            model_name='comment',
            constraint=models.CheckConstraint(check=models.Q(('content', ''), ('deleted', False), ('image', None), _negated=True), name='content_image_both_not_empty'),
        ),
    ]
