from django.db.models import Sum

from .models import TagUse, Trending

from datetime import date, timedelta
from typing import List


class TrendingData:
    def __init__(self):
        # Only compute for yesterday; doing it for today will result in missing data (must be done at end of day)
        self.day = date.today() - timedelta(days=1)

        # Data for which tags are trending (most used in past week)
        # e.g. [{"lower_name": "banana", "num_posts": 100}, ...]
        self.trending = TagUse.objects.filter(day__range=[self.day - timedelta(days=6), self.day + timedelta(days=1)]) \
                                      .values("lower_name") \
                                      .annotate(num_posts=Sum("count")) \
                                      .order_by("-num_posts")[:10]

        # Data for number of uses of variants of trending tags
        # e.g. #banana, #Banana, #BaNaNa used
        # e.g. [{"lower_name": "banana", "variants": {"Banana": 60, "banana": 30, "BaNaNa": 10}}, ...]
        self.variants = TagUse.objects.filter(
            day__range=[self.day - timedelta(days=6), self.day + timedelta(days=1)],
            lower_name__in=[tag["lower_name"] for tag in self.trending]
        ).values("lower_name", "variants")

    """
    # Slower
    from collections import Counter
    def sum_values_for_common_keys(l: List[dict]) -> dict:
        c = Counter()
        for d in l:
            c += Counter(d)

        return dict(c)
    """

    def sum_values_for_common_keys(self, l: List[dict]) -> dict:
        result = {}
        # For each dictionary in l
        for dict_ in l:
            # For each key in dictionary
            for key in dict_.keys():
                # Increment value for that key in data
                result[key] = result.get(key, 0) + dict_[key]

        return result

    def compute_trending_data(self) -> List[dict]:
        # Key: lowercase name, value: list of variants dictionaries (currently empty)
        tmp = {tag["lower_name"]: [] for tag in self.trending}
        # Append variants dictionaries to lists
        for variant in self.variants:
            tmp[variant["lower_name"]].append(variant["variants"])
        # Combine variants dictionaries to one big dictionary for each tag
        variant_totals = {k: self.sum_values_for_common_keys(tmp[k]) for k in tmp}

        data = []
        for tag in self.trending:
            tmp = variant_totals[tag["lower_name"]]
            # Get variant of tag with most usage, e.g. #Banana used more than #banana, #BaNaNa, etc.
            variant_to_use = max(tmp, key=tmp.get)
            data.append({
                "name": variant_to_use,
                "num_posts": tag["num_posts"]
            })

        # e.g. [{"name": "Banana", "num_posts": 100}, ...]
        return data

    def run(self):
        data = self.compute_trending_data()
        obj, created = Trending.objects.get_or_create(day=self.day, defaults={"data": data})

        return obj.data
