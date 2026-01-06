from django.contrib.auth.base_user import BaseUserManager

from django.db import models

class UserManager(BaseUserManager):
    """
    Added when UnregisteredUsers were merged into the User object so anything referencing User.objects didn't
    need to be changed.

    Retrieve a queryset of registered users.

    Overrides the default get_queryset method to filter only users with user_type 'U'.

    Returns:
        QuerySet: A filtered queryset containing only registered users.
    """
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                user_type="U", # Circular import if we use User.UserType.USER
            )
        )


    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)

class UnRegManager(models.Manager):
    """
    Manager for Unregistered users
    """

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                user_type="N",
            )
        )


class ContactManager(models.Manager):
    """
    Manager for contact users
    """

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                user_type="C",
            )
        )

