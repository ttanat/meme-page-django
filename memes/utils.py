# Formerly "username_ok_chars"
UOC = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"

# Supported file types
SFT = ("image/jpeg", "image/png", "image/gif", "video/mp4", "video/quicktime")

CATEGORIES = ('movies', 'tv-shows', 'gaming', 'animals', 'internet', 'school', 'anime', 'celebrities', 'sports', 'football', 'nba', 'nfl', 'news', 'university')


from django.db.models import F, Q, Sum, Count, Subquery, OuterRef, IntegerField
from django.db.models.functions import Coalesce
from .models import Meme, Comment, User

# Count likes, dislikes, and points for meme
meme_subquery = Meme.objects.filter(pk=OuterRef("pk")).annotate(p=Coalesce(Sum("likes__point"), 0)).values("p")
POINTS = Subquery(meme_subquery, output_field=IntegerField())

# Count number of comments for meme
COMMENT_COUNT = Count("comments", distinct=True)

# Count likes, dislikes, and points for comment
comment_subquery = Comment.objects.filter(pk=OuterRef("pk")).annotate(p=Coalesce(Sum("comment_likes__point"), 0)).values("p")
COMMENT_POINTS = Subquery(comment_subquery, output_field=IntegerField())

# Count total likes on memes and comments for user
# Use in profile page
TOTAL_POINTS = Subquery(User.objects.filter(pk=OuterRef("pk")).annotate(p=Coalesce(Sum("meme__likes__point"), 0)).values("p"), output_field=IntegerField()) \
             + Subquery(User.objects.filter(pk=OuterRef("pk")).annotate(p=Coalesce(Sum("comment__comment_likes__point"), 0)).values("p"), output_field=IntegerField())

from functools import wraps
from django.core.exceptions import PermissionDenied


def ajax_login_required(*methods):
    """
    Decorator to make view only accept ajax requests from logged in users

    methods (tuple) are the allowed methods for the view, e.g. ajax_login_required("GET", "POST")
    """
    def decorator(func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            if request.is_ajax() and request.user.is_authenticated and request.method in methods:
                return func(request, *args, **kwargs)
            raise PermissionDenied
        return inner
    return decorator
