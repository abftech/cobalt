import bleach
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.urls import reverse

from accounts.models import User
from django.utils import timezone
from django.core.validators import RegexValidator, MaxValueValidator, MinValueValidator

from cobalt.settings import (
    GLOBAL_ORG,
    GLOBAL_TITLE,
    BLEACH_ALLOWED_TAGS,
    BLEACH_ALLOWED_ATTRIBUTES,
    BLEACH_ALLOWED_STYLES,
)

# from organisations.model_managers import MemberMembershipTypeManager

# import payments.models as payments_models

# Variable to control what is expected to be in the RBAC structure for Organisations
# A management script runs to update RBAC structure for all clubs if a new option is found.
# Note, if you change anything here you still need to set up the RBAC defaults and admin groups,
# that doesn't happen automatically.

ORGS_RBAC_GROUPS_AND_ROLES = {
    # Conveners for this orgs events
    # CONVENERS IS THE ANCHOR. THIS IS ASSUMED TO BE THERE WHEN TESTING FOR ADVANCED RBAC.
    # DO NOT CHANGE WITHOUT CHANGING IN CODE
    "conveners": {
        "app": "events",
        "model": "org",
        "action": "edit",
        "description": "Manage congresses",
    },
    # See payments details
    "payments_view": {
        "app": "payments",
        "model": "manage",
        "action": "view",
        "description": "View payments info",
    },
    # Change payments details
    "payments_edit": {
        "app": "payments",
        "model": "manage",
        "action": "edit",
        "description": "Edit payments info",
    },
    # Change member details
    "members_edit": {
        "app": "orgs",
        "model": "members",
        "action": "edit",
        "description": "Edit member info",
    },
    # Manage communications
    "comms_edit": {
        "app": "notifications",
        "model": "orgcomms",
        "action": "edit",
        "description": "Manage communications",
    },
    # Directors
    "directors": {
        "app": "club_sessions",
        "model": "sessions",
        "action": "edit",
        "description": "Directors",
    },
    # Edit Club details like name
    "club_edit": {
        "app": "orgs",
        "model": "org",
        "action": "edit",
        "description": "Edit Club info",
    },
}


def no_future(value):
    today = date.today()
    if value > today:
        raise ValidationError("Date cannot be in the future.")


