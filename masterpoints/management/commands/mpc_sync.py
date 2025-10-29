import sys

from django.core.management.base import BaseCommand

from accounts.models import User
from masterpoints.factories import masterpoint_query_list
from masterpoints.models import ChargeType, MasterpointEvent
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


def sync_events():
    """Events -> MasterpointEvent"""

    print("Syncing Events...")
    for event in masterpoint_query_list("mpci-events"):
        item, _ = MasterpointEvent.objects.get_or_create(old_mpc_id=event["EventID"])
        item.event_code = event["EventCode"]
        item.event_name = event["EventName"]
        item.mp_colour = event["MPColour"]
        item.comments = event["Comments"]
        item.is_closed = event["IsClosed"] == "Y"
        item.billing_club_id = event["BillingClubID"]
        item.t_grade = event["tGrade"]
        item.grade = event["Grade"]
        item.gold_point_event_tier = event["GoldPointEventTier"]
        item.added_by_id = SYSTEM_ACCOUNT.id

        organisation = Organisation.objects.filter(org_id=item.billing_club_id).first()

        if not organisation:
            print(f"Organisation with id={item.billing_club_id} not found. Exiting.")
            continue

        item.billing_organisation = organisation
        print(item.billing_organisation)

        item.save()


def sync_clubs():
    """Sync missing clubs and additional data"""

    for org in masterpoint_query_list("mpci-clubs"):
        item, created = Organisation.objects.get_or_create(org_id=org["ClubNumber"])

        if created:
            item.name = org["ClubName"]
            item.club_email = org["ClubEmail"]
            item.club_website = org["ClubWebsite"]
            # Fix later
            item.secretary_id = 3
            item.save()
            print(f"Created club club number is {item.org_id} pk={item.id} {item.name}")


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Running mpc_sync")

        sync_clubs()
        # sync_charge_types()
        # sync_events()
