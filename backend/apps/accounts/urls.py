from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .session_views import SessionLoginView, SessionLogoutView, SessionRefreshView
from .views import ChangePasswordView, LoginView, LogoutView, MeView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/token/", LoginView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/session/login/", SessionLoginView.as_view(), name="session_login"),
    path("auth/session/refresh/", SessionRefreshView.as_view(), name="session_refresh"),
    path("auth/session/logout/", SessionLogoutView.as_view(), name="session_logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/me/change-password/", ChangePasswordView.as_view(), name="change_password"),
    *router.urls,
]