class Organisation(models.Model):
    """Many of these fields map to fields in the Masterpoints Database
    We don't worry about phone numbers and addresses for secretaries and MP secretaries
    They seem to relate to sending letters to people. We keep the Venue address though."""

    bsb_regex = RegexValidator(
        regex=r"^\d{6}$",
        message="BSB must be exactly 6 numbers long.",
    )

    account_regex = RegexValidator(
        regex=r"^[0-9-]*$",
        message="Account number must contain only digits and dashes",
    )

    ORG_TYPE = [
        ("Club", "Bridge Club"),
        ("State", "State Association"),
        ("National", "National Body"),
        ("Other", "Other"),
    ]

    ORG_STATUS = [
        ("Open", "Open"),
        ("Closed", "Closed"),
    ]

    org_id = models.CharField(f"{GLOBAL_ORG} Club Number", max_length=4, unique=True)
    """ maps to MPC OrgID """

    status = models.CharField(choices=ORG_STATUS, max_length=6, default="Open")

    name = models.CharField(max_length=50)
    """ maps to MPC ClubName """

    secretary = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="secretary"
    )
    """ maps to MPC ClubSecName, but we need to map this to a Cobalt user so not a CharField """

    type = models.CharField(choices=ORG_TYPE, max_length=8, blank=True, null=True)

    club_email = models.CharField(max_length=40, blank=True, null=True)
    """ maps to PMC ClubEmail """

    address1 = models.CharField("Address Line 1", max_length=100, blank=True, null=True)
    """ maps to MPC VenueAddress1 """

    address2 = models.CharField("Address Line 2", max_length=100, blank=True, null=True)
    """ maps to MPC VenueAddress2 """

    suburb = models.CharField(max_length=50, blank=True, null=True)
    """ maps to MPC Venue suburb """

    state = models.CharField(max_length=3, blank=True, null=True)
    """ maps to MPC VenueState"""

    postcode = models.CharField(max_length=10, blank=True, null=True)
    """ maps to MPC VenuePostcode """

    club_website = models.CharField(max_length=100, blank=True, null=True)
    """ maps to MPC ClubWebsite """

    bank_bsb = models.CharField(
        "BSB Number", max_length=7, blank=True, null=True, validators=[bsb_regex]
    )
    bank_account = models.CharField(
        "Bank Account Number",
        max_length=14,
        blank=True,
        null=True,
        validators=[account_regex],
    )

    full_club_admin = models.BooleanField("Use full club admin", default=False)
    """ enable full club admin functionality """

    membership_renewal_date_day = models.IntegerField(
        "Membership Renewal Date - Day",
        default=1,
        validators=[MaxValueValidator(31), MinValueValidator(1)],
        blank=True,
        null=True,
    )

    membership_renewal_date_month = models.IntegerField(
        "Membership Renewal Date - Month",
        default=1,
        validators=[MaxValueValidator(12), MinValueValidator(1)],
        blank=True,
        null=True,
    )

    last_updated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="org_last_updated_by",
    )
    last_updated = models.DateTimeField(auto_now=True)

    default_secondary_payment_method = models.ForeignKey(
        "payments.OrgPaymentMethod",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="org_secondary_payment_type",
    )
    """ bridge credits are the default, but we can use a secondary default if bridge credits aren't an option """

    send_results_email = models.BooleanField(default=True)
    """ Club level control over whether an email is sent to members when results are published """

    results_email_message = models.TextField(default="")
    """ Message sent with the results emails """

    minimum_balance_after_settlement = models.DecimalField(
        decimal_places=2, max_digits=10, default=0
    )
    """ How much of a float to leave in the account balance when settlement takes place """

    xero_contact_id = models.CharField(max_length=50, null=True, default="")
    """ optional customer id for Xero """

    use_last_payment_method_for_player_sessions = models.BooleanField(default=False)
    """ some clubs want to default payments for sessions to use whatever the player last paid with """

    @property
    def next_renewal_date(self):
        """the forthcoming annual renewal date (could be today)"""

        today = timezone.now().date()
        renewal_date = date(
            today.year,
            self.membership_renewal_date_month,
            self.membership_renewal_date_day,
        )
        if renewal_date < today:
            renewal_date = date(
                today.year + 1,
                self.membership_renewal_date_month,
                self.membership_renewal_date_day,
            )
        return renewal_date

    @property
    def current_end_date(self):
        """The end date of the current membership period (today or later)"""
        today = timezone.now().date()
        renewal_date = self.next_renewal_date
        if renewal_date == today:
            end_date = renewal_date + timedelta(years=1) - timedelta(days=1)
        else:
            end_date = renewal_date - timedelta(days=1)
        return end_date

    @property
    def next_end_date(self):
        """the end date of the forthcoming annual renewal cycle
        One year on from the current_renewal_date"""
        current_end = self.next_renewal_date
        return date(current_end.year + 1, current_end.month, current_end.day)

    @property
    def settlement_fee_percent(self):
        """return what our settlement fee is set to"""

        import payments.models as payments

        # Check for specific setting for this org
        override = payments.OrganisationSettlementFees.objects.filter(
            organisation=self
        ).first()
        if override:
            return override.org_fee_percent

        # return default
        default = payments.PaymentStatic.objects.filter(active=True).last()

        return default.default_org_fee_percent

    @property
    def rbac_name_qualifier(self):
        """We use the rbac name qualifier a lot for clubs. Neater to have as a property

        This shows where in the RBAC tree this club lives.

        """

        return "rbac.orgs.clubs.generated.%s.%s" % (
            self.state.lower(),
            self.id,
        )

    @property
    def rbac_admin_name_qualifier(self):
        """
        This shows where in the RBAC admin tree this club lives.
        """

        return "admin.clubs.generated.%s.%s" % (
            self.state.lower(),
            self.id,
        )

    def __str__(self):
        return self.name


