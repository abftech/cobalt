"""Management Commands for accounts"""

from accounts.models import User


def get_or_create_fake_user(
    self, system_number, first, last, about="No info", pic=None
):
    """Helper to get a user or create them if they don't exist"""

    # Check if user already exists
    user = User.objects.filter(username=system_number).first()
    if user:
        self.stdout.write(
            self.style.SUCCESS(f"{system_number} user already exists - ok")
        )
        return user

    user = User.objects.create_user(
        username=system_number,
        email="success@simulator.amazonses.com",
        password="F1shcake",
        first_name=first,
        last_name=last,
        system_number=system_number,
        about=about,
        pic=pic,
    )
    user.save()

    self.stdout.write(
        self.style.SUCCESS(
            f"Successfully created new user - {first} {last}({system_number})"
        )
    )
    return user
