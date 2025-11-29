from time import strptime

import xlsxwriter
from django.db.models import Q
from django.http import HttpResponse

from club_sessions.models import Session
from cobalt.settings import GLOBAL_CURRENCY_SYMBOL
from events.models import Event
from payments.models import OrganisationTransaction
from payments.views.org_report.data import (
    organisation_transactions_by_date_range,
    event_payments_summary_by_date_range,
    sessions_and_payments_by_date_range,
    combined_view_events_sessions_other,
    club_membership_summary_by_date_range,
)
from payments.views.org_report.utils import start_end_date_to_datetime
from utils.views.xls import XLSXStyles


def _organisation_transactions_xls_header(
    request, club, sheet, formats, title, subtitle, subtitle_style, width
):
    """Add a title to a sheet"""

    # Put cursor away from title
    sheet.set_selection(10, 0, 10, 0)

    # Title
    sheet.merge_range(0, 0, 3, width, club.name, formats.h1_info)
    sheet.merge_range(4, 0, 4, width, title, formats.h2_info)
    sheet.merge_range(
        5, 0, 5, width, f"Downloaded by {request.user.full_name}", formats.h3_info
    )
    sheet.merge_range(6, 0, 9, width, subtitle, subtitle_style)

    # Buffer
    sheet.merge_range(10, 0, 10, width, "")


def _details_headings(details_sheet, formats, show_balance=True):
    """common headings for details and combined view"""

    # Now do data headings
    details_sheet.write(11, 0, "Date/Time", formats.detail_row_title)
    details_sheet.set_column("A:A", 25)
    details_sheet.write(11, 1, "Counterparty", formats.detail_row_title)
    details_sheet.set_column("B:B", 35)
    details_sheet.write(11, 2, "Reference", formats.detail_row_title)
    details_sheet.set_column("C:C", 25)
    details_sheet.write(11, 3, "Id", formats.detail_row_title_number)
    details_sheet.set_column("D:D", 10)
    details_sheet.write(11, 4, "Transaction Type", formats.detail_row_title)
    details_sheet.set_column("E:E", 25)
    details_sheet.write(11, 5, "Description", formats.detail_row_title)
    details_sheet.set_column("F:F", 60)
    details_sheet.write(11, 6, "Session ID", formats.detail_row_title_number)
    details_sheet.set_column("G:G", 20)
    details_sheet.write(11, 7, "Session Name", formats.detail_row_title)
    details_sheet.set_column("H:H", 60)
    details_sheet.write(11, 8, "Event ID", formats.detail_row_title_number)
    details_sheet.set_column("I:I", 15)
    details_sheet.write(11, 9, "Event Name", formats.detail_row_title)
    details_sheet.set_column("J:J", 60)
    details_sheet.write(11, 10, "Amount", formats.detail_row_title_number)
    details_sheet.set_column("K:K", 15)
    if show_balance:
        details_sheet.write(11, 11, "Balance", formats.detail_row_title_number)
        details_sheet.set_column("L:L", 15)


def _organisation_transactions_xls_download_details(
    formats, details_sheet, request, club, start_date, end_date, description_search=None
):
    """sub of organisation_transactions_xls_download to handle the details tab"""

    _organisation_transactions_xls_header(
        request,
        club,
        details_sheet,
        formats,
        title=f"Download for {start_date} to {end_date}",
        subtitle="Transactions",
        subtitle_style=formats.h1_success,
        width=11,
    )

    # Now do data headings
    _details_headings(details_sheet, formats)

    # write warning
    if description_search:
        details_sheet.write(
            10,
            0,
            f"Description search is '{description_search}'. This only applies to this tab.",
            formats.h3_primary,
        )

    # Get data
    organisation_transactions = organisation_transactions_by_date_range(
        club, start_date, end_date, description_search
    )

    # Data rows
    for row_no, org_tran in enumerate(organisation_transactions, start=12):
        details_sheet.write(row_no, 0, org_tran.formatted_date, formats.detail_row_data)
        details_sheet.write(row_no, 1, org_tran.counterparty, formats.detail_row_data)
        details_sheet.write(row_no, 2, org_tran.reference_no, formats.detail_row_data)
        details_sheet.write(row_no, 3, org_tran.id, formats.detail_row_number)
        details_sheet.write(row_no, 4, org_tran.type, formats.detail_row_data)
        details_sheet.write(row_no, 5, org_tran.description, formats.detail_row_data)
        details_sheet.write(
            row_no, 6, org_tran.club_session_id, formats.detail_row_number
        )
        details_sheet.write(
            row_no, 7, org_tran.club_session_name, formats.detail_row_data
        )
        details_sheet.write(row_no, 8, org_tran.event_id, formats.detail_row_number)
        details_sheet.write(row_no, 9, org_tran.event_name, formats.detail_row_data)
        details_sheet.write(row_no, 10, org_tran.amount, formats.detail_row_money)
        details_sheet.write(row_no, 11, org_tran.balance, formats.detail_row_money)


