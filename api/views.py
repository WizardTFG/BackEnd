import os

from django.contrib.auth.models import User
from django.db import transaction

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models.users import UserProfile


# Google login
@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):

    credential = request.data.get('credential')

    if not credential:
        return Response(
            {"error": "Falta la credencial de Google"},
            status=400
        )

    try:
        google_user = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            os.environ.get('GOOGLE_CLIENT_ID')
        )

        google_sub = google_user['sub']
        email = google_user.get('email')

        if not email or not google_user.get('email_verified'):
            return Response(
                {"error": "Correo no verificado"},
                status=400
            )

        with transaction.atomic():

            profile = UserProfile.objects.select_related('user').filter(
                google_sub=google_sub
            ).first()

            if profile:
                user = profile.user

            else:
                user = User.objects.create_user(
                    username=f"google_{google_sub}",
                    email=email,
                    first_name=google_user.get('given_name', ''),
                    last_name=google_user.get('family_name', '')
                )

                profile = UserProfile.objects.create(
                    user=user,
                    google_sub=google_sub,
                    imagen=google_user.get('picture', '')
                )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "imagen": profile.imagen,
                "is_admin": profile.is_admin
            }
        })

    except ValueError as e:
        # print("ERROR REAL:", repr(e))
        return Response(
            {"error": "Credencial de Google no válida"},
            status=401
        )


# Obtener usuario actual
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):

    profile = request.user.profile

    return Response({
        "id": request.user.id,
        "username": request.user.username,
        "email": request.user.email,
        "first_name": request.user.first_name,
        "imagen": profile.imagen,
        "is_admin": profile.is_admin
    })