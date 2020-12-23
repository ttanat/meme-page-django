from django.http import JsonResponse, HttpResponse
from django.db import IntegrityError
from django.db.models import F, Q
# from django.views.decorators.cache import cache_page
from django.contrib.auth import authenticate

from memes.models import Page, User, Profile

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

import re


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
    username = request.POST.get("username")
    email = request.POST.get("email")
    password1 = request.POST.get("password1")

    if not username or not email or not password1:
        error = "Username" if not username else "Email" if not email else "Password"
        return JsonResponse({"message": f"{error} cannot be blank", "field": error[0].lower()})
    if len(username) > 32:
        return JsonResponse({"message": "Maximum 32 characters", "field": "u"})
    if not re.search("^[a-zA-Z0-9_]+$", username):
        return JsonResponse({"message": "Invalid username", "field": "u"})
    if not re.search("^\S+@\S+\.[a-zA-Z]+$", email):
        return JsonResponse({"message": "Please enter a valid email", "field": "e"})
    # if len(password1) < 6:
        # return JsonResponse({"message": "Password must be at least 6 characters", "field": "p"})
    if password1 != request.POST.get("password2"):
        return JsonResponse({"message": "Password does not match", "field": "p2"})
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({"message": "Username already taken", "field": "u", "taken": True})
    if User.objects.filter(email=email).exists():
        return JsonResponse({"message": "Email already in use", "field": "e"})

    user = None
    try:
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
