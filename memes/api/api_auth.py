from django.http import JsonResponse, HttpResponse
from django.db import IntegrityError, transaction
from django.db.models import F, Q
# from django.views.decorators.cache import cache_page
from django.contrib.auth import authenticate

from memes.models import Page, User, Profile

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

import re
from string import ascii_letters


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    user = authenticate(request, username=request.POST["username"], password=request.POST["password"])
    if user is not None:
        if user.banned:
            return HttpResponse(status=403)
        else:
            refresh = RefreshToken.for_user(user)
            return JsonResponse({
                "refresh": f"{refresh}",
                "access": f"{refresh.access_token}",
            })

    return HttpResponse(status=401)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_session(request):
    user = request.user
    assert not user.banned
    profile = Profile.objects.values("bio", "clout", "num_followers", "num_following").get(user=user)

    return Response({
        "username": user.username,
        "image": user.small_image.url if user.small_image else None,
        "bio": profile["bio"],
        "stats": {
            "clout": profile["clout"],
            "num_followers": profile["num_followers"],
            "num_following": profile["num_following"]
        },
        "moderating": Page.objects.filter(Q(admin=user)|Q(moderators=user)).annotate(dname=F("display_name")).values("name", "dname", "private"),
        "subscriptions": user.subscriptions.annotate(dname=F("display_name")).values("name", "dname", "private", "permissions")
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    # Blacklist token
    pass


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    # refresh_token = RefreshToken.for_user(User.objects.get(username='bob'))
    # return JsonResponse({
    #     "registered": True,
    #     "refresh": f"{refresh_token}",
    #     "access": f"{refresh_token.access_token}"
    # })
    username = request.POST["username"]
    email = request.POST["email"]
    password1 = request.POST["password1"]

    # Check username, email, and password is submitted
    if not username or not email or not password1:
        error = "Username" if not username else "Email" if not email else "Password"
        return JsonResponse({"message": f"{error} cannot be blank", "field": error[0].lower()})

    # Check length of username <= 32
    if len(username) > 32:
        return JsonResponse({"message": "Maximum 32 characters", "field": "u"})
    # Check at least one letter [a-zA-Z] in username
    if not any(c in username for c in ascii_letters) or not re.search(".*[a-zA-Z].*", username):
        return JsonResponse({"message": "Username must have at least one letter", "field": "u"})
    # Check username only contains valid characters
    if not re.search("^[a-zA-Z0-9_]+$", username):
        return JsonResponse({"message": "Invalid username", "field": "u"})

    # Loose check for email (non-whitespace @ non-whitespace dot letters)
    if not re.search("^\S+@\S+\.[a-zA-Z]+$", email):
        return JsonResponse({"message": "Please enter a valid email", "field": "e"})

    # Check password length is at least 6
    # if len(password1) < 6:
        # return JsonResponse({"message": "Password must be at least 6 characters", "field": "p"})
    # Check password matches with confirm password
    if password1 != request.POST.get("password2"):
        return JsonResponse({"message": "Password does not match", "field": "p2"})

    # Check if email already in use with active users
    if User.objects.filter(email=email, is_active=True).exists():
        return JsonResponse({"message": "Email already in use", "field": "e"})

    try:
        with transaction.atomic():
            # Case-insensitive check if username already exists
            if User.objects.filter(username__iexact=username).exists():
                return JsonResponse({"message": "Username already taken", "field": "u", "taken": True})

            user = None
            user = User.objects.create_user(username, email, password1)
            if user is not None:
                refresh_token = RefreshToken.for_user(user)
                return JsonResponse({
                    "registered": True,
                    "refresh": f"{refresh_token}",
                    "access": f"{refresh_token.access_token}"
                })
    except IntegrityError:
        return JsonResponse({"message": "User already exists"})

    return JsonResponse({"message": "Unexpected error occurred"})
