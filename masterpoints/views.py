import calendar
import html
import io
from datetime import datetime, date
from json import JSONDecodeError

import requests
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, FileResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Image, Paragraph
from xhtml2pdf import pisa

from cobalt.settings import GLOBAL_MPSERVER
from .factories import masterpoint_factory_creator, masterpoint_query_list


#####
#
# This module is a little strange as it gets all of its data from
# an external source, not from our database.
#
# We use requests to access a node.js web service which connects
# to a SQL Server database. Confluence can tell you more
#
######


def masterpoint_query_local(query):
    """Generic function to talk to the masterpoints server and return data

    THIS IS A DUPLICATE OF THE FUNCTION IN UTILS/UTIL_VIEWS/MASTERPOINTS
    due to circular dependency problems.

    Takes in a SQLServer query e.g. "select count(*) from table"

    Returns an iterable, either an empty list or the response from the server.

    In case there is a problem connecting to the server, this will do everything it
    can to fail silently.

    """

    # Try to load data from MP Server

    try:
        response = requests.get(query, timeout=10).json()
    except Exception as exc:
        print(exc)
        response = []

    return response


def process_transactions(details, month, year):
    """
    Separate process and provisional details
    add formatting to the matchpoint numbers
    """
    provisional_details = []
    fixed_details = []
    month = int(month)
    year = int(year)
    for d in details:
        if d["PostingMonth"] >= month and d["PostingYear"] == year:
            provisional_details.append(d)
        else:
            fixed_details.append(d)
    return fixed_details, provisional_details


