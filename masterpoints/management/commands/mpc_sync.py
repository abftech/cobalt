import cProfile
import io
import pstats
import sys

from django.core.management.base import BaseCommand
from django.db.models import Max

from accounts.models import User, UnregisteredUser
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
    ClubMembershipHistory,
)
from masterpoints.views import get_abf_checksum
from organisations.models import Organisation

SYSTEM_ACCOUNT = User.objects.filter(pk=3).first()


def sync_charge_types():
    """ChargeTypes -> ChargeType"""

    print("Syncing ChargeType...")

    for charge_type in masterpoint_query_list("mpci-charge-types"):
        item, _ = ChargeType.objects.get_or_create(
            old_mpc_id=charge_type["ChargeTypeID"]
        )
        item.type_name = charge_type["TypeName"]
        item.fee_including_gst = charge_type["FeeInclGST"]
        item.show_on_invoice = charge_type["IsShowOnInvoice"] == "Y"
        item.is_gst_taxable = charge_type["IsGSTTaxable"] == "Y"
        item.invoice_words = charge_type["InvoiceWords"]
        item.show_on_price_list = charge_type["IsShowOnPriceList"] == "Y"
        item.price_list_sequence = charge_type["PriceListSequence"]
        item.mps_or_player = charge_type["MPsOrPlayers"]
        item.save()


def sync_events(query_list, force_closed=False):
    """Events -> MasterpointEvent"""

    print(f"Syncing Events...{force_closed=}")
    for event in query_list:
        item, _ = MasterpointEvent.objects.get_or_create(old_mpc_id=event["EventID"])
        item.event_code = event["EventCode"]
        item.event_name = event["EventName"]
        item.mp_colour = event["MPColour"]
        item.comments = event["Comments"]
        item.is_closed = event["IsClosed"] == "Y"
        item.billing_club_id = event["BillingClubID"]
        item.t_grade = event["tGrade"]
        item.grade = event["Grade"]
        item.added_by_id = SYSTEM_ACCOUNT.id

        # MPC uses -1 for DeletedEvents
        if item.billing_club_id > 0:

            organisation = Organisation.objects.filter(
                old_mpc_id=item.billing_club_id
            ).first()

            if not organisation:
                print(
                    f"Organisation with id={item.billing_club_id} not found. Exiting."
                )
                continue

            item.billing_organisation = organisation

        if force_closed:
            item.is_closed = True
        else:
            # DeletedEvents does not have GoldPointEventTier
            item.gold_point_event_tier = event["GoldPointEventTier"]

        item.save()


def sync_clubs():
    """Sync missing clubs and additional data"""

    # TODO: This needs a lot of work to sync critical data. For now we just add missing clubs
    # So other things work

    print("Syncing clubs...")

    for org in masterpoint_query_list("mpci-clubs"):

        club = Organisation.objects.filter(org_id=org["ClubNumber"]).first()

        if not club:
            club = Organisation(org_id=org["ClubNumber"])

            club.name = org["ClubName"]
            club.club_email = org["ClubEmail"]
            club.club_website = org["ClubWebsite"]
            club.status = "Open" if org["IsClosed"] == "N" else "Closed"
            # Fix later
            club.secretary = SYSTEM_ACCOUNT
            club.save()
            print(
                f"Created club. Club number is {club.org_id} pk={club.id} {club.name}"
            )

        club.old_mpc_id = org["ClubID"]
        club.save()


def sync_green_point_achievement_bands():
    """GreenPointAchievementBands -> GreenPointAchievementBand"""

    print("Syncing GreenPointAchievementBands...")

    for item in masterpoint_query_list("mpci-GreenPointAchievementBands"):

        band = GreenPointAchievementBand.objects.filter(
            old_mpc_id=item["BandID"]
        ).first() or GreenPointAchievementBand(old_mpc_id=item["BandID"])

        band.low_points = item["LoPoints"]
        band.high_points = item["HiPoints"]

        band.save()


def sync_periods():
    """Periods -> Period"""

    print("syncing periods...")

    for item in masterpoint_query_list("mpci-periods"):
        period = Period.objects.filter(old_mpc_id=item["PeriodID"]).first() or Period(
            old_mpc_id=item["PeriodID"]
        )

        period.period_month = item["PeriodMonth"]
        period.period_year = item["PeriodYear"]
        period.is_current = item["IsCurrent"] == "Y"
        period.period_end = item["PeriodEnd"]

        period.save()


