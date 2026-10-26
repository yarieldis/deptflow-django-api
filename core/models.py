from django.contrib.auth.models import AbstractUser
from django.db import models

from core.uuid import uuid7


class User(AbstractUser):
    """Custom auth user with a UUID primary key.

    DeptFlow separates the organizational record (``people.Person``) from the
    login account. This model is the login account; ``Person.user`` links to it
    via a nullable FK.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    def __str__(self) -> str:
        return self.username
