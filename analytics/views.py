# from django.views.decorators.cache import cache_page

from .models import Trending
from .trending import TrendingData

from rest_framework.decorators import api_view
from rest_framework.response import Response

from datetime import date


@api_view(["GET"])
def trending(request):
    """
    Get list of most used hashtags
    """
    try:
        return Response(Trending.objects.values_list("data", flat=True).get(day=date.today()))
    except Trending.DoesNotExist:
        return Response(TrendingData().run())
