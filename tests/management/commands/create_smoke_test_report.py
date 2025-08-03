import os
import sys

from django.core.exceptions import SuspiciousOperation
from django.core.management.base import BaseCommand

from cobalt.settings import COBALT_HOSTNAME
from tests.test_manager import CobaltTestManagerUnit
from tests.views import create_smoke_test_report


class Command(BaseCommand):
    def handle(self, *args, **options):
        create_smoke_test_report()