def _organisation_transactions_xls_download_combined(
    formats, details_sheet, request, club, start_date, end_date
):
    """sub of organisation_transactions_xls_download to handle the combined tab"""

    _organisation_transactions_xls_header(
        request,
        club,
        details_sheet,
        formats,
        title=f"Download for {start_date} to {end_date}",
        subtitle="Combined",
        subtitle_style=formats.h1_success,
        width=10,
    )

    # Now do data headings
    _details_headings(details_sheet, formats, show_balance=False)

    # write warning
    details_sheet.write(
        10,
        0,
        "Events and Sessions use their start date, payments can occur on different dates.",
        formats.h3_primary,
    )

    # Get data
    organisation_transactions = combined_view_events_sessions_other(
        club, start_date, end_date
    )

    # Data rows
    for row_no, org_tran_tuple in enumerate(organisation_transactions, start=12):
        org_tran = org_tran_tuple[1]
        details_sheet.write(
            row_no, 0, org_tran.get("formatted_date", ""), formats.detail_row_data
        )
        details_sheet.write(
            row_no, 1, org_tran.get("counterparty", "Multiple"), formats.detail_row_data
        )
        details_sheet.write(
            row_no, 2, org_tran.get("reference_no", "-"), formats.detail_row_data
        )
        details_sheet.write(
            row_no, 3, org_tran.get("id", "-"), formats.detail_row_number
        )
        details_sheet.write(
            row_no, 4, org_tran.get("type", ""), formats.detail_row_data
        )
        details_sheet.write(
            row_no, 5, org_tran.get("description", ""), formats.detail_row_data
        )
        details_sheet.write(
            row_no, 6, org_tran.get("club_session_id", ""), formats.detail_row_number
        )
        details_sheet.write(
            row_no, 7, org_tran.get("club_session_name", ""), formats.detail_row_data
        )
        details_sheet.write(
            row_no, 8, org_tran.get("event_id", ""), formats.detail_row_number
        )
        details_sheet.write(
            row_no, 9, org_tran.get("event_name", ""), formats.detail_row_data
        )
        details_sheet.write(
            row_no, 10, org_tran.get("amount", ""), formats.detail_row_money
        )
        if "amount_outside_range" in org_tran:
            msg = f"Payments of {GLOBAL_CURRENCY_SYMBOL}{org_tran['amount_outside_range']} were made outside the date range"
            details_sheet.write(row_no, 11, msg, formats.warning_message)
            details_sheet.set_column("L:L", 100)


def _organisation_transactions_xls_download_membership(
    formats, details_sheet, request, club, start_date, end_date
):
    """sub of organisation_transactions_xls_download to handle the membership tab"""

    _organisation_transactions_xls_header(
        request,
        club,
        details_sheet,
        formats,
        title=f"Download for {start_date} to {end_date}",
        subtitle="Memberships",
        subtitle_style=formats.h1_success,
        width=10,
    )

    # Now do data headings
    _details_headings(details_sheet, formats, show_balance=False)

    # Get data
    start_datetime, end_datetime = start_end_date_to_datetime(start_date, end_date)

    membership_transactions = OrganisationTransaction.objects.filter(
        organisation=club,
        created_date__gte=start_datetime,
        created_date__lte=end_datetime,
        type="Club Membership",
    )

    # Data rows
    for row_no, org_tran in enumerate(membership_transactions, start=12):
        details_sheet.write(
            row_no,
            0,
            org_tran.created_date.strftime("%Y-%m-%d %H:%M:%S"),
            formats.detail_row_data,
        )
        details_sheet.write(
            row_no, 1, org_tran.member.full_name, formats.detail_row_data
        )
        details_sheet.write(row_no, 2, org_tran.reference_no, formats.detail_row_data)
        details_sheet.write(row_no, 3, org_tran.id, formats.detail_row_number)
        details_sheet.write(row_no, 4, org_tran.type, formats.detail_row_data)
        details_sheet.write(row_no, 5, org_tran.description, formats.detail_row_data)
        details_sheet.write(row_no, 6, "", formats.detail_row_data)
        details_sheet.write(row_no, 7, "", formats.detail_row_data)
        details_sheet.write(row_no, 8, "", formats.detail_row_data)
        details_sheet.write(row_no, 9, "", formats.detail_row_data)
        details_sheet.write(row_no, 10, org_tran.amount, formats.detail_row_money)


