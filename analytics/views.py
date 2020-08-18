from django.http import HttpResponse
from django.db.models import Sum
# from django.views.decorators.cache import cache_page

from .models import TagUse, Trending

from rest_framework.decorators import api_view
from rest_framework.response import Response

from datetime import date, timedelta
from typing import List

"""
# Slower
from collections import Counter
def sum_values_for_common_keys(l: List[dict]) -> dict:
    c = Counter()
    for d in l:
        c += Counter(d)

    return dict(c)
"""

def sum_values_for_common_keys(l: List[dict]) -> dict:
    result = {}
    # For each dictionary in l
    for dict_ in l:
        # For each key in dictionary
        for key in dict_.keys():
            # Increment value for that key in data
            result[key] = result.get(key, 0) + dict_[key]

    return result


def compute_trending_data(trending: List[dict], variants: List[dict]) -> List[dict]:
    # Key: lowercase name, value: list of variants dictionaries (currently empty)
    tmp = {tag["lower_name"]: [] for tag in trending}
    # Append variants dictionaries to lists
    for variant in variants:
        tmp[variant["lower_name"]].append(variant["variants"])
    # Combine variants dictionaries to one big dictionary for each tag
    variant_totals = {k: sum_values_for_common_keys(tmp[k]) for k in tmp}

    data = []
    for tag in trending:
        tmp = variant_totals[tag["lower_name"]]
        # Get variant of tag with most usage, e.g. #Banana used more than #banana, #BaNaNa, etc.
        variant_to_use = max(tmp, key=tmp.get)
        data.append({
            "name": variant_to_use,
            "num_posts": tag["num_posts"]
        })

    # e.g. [{"name": "Banana", "num_posts": 100}, ...]
    return data


# @cache_page(60 * 60)
@api_view(["GET"])
def trending(request):
    """
    Get list of trending hashtags
    """
    try:
        return Response(Trending.objects.values_list("data", flat=True).get(day=date.today()))
    except Trending.DoesNotExist:
        # Data for which tags are trending (most used in past week)
        # e.g. [{"lower_name": "banana", "num_posts": 100}, ...]
        trending = TagUse.objects.filter(day__gt=date.today() - timedelta(days=6)) \
                                 .values("lower_name") \
                                 .annotate(num_posts=Sum("count")) \
                                 .order_by("-num_posts")[:10]
        # Can respond with this if tag names case-insensitive

        # Data for number of uses of variants of trending tags
        # e.g. #banana, #Banana, #BaNaNa used
        # e.g. [{"lower_name": "banana", "variants": {"Banana": 60, "banana": 30, "BaNaNa": 10}}, ...]
        variants = TagUse.objects.filter(
            day__gt=date.today() - timedelta(days=6),
            lower_name__in=[tag["lower_name"] for tag in trending]
        ).values("lower_name", "variants")

        # e.g. [{"name": "Banana", "num_posts": 100}, ...]
        data = compute_trending_data(trending, variants)

        obj, created = Trending.objects.get_or_create(day=date.today(), defaults={"data": data})

        return Response(obj.data)