def sync_ranks():
    """Ranks -> Rank"""

    print("syncing ranks...")

    for item in masterpoint_query_list("mpci-ranks"):
        rank = Rank.objects.filter(old_mpc_id=item["RankID"]).first() or Rank(
            old_mpc_id=item["RankID"]
        )

        rank.rank_name = item["RankName"]
        rank.rank_old_name = item["RankOldName"]
        rank.rank_sequence = item["RankSequence"]
        rank.total_needed = item["TotalNeeded"]
        rank.gold_needed = item["GoldNeeded"]
        rank.red_gold_needed = item["RedGoldNeeded"]

        rank.save()


def sync_promotions():
    """Promotions -> Promotion"""

    print("syncing promotions...")

    for item in masterpoint_query_list("mpci-promotions"):
        promotion = Promotion.objects.filter(
            old_mpc_id=item["PromotionID"]
        ).first() or Promotion(old_mpc_id=item["PromotionID"])

        # Link to rank object
        rank = Rank.objects.filter(old_mpc_id=item["RankID"]).first()
        promotion.rank = rank

        # Link to period object
        period = Period.objects.filter(old_mpc_id=item["PeriodID"]).first()
        promotion.period = period

        # Link to player - we can't use a foreign key
        player = (
            User.objects.filter(old_mpc_id=item["PlayerID"]).first()
            or UnregisteredUser.objects.filter(old_mpc_id=item["PlayerID"]).first()
        )
        if player:
            promotion.system_number = player.system_number
        else:
            print(
                f"No matching user found for PlayerID={item['PlayerID']}. PromotionID={item['PromotionID']}"
            )
            continue

        promotion.record_date = item["RecordDate"]

        promotion.save()


def sync_players():
    """Players -> User/UnregisteredUser"""

    print("syncing players...")

    added_count = 0
    skipped_count = 0

    batch_size = 5000

    min_batch = 0
    max_batch = batch_size

    data_returned = True

    while data_returned:
        data_returned = False
        print(f"Processing {min_batch} to {max_batch}")
        for item in masterpoint_query_list(f"mpci-players/{min_batch}/{max_batch}"):
            data_returned = True

            # The ABF Raw field has the ABF number
            if "ABFNumberRaw" in item:
                abf_number = item["ABFNumberRaw"]
            else:
                print("Skipping record with no ABF number")
                print(item)
                skipped_count += 1
                continue

            # Convert string to number
            abf_number = int(abf_number)

            # See if we have a user or unregistered user matching this record
            user = (
                User.objects.filter(system_number=abf_number).first()
                or UnregisteredUser.objects.filter(system_number=abf_number).first()
            )

            # If not, create an unregistered user
            if not user:
                user = UnregisteredUser(system_number=abf_number)
                user.first_name = item["GivenNames"]
                user.last_name = item["Surname"]
                user.origin = "MPCS"
                user.last_updated_by = SYSTEM_ACCOUNT
                added_count += 1

            user.old_mpc_id = item["PlayerID"]
            user.save()

        min_batch = max_batch + 1
        max_batch = max_batch + batch_size

    unmatched_users = User.objects.filter(old_mpc_id__isnull=True).count()
    unmatched_unreg_users = UnregisteredUser.objects.filter(
        old_mpc_id__isnull=True
    ).count()
    print(f"Added: {added_count}. Skipped: {skipped_count}.")
    print(
        f"Unmatched Users: {unmatched_users}. Unmatched Unregistered Users: {unmatched_unreg_users}"
    )


def sync_mp_batches():
    """MPBatches -> MPBatch"""

    print("syncing MP Batches...")

    batch_size = 5000

    # Get new data only
    min_batch = (
        MPBatch.objects.aggregate(max_my_field=Max("old_mpc_id"))["max_my_field"] or 1
    )
    max_batch = min_batch + batch_size

    data_returned = True

    while data_returned:
        data_returned = False
        print(f"Processing {min_batch} to {max_batch}")
        for item in masterpoint_query_list(f"mpci-batches/{min_batch}/{max_batch}"):
            data_returned = True

            mp_batch = MPBatch()
            mp_batch.old_mpc_id = item["MPBatchID"]
            mp_batch.mps_submitted_green = item["MPsSubmittedGreen"]
            mp_batch.mps_submitted_red = item["MPsSubmittedRed"]
            mp_batch.mps_submitted_gold = item["MPsSubmittedGold"]
            mp_batch.old_mpc_posted_by_user_id = item["PostedByUserID"]
            mp_batch.posted_date = item["PostedDate"]
            mp_batch.source = item["Source"]
            mp_batch.event_or_club_id = item["EventOrClubID"]
            mp_batch.posting_month = item["PostingMonth"]
            mp_batch.posting_year = item["PostingYear"]
            mp_batch.is_mccutcheon_eligible = item["IsMcCutcheonEligible"] == "Y"
            mp_batch.is_approved = item["IsApproved"] == "Y"
            mp_batch.uploaded_comments = item["UploaderComments"]
            mp_batch.admin_comments = item["AdminComments"]
            mp_batch.is_charged = item["IsCharged"] == "Y"
            mp_batch.authorisation_number = item["AuthorisationNumber"]
            mp_batch.uploaded_filename = item["UploadedFileName"]
            mp_batch.how_submitted = item["HowSubmitted"]
            mp_batch.event_month = item["EventMonth"]

            mp_batch.save()

        min_batch = max_batch + 1
        max_batch = max_batch + batch_size