def _organisation_transactions_xls_download_other(
    formats, details_sheet, request, club, start_date, end_date
):
    """sub of organisation_transactions_xls_download to handle the other tab"""

    _organisation_transactions_xls_header(
        request,
        club,
        details_sheet,
        formats,
        title=f"Download for {start_date} to {end_date}",
        subtitle="Other",
        subtitle_style=formats.h1_success,
        width=10,
    )

    # Now do data headings
    _details_headings(details_sheet, formats, show_balance=False)

    # Get data
    start_datetime, end_datetime = start_end_date_to_datetime(start_date, end_date)

    other_transactions = (
        OrganisationTransaction.objects.filter(
            organisation=club,
            created_date__gte=start_datetime,
            created_date__lte=end_datetime,
        )
        .exclude(
            type__in=[
                "Settlement",
                "Club Payment",
                "Club Membership",
            ]
        )
        .exclude(club_session_id__isnull=False)
        .exclude(
            Q(type__in=["Entry to an event", "Refund"]) & Q(event_id__isnull=False)
        )
    )

    # Get session names
    session_ids = []
    for item in other_transactions:
        if item.club_session_id and item.club_session_id not in session_ids:
            session_ids.append(item.club_session_id)

    sessions = Session.objects.filter(id__in=session_ids)

    sessions_dict = {session.id: session.description for session in sessions}

    # Get event names
    event_ids = []
    for item in other_transactions:
        if item.event_id and item.event_id not in event_ids:
            event_ids.append(item.event_id)

    events = Event.objects.filter(id__in=event_ids).select_related("congress")
    events_dict = {
        event.id: f"{event.congress} - {event.event_name}" for event in events
    }

    # Data rows
    for row_no, other_tran in enumerate(other_transactions, start=12):
        details_sheet.write(
            row_no,
            0,
            other_tran.created_date.strftime("%Y-%m-%d %H:%M:%S"),
            formats.detail_row_data,
        )
        details_sheet.write(
            row_no, 1, other_tran.member.full_name, formats.detail_row_data
        )
        details_sheet.write(row_no, 2, other_tran.reference_no, formats.detail_row_data)
        details_sheet.write(row_no, 3, other_tran.id, formats.detail_row_number)
        details_sheet.write(row_no, 4, other_tran.type, formats.detail_row_data)
        details_sheet.write(row_no, 5, other_tran.description, formats.detail_row_data)
        details_sheet.write(
            row_no, 6, other_tran.club_session_id, formats.detail_row_data
        )

        if other_tran.club_session_id:
            session_name = sessions_dict.get(
                other_tran.club_session_id, "Unknown session - may be deleted"
            )
        else:
            session_name = ""

        details_sheet.write(row_no, 7, session_name, formats.detail_row_data)
        details_sheet.write(row_no, 8, other_tran.event_id, formats.detail_row_data)

        if other_tran.event_id:
            event_name = events_dict.get(
                other_tran.event_id, "Unknown event - may be deleted"
            )
        else:
            event_name = ""

        details_sheet.write(row_no, 9, event_name, formats.detail_row_data)
        details_sheet.write(row_no, 10, other_tran.amount, formats.detail_row_money)