@login_required()
def masterpoints_detail(request, system_number=None, years=1, retry=False):
    if system_number is None:
        system_number = request.user.system_number

    # Get summary data
    qry = "%s/mps/%s" % (GLOBAL_MPSERVER, system_number)
    r = masterpoint_query_local(qry)

    if len(r) == 0:

        if retry:  # This isn't the first time we've been here
            messages.error(
                request,
                f"Masterpoints module unable to find entry for id: {system_number}",
                extra_tags="cobalt-message-error",
            )
            return redirect("dashboard:dashboard")

        # not found - set error and call this again
        messages.warning(
            request,
            f"No Masterpoints entry found for id: {system_number}",
            extra_tags="cobalt-message-warning",
        )
        return masterpoints_detail(request, retry=True)

    summary = r[0]

    # Set active to a boolean
    if summary["IsActive"] == "Y":
        summary["IsActive"] = True
    else:
        summary["IsActive"] = False

    # Get provisional month and year, anything this date or later is provisional
    #   qry = "%s/provisionaldate" % GLOBAL_MPSERVER
    #   data = requests.get(qry).json()[0]
    #   prov_month = "%02d" % int(data["month"])
    #   prov_year = data["year"]

    # Get home club name
    qry = "%s/club/%s" % (GLOBAL_MPSERVER, summary["HomeClubID"])
    club = requests.get(qry).json()[0]["ClubName"]

    # Get last year in YYYY-MM format
    dt = date.today()
    dt = dt.replace(year=dt.year - years)
    year = dt.strftime("%Y")
    month = dt.strftime("%m")

    # Get the detail list of recent activity
    qry = "%s/mpdetail/%s/postingyear/%s/postingmonth/%s" % (
        GLOBAL_MPSERVER,
        system_number,
        year,
        month,
    )
    details = requests.get(qry).json()

    counter = summary["TotalMPs"]  # we need to construct the balance to show
    gold = float(summary["TotalGold"])
    red = float(summary["TotalRed"])
    green = float(summary["TotalGreen"])

    # build list for the fancy chart at the top while we loop through.
    labels_key = []
    labels = []
    chart_green = {}
    chart_red = {}
    chart_gold = {}

    # build chart labels
    # go back a year then move forward
    rolling_date = datetime.today() + relativedelta(years=-years)

    for i in range(12 * years + 1):
        year = rolling_date.strftime("%Y")
        month = rolling_date.strftime("%m")
        labels_key.append("%s-%s" % (year, month))
        if years == 1:
            labels.append(rolling_date.strftime("%b"))
        else:
            labels.append(rolling_date.strftime("%b %Y"))
        rolling_date = rolling_date + relativedelta(months=+1)
        chart_gold["%s-%s" % (year, month)] = 0.0
        chart_red["%s-%s" % (year, month)] = 0.0
        chart_green["%s-%s" % (year, month)] = 0.0

    details, futureTrans = process_transactions(details, month, year)
    # todo: Tanmay to first extract details into two--> one current month next -- "future"
    # deatils will just have till current month future will go in provisional variable
    # loop through the details and augment the data to pass to the template
    # we are just adding running total data for the table of details
    for d in details:
        counter = counter - d["mps"]

        d["running_total"] = counter
        d["PostingDate"] = "%s-%02d" % (d["PostingYear"], d["PostingMonth"])
        d["PostingDateDisplay"] = "%s-%s" % (
            calendar.month_abbr[d["PostingMonth"]],
            d["PostingYear"],
        )

        # Its too slow to filter at the db so skip any month we don't want
        if not d["PostingDate"] in chart_gold:
            continue

        if d["MPColour"] == "Y":
            gold = gold - float(d["mps"])
            chart_gold[d["PostingDate"]] = chart_gold[d["PostingDate"]] + float(
                d["mps"]
            )
        elif d["MPColour"] == "R":
            red = red - float(d["mps"])
            chart_red[d["PostingDate"]] = chart_red[d["PostingDate"]] + float(d["mps"])
        elif d["MPColour"] == "G":
            green = green - float(d["mps"])
            chart_green[d["PostingDate"]] = chart_green[d["PostingDate"]] + float(
                d["mps"]
            )

    # fill in the chart data
    running_gold = float(summary["TotalGold"])
    gold_series = []
    for label in reversed(labels_key):
        running_gold = running_gold - chart_gold[label]
        gold_series.append(float("%.2f" % running_gold))
    gold_series.reverse()

    running_red = float(summary["TotalRed"])
    red_series = []
    for label in reversed(labels_key):
        running_red = running_red - chart_red[label]
        red_series.append(float("%.2f" % running_red))
    red_series.reverse()

    running_green = float(summary["TotalGreen"])
    green_series = []
    for label in reversed(labels_key):
        running_green = running_green - chart_green[label]
        green_series.append(float("%.2f" % running_green))
    green_series.reverse()

    chart = {
        "labels": labels,
        "gold": gold_series,
        "red": red_series,
        "green": green_series,
    }

    total = "%.2f" % (green + red + gold)
    green = "%.2f" % green
    red = "%.2f" % red
    gold = "%.2f" % gold

    bottom = {"gold": gold, "red": red, "green": green, "total": total}

    # Show bullets on lines or not
    if years > 2:
        show_point = "false"
    else:
        show_point = "true"

    # Show title every X points
    points_dict = {1: 1, 2: 3, 3: 5, 4: 12, 5: 12}
    try:
        points_every = points_dict[years]
    except KeyError:
        points_every = len(labels) - 1  # start and end only

    timescale = f"Last {years} years"

    if years == 1:
        timescale = "Last 12 Months"

    return render(
        request,
        "masterpoints/details.html",
        {
            "details": details,
            "summary": summary,
            "club": club,
            "chart": chart,
            "bottom": bottom,
            "show_point": show_point,
            "points_every": points_every,
            "system_number": system_number,
            "timescale": timescale,
        },
    )


