from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Meme)
admin.site.register(Tag)
admin.site.register(Comment)
admin.site.register(MemeLike)
admin.site.register(CommentLike)
admin.site.register(Page)