def _organisation_transactions_xls_download_sessions(
    formats, sessions_sheet, request, club, start_date, end_date
):
    """sub of organisation_transactions_xls_download to handle the sessions tab"""

    # Add main heading
    _organisation_transactions_xls_header(
        request,
        club,
        sessions_sheet,
        formats,
        title=f"Download for {start_date} to {end_date}",
        subtitle="Sessions",
        subtitle_style=formats.h1_primary,
        width=3,
    )

    # Now do data headings
    sessions_sheet.write(11, 0, "Session Date", formats.detail_row_title)
    sessions_sheet.set_column("A:A", 35)
    sessions_sheet.write(11, 1, "Session ID", formats.detail_row_title_number)
    sessions_sheet.set_column("B:B", 20)
    sessions_sheet.write(11, 2, "Session Name", formats.detail_row_title)
    sessions_sheet.set_column("C:C", 60)
    sessions_sheet.write(11, 3, "Amount", formats.detail_row_title_number)
    sessions_sheet.set_column("D:D", 15)

    # write warning
    sessions_sheet.write(
        10,
        0,
        "This has data for session within the date range. Payments may have occurred outside the date range.",
        formats.h3_primary,
    )

    # Get sessions in this date range and associated payments
    sessions_in_range, payments_dict = sessions_and_payments_by_date_range(
        club, start_date, end_date
    )

    # write data
    for row_no, session_in_range_id in enumerate(sessions_in_range, start=12):

        amount = payments_dict.get(session_in_range_id, "No Payments")

        sessions_sheet.write(
            row_no,
            0,
            f"{sessions_in_range[session_in_range_id].session_date}",
            formats.detail_row_data,
        )
        sessions_sheet.write(row_no, 1, session_in_range_id, formats.detail_row_number)
        sessions_sheet.write(
            row_no,
            2,
            sessions_in_range[session_in_range_id].description,
            formats.detail_row_data,
        )
        sessions_sheet.write(row_no, 3, amount, formats.detail_row_money)


def _organisation_transactions_xls_download_movements(
    formats, movement_sheet, request, club, start_date, end_date
):
    """sub of organisation_transactions_xls_download to handle the movement report tab"""

    from organisations.views.club_menu_tabs.finance import (
        organisation_transactions_filtered_data_movement_queries,
    )

    # Add main heading
    _organisation_transactions_xls_header(
        request,
        club,
        movement_sheet,
        formats,
        title=f"Download for {start_date} to {end_date}",
        subtitle="Movement Summary",
        subtitle_style=formats.h1_primary,
        width=2,
    )

    # Now do data headings
    movement_sheet.write(11, 0, "Type", formats.detail_row_title)
    movement_sheet.set_column("A:A", 55)
    movement_sheet.write(11, 1, "Date", formats.detail_row_title_number)
    movement_sheet.set_column("B:B", 30)
    movement_sheet.write(11, 2, "Amount", formats.detail_row_title_number)
    movement_sheet.set_column("C:C", 40)

    # Get movement summary
    # Get data
    (
        opening_balance,
        closing_balance,
        settlements,
        events_total,
        sessions_total,
        club_memberships,
        other_adjustments,
    ) = organisation_transactions_filtered_data_movement_queries(
        club, start_date, end_date
    )

    # write data
    movement_sheet.write(12, 0, "Opening Balance", formats.detail_row_data)
    movement_sheet.write(12, 1, start_date, formats.detail_row_number)
    movement_sheet.write(12, 2, opening_balance, formats.detail_row_money)

    movement_sheet.write(13, 0, "Settlements", formats.detail_row_data)
    movement_sheet.write(13, 1, "", formats.detail_row_data)
    movement_sheet.write(13, 2, settlements["total"] or 0, formats.detail_row_money)

    movement_sheet.write(14, 0, "Event Entries", formats.detail_row_data)
    movement_sheet.write(14, 1, "", formats.detail_row_data)
    movement_sheet.write(14, 2, events_total, formats.detail_row_money)

    movement_sheet.write(15, 0, "Club Sessions", formats.detail_row_data)
    movement_sheet.write(15, 1, "", formats.detail_row_data)
    movement_sheet.write(15, 2, sessions_total, formats.detail_row_money)

    movement_sheet.write(16, 0, "Club Memberships", formats.detail_row_data)
    movement_sheet.write(16, 1, "", formats.detail_row_data)
    movement_sheet.write(
        16, 2, club_memberships["total"] or 0, formats.detail_row_money
    )

    movement_sheet.write(17, 0, "Other", formats.detail_row_data)
    movement_sheet.write(17, 1, "", formats.detail_row_data)
    movement_sheet.write(
        17, 2, other_adjustments["total"] or 0, formats.detail_row_money
    )

    movement_sheet.write(18, 0, "Closing Balance", formats.detail_row_data)
    movement_sheet.write(18, 1, end_date, formats.detail_row_number)
    movement_sheet.write(18, 2, closing_balance, formats.detail_row_money)


