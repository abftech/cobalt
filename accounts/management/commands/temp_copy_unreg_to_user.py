from django.core.management.base import BaseCommand
from django.db import IntegrityError

from accounts.models import User, UnregisteredUser

""" temporary script to move unregistered users across to become Users """

class Command(BaseCommand):
    def handle(self, *args, **options):

        for player in UnregisteredUser.all_objects.all():
            new_user = User()
            new_user.email = "fixlater@broken.com"
            new_user.system_number = player.system_number
            if player.internal_system_number:
                new_user.user_type = User.UserType.CONTACT
            else:
                new_user.user_type = User.UserType.UNREGISTERED
            new_user.first_name = player.first_name
            new_user.last_name = player.last_name
            new_user.username = player.system_number

            try:
                new_user.save()
                player.delete()
            except IntegrityError:
                print(f"Error - likely dupe ABF number {player.system_number}")
                continue
            print(f"Create new user {new_user}. Deleted old unreg user {player}")
