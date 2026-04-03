import io
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from accounts.forms import SystemCardForm
from accounts.models import SystemCard, User


def _save_card_as_template(system_card, filename):
    """Utility to save a card as a template"""

    with open(f"accounts/system_card_templates/{filename}", "w") as outfile:

        # Grab values for system_card
        for name in dir(system_card):
            if name[0] != "_":
                try:
                    val = getattr(system_card, name)
                    if type(val) in [str, int, bool, User]:
                        outfile.write(f"{name}:{val}\n")
                except AttributeError:
                    pass


def _build_all_responses(system_card):
    """Build the all_responses dict from database fields on the system card"""

    sc = system_card
    return {
        "LINK-1C": {
            1: {
                "1D": sc.response_1c_1d,
                "1H": sc.response_1c_1h,
                "1S": sc.response_1c_1s,
                "1N": sc.response_1c_1n,
            },
            2: {
                "2C": sc.response_1c_2c,
                "2D": sc.response_1c_2d,
                "2H": sc.response_1c_2h,
                "2S": sc.response_1c_2s,
                "2N": sc.response_1c_2n,
            },
            3: {
                "3C": sc.response_1c_3c,
                "3D": sc.response_1c_3d,
                "3H": sc.response_1c_3h,
                "3S": sc.response_1c_3s,
                "3N": sc.response_1c_3n,
                "Other": sc.response_1c_other,
            },
        },
        "LINK-1D": {
            1: {
                "1H": sc.response_1d_1h,
                "1S": sc.response_1d_1s,
                "1N": sc.response_1d_1n,
            },
            2: {
                "2C": sc.response_1d_2c,
                "2D": sc.response_1d_2d,
                "2H": sc.response_1d_2h,
                "2S": sc.response_1d_2s,
                "2N": sc.response_1d_2n,
            },
            3: {
                "3C": sc.response_1d_3c,
                "3D": sc.response_1d_3d,
                "3H": sc.response_1d_3h,
                "3S": sc.response_1d_3s,
                "3N": sc.response_1d_3n,
                "Other": sc.response_1d_other,
            },
        },
        "LINK-1H": {
            1: {"1S": sc.response_1h_1s, "1N": sc.response_1h_1n},
            2: {
                "2C": sc.response_1h_2c,
                "2D": sc.response_1h_2d,
                "2H": sc.response_1h_2h,
                "2S": sc.response_1h_2s,
                "2N": sc.response_1h_2n,
            },
            3: {
                "3C": sc.response_1h_3c,
                "3D": sc.response_1h_3d,
                "3H": sc.response_1h_3h,
                "3S": sc.response_1h_3s,
                "3N": sc.response_1h_3n,
                "Other": sc.response_1h_other,
            },
        },
        "LINK-1S": {
            1: {"1N": sc.response_1s_1n},
            2: {
                "2C": sc.response_1s_2c,
                "2D": sc.response_1s_2d,
                "2H": sc.response_1s_2h,
                "2S": sc.response_1s_2s,
                "2N": sc.response_1s_2n,
            },
            3: {
                "3C": sc.response_1s_3c,
                "3D": sc.response_1s_3d,
                "3H": sc.response_1s_3h,
                "3S": sc.response_1s_3s,
                "3N": sc.response_1s_3n,
                "Other": sc.response_1s_other,
            },
        },
        "LINK-1N": {
            3: {
                "3C": sc.response_1n_3c,
                "3D": sc.response_1n_3d,
                "3H": sc.response_1n_3h,
                "3S": sc.response_1n_3s,
                "3N": sc.response_1n_3n,
                "Other": sc.response_1n_other,
            },
        },
        "LINK-2C": {
            2: {
                "2D": sc.response_2c_2d,
                "2H": sc.response_2c_2h,
                "2S": sc.response_2c_2s,
                "2N": sc.response_2c_2n,
            },
            3: {
                "3C": sc.response_2c_3c,
                "3D": sc.response_2c_3d,
                "3H": sc.response_2c_3h,
                "3S": sc.response_2c_3s,
                "3N": sc.response_2c_3n,
                "Other": sc.response_2c_other,
            },
        },
        "LINK-2D": {
            2: {
                "2H": sc.response_2d_2h,
                "2S": sc.response_2d_2s,
                "2N": sc.response_2d_2n,
            },
            3: {
                "3C": sc.response_2d_3c,
                "3D": sc.response_2d_3d,
                "3H": sc.response_2d_3h,
                "3S": sc.response_2d_3s,
                "3N": sc.response_2d_3n,
                "Other": sc.response_2d_other,
            },
        },
        "LINK-2H": {
            2: {"2S": sc.response_2h_2s, "2N": sc.response_2h_2n},
            3: {
                "3C": sc.response_2h_3c,
                "3D": sc.response_2h_3d,
                "3H": sc.response_2h_3h,
                "3S": sc.response_2h_3s,
                "3N": sc.response_2h_3n,
                "Other": sc.response_2h_other,
            },
        },
        "LINK-2S": {
            2: {"2N": sc.response_2s_2n},
            3: {
                "3C": sc.response_2s_3c,
                "3D": sc.response_2s_3d,
                "3H": sc.response_2s_3h,
                "3S": sc.response_2s_3s,
                "3N": sc.response_2s_3n,
                "Other": sc.response_2s_other,
            },
        },
        "LINK-2N": {
            3: {
                "3C": sc.response_2n_3c,
                "3D": sc.response_2n_3d,
                "3H": sc.response_2n_3h,
                "3S": sc.response_2n_3s,
                "3N": sc.response_2n_3n,
                "Other": sc.response_2n_other,
            },
        },
    }


