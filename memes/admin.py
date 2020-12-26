from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Following)
admin.site.register(Meme)
admin.site.register(Category)
admin.site.register(Comment)
admin.site.register(MemeLike)
admin.site.register(CommentLike)
admin.site.register(Page)
admin.site.register(Moderator)
admin.site.register(SubscribeRequest)
admin.site.register(InviteLink)
admin.site.register(ModeratorInvite)
