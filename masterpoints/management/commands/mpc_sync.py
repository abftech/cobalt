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
from organisations.models import Organisation

SYSTEM_ACCOUNT = User.objects.filter(pk=3).first()

def _print_timing(start_time):
    """ Helper to print time taken for each function to run """
    
    print(f"Run time(H:M:S:ms): {str(datetime.timedelta(seconds=time.perf_counter() - start_time))}"[:-4])


def sync_charge_types():
    """ChargeTypes -> ChargeType"""

    print("Syncing ChargeType...")

    start_time = time.perf_counter()

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

    _print_timing(start_time)


def sync_events(query_list, force_closed=False):
    """Events -> MasterpointEvent"""

    print(f"Syncing Events...{force_closed=}")

    start_time = time.perf_counter()

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

    _print_timing(start_time)


def sync_clubs():
    """Sync missing clubs and additional data"""

    # TODO: This needs a lot of work to sync critical data. For now we just add missing clubs
    # So other things work

    print("Syncing clubs...")

    start_time = time.perf_counter()

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

    _print_timing(start_time)


def sync_green_point_achievement_bands():
    """GreenPointAchievementBands -> GreenPointAchievementBand"""

    print("Syncing GreenPointAchievementBands...")

    start_time = time.perf_counter()

    for item in masterpoint_query_list("mpci-GreenPointAchievementBands"):

        band = GreenPointAchievementBand.objects.filter(
            old_mpc_id=item["BandID"]
        ).first() or GreenPointAchievementBand(old_mpc_id=item["BandID"])

        band.low_points = item["LoPoints"]
        band.high_points = item["HiPoints"]

        band.save()

    _print_timing(start_time)

def sync_periods():
    """Periods -> Period"""

    print("syncing periods...")

    start_time = time.perf_counter()

    for item in masterpoint_query_list("mpci-periods"):
        period = Period.objects.filter(old_mpc_id=item["PeriodID"]).first() or Period(
            old_mpc_id=item["PeriodID"]
        )

        period.period_month = item["PeriodMonth"]
        period.period_year = item["PeriodYear"]
        period.is_current = item["IsCurrent"] == "Y"
        period.period_end = item["PeriodEnd"]

        period.save()

    _print_timing(start_time)

def sync_ranks():
    """Ranks -> Rank"""

    print("syncing ranks...")

    start_time = time.perf_counter()

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

    _print_timing(start_time)

def sync_promotions():
    """Promotions -> Promotion"""

    print("syncing promotions...")

    start_time = time.perf_counter()

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
            or User.unreg_objects.filter(old_mpc_id=item["PlayerID"]).first()
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

    _print_timing(start_time)


def sync_players():
    """Players -> User/UnregisteredUser"""

    print("syncing players...")

    start_time = time.perf_counter()

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

            if "ABFNumber" in item:
                abf_number = item["ABFNumber"]
                # print(f"using ABFNumber: {item['ABFNumber']} {item['GivenNames']} {item['Surname']} {item['IsActive']}")
            elif "ABFNumberRaw" in item:
                abf_number = item["ABFNumberRaw"]
                # print(f"using ABFNumberRaw: {item['ABFNumberRaw']} {item['GivenNames']} {item['Surname']} {item['IsActive']}")
            else:
                print("Skipping record with no ABF number")
                print(item)
                skipped_count += 1
                continue

            # Convert string to number
            abf_number = int(abf_number)

            # See if we have a user or unregistered user matching this record
            user = User.all_objects.filter(system_number=abf_number).first()

            # If not, create an unregistered user
            if not user:
                user = User(user_type=User.UserType.UNREGISTERED, system_number=abf_number)
                user.first_name = item["GivenNames"]
                user.last_name = item["Surname"]
                user.username = abf_number
                user.is_active = False
#                user.last_updated_by = SYSTEM_ACCOUNT
                added_count += 1

            user.old_mpc_id = item["PlayerID"]
            user.is_abf_active = item["IsActive"] == "Y"
            user.save()

        min_batch = max_batch + 1
        max_batch = max_batch + batch_size

    unmatched_users = User.objects.filter(old_mpc_id__isnull=True).count()
    unmatched_unreg_users = User.unreg_objects.filter(
        old_mpc_id__isnull=True
    ).count()
    print(f"Added: {added_count}. Skipped: {skipped_count}.")
    print(
        f"Unmatched Users: {unmatched_users}. Unmatched Unregistered Users: {unmatched_unreg_users}"
    )
    _print_timing(start_time)

