from django.http import JsonResponse
from django.utils import timezone
# from django.views.decorators.cache import cache_page

from .models import Trending
from memes.models import Meme

from rest_framework.decorators import api_view

from datetime import timedelta


@api_view(["GET"])
def trending(request):
    """ Get list of most popular hashtags """

    try:
        t = Trending.objects.last()
        data = t.data
        create_new_data = t.timestamp < timezone.now() - timedelta(hours=1)
    except Trending.DoesNotExist:
        # Should only get here the first ever time this view is called
        data = []
        create_new_data = True

    if create_new_data:
        new_trending = Trending.objects.create(data=data)

        now = timezone.now()
        hrs3 = now - timedelta(hours=3)
        days2 = now - timedelta(days=2)

        tags_data = Meme.objects.filter(private=False, page_private=False, upload_date__gt=now-timedelta(weeks=1)) \
                                .values_list("tags_lower", "upload_date")

        points = {}
        for tags, timestamp in tags_data:
            # Calculate points for tags based on when they were used (more recent = more points)
            point = 2 if timestamp < days2 else 7 if timestamp < hrs3 else 10
            for tag in tags:
                points[tag] = points.get(tag, 0) + point

        data = sorted(points, key=points.get, reverse=True)[:10]
        new_trending.data = data
        new_trending.save(update_fields=["data"])

    return JsonResponse(data, safe=False)
