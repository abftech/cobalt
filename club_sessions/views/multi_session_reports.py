import csv
import datetime
from decimal import Decimal

import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from club_sessions.models import Session, SessionEntry, SessionMiscPayment, SessionType
from club_sessions.views.core import SITOUT

from organisations.models import Organisation
from payments.models import OrgPaymentMethod
from rbac.core import rbac_user_has_role
from rbac.views import rbac_forbidden
from utils.views.xls import XLSXStyles

ALLOWED_USERS = [4, 72, 3844, 286, 128, 5999]
PAGE_SIZE = 25


def _check_access(request, club):
    if request.user.id not in ALLOWED_USERS:
        return HttpResponseForbidden("Access not yet available")
    club_role = f"club_sessions.sessions.{club.id}.edit"
    if not rbac_user_has_role(request.user, club_role):
        return rbac_forbidden(request, club_role)
    return None


def _reference_dates():
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    last_month = today.replace(day=1) - datetime.timedelta(days=1)
    first_of_last_month_str = f"{last_month.strftime('%Y-%m')}-01"
    last_of_last_month_str = last_month.strftime("%Y-%m-%d")
    first_of_last_year_str = datetime.date(
        int(today.strftime("%Y")) - 1, 1, 1
    ).strftime("%Y-%m-%d")
    last_of_last_year_str = datetime.date(
        int(today.strftime("%Y")) - 1, 12, 31
    ).strftime("%Y-%m-%d")
    return {
        "Month to date": (f"{today.strftime('%Y-%m')}-01", today_str),
        "Year to date": (f"{today.strftime('%Y')}-01-01", today_str),
        "Last Month": (first_of_last_month_str, last_of_last_month_str),
        "Last Year": (first_of_last_year_str, last_of_last_year_str),
        "All": ("1901-01-01", today_str),
    }


def _get_sessions_in_range(club, start_date, end_date, session_type_filter):
    qs = (
        Session.objects.filter(
            session_type__organisation=club,
            session_date__range=(start_date, end_date),
        )
        .select_related("director", "session_type")
        .order_by("session_date", "pk")
    )
    if session_type_filter and session_type_filter != "all":
        qs = qs.filter(session_type__name=session_type_filter)
    return qs


def _get_all_payment_methods(sessions):
    return sorted(
        OrgPaymentMethod.objects.filter(sessionentry__session__in=sessions)
        .values_list("payment_method", flat=True)
        .distinct()
    )


def _build_player_number_data(sessions, payment_methods):
    rows = []
    total_pm = [0] * len(payment_methods)
    total_tables = Decimal(0)
    total_unprocessed = 0
    total_players = 0

    for session in sessions:
        entries = SessionEntry.objects.filter(session=session).exclude(
            system_number=SITOUT
        )
        player_count = entries.count()
        tables = Decimal(player_count) / 4

        pm_values = []
        for i, pm in enumerate(payment_methods):
            count = entries.filter(payment_method__payment_method=pm).count()
            pm_values.append(count)
            total_pm[i] += count

        unprocessed = entries.filter(is_paid=False).exclude(fee=0).count()

        rows.append(
            {
                "session": session,
                "tables": tables,
                "pm_values": pm_values,
                "unprocessed": unprocessed,
                "total": player_count,
            }
        )

        total_tables += tables
        total_unprocessed += unprocessed
        total_players += player_count

    totals = {
        "sessions": len(rows),
        "tables": total_tables,
        "pm_values": total_pm,
        "unprocessed": total_unprocessed,
        "total": total_players,
    }
    return rows, totals


