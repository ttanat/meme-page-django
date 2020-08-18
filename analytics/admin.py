from django.contrib import admin

from .models import View, TagUse, Trending

admin.site.register(View)
admin.site.register(TagUse)
admin.site.register(Trending)
