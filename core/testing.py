from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken


def make_user(username="tester", password="secret"):
    User = get_user_model()
    return User.objects.create_user(username=username, password=password)


def auth_headers(user=None):
    """Return HTTP_AUTHORIZATION headers carrying a JWT for ``user``."""
    if user is None:
        user = make_user()
    access = str(RefreshToken.for_user(user).access_token)
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}