def system_card_view(request, user_id, system_card_name):
    """Show a system card"""

    user = User.objects.filter(pk=user_id).first()
    if not user:
        raise Http404

    system_card = (
        SystemCard.objects.filter(user=user, card_name=system_card_name)
        .order_by("-save_date")
        .first()
    )

    if not system_card:
        raise Http404

    form = SystemCardForm(instance=system_card)

    return render(
        request,
        "accounts/system_card/system_card.html",
        {
            "all_responses": _build_all_responses(system_card),
            "form": form,
            "system_card": system_card,
            "editable": False,
            "template": "empty.html",
        },
    )


@login_required
def system_card_edit(request, system_card_name):
    """Edit a system card"""

    system_card = (
        SystemCard.objects.filter(user=request.user, card_name=system_card_name)
        .order_by("-save_date")
        .first()
    )
    if not system_card:
        if not request.POST:
            raise Http404
        else:
            return HttpResponse("Card not found")

    if system_card.user != request.user:
        return HttpResponse("Access Denied. You are not the owner of this system card.")

    if request.method == "POST":
        form = SystemCardForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "accounts/system_card/system_card_save.html",
                {"message": f"Errors on Card - not saved<br>{form.errors}"},
            )

        # Create a new system card each time we save it so user can go back if they mess it up
        new_system_card = form.save(commit=False)
        new_system_card.user = system_card.user
        new_system_card.card_name = request.POST.get("card_new_name")

        new_system_card.save()
        response = render(
            request,
            "accounts/system_card/system_card_save.html",
            {"message": "Card saved"},
        )

        if system_card.card_name != new_system_card.card_name:
            # Tell htmx to redirect as we have changed the URL
            response["HX-Redirect"] = reverse(
                "accounts:system_card_edit",
                kwargs={"system_card_name": new_system_card.card_name},
            )

        _save_card_as_template(system_card, "standard_american.txt")

        return response

    form = SystemCardForm(instance=system_card)

    return render(
        request,
        "accounts/system_card/system_card.html",
        {
            "editable": True,
            "form": form,
            "system_card": system_card,
            "all_responses": _build_all_responses(system_card),
            "template": "base.html",
        },
    )


@login_required
def create_pdf_system_card(request, system_card_name):
    """Generate a PDF of the system card"""

    # File-like object
    buffer = io.BytesIO()

    # Create the PDF object
    width, height = A4
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf = _fill_in_system_card(pdf, system_card_name, width, height)

    # Close it off
    pdf.showPage()
    pdf.save()

    # rewind and return the file
    buffer.seek(0)
    # return FileResponse(buffer, as_attachment=True, filename='hello.pdf')
    return FileResponse(buffer, filename="hello.pdf")


def _fill_in_system_card(pdf, system_card_name, width, height):
    """ugly code to file in the system card for the pdf"""

    pdf.setFont("Times-Roman", 20)

    # Draw on the canvas
    pdf.drawString(50, height - 50, "AUSTRALIAN BRIDGE")
    pdf.drawString(50, height - 80, "FEDERATION")

    return pdf


@login_required
def system_card_list(request):
    """List a user's system cards and allow creating a new one"""

    # Get the latest version of each distinct card name
    latest_dates = (
        SystemCard.objects.filter(user=request.user)
        .values("card_name")
        .annotate(latest=Max("save_date"))
    )
    system_cards = []
    for item in latest_dates:
        card = SystemCard.objects.get(
            user=request.user, card_name=item["card_name"], save_date=item["latest"]
        )
        system_cards.append(card)

    system_cards.sort(key=lambda c: c.card_name)

    return render(
        request,
        "accounts/system_card/system_card_list.html",
        {"system_cards": system_cards},
    )


@login_required
def system_card_create(request):
    """Create a new blank system card and redirect to edit it"""

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    card_name = request.POST.get("card_name", "").strip()
    if not card_name:
        return HttpResponse("Card name is required")

    if SystemCard.objects.filter(user=request.user, card_name=card_name).exists():
        return HttpResponse(f"You already have a card called '{card_name}'")

    SystemCard.objects.create(user=request.user, card_name=card_name)

    return redirect(
        reverse("accounts:system_card_edit", kwargs={"system_card_name": card_name})
    )