class MembershipType(models.Model):
    """Clubs can have multiple membership types. A member can only belong to one membership type per club at one time"""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)

    name = models.CharField("Name of Membership", max_length=20)

    description = models.TextField("Description", blank=True, null=True)

    annual_fee = models.DecimalField(
        "Annual Fee", max_digits=12, decimal_places=2, blank=True, null=True
    )

    grace_period_days = models.IntegerField("Payment Grace Period (days)", default=31)

    is_default = models.BooleanField("Default Membership Type", default=False)

    does_not_pay_session_fees = models.BooleanField(
        "Play Normal Sessions for Free", default=False
    )

    does_not_renew = models.BooleanField("Never Expires", default=False)

    last_modified_by = models.ForeignKey(User, on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    # Order so is_default is at the top
    class Meta:
        ordering = ("-is_default",)

    def __str__(self):
        return f"{self.organisation} - {self.name}"


class MemberMembershipType(models.Model):
    """
    This links members to a club membership.
    Note that a player can have multiple records for an organistaion, but they
    should be non-overlapping in time. Only the most recent determies the overall
    membership status for the person.
    """

    system_number = models.IntegerField("%s Number" % GLOBAL_ORG, blank=True)

    # Note: deleting a MembershipType that has any references will cause an exception
    membership_type = models.ForeignKey(MembershipType, on_delete=models.PROTECT)

    home_club = models.BooleanField("Is Member's Home Club", default=False)

    start_date = models.DateField("Started At", auto_now_add=True)

    end_date = models.DateField("Ends At", blank=True, null=True, default=None)
    """ Membership end date, None if membershipy type is perpetual """

    paid_until_date = models.DateField(
        "Paid Until", blank=True, null=True, default=None
    )
    """ Typically either the end_date or the end of the previous period  """

    due_date = models.DateField("Payment due date", blank=True, null=True, default=None)
    """ Date by which payment is due, none if paid, otherwise typically paid_unitl_date plus a grace period """

    fee = models.DecimalField(
        "Fee", max_digits=12, decimal_places=2, blank=True, null=True
    )
    """ The last fee payable """

    MEMBERSHIP_STATE_CURRENT = "CUR"
    MEMBERSHIP_STATE_DUE = "DUE"
    MEMBERSHIP_STATE_ENDED = "END"
    MEMBERSHIP_STATE_LAPSED = "LAP"
    MEMBERSHIP_STATE_RESIGNED = "RES"
    MEMBERSHIP_STATE_TERMINATED = "TRM"
    MEMBERSHIP_STATE_DECEASED = "DEC"

    MEMBERSHIP_STATE = [
        (MEMBERSHIP_STATE_CURRENT, "Current"),
        (MEMBERSHIP_STATE_DUE, "Due"),
        (MEMBERSHIP_STATE_ENDED, "Ended"),
        (MEMBERSHIP_STATE_LAPSED, "Lapsed"),
        (MEMBERSHIP_STATE_RESIGNED, "Resigned"),
        (MEMBERSHIP_STATE_TERMINATED, "Terminated"),
        (MEMBERSHIP_STATE_DECEASED, "Deceased"),
    ]

    membership_state = models.CharField(
        "State",
        max_length=4,
        choices=MEMBERSHIP_STATE,
        default=MEMBERSHIP_STATE_CURRENT,
    )
    """ The current state of this membership, note this is date dependent"""

    last_modified_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="last_modified_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_paid(self):
        """Has the membership been paid?"""
        if not self.end_date:
            # A perpetual membership type
            return True
        return self.paid_until_date == self.end_date

    @property
    def is_final_state(self):
        """Is this in a finalised state (ie not current or due)"""
        return self.membership_state not in [
            self.MEMBERSHIP_STATE_CURRENT,
            self.MEMBERSHIP_STATE_DUE,
        ]

    def refresh_state(self, as_at_date=None, commit=True):
        """Ensure that the membership state is correct.

        No changes are made if the object is already in a finalised state
        (eg deceased) or the membership type is not renewing

        Args:
            as_at_date (Date or None): the date to use, current if None
            commit (boolean): save changes?

        Returns:
            boolean: was a change made?
        """

        old_state = self.membership_state
        if not self.is_final_state and self.end_date:
            now = as_at_date if as_at_date else timezone.now().date()
            if self.paid_until_date <= now:
                self.membership_state = self.MEMBERSHIP_STATE_CURRENT
            elif now <= self.due_date:
                self.membership_state = self.MEMBERSHIP_STATE_DUE
            else:
                self.membership_state = self.MEMBERSHIP_STATE_LAPSED
            if self.membership_state != old_state and commit:
                self.save()
        return self.membership_state != old_state

    # JPG clean-up after testing, should not be used
    # @property
    # def active(self):
    #     """Get if this is active or not"""
    #     now = timezone.now()
    #     if self.start_date > now:
    #         return False
    #     # if self.end_date < now:
    #     #     return False
    #     return True

    def __str__(self):
        return (
            f"{self.system_number}, member of {self.membership_type.organisation.name}"
        )


class ClubLog(models.Model):
    """log of things that happen for a Club"""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    actor = models.ForeignKey(User, on_delete=models.CASCADE)
    action_date = models.DateTimeField(auto_now_add=True)
    action = models.TextField("Action")

    def __str__(self):
        return f"{self.organisation} -  {self.actor}"


class MemberClubDetails(models.Model):
    """Club specific details about a member.

    Note that this is a different model to the previous MemberClubEmail model. All club members
    will have a MemberClubDetails record regardless of whether they are registered or unregistered
    in My ABF, and regardless of whether their is a club specific email.

    latest+membership and membership_status are programatically set, not determined at runtime,
    to allow database queries to use these attributes efficiently.

    Note that some fields are duplicates of fields in the User model. This is to allow members
    to supply different information to clubs."""

    club = models.ForeignKey(Organisation, on_delete=models.CASCADE)

    system_number = models.IntegerField("%s Number" % GLOBAL_ORG)

    latest_membership = models.ForeignKey(
        MemberMembershipType, on_delete=models.SET_NULL, null=True
    )
    """ The most recent MemberMembershipRecord for this member, may not be current """

    MEMBERSHIP_STATUS_CURRENT = "CUR"
    MEMBERSHIP_STATUS_DUE = "DUE"
    MEMBERSHIP_STATUS_ENDED = "END"
    MEMBERSHIP_STATUS_LAPSED = "LAP"
    MEMBERSHIP_STATUS_RESIGNED = "RES"
    MEMBERSHIP_STATUS_TERMINATED = "TRM"
    MEMBERSHIP_STATUS_DECEASED = "DEC"
    MEMBERSHIP_STATUS_CONTACT = "CON"

    MEMBERSHIP_STATUS = [
        (MEMBERSHIP_STATUS_CURRENT, "Current"),
        (MEMBERSHIP_STATUS_DUE, "Due"),
        (MEMBERSHIP_STATUS_ENDED, "Ended"),
        (MEMBERSHIP_STATUS_LAPSED, "Lapsed"),
        (MEMBERSHIP_STATUS_RESIGNED, "Resigned"),
        (MEMBERSHIP_STATUS_TERMINATED, "Terminated"),
        (MEMBERSHIP_STATUS_DECEASED, "Deceased"),
        (MEMBERSHIP_STATUS_CONTACT, "Contact"),
    ]

    membership_status = models.CharField(
        "Membership Status",
        max_length=4,
        choices=MEMBERSHIP_STATUS,
        default=MEMBERSHIP_STATUS_CURRENT,
    )
    """ The current state of this membership, note this is date dependent"""

    joined_date = models.DateField("Date Joined", null=True, blank=True)

    address1 = models.CharField("Address Line 1", max_length=100, blank=True, null=True)

    address2 = models.CharField("Address Line 2", max_length=100, blank=True, null=True)

    state = models.CharField(max_length=3, blank=True, null=True)

    postcode = models.CharField(max_length=10, blank=True, null=True)

    mobile_regex = RegexValidator(
        regex=r"^04\d{8}$",
        message="We only accept Australian phone numbers starting 04 which are 10 numbers long.",
    )
    mobile = models.CharField(
        "Mobile Number",
        blank=True,
        unique=True,
        null=True,
        max_length=15,
        validators=[mobile_regex],
    )

    phone_regex = RegexValidator(
        regex=r"^(\d{8}|\d{10})$",
        message="We only accept Australian phone numbers with 8 or 10 digits.",
    )
    other_phone = models.CharField(
        "Phone",
        blank=True,
        unique=True,
        null=True,
        max_length=15,
        validators=[phone_regex],
    )

    dob = models.DateField(blank="True", null=True, validators=[no_future])

    club_membership_number = models.CharField(max_length=15, blank=True, null=True)

    emergency_contact = models.CharField(
        "Emergency Contact", max_length=150, blank=True, null=True
    )

    notes = models.TextField(blank=True, null=True)

    email = models.EmailField(
        "Email for your club only", unique=False, null=True, blank=True
    )
    """ Club specific email address """

    email_hard_bounce = models.BooleanField(default=False)
    """ Set this flag if we get a hard bounce from sending an email """

    email_hard_bounce_reason = models.TextField(null=True, blank=True)
    """ Reason for the bounce """

    email_hard_bounce_date = models.DateTimeField(null=True, blank=True)
    """ Date of a hard bounce """

    class Meta:
        unique_together = ("club", "system_number")

    @property
    def left_date(self):
        """Date left the club, or None"""
        if self.membership_status in [
            self.MEMBERSHIP_STATUS_CURRENT,
            self.MEMBERSHIP_STATUS_DUE,
            self.MEMBERSHIP_STATUS_CONTACT,
        ]:
            return None
        else:
            return self.latest_membership.end_date if self.latest_membership else None

    def refresh_status(self, as_at_date=None, commit=True):
        """Ensure that the membership status and current membership are correct.

        Args:
            as_at_date (Date or None): the date to use, current if None
            commit (boolean): save changes?

        Returns:
            boolean: was a change made?

        Note: this calls refresh_state on the most recent MemberMembershipType.
        Note: if this is called with commit=False, the caller needs to handle saving
        any changes made to the most recent MemberMembershipType."""

        if self.membership_status == self.MEMBERSHIP_STATUS_DECEASED:
            return False

        changed = False

        latest_mmt = (
            MemberMembershipType.objects.filter(
                system_number=self.system_number,
                membership_type__organisation=self.club,
            )
            .order_by("end_date")
            .last()
        )

        if not latest_mmt:
            # no membership type association, so should be a contact
            if (
                self.membership_status != self.MEMBERSHIP_STATUS_CONTACT
                or self.latest_membership
            ):
                self.membership_status = self.MEMBERSHIP_STATUS_CONTACT
                self.latest_membership = None
                changed = True
        else:
            changed = latest_mmt.refresh_state(as_at_date=as_at_date, commit=commit)
            if self.latest_membership != latest_mmt or changed:
                self.latest_membership = latest_mmt
                self.membership_status = latest_mmt.membership_state
                changed = True
            elif self.membership_status != latest_mmt.membership_state:
                self.membership_status = latest_mmt.membership_state
                changed = True

        if changed:
            self.save()

        return changed

    def __str__(self):
        return f"{self.organisation} - {self.system_number}"


class ClubMemberLog(models.Model):
    """log of things that happen for a member in a club"""

    club = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )
    system_number = models.IntegerField("System number")
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField("Description")

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.organisation} {self.member_system_number} - {self.actor}"