@login_required()
def masterpoints_search(request):
    if request.method == "POST":
        system_number = request.POST["system_number"]
        last_name = request.POST["last_name"]
        first_name = request.POST["first_name"]
        if system_number:
            return redirect("view/%s/" % system_number)
        else:
            if not first_name:  # last name only
                matches = requests.get(
                    "%s/lastname_search/%s" % (GLOBAL_MPSERVER, last_name)
                ).json()
            elif not last_name:  # first name only
                matches = requests.get(
                    "%s/firstname_search/%s" % (GLOBAL_MPSERVER, first_name)
                ).json()
            else:  # first and last names
                matches = requests.get(
                    "%s/firstlastname_search/%s/%s"
                    % (GLOBAL_MPSERVER, first_name, last_name)
                ).json()
            if len(matches) == 1:
                system_number = matches[0]["ABFNumber"]
                return redirect("view/%s/" % system_number)
            else:
                return render(
                    request,
                    "masterpoints/masterpoints_search_results.html",
                    {"matches": matches},
                )
    else:
        return redirect("view/%s/" % request.user.system_number)


def system_number_lookup(request):
    """
    Called from the registration page. Takes in a system number and returns
    the member first and lastname or an error message.
    """

    if request.method == "GET":
        system_number = request.GET["system_number"]

        mp_source = masterpoint_factory_creator()
        return HttpResponse(mp_source.system_number_lookup(system_number))


def system_number_available(system_number):
    """
    Called from the registration page. Takes in a system number and returns
    True if number is valid and available
    """

    if not system_number.isdigit():
        return False

    mp_source = masterpoint_factory_creator()
    return mp_source.system_number_available(system_number)


def get_masterpoints(system_number):
    # Called from Dashboard

    mp_source = masterpoint_factory_creator()
    return mp_source.get_masterpoints(system_number)


def user_summary(system_number):
    """This is only here until we move masterpoints into Cobalt.
    It gets basic things such as home club and masterpoints.
    """

    mp_source = masterpoint_factory_creator()
    return mp_source.user_summary(system_number)


def get_abf_checksum(abf_raw: int) -> int:
    """Calculate the checksum for an ABF number given the raw number without the checksum

    Formula is:

    convert to 6 digit with leading 0, e.g. 62024 becomes 062024
    total is 0th place x 7, 1st place x 6, 2nd place x 5 etc
    result = total mod 11
    if result = 0 checksum = 0
    else checksum = 11 - (result mod 11)

    """

    abf_string = f"{abf_raw:06d}"

    total = sum(int(val) * (7 - index) for index, val in enumerate(abf_string))

    mod = total % 11

    if mod == 0:
        return 0

    if mod == 1:
        return 1

    return 11 - mod