def _build_dollar_value_data(sessions, payment_methods):
    blocks = []
    grand_pm = [Decimal(0)] * len(payment_methods)
    grand_tables = Decimal(0)
    grand_unprocessed = Decimal(0)
    grand_total = Decimal(0)

    for session in sessions:
        entries = SessionEntry.objects.filter(session=session).exclude(
            system_number=SITOUT
        )
        player_count = entries.count()
        tables = Decimal(player_count) / 4

        pm_amounts = []
        for pm in payment_methods:
            amount = entries.filter(payment_method__payment_method=pm).aggregate(
                s=Sum("fee")
            )["s"] or Decimal(0)
            pm_amounts.append(amount)

        unprocessed_fees = entries.filter(is_paid=False).aggregate(s=Sum("fee"))[
            "s"
        ] or Decimal(0)
        session_table_total = entries.aggregate(s=Sum("fee"))["s"] or Decimal(0)

        extras_qs = (
            SessionMiscPayment.objects.filter(session_entry__session=session)
            .values("description", "payment_method__payment_method")
            .annotate(total=Sum("amount"))
            .order_by("description")
        )
        extras_by_desc_dict = {}
        for row in extras_qs:
            desc = row["description"]
            pm = row["payment_method__payment_method"]
            if desc not in extras_by_desc_dict:
                extras_by_desc_dict[desc] = {p: Decimal(0) for p in payment_methods}
                extras_by_desc_dict[desc]["row_total"] = Decimal(0)
            if pm in extras_by_desc_dict[desc]:
                extras_by_desc_dict[desc][pm] += row["total"]
            extras_by_desc_dict[desc]["row_total"] += row["total"]

        extras_by_desc = []
        extras_pm_totals = [Decimal(0)] * len(payment_methods)
        for desc, data in extras_by_desc_dict.items():
            pm_list = [data.get(pm, Decimal(0)) for pm in payment_methods]
            for i, v in enumerate(pm_list):
                extras_pm_totals[i] += v
            extras_by_desc.append(
                {"desc": desc, "pm_values": pm_list, "row_total": data["row_total"]}
            )

        extras_unprocessed = SessionMiscPayment.objects.filter(
            session_entry__session=session, payment_made=False
        ).aggregate(s=Sum("amount"))["s"] or Decimal(0)
        total_unprocessed = unprocessed_fees + extras_unprocessed
        extras_total = sum(extras_pm_totals)
        grand_session_total = session_table_total + extras_total
        combined_pm = [
            pm_amounts[i] + extras_pm_totals[i] for i in range(len(payment_methods))
        ]

        blocks.append(
            {
                "session": session,
                "tables": tables,
                "pm_amounts": pm_amounts,
                "combined_pm": combined_pm,
                "unprocessed": total_unprocessed,
                "session_total": session_table_total,
                "grand_session_total": grand_session_total,
                "extras_by_desc": extras_by_desc,
            }
        )

        grand_tables += tables
        grand_unprocessed += total_unprocessed
        grand_total += grand_session_total
        for i in range(len(payment_methods)):
            grand_pm[i] += combined_pm[i]

    grand = {
        "tables": grand_tables,
        "pm_values": grand_pm,
        "unprocessed": grand_unprocessed,
        "total": grand_total,
    }
    return blocks, grand


@login_required()
def multi_session_report(request, club_id):
    """Full-page view: renders the filter form only. Results loaded via HTMX."""
    club = get_object_or_404(Organisation, pk=club_id)

    denied = _check_access(request, club)
    if denied:
        return denied

    reference_dates = _reference_dates()
    session_types = (
        SessionType.objects.filter(organisation=club)
        .values_list("name", flat=True)
        .distinct()
    )

    return render(
        request,
        "club_sessions/reports/multi_session_report.html",
        {
            "club": club,
            "reference_dates": reference_dates,
            "session_types": session_types,
        },
    )