def sync_mp_trans(full_sync=False):
    """MPTrans -> MPTrans"""

    print("syncing MP Trans...")

    batch_size = 5000

    # Get new data only unless we are doing a full sync
    min_batch = (
        MPTran.objects.aggregate(max_my_field=Max("old_mpc_id"))["max_my_field"] or 0
    )
    if full_sync:
        min_batch = 0
    max_batch = min_batch + batch_size

    data_returned = True

    while data_returned:
        data_returned = False
        print(f"Processing {min_batch} to {max_batch}")
        for item in masterpoint_query_list(f"mpci-trans/{min_batch}/{max_batch}"):
            data_returned = True

            mp_trans = (
                MPTran.objects.filter(old_mpc_id=item["TranID"]).first() or MPTran()
            )

            mp_trans.old_mpc_id = item["TranID"]
            mp_trans.old_mpc_player_id = item["PlayerID"]
            mp_trans.old_mp_batch_id = item["MPBatchID"]
            mp_trans.mp_colour = item["MPColour"]
            mp_trans.mp_amount = item["MPs"]
            mp_trans.source = item["Source"]
            mp_trans.is_approved = item["IsApproved"] == "Y"

            # validate and add system number
            player = (
                User.objects.filter(old_mpc_id=item["PlayerID"]).first()
                or UnregisteredUser.objects.filter(old_mpc_id=item["PlayerID"]).first()
            )
            if player:
                mp_trans.system_number = player.system_number
            else:
                print(
                    f"No matching user found for PlayerID={item['PlayerID']}. MPTransID={item['TranID']}"
                )
                continue

            # link to mp_batch
            mp_batch = MPBatch.objects.filter(old_mpc_id=item["MPBatchID"]).first()

            if mp_batch:
                mp_trans.mp_batch = mp_batch
            else:
                print(
                    f"No matching user found for BatchID={item['MPBatchID']}. MPTransID={item['TranID']}"
                )
                continue

            mp_trans.save()

        min_batch = max_batch + 1
        max_batch = max_batch + batch_size


def sync_mpc_club_membership_history():
    """ClubMembership -> ClubMembershipHistory"""

    print("syncing club membership history...")

    for item in masterpoint_query_list("mpci-club-membership"):

        membership = ClubMembershipHistory.objects.filter(
            old_mpc_id=item["RecordID"]
        ).first() or ClubMembershipHistory(old_mpc_id=item["RecordID"])

        membership.billing_year = item["BillingYear"]
        membership.billing_month = item["BillingMonth"]
        membership.old_mpc_club_id = item["ClubID"]
        membership.home_members = item["HomeMembers"]

        club = Organisation.objects.filter(old_mpc_id=item["ClubID"]).first()
        if club:
            membership.club = club
        else:
            print(
                f"No matching club found for ClubID={item['ClubID']}. RecordID={item['RecordID']}"
            )
            continue

        membership.save()


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Running mpc_sync")

        # sync_clubs()
        # sync_players()
        # sync_charge_types()
        # sync_events(masterpoint_query_list("mpci-events"))
        # sync_events(masterpoint_query_list("mpci-deleted-events"), force_closed=True)
        # sync_green_point_achievement_bands()
        # sync_periods()
        # sync_ranks()
        # sync_promotions()
        # sync_mp_batches()
        # sync_mp_trans(full_sync=True)
        sync_mpc_club_membership_history()

        # profiler = cProfile.Profile()
        #
        # # Enable profiling
        # profiler.enable()
        #
        # # Run the code you want to profile
        # sync_mp_trans(full_sync=True)
        #
        # # Disable profiling
        # profiler.disable()
        #
        # # Create a StringIO object to capture the profile output
        # s = io.StringIO()
        #
        # # Create a pstats.Stats object from the profiler data
        # # Sort the statistics by cumulative time for better insight into bottlenecks
        # sortby = pstats.SortKey.CUMULATIVE
        # ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
        #
        # # Print the statistics to the StringIO object
        # ps.print_stats()
        #
        # # Print the captured profile output
        # print(s.getvalue())
