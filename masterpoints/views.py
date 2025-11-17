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

from cobalt.settings import MP_USE_DJANGO
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
def masterpoints_detail_html(request, system_number=None, years=1):

    mp_source = masterpoint_factory_creator()
    status, data = mp_source.masterpoints_detail(request, system_number, years)

    if not status:
        return redirect("dashboard:dashboard")

    # Can be removed once we cut over from the MPC
    if MP_USE_DJANGO:
        template = "masterpoints/details.html"
    else:
        template = "masterpoints/details-old.html"

    return render(
        request,
        template,
        data,
    )


@login_required()
def masterpoints_search(request):
    """ Called from the masterpoints page to search fo other users """

    if request.method != "POST":
        return redirect(f"view/{request.user.system_number}/")
    system_number = request.POST["system_number"]
    last_name = request.POST["last_name"]
    first_name = request.POST["first_name"]
    mp_source = masterpoint_factory_creator()
    return mp_source.masterpoint_search(request, system_number, last_name, first_name)


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

    return 1 if mod == 1 else 11 - mod


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

    mp_source = masterpoint_factory_creator()
    summary = mp_source.user_summary(system_number)

    club_name = summary["home_club"]

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
        "cobalt/static/assets/img/ABFlogo.png",
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

    # If no data, return nothing
    if not abf_number and not first_name and not last_name:
        return HttpResponse("")

    mp_source = masterpoint_factory_creator()
    status, active_matches = mp_source.user_search(abf_number, first_name, last_name)

    if not status:
        return HttpResponse(f"<h2>{active_matches}</h2>")

    if MP_USE_DJANGO:
        template =  "masterpoints/registration_card_logged_out_htmx.html"
    else:
        template =  "masterpoints/registration_card_logged_out_htmx_old.html"

    return render(
        request,
       template,
        {"matches": active_matches},
    )
