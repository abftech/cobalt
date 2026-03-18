# Clear any locks so batch can be run

from django.core.management.base import BaseCommand

from utils.models import Lock


class Command(BaseCommand):

    def handle(self, *args, **options):
        Lock.objects.all().delete()