# JPG TO DO: Deprecated - delete after club admin release data conversion
class MemberClubEmail(models.Model):
    """This is used for people who are NOT signed yp to Cobalt. This is for Clubs to keep track of
    the email addresses of their members. Email addresses are an emotive topic in Australian bridge
    with clubs often refusing to share their email lists with others (including State bodies and the ABF)
    for fear that their rivals will get hold of their member's contact details and lure them away.

    We initially had a public email on the UnregisteredUser object but this was removed. You may
    find old references to this in the code. Now we only have an email address stored in here and
    it is only available to the club that set it up.

    Once a user signs up for Cobalt this is no longer required and the user themselves can manage
    their own contact details."""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    system_number = models.IntegerField("%s Number" % GLOBAL_ORG)
    email = models.EmailField("Email for your club only", unique=False)
    email_hard_bounce = models.BooleanField(default=False)
    """ Set this flag if we get a hard bounce from sending an email """
    email_hard_bounce_reason = models.TextField(null=True, blank=True)
    """ Reason for the bounce """
    email_hard_bounce_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("organisation", "system_number")

    def __str__(self):
        return f"{self.organisation} - {self.system_number}"


class ClubTag(models.Model):
    """Tags are used by clubs to group members together mainly for email purposes. This is the definition
    for a tag"""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    tag_name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.organisation} - {self.tag_name}"