def sync_mp_batches():
    """MPBatches -> MPBatch"""

    print("syncing MP Batches...")

    start_time = time.perf_counter()

    batch_size = 5000

    min_batch = 0
    max_batch = min_batch + batch_size

    # Update the check flag so we know if something has been deleted
    MPBatch.objects.filter(id__gte=min_batch).update(check_flag=False)

    data_returned = True

    while data_returned:
        data_returned = False
        print(f"Processing {min_batch} to {max_batch}")
        for item in masterpoint_query_list(f"mpci-batches/{min_batch}/{max_batch}"):
            data_returned = True

            mp_batch = MPBatch.objects.filter(old_mpc_id=item["MPBatchID"]).first() or MPBatch(old_mpc_id=item["MPBatchID"])

            mp_batch.check_flag = True
            mp_batch.mps_submitted_green = item["MPsSubmittedGreen"]
            mp_batch.mps_submitted_red = item["MPsSubmittedRed"]
            mp_batch.mps_submitted_gold = item["MPsSubmittedGold"]
            mp_batch.old_mpc_posted_by_user_id = item["PostedByUserID"]
            mp_batch.posted_date = item["PostedDate"]
            mp_batch.source = item["Source"]
            mp_batch.old_mpc_event_or_club_id = item["EventOrClubID"]
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

            # Map to MasterpointEvent or Organisation
            if mp_batch.source == MPSource.CLUB:
                club = Organisation.objects.filter(old_mpc_id=mp_batch.old_mpc_event_or_club_id).first()
                mp_batch.club = club
            elif mp_batch.source == MPSource.EVENT:
                mp_event = MasterpointEvent.objects.filter(old_mpc_id=mp_batch.old_mpc_event_or_club_id).first()
                mp_batch.masterpoint_event = mp_event

            mp_batch.save()

        min_batch = max_batch + 1
        max_batch = max_batch + batch_size

    # Anything that still has the check flag as false was not found on the MPC side
    missing = MPBatch.objects.filter(check_flag=False)
    print(f"Found {missing.count()} deleted batches. Removing from MyABF")
    missing.delete()

    _print_timing(start_time)


def sync_mp_trans(full_sync=False):
    """MPTrans -> MPTrans"""

    print("syncing MP Trans...")

    start_time = time.perf_counter()

    batch_size = 5000
    rewind = 500_000
    errors = 0

    # Get new data only unless we are doing a full sync
    min_batch = (
        MPTran.objects.aggregate(max_my_field=Max("old_mpc_id"))["max_my_field"] or 0
    )

    # Rewind as recent things could have changed but old things won't
    min_batch = min_batch - rewind
    if min_batch < 0:
        min_batch = 0

    if full_sync:
        min_batch = 0
    max_batch = min_batch + batch_size

    data_returned = True

    while data_returned:
        data_returned = False
        print(f"Processing {min_batch} to {max_batch}")
        data = masterpoint_query_list(f"mpci-trans/{min_batch}/{max_batch}")

        # Load the foreign keys in one hit
        player_list = []
        mp_batch_list = []
        for item in data:
            player_list.append(item["PlayerID"])
            mp_batch_list.append(item["MPBatchID"])

        players = User.all_objects.filter(old_mpc_id__in=player_list)
        mp_batches = MPBatch.objects.filter(old_mpc_id__in=mp_batch_list)

        player_dict = {}
        for player in players:
            player_dict[player.old_mpc_id] = player.id

        mp_batch_dict = {}
        for mp_batch in mp_batches:
            mp_batch_dict[mp_batch.old_mpc_id] = mp_batch.id

        for item in data:
            data_returned = True

            mp_trans = (
                MPTran.objects.filter(old_mpc_id=item["TranID"]).first() or MPTran(old_mpc_id=item["TranID"])
            )
            mp_trans.old_mpc_player_id = item["PlayerID"]
            mp_trans.old_mp_batch_id = item["MPBatchID"]
            mp_trans.mp_colour = item["MPColour"]
            mp_trans.mp_amount = item["MPs"]
            mp_trans.source = item["Source"]
            mp_trans.is_approved = item["IsApproved"] == "Y"

            try:
                # add link to user
                mp_trans.user_id = player_dict[mp_trans.old_mpc_player_id]
            except KeyError:
                print(f"Error looking for {mp_trans.old_mpc_player_id} in Player dictionary")
                errors += 1
                continue

            try:
                # link to MP Batch
                mp_trans.mp_batch_id = mp_batch_dict[mp_trans.old_mp_batch_id]
            except KeyError:
                print(f"Error looking for {mp_trans.old_mp_batch_id} in Batch ID dictionary")
                errors += 1
                continue

            mp_trans.save()

        min_batch = max_batch + 1
        max_batch = max_batch + batch_size

    print(f"Finished with {errors} errors")
    _print_timing(start_time)


def sync_mpc_club_membership_history():
    """ClubMembership -> ClubMembershipHistory"""

    print("syncing club membership history...")

    start_time = time.perf_counter()

    club_dict = {}
    for club in Organisation.objects.all():
        club_dict[club.old_mpc_id] = club.id

    for item in masterpoint_query_list("mpci-club-membership"):

        membership = ClubMembershipHistory.objects.filter(
            old_mpc_id=item["RecordID"]
        ).first() or ClubMembershipHistory(old_mpc_id=item["RecordID"])

        membership.billing_year = item["BillingYear"]
        membership.billing_month = item["BillingMonth"]
        membership.old_mpc_club_id = item["ClubID"]
        membership.home_members = item["HomeMembers"]

        if item["ClubID"] in club_dict:
            membership.club_id = club_dict[item["ClubID"]]
        else:
            print(
                f"No matching club found for ClubID={item['ClubID']}. RecordID={item['RecordID']}"
            )
            continue

        membership.save()

    _print_timing(start_time)


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Running mpc_sync")

        # Order matters, we need to link to foreign keys so they need to exist first
        sync_clubs()
        sync_players()
        sync_charge_types()
        sync_events(masterpoint_query_list("mpci-events"))
        sync_events(masterpoint_query_list("mpci-deleted-events"), force_closed=True)
        sync_green_point_achievement_bands()
        sync_periods()
        sync_ranks()
        sync_promotions()
        sync_mp_batches()
        sync_mp_trans(full_sync=False)
        sync_mpc_club_membership_history()