def abf_checksum_is_valid(abf_number: int) -> bool:
    """Takes an ABF number and confirms the number has a valid checksum. Doesn't check with the MPC to
    see if this is a valid number (not inactive, actually registered etc)."""

    this_checksum = abf_number % 10  # last digit
    true_checksum = get_abf_checksum(abf_number // 10)  # not last digit

    return this_checksum == true_checksum


def search_mpc_users_by_name(first_name_search, last_name_search):
    """search the masterpoint centre for users by first and last name"""

    # TODO: write a version of this for the other (text file) factory
    if not first_name_search:
        first_name_search = "None"
    if not last_name_search:
        last_name_search = "None"
    return masterpoint_query_list(
        f"firstlastname_search_active/{first_name_search}/{last_name_search}"
    )


def download_abf_card_pdf(request):
    """
    Downloads a PDF with basic information about this registered user
    """

    # Get parameter if provided, otherwise use the logged in user
    abf_number = request.GET.get("abf_number")

    try:
        system_number = abf_number or request.user.system_number
    except AttributeError:
        return HttpResponse("User details not found", status=400)

    qry = f"{GLOBAL_MPSERVER}/mps/{system_number}"
    try:
        summary = masterpoint_query_local(qry)[0]
    except IndexError:
        return HttpResponse("User details not found", status=400)

    club_name = _get_club_name(summary["HomeClubID"])

    if not club_name:
        return HttpResponse("Club details not found", status=400)

    # File-like object
    buffer = io.BytesIO()

    # Create the PDF object
    width, height = A4
    pdf = canvas.Canvas(buffer, pagesize=A4)

    # expiry - 31st of next March
    if datetime.now().month > 3:
        expiry = f"31/03/{datetime.now().year + 1}"
    else:
        expiry = f"31/03/{datetime.now().year}"

    # add data
    pdf = _draw_membership_card(pdf, summary, width, height, expiry, club_name)

    # Close it off
    pdf.showPage()
    pdf.save()

    # rewind and return the file
    buffer.seek(0)
    return FileResponse(buffer, filename=f"ABF Registration for {system_number}.pdf")


def _get_club_name(club_id):
    """
    Return the club name from the club_id
    """

    qry = f"{GLOBAL_MPSERVER}/club/{club_id}"
    club_details = masterpoint_query_local(qry)
    print(club_details)

    return club_details[0]["ClubName"]


def _draw_membership_card(pdf, summary, width, height, expiry, club_name):
    """fiddly bits of formatting the card"""

    # dimensions of credit card - this is the size we want
    card_height_mm = 53.98
    card_width_mm = 85.6

    # page height in mm
    height_mm = height / mm
    width_mm = width / mm

    # Draw borders of card
    x_offset_mm = (width_mm - card_width_mm) / 2
    y_offset_mm = 10

    # work out corners
    left = x_offset_mm * mm
    right = (card_width_mm * mm) + left
    top = height_mm * mm - y_offset_mm * mm
    bottom = top - card_height_mm * mm

    # Add ABF Logo
    scaling = 0.06
    pdf.drawInlineImage(
        "cobalt/static/assets/img/abflogo.png",
        left + 8,
        top - 24,
        640 * scaling,
        351 * scaling,
    )

    # Add MyABF Logo
    scaling = 0.05
    pdf.drawInlineImage(
        "cobalt/static/assets/img/abftechlogo.png",
        left + 197,
        top - 26,
        960 * scaling,
        540 * scaling,
    )

    # Write on the canvas
    pdf.setFont("Helvetica", 19)
    pdf.drawString(left + 52, top - 17, "Registration Card")
    pdf.setFont("Helvetica", 6)
    pdf.drawString(left + 173, top - 24, "issued by")
    pdf.setFont("Times-Roman", 9)
    pdf.drawString(left + 7, bottom + 3, "Australian Bridge Federation Incorporated")
    pdf.setFont("Times-Roman", 6)
    pdf.drawString(right - 60, bottom + 3, "ABN 70 053 651 666")
    pdf.setFont("Helvetica", 15)
    pdf.drawString(
        45 * mm, 180 * mm, "Here is your ABF Registration card to print and keep."
    )

    # left
    pdf.line(left, top, left, bottom)
    # top
    pdf.line(left, top, right, top)
    # right
    pdf.line(right, top, right, bottom)
    # bottom
    pdf.line(left, bottom, right, bottom)

    # Table 1 - name
    data = [
        ["NAME"],
        [f"{summary['GivenNames']} {summary['Surname']}"],
    ]

    table = Table(
        data,
        colWidths=(80 * mm),
        style=[
            ("GRID", (0, 0), (1, 1), 1, colors.black),
            ("BACKGROUND", (0, 0), (1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (1, 1), "Times-Roman"),
            ("TOPPADDING", (0, 0), (1, 0), 1),
            ("TOPPADDING", (0, 1), (1, 1), 1),
            ("BOTTOMPADDING", (0, 0), (1, 0), 0),
            ("BOTTOMPADDING", (0, 1), (1, 1), 3),
            ("FONTSIZE", (0, 0), (1, 0), 6),
            ("FONTSIZE", (0, 1), (1, 1), 10),
        ],
    )

    table.wrapOn(pdf, 0, 0)
    table.drawOn(pdf, 65 * mm, top - 20 * mm)

    # Table 2 - club
    data = [
        ["CLUB"],
        [club_name],
    ]

    table = Table(
        data,
        colWidths=(80 * mm),
        style=[
            ("GRID", (0, 0), (1, 1), 1, colors.black),
            ("BACKGROUND", (0, 0), (1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (1, 1), "Times-Roman"),
            ("TOPPADDING", (0, 0), (1, 0), 1),
            ("TOPPADDING", (0, 1), (1, 1), 1),
            ("BOTTOMPADDING", (0, 0), (1, 0), 0),
            ("BOTTOMPADDING", (0, 1), (1, 1), 3),
            ("FONTSIZE", (0, 0), (1, 0), 6),
            ("FONTSIZE", (0, 1), (1, 1), 10),
        ],
    )

    table.wrapOn(pdf, 0, 0)
    table.drawOn(pdf, 65 * mm, top - 30 * mm)

    # Table 3 - ABF number, rank, valid to
    data = [
        ["ABF NUMBER", "MASTERPOINTS RANK", "VALID TO"],
        [summary["ABFNumber"], summary["RankName"], expiry],
    ]

    table = Table(
        data,
        colWidths=(20 * mm, 40 * mm, 20 * mm),
        style=[
            ("GRID", (0, 0), (2, 1), 1, colors.black),
            ("BACKGROUND", (0, 0), (2, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (2, 1), "Times-Roman"),
            ("TOPPADDING", (0, 0), (2, 0), 1),
            ("TOPPADDING", (0, 1), (2, 1), 1),
            ("BOTTOMPADDING", (0, 0), (2, 0), 0),
            ("BOTTOMPADDING", (0, 1), (2, 1), 3),
            ("FONTSIZE", (0, 0), (2, 0), 6),
            ("FONTSIZE", (0, 1), (2, 1), 10),
        ],
    )

    table.wrapOn(pdf, 0, 0)
    table.drawOn(pdf, 65 * mm, top - 40 * mm)

    # Table 4 - points
    data = [
        ["GOLD POINTS", "RED POINTS", "GREEN POINTS", "TOTAL POINTS"],
        [
            summary["TotalGold"],
            summary["TotalRed"],
            summary["TotalGreen"],
            summary["TotalMPs"],
        ],
    ]

    table = Table(
        data,
        colWidths=(20 * mm, 20 * mm, 20 * mm, 20 * mm),
        style=[
            ("GRID", (0, 0), (3, 1), 1, colors.black),
            ("BACKGROUND", (0, 0), (3, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (3, 1), "Times-Roman"),
            ("TOPPADDING", (0, 0), (3, 0), 1),
            ("TOPPADDING", (0, 1), (3, 1), 1),
            ("BOTTOMPADDING", (0, 0), (3, 0), 0),
            ("BOTTOMPADDING", (0, 1), (3, 1), 3),
            ("FONTSIZE", (0, 0), (3, 0), 6),
            ("FONTSIZE", (0, 1), (3, 1), 10),
        ],
    )

    table.wrapOn(pdf, 0, 0)
    table.drawOn(pdf, 65 * mm, top - 50 * mm)

    return pdf


def abf_registration_card(request):
    """Logged out search for user to print a registration card"""

    return render(request, "masterpoints/registration_card_logged_out.html")


def abf_registration_card_htmx(request):
    """Perform the user search and return the list"""

    abf_number = request.POST.get("abf_number")
    first_name = request.POST.get("first_name")
    last_name = request.POST.get("last_name")

    if abf_number:
        matches = requests.get(f"{GLOBAL_MPSERVER}/mps/{abf_number}").json()
        if len(matches) == 0:
            return HttpResponse("<h2>No match found</h2>")
    elif not first_name:  # last name only
        matches = requests.get(f"{GLOBAL_MPSERVER}/lastname_search/{last_name}").json()
    elif not last_name:  # first name only
        matches = requests.get(
            f"{GLOBAL_MPSERVER}/firstname_search/{first_name}"
        ).json()
    else:  # first and last names
        matches = requests.get(
            f"{GLOBAL_MPSERVER}/firstlastname_search/{first_name}/{last_name}"
        ).json()

    # Filter out inactive
    active_matches = []
    for match in matches:
        if match["IsActive"] == "Y":
            active_matches.append(match)

    if len(active_matches) == 0:
        return HttpResponse("<h2>No match found</h2>")

    return render(
        request,
        "masterpoints/registration_card_logged_out_htmx.html",
        {"matches": active_matches},
    )
