# Generated by Django 3.1.2 on 2020-11-14 11:13

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import memes.models.core
import memes.models.page


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
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
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('image', models.ImageField(blank=True, null=True, upload_to=memes.models.core.user_directory_path_profile)),
                ('nsfw', models.BooleanField(default=False)),
                ('show_nsfw', models.BooleanField(default=False)),
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
                ('name', models.CharField(choices=[('movies', 'Movies'), ('tv', 'TV'), ('gaming', 'Gaming'), ('animals', 'Animals'), ('internet', 'Internet'), ('school', 'School'), ('anime', 'Anime'), ('celebrities', 'Celebrities'), ('sports', 'Sports'), ('football', 'Football'), ('nba', 'NBA'), ('nfl', 'NFL'), ('news', 'News'), ('university', 'University')], max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=32)),
                ('meme_uuid', models.CharField(max_length=11)),
                ('uuid', models.CharField(default=memes.models.core.set_uuid, max_length=11, unique=True)),
                ('post_date', models.DateTimeField(auto_now_add=True)),
                ('content', models.CharField(blank=True, max_length=150)),
                ('image', models.ImageField(blank=True, null=True, upload_to=memes.models.core.user_directory_path_comments)),
                ('points', models.IntegerField(default=0)),
                ('num_replies', models.PositiveIntegerField(default=0)),
                ('edited', models.BooleanField(default=False)),
                ('deleted', models.PositiveSmallIntegerField(choices=[(0, 'Not deleted'), (1, 'Deleted by user'), (2, 'Deleted by meme OP'), (3, 'Removed by moderator'), (4, 'Deleted by staff')], default=0)),
            ],
        ),
        migrations.CreateModel(
            name='CommentLike',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point', models.IntegerField()),
                ('liked_on', models.DateTimeField(auto_now=True)),
                ('comment_uuid', models.CharField(max_length=11)),
            ],
        ),
        migrations.CreateModel(
            name='Following',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_followed', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='InviteLink',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(default=memes.models.page.get_invite_link, max_length=7)),
                ('uses', models.PositiveSmallIntegerField(default=1)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Meme',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=32)),
                ('page_private', models.BooleanField(default=False)),
                ('page_name', models.CharField(blank=True, max_length=32)),
                ('page_display_name', models.CharField(blank=True, max_length=32)),
                ('original', models.FileField(upload_to=memes.models.core.original_meme_path)),
                ('large', models.FileField(blank=True, null=True, upload_to='')),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='')),
                ('content_type', models.CharField(choices=[('image/jpeg', 'JPEG'), ('image/png', 'PNG'), ('image/gif', 'GIF'), ('video/mp4', 'MP4'), ('video/quicktime', 'MOV')], max_length=15)),
                ('uuid', models.CharField(default=memes.models.core.set_uuid, max_length=11, unique=True)),
                ('dank', models.BooleanField(default=False)),
                ('caption', models.CharField(blank=True, max_length=100)),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('num_likes', models.PositiveIntegerField(default=0)),
                ('num_dislikes', models.PositiveIntegerField(default=0)),
                ('points', models.IntegerField(default=0)),
                ('num_comments', models.PositiveIntegerField(default=0)),
                ('nsfw', models.BooleanField(default=False)),
                ('num_views', models.PositiveIntegerField(default=0)),
                ('ip_address', models.GenericIPAddressField(null=True)),
                ('hidden', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='MemeLike',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point', models.IntegerField()),
                ('liked_on', models.DateTimeField(auto_now=True)),
                ('meme_uuid', models.CharField(max_length=11)),
            ],
        ),
        migrations.CreateModel(
            name='Moderator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='ModeratorInvite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['id'],
            },
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
                ('num_views', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('num_memes', models.PositiveIntegerField(default=0)),
                ('clout', models.IntegerField(default=0)),
                ('bio', models.CharField(blank=True, max_length=64)),
                ('num_followers', models.PositiveIntegerField(default=0)),
                ('num_following', models.PositiveIntegerField(default=0)),
                ('num_views', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Subscriber',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='SubscribeRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.CheckConstraint(check=models.Q(name__regex='^[a-zA-Z][a-zA-Z0-9_]*$'), name='tag_chars_valid'),
        ),
        migrations.AddField(
            model_name='subscriberequest',
            name='page',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.page'),
        ),
        migrations.AddField(
            model_name='subscriberequest',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='subscriber',
            name='page',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.page'),
        ),
        migrations.AddField(
            model_name='subscriber',
            name='subscriber',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='page',
            name='admin',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='page',
            name='moderators',
            field=models.ManyToManyField(related_name='moderating', through='memes.Moderator', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='page',
            name='subscribers',
            field=models.ManyToManyField(related_name='subscriptions', through='memes.Subscriber', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='moderatorinvite',
            name='invitee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='moderatorinvite',
            name='page',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.page'),
        ),
        migrations.AddField(
            model_name='moderator',
            name='page',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.page'),
        ),
        migrations.AddField(
            model_name='moderator',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='memelike',
            name='meme',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='memes.meme'),
        ),
        migrations.AddField(
            model_name='memelike',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='meme',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='memes.category'),
        ),
        migrations.AddField(
            model_name='meme',
            name='page',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='memes.page'),
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
        migrations.AddField(
            model_name='invitelink',
            name='page',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='memes.page'),
        ),
        migrations.AddField(
            model_name='following',
            name='follower',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='follower', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='following',
            name='following',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='following', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='commentlike',
            name='comment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comment_likes', to='memes.comment'),
        ),
        migrations.AddField(
            model_name='commentlike',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='comment',
            name='meme',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='memes.meme'),
        ),
        migrations.AddField(
            model_name='comment',
            name='reply_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='memes.comment'),
        ),
        migrations.AddField(
            model_name='comment',
            name='root',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='memes.comment'),
        ),
        migrations.AddField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='user',
            name='follows',
            field=models.ManyToManyField(related_name='followers', through='memes.Following', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups'),
        ),
        migrations.AddField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions'),
        ),
        migrations.AddConstraint(
            model_name='page',
            constraint=models.CheckConstraint(check=models.Q(name__regex='^[a-zA-Z0-9_]+$'), name='page_name_chars_valid'),
        ),
        migrations.AddConstraint(
            model_name='memelike',
            constraint=models.UniqueConstraint(fields=('user', 'meme'), name='unique_meme_vote'),
        ),
        migrations.AddConstraint(
            model_name='invitelink',
            constraint=models.CheckConstraint(check=models.Q(('uses__lte', 100), ('uses__gt', 0)), name='invite_link_use_limit'),
        ),
        migrations.AddConstraint(
            model_name='commentlike',
            constraint=models.UniqueConstraint(fields=('user', 'comment'), name='unique_comment_vote'),
        ),
        migrations.AddConstraint(
            model_name='comment',
            constraint=models.CheckConstraint(check=models.Q(('content', ''), ('deleted', 0), ('image', None), _negated=True), name='content_image_both_not_empty'),
        ),
    ]