class MemberClubTag(models.Model):
    """Links a member to a tag for a club"""

    club_tag = models.ForeignKey(ClubTag, on_delete=models.CASCADE)
    system_number = models.IntegerField("%s Number" % GLOBAL_ORG, blank=True)

    def __str__(self):
        return f"{self.club_tag} - {self.system_number}"


class Visitor(models.Model):
    """Visitors to a club"""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    email = models.EmailField()
    first_name = models.CharField("First Name", max_length=150)
    last_name = models.CharField("Last Name", max_length=150)
    notes = models.TextField(blank=True, null=True)


class OrganisationFrontPage(models.Model):
    """Basic information about an organisation, primarily for the public profile. Likely to be extended later"""

    organisation = models.OneToOneField(
        Organisation, on_delete=models.CASCADE, primary_key=True
    )
    summary = models.TextField()

    def __str__(self):
        return f"Front Page for {self.organisation}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            # First time, set default
            self.summary = """
                        <h2 class="text-center" style="color: black;"><span style="font-size: 90px;">♣</span>
                        </h2>
                        <h1 style="text-align: center; ">
                        <font color="#9c00ff">{{ BRIDGE_CLUB }}</font>
                        </h1>
                        <br>
                        <p>
                        <span style="font-size: 18px;">This page hasn't been set up yet.
                        If you are an administrator for this club you can change this through
                        the Communications section of Club Admin.
                        </span>
                        </p>
                        {{ website }}
                        <h3 class="">Registered Address</h3>
                        <p style="font-size: 18px; line-height: 0.5;"><b>{{ Address1 }}</b></p>
                        <p style="font-size: 18px; line-height: 0.5;"><b>{{ Address2 }}</b></p>
                        <p style="font-size: 18px; line-height: 0.5;"><b>{{ Suburb }}</b></p>
                        <p style="font-size: 18px; line-height: 0.5;"><b>{{ State }} {{ Postcode }}</b></p>
                        <p style="line-height: 0.5;"><br></p>
                        <p>{{ RESULTS }}</p>
                        <p>{{ CALENDAR }}</p>
            """

            self.summary = self.summary.replace(
                "{{ BRIDGE_CLUB }}", self.organisation.name
            )

            replace_with = self.organisation.address1 or ""
            self.summary = self.summary.replace("{{ Address1 }}", replace_with)

            replace_with = self.organisation.address2 or ""
            self.summary = self.summary.replace("{{ Address2 }}", replace_with)

            replace_with = self.organisation.suburb or ""
            self.summary = self.summary.replace("{{ Suburb }}", replace_with)

            self.summary = self.summary.replace("{{ State }}", self.organisation.state)

            replace_with = self.organisation.postcode or ""
            self.summary = self.summary.replace("{{ Postcode }}", replace_with)

            url = reverse(
                "accounts:public_profile", kwargs={"pk": self.organisation.secretary.id}
            )
            email_url = reverse(
                "notifications:member_to_member_email",
                kwargs={"member_id": self.organisation.secretary.id},
            )
            replace_with = f"""Club Secretary is: <a href='{url}'>{self.organisation.secretary.full_name}</a>.
                            <br><br><a href='{email_url}'>Click here to contact {self.organisation.secretary.first_name}</a>."""
            self.summary = self.summary.replace("{{ secretary }}", replace_with)

            if self.organisation.club_website:
                # Add http to start of not present
                if self.organisation.club_website.find("http") == -1:
                    self.organisation.club_website = (
                        f"http://{self.organisation.club_website}"
                    )

                replace_with = f"""<p><span style="font-size: 18px;">
                                    This club has a website at <a href="{self.organisation.club_website}"
                                    target="_blank">{self.organisation.club_website}</a></span></p>"""
            else:
                replace_with = ""
            self.summary = self.summary.replace("{{ website }}", replace_with)

        # See if we have changed and run through bleach
        elif getattr(self, "_text_changed", True):
            self.summary = bleach.clean(
                self.summary,
                strip=True,
                tags=BLEACH_ALLOWED_TAGS,
                attributes=BLEACH_ALLOWED_ATTRIBUTES,
                styles=BLEACH_ALLOWED_STYLES,
            )

        super(OrganisationFrontPage, self).save(*args, **kwargs)