@login_required()
def multi_session_report_results(request, club_id):
    """HTMX endpoint: returns paginated results HTML fragment."""
    club = get_object_or_404(Organisation, pk=club_id)

    denied = _check_access(request, club)
    if denied:
        return denied

    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")
    view_type = request.POST.get("view_type", "player_numbers")
    session_type_filter = request.POST.get("session_type_filter", "all")
    page_number = request.POST.get("page", 1)

    if not start_date or not end_date:
        return HttpResponse("")

    sessions = _get_sessions_in_range(club, start_date, end_date, session_type_filter)
    payment_methods = _get_all_payment_methods(sessions)

    if view_type == "player_numbers":
        rows, totals = _build_player_number_data(sessions, payment_methods)
        paginator = Paginator(rows, PAGE_SIZE)
        page_obj = paginator.get_page(page_number)
        return render(
            request,
            "club_sessions/reports/multi_session_results_player_numbers.html",
            {
                "club": club,
                "payment_methods": payment_methods,
                "page_obj": page_obj,
                "totals": totals,
                "start_date": start_date,
                "end_date": end_date,
                "view_type": view_type,
                "session_type_filter": session_type_filter,
            },
        )
    else:
        blocks, grand = _build_dollar_value_data(sessions, payment_methods)
        paginator = Paginator(blocks, PAGE_SIZE)
        page_obj = paginator.get_page(page_number)
        return render(
            request,
            "club_sessions/reports/multi_session_results_dollar_values.html",
            {
                "club": club,
                "payment_methods": payment_methods,
                "page_obj": page_obj,
                "grand": grand,
                "start_date": start_date,
                "end_date": end_date,
                "view_type": view_type,
                "session_type_filter": session_type_filter,
            },
        )


@login_required()
def multi_session_report_xlsx(request, club_id):
    """XLSX download."""
    club = get_object_or_404(Organisation, pk=club_id)

    denied = _check_access(request, club)
    if denied:
        return denied

    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")
    view_type = request.POST.get("view_type", "player_numbers")
    session_type_filter = request.POST.get("session_type_filter", "all")

    if not start_date or not end_date:
        return HttpResponse("Missing dates")

    sessions = _get_sessions_in_range(club, start_date, end_date, session_type_filter)
    payment_methods = _get_all_payment_methods(sessions)
    return _xlsx_download(
        request, club, sessions, payment_methods, view_type, start_date, end_date
    )


@login_required()
def multi_session_report_csv(request, club_id):
    """CSV download."""
    club = get_object_or_404(Organisation, pk=club_id)

    denied = _check_access(request, club)
    if denied:
        return denied

    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")
    view_type = request.POST.get("view_type", "player_numbers")
    session_type_filter = request.POST.get("session_type_filter", "all")

    if not start_date or not end_date:
        return HttpResponse("Missing dates")

    sessions = _get_sessions_in_range(club, start_date, end_date, session_type_filter)
    payment_methods = _get_all_payment_methods(sessions)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="session_report_{start_date}_to_{end_date}.csv"'
    )
    writer = csv.writer(response)

    headers = (
        ["Description", "Date", "Time", "Director", "Type", "Tables"]
        + payment_methods
        + ["Unprocessed", "Total"]
    )

    if view_type == "player_numbers":
        rows, totals = _build_player_number_data(sessions, payment_methods)
        writer.writerow(
            [club.name, f"Session Report: {start_date} to {end_date}", "Player Numbers"]
        )
        writer.writerow([])
        writer.writerow(headers)
        for r in rows:
            s = r["session"]
            writer.writerow(
                [
                    s.description,
                    s.session_date,
                    s.time_of_day,
                    str(s.director) if s.director else "",
                    s.session_type.name,
                    r["tables"],
                ]
                + r["pm_values"]
                + [r["unprocessed"], r["total"]]
            )
        writer.writerow(
            [
                f"Totals ({totals['sessions']} sessions)",
                "",
                "",
                "",
                "",
                totals["tables"],
            ]
            + totals["pm_values"]
            + [totals["unprocessed"], totals["total"]]
        )

    else:
        blocks, grand = _build_dollar_value_data(sessions, payment_methods)
        writer.writerow(
            [club.name, f"Session Report: {start_date} to {end_date}", "Dollar Values"]
        )
        writer.writerow([])
        writer.writerow(headers)
        for block in blocks:
            s = block["session"]
            writer.writerow(
                [
                    s.description,
                    s.session_date,
                    s.time_of_day,
                    str(s.director) if s.director else "",
                    s.session_type.name,
                    block["tables"],
                ]
                + [float(v) for v in block["pm_amounts"]]
                + [float(block["unprocessed"]), float(block["session_total"])]
            )
            for extra in block["extras_by_desc"]:
                writer.writerow(
                    [f"  {extra['desc']}", "", "", "", "", ""]
                    + [float(v) for v in extra["pm_values"]]
                    + ["", float(extra["row_total"])]
                )
            writer.writerow(
                ["Session Total", "", "", "", "", float(block["tables"])]
                + [float(v) for v in block["combined_pm"]]
                + [float(block["unprocessed"]), float(block["grand_session_total"])]
            )
            writer.writerow([])
        writer.writerow(
            [
                f"Grand Total: {start_date} to {end_date}",
                "",
                "",
                "",
                "",
                float(grand["tables"]),
            ]
            + [float(v) for v in grand["pm_values"]]
            + [float(grand["unprocessed"]), float(grand["total"])]
        )

    return response