def _organisation_transactions_xls_download_events(
    formats, sessions_sheet, request, club, start_date, end_date
):
    """sub of organisation_transactions_xls_download to handle the events tab"""

    # Add main heading
    _organisation_transactions_xls_header(
        request,
        club,
        sessions_sheet,
        formats,
        title=f"Download for {start_date} to {end_date}",
        subtitle="Events",
        subtitle_style=formats.h1_warning,
        width=4,
    )

    # Now do data headings
    sessions_sheet.write(11, 0, "Event Start Date", formats.detail_row_title)
    sessions_sheet.set_column("A:A", 35)
    sessions_sheet.write(11, 1, "Event ID", formats.detail_row_title_number)
    sessions_sheet.set_column("B:B", 20)
    sessions_sheet.write(11, 2, "Congress", formats.detail_row_title)
    sessions_sheet.set_column("C:C", 60)
    sessions_sheet.write(11, 3, "Event Name", formats.detail_row_title)
    sessions_sheet.set_column("D:D", 60)
    sessions_sheet.write(11, 4, "Amount", formats.detail_row_title_number)
    sessions_sheet.set_column("E:E", 15)

    # Get sessions in this date range and associated payments
    event_data = event_payments_summary_by_date_range(club, start_date, end_date)

    # write data
    for row_no, event_id in enumerate(event_data, start=12):

        print(event_data[event_id]["start_date"])

        sessions_sheet.write(
            row_no, 0, f"{event_data[event_id]['start_date']}", formats.detail_row_data
        )
        sessions_sheet.write(row_no, 1, event_id, formats.detail_row_number)
        sessions_sheet.write(
            row_no, 2, event_data[event_id]["congress_name"], formats.detail_row_data
        )
        sessions_sheet.write(
            row_no, 3, event_data[event_id]["event_name"], formats.detail_row_data
        )
        sessions_sheet.write(
            row_no, 4, event_data[event_id]["amount"], formats.detail_row_money
        )

        if event_data[event_id]["amount_outside_range"] != 0:
            msg = f"Payments of {GLOBAL_CURRENCY_SYMBOL}{event_data[event_id]['amount_outside_range']} were made outside the date range"
            sessions_sheet.write(row_no, 5, msg, formats.warning_message)
            sessions_sheet.set_column("F:F", 100)


def organisation_transactions_xls_download(
    request, club, start_date, end_date, description_search=None
):
    """Download XLS File of org transactions"""

    # Create HttpResponse to put the Excel file into
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="statement.xlsx"'

    # Create an Excel file and add worksheets
    workbook = xlsxwriter.Workbook(response)
    movement_sheet = workbook.add_worksheet("Movement Summary")
    details_sheet = workbook.add_worksheet("Transactions")
    sessions_sheet = workbook.add_worksheet("Sessions")
    events_sheet = workbook.add_worksheet("Events")
    combined_sheet = workbook.add_worksheet("Combined")
    membership_sheet = workbook.add_worksheet("Membership")
    other_sheet = workbook.add_worksheet("Other")

    # Create styles
    formats = XLSXStyles(workbook)

    # Movements Summary tab
    _organisation_transactions_xls_download_movements(
        formats, movement_sheet, request, club, start_date, end_date
    )

    # Details tab
    _organisation_transactions_xls_download_details(
        formats, details_sheet, request, club, start_date, end_date
    )

    # Sessions tab
    _organisation_transactions_xls_download_sessions(
        formats, sessions_sheet, request, club, start_date, end_date
    )

    # Events tab
    _organisation_transactions_xls_download_events(
        formats, events_sheet, request, club, start_date, end_date
    )

    # Combination tab
    _organisation_transactions_xls_download_combined(
        formats, combined_sheet, request, club, start_date, end_date
    )

    # Membership tab
    _organisation_transactions_xls_download_membership(
        formats, membership_sheet, request, club, start_date, end_date
    )

    # Other tab
    _organisation_transactions_xls_download_other(
        formats, other_sheet, request, club, start_date, end_date
    )

    workbook.close()

    return response
