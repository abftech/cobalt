from django.core.management.base import BaseCommand
from django.db import IntegrityError

from accounts.models import User, UnregisteredUser
from cobalt.settings import UNREGISTERED_USER_NOT_SET_EMAIL

""" temporary script to move unregistered users across to become Users """

class Command(BaseCommand):
    def handle(self, *args, **options):

        print(f"About to convert {UnregisteredUser.all_objects.count()} unregistered users...")

        for player in UnregisteredUser.all_objects.all():
            new_user = User()
            new_user.email = UNREGISTERED_USER_NOT_SET_EMAIL
            new_user.system_number = player.system_number
            if player.internal_system_number:
                new_user.user_type = User.UserType.CONTACT
            else:
                new_user.user_type = User.UserType.UNREGISTERED
            new_user.first_name = player.first_name
            new_user.last_name = player.last_name
            new_user.username = player.system_number
            new_user.is_active = False

            try:
                new_user.save()
                player.delete()
            except IntegrityError:
                print(f"Error - likely dupe ABF number {player.system_number}")
                continue
            print(f"Create new user {new_user}. Deleted old unreg user {player}")