def _xlsx_download(
    request, club, sessions, payment_methods, view_type, start_date, end_date
):
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="session_report_{start_date}_to_{end_date}.xlsx"'
    )

    workbook = xlsxwriter.Workbook(response)
    formats = XLSXStyles(workbook)
    sheet = workbook.add_worksheet("Session Report")
    sheet.set_selection(6, 0, 6, 0)

    col_count = len(payment_methods) + 7
    sheet.merge_range(0, 0, 3, col_count, club.name, formats.h1)
    sheet.merge_range(
        4, 0, 4, col_count, f"Session Report: {start_date} to {end_date}", formats.h2
    )
    sheet.merge_range(
        5, 0, 5, col_count, f"Downloaded by {request.user.full_name}", formats.h3
    )
    sheet.merge_range(6, 0, 6, col_count, "")

    headers = (
        ["Description", "Date", "Time", "Director", "Type", "Tables"]
        + payment_methods
        + ["Unprocessed", "Total"]
    )
    row = 7
    for col, header in enumerate(headers):
        sheet.write(row, col, header, formats.detail_row_title)

    # Fixed widths for the first six columns
    sheet.set_column(0, 0, 50)  # Description
    sheet.set_column(1, 1, 14)  # Date
    sheet.set_column(2, 2, 12)  # Time
    sheet.set_column(3, 3, 30)  # Director
    sheet.set_column(4, 4, 20)  # Type
    sheet.set_column(5, 5, 10)  # Tables
    # Payment method columns: wide enough for the header text
    for i, pm in enumerate(payment_methods):
        sheet.set_column(6 + i, 6 + i, max(len(pm) + 4, 16))
    # Unprocessed and Total
    sheet.set_column(
        6 + len(payment_methods), 6 + len(payment_methods), 16
    )  # Unprocessed
    sheet.set_column(7 + len(payment_methods), 7 + len(payment_methods), 10)  # Total

    row += 1

    pm_col_offset = 6
    pm_count = len(payment_methods)

    if view_type == "player_numbers":
        rows, totals = _build_player_number_data(sessions, payment_methods)
        for r in rows:
            s = r["session"]
            sheet.write(row, 0, s.description, formats.detail_row_data)
            sheet.write(row, 1, str(s.session_date), formats.detail_row_data)
            sheet.write(row, 2, s.time_of_day, formats.detail_row_data)
            sheet.write(
                row, 3, str(s.director) if s.director else "", formats.detail_row_data
            )
            sheet.write(row, 4, s.session_type.name, formats.detail_row_data)
            sheet.write(row, 5, float(r["tables"]), formats.detail_row_number)
            for i, val in enumerate(r["pm_values"]):
                sheet.write(row, pm_col_offset + i, val, formats.detail_row_number)
            sheet.write(
                row,
                pm_col_offset + pm_count,
                r["unprocessed"],
                formats.detail_row_number,
            )
            sheet.write(
                row, pm_col_offset + pm_count + 1, r["total"], formats.detail_row_number
            )
            row += 1

        sheet.write(
            row, 0, f"Totals ({totals['sessions']} sessions)", formats.detail_row_title
        )
        sheet.write(row, 5, float(totals["tables"]), formats.detail_row_number)
        for i, val in enumerate(totals["pm_values"]):
            sheet.write(row, pm_col_offset + i, val, formats.detail_row_number)
        sheet.write(
            row,
            pm_col_offset + pm_count,
            totals["unprocessed"],
            formats.detail_row_number,
        )
        sheet.write(
            row,
            pm_col_offset + pm_count + 1,
            totals["total"],
            formats.detail_row_number,
        )

    else:
        blocks, grand = _build_dollar_value_data(sessions, payment_methods)
        for block in blocks:
            s = block["session"]
            sheet.write(row, 0, s.description, formats.detail_row_data)
            sheet.write(row, 1, str(s.session_date), formats.detail_row_data)
            sheet.write(row, 2, s.time_of_day, formats.detail_row_data)
            sheet.write(
                row, 3, str(s.director) if s.director else "", formats.detail_row_data
            )
            sheet.write(row, 4, s.session_type.name, formats.detail_row_data)
            sheet.write(row, 5, float(block["tables"]), formats.detail_row_number)
            for i, val in enumerate(block["pm_amounts"]):
                sheet.write(
                    row, pm_col_offset + i, float(val), formats.detail_row_money
                )
            sheet.write(
                row,
                pm_col_offset + pm_count,
                float(block["unprocessed"]),
                formats.detail_row_money,
            )
            sheet.write(
                row,
                pm_col_offset + pm_count + 1,
                float(block["session_total"]),
                formats.detail_row_money,
            )
            row += 1

            for extra in block["extras_by_desc"]:
                sheet.write(row, 0, f"  {extra['desc']}", formats.detail_row_data)
                for i, val in enumerate(extra["pm_values"]):
                    sheet.write(
                        row, pm_col_offset + i, float(val), formats.detail_row_money
                    )
                sheet.write(
                    row,
                    pm_col_offset + pm_count + 1,
                    float(extra["row_total"]),
                    formats.detail_row_money,
                )
                row += 1

            sheet.write(row, 0, "Session Total", formats.detail_row_title)
            sheet.write(row, 5, float(block["tables"]), formats.detail_row_number)
            for i, val in enumerate(block["combined_pm"]):
                sheet.write(
                    row, pm_col_offset + i, float(val), formats.detail_row_money
                )
            sheet.write(
                row,
                pm_col_offset + pm_count,
                float(block["unprocessed"]),
                formats.detail_row_money,
            )
            sheet.write(
                row,
                pm_col_offset + pm_count + 1,
                float(block["grand_session_total"]),
                formats.detail_row_money,
            )
            row += 2

        sheet.write(
            row, 0, f"Grand Total: {start_date} to {end_date}", formats.detail_row_title
        )
        sheet.write(row, 5, float(grand["tables"]), formats.detail_row_number)
        for i, val in enumerate(grand["pm_values"]):
            sheet.write(row, pm_col_offset + i, float(val), formats.detail_row_money)
        sheet.write(
            row,
            pm_col_offset + pm_count,
            float(grand["unprocessed"]),
            formats.detail_row_money,
        )
        sheet.write(
            row,
            pm_col_offset + pm_count + 1,
            float(grand["total"]),
            formats.detail_row_money,
        )

    row += 3
    sheet.insert_image(
        row,
        0,
        "cobalt/static/assets/img/abftechlogo.png",
        {"x_scale": 0.17, "y_scale": 0.17},
    )

    workbook.close()
    return response
