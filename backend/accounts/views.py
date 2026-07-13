"""
Authentication views — login, logout, and current user.
"""

from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, UserSerializer


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFTokenView(APIView):
    """Provide CSRF token for SPA before login."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})