class MiscPayType(models.Model):
    """Labels for different kinds of miscellaneous payments for clubs. eg. Parking, books"""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    description = models.CharField(max_length=30)
    default_amount = models.DecimalField(default=0, decimal_places=2, max_digits=8)


class OrgVenue(models.Model):
    """Used by clubs that have multiple venues so we can identify sessions properly"""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    venue = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.organisation} - {self.venue}"


class OrgEmailTemplate(models.Model):
    """Allow an organisation to handle their own email templates"""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    template_name = models.CharField(max_length=100)
    banner = models.ImageField(
        upload_to="email_banners/", default="email_banners/myabf-email.png"
    )
    footer = models.TextField(blank=True, null=True)
    from_name = models.CharField(max_length=100, default=GLOBAL_TITLE)
    reply_to = models.CharField(
        verbose_name="Reply to", max_length=100, blank=True, null=True
    )
    box_colour = models.CharField(max_length=7, default="#9c27b0")
    box_font_colour = models.CharField(max_length=7, default="#ffffff")
    last_modified_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="template_last_modified_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.organisation} - {self.template_name}"

    # If the text changes, run it through bleach before saving
    def save(self, *args, **kwargs):

        if self.footer and getattr(self, "_footer_changed", True):
            self.footer = bleach.clean(
                self.footer,
                strip=True,
                tags=BLEACH_ALLOWED_TAGS,
                attributes=BLEACH_ALLOWED_ATTRIBUTES,
                styles=BLEACH_ALLOWED_STYLES,
            )

        super().save(*args, **kwargs)


class WelcomePack(models.Model):
    """Clubs can manage a welcome email for new members"""

    organisation = models.OneToOneField(to=Organisation, on_delete=models.CASCADE)
    template = models.ForeignKey(
        OrgEmailTemplate,
        on_delete=models.CASCADE,
        related_name="welcome_pack_template",
        null=True,
        blank=True,
    )
    welcome_email = models.TextField()
    last_modified_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="welcome_pack_last_modified_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.organisation} - {self.template}"

    # If the text changes, run it through bleach before saving
    def save(self, *args, **kwargs):

        if self.welcome_email and getattr(self, "_welcome_email_changed", True):
            self.welcome_email = bleach.clean(
                self.welcome_email,
                strip=True,
                tags=BLEACH_ALLOWED_TAGS,
                attributes=BLEACH_ALLOWED_ATTRIBUTES,
                styles=BLEACH_ALLOWED_STYLES,
            )

        super().save(*args, **kwargs)
