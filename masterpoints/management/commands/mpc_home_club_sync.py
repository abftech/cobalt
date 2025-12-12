import datetime
import time

from django.core.management.base import BaseCommand
from django.db.models import Max

from accounts.models import User
from masterpoints.factories import masterpoint_query_list
from masterpoints.models import (
    ChargeType,
    MasterpointEvent,
    GreenPointAchievementBand,
    Period,
    Rank,
    Promotion,
    MPBatch,
    MPTran,
    ClubMembershipHistory, MPSource,
)
from organisations.models import Organisation, MembershipType, MemberMembershipType

SYSTEM_ACCOUNT = User.objects.filter(pk=3).first()

def _print_timing(start_time):
    """ Helper to print time taken for each function to run """
    
    print(f"Run time(H:M:S:ms): {str(datetime.timedelta(seconds=time.perf_counter() - start_time))}"[:-4])

class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Running mpc_home_club_sync")

        print("syncing home clubs...")

        start_time = time.perf_counter()

        batch_size = 5000

        min_batch = 0
        max_batch = batch_size

        data_returned = True

        while data_returned:
            data_returned = False
            print(f"Processing {min_batch} to {max_batch}")
            for item in masterpoint_query_list(f"mpci-players/{min_batch}/{max_batch}"):
                data_returned = True

                if "ABFNumber" in item:
                    abf_number = item["ABFNumber"]
                elif "ABFNumberRaw" in item:
                    abf_number = item["ABFNumberRaw"]
                else:
                    print("Skipping record with no ABF number")
                    print(item)
                    continue

                # Convert string to number
                abf_number = int(abf_number)

                # See if we have a user or unregistered user matching this record
                user = User.all_objects.filter(system_number=abf_number).first()

                if not user:
                    print(f"User not found for ABF Number: {abf_number}")
                    continue

                # Get the club
                club = Organisation.objects.filter(org_id=item["HomeClubID"]).first()

                if not club:
                    print(f"Club not found with Club No={item['HomeClubID']}")
                    continue

                # See if this user is already a member
                member_membership_type = MemberMembershipType.objects.filter(mem)

                # Get the default membership type
                membership_type = MembershipType.objects.filter(organisation=club).filter(is_default=True).first()

                # If not found then create one
                if not membership_type:
                    membership_type = MembershipType(
                        organisation=club,
                        name="System Generated",
                        description="System generated membership type.\n\nThis is the default membership type. "
                                    "You can edit the values to suit your club. \n\n"
                                    "The checkboxes are generally used for special memberships such as Life Members.",
                        annual_fee=0,
                        last_modified_by=SYSTEM_ACCOUNT,
                        is_default=True,
                    )
                    membership_type.save()

                #

            min_batch = max_batch + 1
            max_batch = max_batch + batch_size

        _print_timing(start_time)
