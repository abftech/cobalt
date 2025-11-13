"""Models for our definitions of a user within the system."""

import random
import string
from datetime import date

from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from accounts.managers import UserManager, ContactManager, UnRegManager
from cobalt.settings import (
    AUTO_TOP_UP_MAX_AMT,
    GLOBAL_ORG,
    TBA_PLAYER,
    RBAC_EVERYONE,
    ABF_USER,
    API_KEY_PREFIX,
)
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models
def no_future(value):
    today = date.today()
    if value > today:
        raise ValidationError("Date cannot be in the future.")



class User(AbstractUser):
    """
    User class based upon AbstractUser.
    """

    """
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"PlayerID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"
,{"ORDINAL_POSITION":2,"COLUMN_NAME":"ABFNumber","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":10,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":3,"COLUMN_NAME":"ABFNumberRaw","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":4,"COLUMN_NAME":"Title","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":10,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":5,"COLUMN_NAME":"Surname","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":6,"COLUMN_NAME":"GivenNames","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":7,"COLUMN_NAME":"RankID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":8,"COLUMN_NAME":"HomeClubID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":9,"COLUMN_NAME":"DOBDay","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":2,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":10,"COLUMN_NAME":"DOBMonth","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":2,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":11,"COLUMN_NAME":"DOBYear","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":2,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":12,"COLUMN_NAME":"Address1","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":100,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":13,"COLUMN_NAME":"Address2","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":100,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":14,"COLUMN_NAME":"AddressState","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":3,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":15,"COLUMN_NAME":"AddressPostcode","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":10,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":16,"COLUMN_NAME":"Gender","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":17,"COLUMN_NAME":"IsActive","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":18,"COLUMN_NAME":"TotalMPs","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":19,"COLUMN_NAME":"TotalGold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":20,"COLUMN_NAME":"TotalRed","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":21,"COLUMN_NAME":"TotalGreen","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":22,"COLUMN_NAME":"ThisYearMPs","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":23,"COLUMN_NAME":"Y1Gold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":24,"COLUMN_NAME":"Y1Red","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":25,"COLUMN_NAME":"Y1Green","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":26,"COLUMN_NAME":"Y2Gold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":27,"COLUMN_NAME":"Y2Red","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":28,"COLUMN_NAME":"Y2Green","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":29,"COLUMN_NAME":"PriorGold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":30,"COLUMN_NAME":"PriorRed","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":31,"COLUMN_NAME":"PriorGreen","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":32,"COLUMN_NAME":"Q1Gold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":33,"COLUMN_NAME":"Q1Red","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":34,"COLUMN_NAME":"Q1Green","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":35,"COLUMN_NAME":"Q2Gold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":36,"COLUMN_NAME":"Q2Red","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":37,"COLUMN_NAME":"Q2Green","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":38,"COLUMN_NAME":"Q3Gold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":39,"COLUMN_NAME":"Q3Red","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":40,"COLUMN_NAME":"Q3Green","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":41,"COLUMN_NAME":"Q4Gold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":42,"COLUMN_NAME":"Q4Red","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":43,"COLUMN_NAME":"Q4Green","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":44,"COLUMN_NAME":"Pre82Red","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":45,"COLUMN_NAME":"IsMcCutcheonEligible","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":46,"COLUMN_NAME":"McCutcheonState","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":3,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":47,"COLUMN_NAME":"YearStartRankID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":48,"COLUMN_NAME":"LastPromotionPeriodID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":49,"COLUMN_NAME":"McCutcheonMPs","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":50,"COLUMN_NAME":"McCutcheonRank","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":51,"COLUMN_NAME":"IsRegistrationCardRequired","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":52,"COLUMN_NAME":"YearDeletedOrInactive","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":4,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":53,"COLUMN_NAME":"YearAgoGold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":54,"COLUMN_NAME":"YearAgoRed","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":55,"COLUMN_NAME":"YearAgoGreen","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":56,"COLUMN_NAME":"PreferredFirstName","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":57,"COLUMN_NAME":"PreviousRankID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":58,"COLUMN_NAME":"IntraGreenPeriod","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":59,"COLUMN_NAME":"IntraRedPeriod","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":60,"COLUMN_NAME":"IntraGreenYTD","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":61,"COLUMN_NAME":"IntraRedYTD","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":62,"COLUMN_NAME":"GPAThisPeriod","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":63,"COLUMN_NAME":"GPAThisYTD","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":64,"COLUMN_NAME":"PeriodGreen","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":65,"COLUMN_NAME":"PeriodRed","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":66,"COLUMN_NAME":"PeriodGold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":67,"COLUMN_NAME":"OldTotalGreen","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":68,"COLUMN_NAME":"OldTotalRed","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":69,"COLUMN_NAME":"OldTotalGold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":70,"COLUMN_NAME":"EmailAddress","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":71,"COLUMN_NAME":"DateAdded","DATA_TYPE":"datetime","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":72,"COLUMN_NAME":"IsRankCertificateRequired","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":73,"COLUMN_NAME":"LastYearMPs","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":74,"COLUMN_NAME":"PriorMPs","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":75,"COLUMN_NAME":"QuarterGreen","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":76,"COLUMN_NAME":"QuarterRed","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":77,"COLUMN_NAME":"QuarterGold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":78,"COLUMN_NAME":"Comments","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":200,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":79,"COLUMN_NAME":"IsInactivationRequested","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":80,"COLUMN_NAME":"OldAddress1","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":100,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":81,"COLUMN_NAME":"OldAddress2","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":100,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":82,"COLUMN_NAME":"OldAddressState","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":3,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":83,"COLUMN_NAME":"OldAddressPostcode","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":10,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":84,"COLUMN_NAME":"T_PriorMPs","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":85,"COLUMN_NAME":"OldYearStartRankID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":86,"COLUMN_NAME":"IsUsingAlias","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":87,"COLUMN_NAME":"RealName","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":88,"COLUMN_NAME":"PhoneNumber","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"
,{"ORDINAL_POSITION":89,"COLUMN_NAME":"Is1000Club","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"NO"
,{"ORDINAL_POSITION":90,"COLUMN_NAME":"IsPrinting1000ClubThisMonth","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"NO"
    """

    class UserType(models.TextChoices):
        USER = "U", "User"
        """ A 'normal' registered user with a password and validated email address """
        UNREGISTERED = "N", "Unregistered User"
        """ A member of the ABF with a valid ABF number, but not a user of MyABF, can be converted to a User """
        CONTACT = "C", "Contact"
        """ A contact for an organisation who is not an ABF member """

    email = models.EmailField(unique=False)
    system_number = models.IntegerField(
        "%s Number" % GLOBAL_ORG,
        blank=True,
        unique=True,
        db_index=True,
    )
    user_type = models.CharField(max_length=1, choices=UserType.choices, default=UserType.USER)

    deceased = models.BooleanField("Deceased", default=False)
    """ Player is deceased, status set by My ABF support """

    phone_regex = RegexValidator(
        #  regex=r"^\+?1?\d{9,15}$",
        regex=r"^04\d{8}$",
        message="We only accept Australian phone numbers starting 04 which are 10 numbers long.",
    )
    mobile = models.CharField(
        "Mobile Number",
        blank=True,
        unique=True,
        null=True,
        max_length=15,
        validators=[phone_regex],
    )
    about = models.TextField("About Me", blank=True, null=True, max_length=800)
    pic = models.ImageField(
        upload_to="pic_folder/", default="pic_folder/default-avatar.png"
    )
    dob = models.DateField(blank="True", null=True, validators=[no_future])
    bbo_name = models.CharField("BBO Username", blank=True, null=True, max_length=20)
    auto_amount = models.PositiveIntegerField(
        "Auto Top Up Amount",
        blank=True,
        null=True,
        validators=[MaxValueValidator(AUTO_TOP_UP_MAX_AMT)],
    )
    stripe_customer_id = models.CharField(
        "Stripe Customer Id", blank=True, null=True, max_length=25
    )

    AUTO_STATUS = [
        ("Off", "Off"),
        ("Pending", "Pending"),
        ("On", "On"),
    ]

    stripe_auto_confirmed = models.CharField(
        "Stripe Auto Confirmed", max_length=9, choices=AUTO_STATUS, default="Off"
    )

    system_number_search = models.BooleanField(
        "Show %s number on searches" % GLOBAL_ORG, default=True
    )
    receive_sms_results = models.BooleanField("Receive SMS Results", default=True)
    receive_email_results = models.BooleanField(
        "Receive Results by Email", default=True
    )
    receive_sms_reminders = models.BooleanField("Receive SMS Reminders", default=False)
    receive_abf_newsletter = models.BooleanField("Receive ABF Newsletter", default=True)
    receive_marketing = models.BooleanField("Receive Marketing", default=True)
    receive_monthly_masterpoints_report = models.BooleanField(
        "Receive Monthly Masterpoints Report", default=True
    )
    receive_payments_emails = models.BooleanField(
        "Receive Payments Emails", default=True
    )
    receive_low_balance_emails = models.BooleanField(default=True)
    receive_member_to_member_emails = models.BooleanField(default=True)
    windows_scrollbar = models.BooleanField(
        "Use Perfect Scrollbar on Windows", default=False
    )
    last_activity = models.DateTimeField(blank=True, null=True)

    is_abf_active = models.BooleanField(default=True, blank=True)
    """ Is this person an active member of the ABF """

    old_mpc_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    """ Temporary link to old Masterpoint Centre record, required for MPC work """

    all_objects = models.Manager()
    objects = UserManager()
    unreg_objects = UnRegManager()
    contact_objects = ContactManager()

    REQUIRED_FIELDS = [
        "system_number",
        "email",
    ]  # tells createsuperuser to ask for them

    def __str__(self):
        if self.id in (TBA_PLAYER, RBAC_EVERYONE, ABF_USER):
            return self.first_name
        else:
            return f"{self.full_name} ({GLOBAL_ORG}: {self.system_number})"

    @property
    def full_name(self):
        """Returns the person's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def href(self):
        """Returns an HTML link tag that can be used to go to the users public profile"""

        url = reverse("accounts:public_profile", kwargs={"pk": self.id})
        return format_html(
            "<a href='{}' target='_blank'>{}</a>", mark_safe(url), self.full_name
        )


class UnregisteredUserManager(models.Manager):
    """
    Manager to return a query set of unregistered users with non-internal system
    numbers only
    """

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                internal_system_number=False,
            )
        )


class UnregisteredUser(models.Model):
    """Represents users who we have only partial information about and who have not registered themselves yet.
    When a User registers, the matching instance of Unregistered User will be removed.

    Email addresses are a touchy subject as some clubs believe they own this information and do not
    want it shared with other clubs. We protect email address by having another model (UnregisteredUserEmail)
    that is organisation specific. The email address in this model is from the MPC (considered "public"
    although it is not shown to anyone), while the other email address is "private" to the club that
    provided it, but ironically shown to the club that did and editable.
    """

    from organisations.models import Organisation

    ORIGINS = [
        ("MPC", "Masterpoints Centre Import"),
        ("MPCS", "Masterpoints Centre Sync"),
        ("Pianola", "Pianola Import"),
        ("CSV", "CSV Import"),
        ("Manual", "Manual Entry"),
    ]

    system_number = models.IntegerField(
        "%s Number" % GLOBAL_ORG,
        unique=True,
        db_index=True,
    )
    first_name = models.CharField("First Name", max_length=150, blank=True, null=True)
    last_name = models.CharField("Last Name", max_length=150, blank=True, null=True)
    origin = models.CharField("Origin", choices=ORIGINS, max_length=10)

    deceased = models.BooleanField("Deceased", default=False)
    """ Player is deceased, status set by My ABF support """

    internal_system_number = models.BooleanField(default=False)

    last_updated_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="last_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_registration_invite_sent = models.DateTimeField(
        "Last Registration Invite Sent", blank=True, null=True
    )
    last_registration_invite_by_user = models.ForeignKey(
        User, on_delete=models.PROTECT, blank=True, null=True
    )
    last_registration_invite_by_club = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="last_registration_invite_by_club",
    )
    added_by_club = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="added_by_club",
    )
    identifier = models.CharField(
        max_length=10,
        default="NOTSET",
    )
    """ random string identifier to use in emails to handle preferences. Can't use the pk obviously """

    is_active = models.BooleanField(default=True)

    old_mpc_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    """ Temporary link to old Masterpoint Centre record, required for MPC work """

    # Managers: objects excludes internal system number records, all_objects does not
    all_objects = models.Manager()
    objects = UnregisteredUserManager()

    def save(self, *args, **kwargs):
        """create identifier on first save"""
        if not self.pk:
            self.identifier = "".join(
                random.SystemRandom().choice(string.ascii_letters + string.digits)
                for _ in range(10)
            )
        super(UnregisteredUser, self).save(*args, **kwargs)

    def __str__(self):
        if self.internal_system_number:
            return f"{self.full_name} (No {GLOBAL_ORG} number)"
        else:
            return f"{self.full_name} ({GLOBAL_ORG}: {self.system_number})"

    @property
    def full_name(self):
        """Returns the person's full name."""
        return f"{self.first_name} {self.last_name}"


class TeamMate(models.Model):
    """link two members together"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="team_mate_user"
    )
    team_mate = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="team_mate_team_mate"
    )
    make_payments = models.BooleanField("Use my account", default=False)

    def __str__(self):
        if self.make_payments:
            return f"Plus - {self.user.full_name} - {self.team_mate.full_name}"
        else:
            return f"Basic - {self.user.full_name} - {self.team_mate.full_name}"


class UserPaysFor(models.Model):
    """Allow a user to charge their bridge to another person"""

    class Circumstance(models.TextChoices):
        ALWAYS = "AL", "Always"
        IF_PLAYING_TOGETHER = "PT", "If Playing Together"
        IF_PLAYING_SAME_SESSION = "PS", "If Playing Same Session"

    sponsor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sponsor")
    lucky_person = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lucky_person"
    )
    criterion = models.CharField(
        max_length=2, choices=Circumstance.choices, default=Circumstance.ALWAYS
    )

    def __str__(self):
        return f"{self.sponsor.full_name} pays for {self.lucky_person.full_name}"


def _create_api_token():
    string_size = 40 - len(API_KEY_PREFIX)
    random_string = "".join(
        random.SystemRandom().choice(
            string.ascii_letters + string.digits + "!$^()-_{}|/"
        )
        for _ in range(string_size)
    )
    return f"{API_KEY_PREFIX}{random_string}"


class APIToken(models.Model):
    """API Tokens map to a user and are used by any API functions

    We don't put an expiry on the token but this could be added later if required."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(
        max_length=40,
        default="Overridden on save",
        help_text="This is set when you first save it",
    )
    created_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.created_date}"

    def save(self, *args, **kwargs):
        """Create token on first save"""

        if len(self.token) != 40:
            self.token = _create_api_token()

        super(APIToken, self).save(*args, **kwargs)


class UserAdditionalInfo(models.Model):
    """Additional information about a user that is not regularly accessed.
    The intention is to move all of the extras from the User class into here over time
    as the User is getting overloaded and is accessed constantly by Django so we should
    try to keep it clean.
    """
    # Import here to avoid circular dependencies
    from organisations.models import Organisation

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email_hard_bounce = models.BooleanField(default=False)
    """ Set this flag if we get a hard bounce from sending an email """
    email_hard_bounce_reason = models.TextField(null=True, blank=True)
    """ Reason for the bounce """
    email_hard_bounce_date = models.DateTimeField(null=True, blank=True)
    congress_view_filters = models.CharField(max_length=400, blank=True)
    """ user preferences for the congress listing page """
    member_sort_order = models.CharField(max_length=20, blank=True)
    """ sort order for the club menu members tab list """
    last_club_visited = models.IntegerField(null=True, blank=True)
    """ used to store which club was last visited for users with access to multiple clubs """
    last_registration_invite_sent = models.DateTimeField(
        "Last Registration Invite Sent", blank=True, null=True
    )

    def __str__(self):
        return self.user.__str__()


class NextInternalSystemNumber(models.Model):
    """A singleton table to manage the next internal system number

    All access should be through the next_available class method:

        system_number = NextInternalSystemNumber.next_available()

    This will return the number to be used, update the stored value
    and take a row level update lock until the end of the transaction.

    NOTE: As this is holding a lock, make sure that the transaction is
    completed (comitted or rolled back) as quickly as possible.
    """

    _first_number = 1_000_000_000

    number = models.IntegerField("Next Internal System Number", default=_first_number)

    def save(self, *args, **kwargs):
        self.pk = 1
        super(NextInternalSystemNumber, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        """Load the singleton, taking an update lock
        Must be called within a transaction"""
        try:
            obj = cls.objects.select_for_update().get(pk=1)
        except cls.DoesNotExist:
            obj = cls()
            obj.number = cls._first_number
            obj.save()
            obj = cls.objects.select_for_update().get(pk=1)
        return obj

    @classmethod
    def next_available(cls):
        """Returns the next available internal system number
        Note that this takes an update lock on the singleton until
         the end of teh outermost transaction"""
        nisn = cls.load()
        allocated_number = nisn.number
        nisn.number += 1
        nisn.save()
        return allocated_number

    @classmethod
    def is_internal(cls, number):
        """Checks whether the number is an internal system number"""
        return number >= cls._first_number


class SystemCard(models.Model):
    """System cards for users"""

    class SystemClassification(models.TextChoices):
        GREEN = "G"
        BLUE = "B"
        YELLOW = "Y"
        RED = "R"

    # Meta data
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card_name = models.CharField(max_length=100)
    save_date = models.DateTimeField(auto_now=True)

    # Basic Info
    player1 = models.CharField(max_length=100, blank=True)
    player2 = models.CharField(max_length=100, blank=True)
    basic_system = models.CharField(max_length=50, default="Standard American")
    system_classification = models.CharField(
        max_length=1,
        choices=SystemClassification.choices,
        default=SystemClassification.GREEN,
    )
    brown_sticker = models.BooleanField(default=False)
    brown_sticker_why = models.CharField(max_length=50, blank=True)
    canape = models.BooleanField(default=False)

    # Openings
    opening_1c = models.CharField(max_length=20, blank=True)
    opening_1d = models.CharField(max_length=20, blank=True)
    opening_1h = models.CharField(max_length=20, blank=True)
    opening_1s = models.CharField(max_length=20, blank=True)
    opening_1nt = models.CharField(max_length=20, blank=True)

    # Summary
    summary_bidding = models.CharField(max_length=100, blank=True)
    summary_carding = models.CharField(max_length=100, blank=True)

    # Pre-alerts
    pre_alerts = models.TextField(blank=True)

    # 1NT Responses
    nt1_response_2c = models.CharField(max_length=20, blank=True)
    nt1_response_2d = models.CharField(max_length=20, blank=True)
    nt1_response_2h = models.CharField(max_length=20, blank=True)
    nt1_response_2s = models.CharField(max_length=20, blank=True)
    nt1_response_2nt = models.CharField(max_length=20, blank=True)

    # 2 Level Openings
    opening_2c = models.CharField(max_length=20, blank=True)
    opening_2d = models.CharField(max_length=20, blank=True)
    opening_2h = models.CharField(max_length=20, blank=True)
    opening_2s = models.CharField(max_length=20, blank=True)
    opening_2nt = models.CharField(max_length=20, blank=True)

    # Higher Openings
    opening_3nt = models.CharField(max_length=20, blank=True)
    opening_other = models.CharField(max_length=20, blank=True)

    # Competitive bids
    competitive_doubles = models.CharField(max_length=100, blank=True)
    competitive_lead_directing_doubles = models.CharField(max_length=100, blank=True)
    competitive_jump_overcalls = models.CharField(max_length=100, blank=True)
    competitive_unusual_nt = models.CharField(max_length=100, blank=True)
    competitive_1nt_overcall_immediate = models.CharField(max_length=20, blank=True)
    competitive_1nt_overcall_reopening = models.CharField(max_length=20, blank=True)
    competitive_negative_double_through = models.CharField(max_length=20, blank=True)
    competitive_responsive_double_through = models.CharField(max_length=20, blank=True)
    competitive_immediate_cue_bid_minor = models.CharField(max_length=100, blank=True)
    competitive_immediate_cue_bid_major = models.CharField(max_length=100, blank=True)
    competitive_weak_2_defense = models.CharField(max_length=100, blank=True)
    competitive_weak_3_defense = models.CharField(max_length=100, blank=True)
    competitive_transfer_defense = models.CharField(max_length=100, blank=True)
    competitive_nt_defense = models.CharField(max_length=100, blank=True)

    # Basic Responses
    basic_response_jump_raise_minor = models.CharField(max_length=100, blank=True)
    basic_response_jump_raise_major = models.CharField(max_length=100, blank=True)
    basic_response_jump_shift_minor = models.CharField(max_length=100, blank=True)
    basic_response_jump_shift_major = models.CharField(max_length=100, blank=True)
    basic_response_to_2c_opening = models.CharField(max_length=100, blank=True)
    basic_response_to_strong_2_opening = models.CharField(max_length=100, blank=True)
    basic_response_to_2nt_opening = models.CharField(max_length=100, blank=True)

    # Carding - suit
    play_suit_lead_sequence = models.CharField(max_length=100, blank=True)
    play_suit_lead_4_or_more = models.CharField(max_length=100, blank=True)
    play_suit_lead_4_small = models.CharField(max_length=100, blank=True)
    play_suit_lead_3 = models.CharField(max_length=100, blank=True)
    play_suit_lead_in_partners_suit = models.CharField(max_length=100, blank=True)
    play_suit_discards = models.CharField(max_length=100, blank=True)
    play_suit_count = models.CharField(max_length=100, blank=True)
    play_suit_signal_on_partner_lead = models.CharField(max_length=100, blank=True)

    # Carding - NT
    play_nt_lead_sequence = models.CharField(max_length=100, blank=True)
    play_nt_lead_4_or_more = models.CharField(max_length=100, blank=True)
    play_nt_lead_4_small = models.CharField(max_length=100, blank=True)
    play_nt_lead_3 = models.CharField(max_length=100, blank=True)
    play_nt_lead_in_partners_suit = models.CharField(max_length=100, blank=True)
    play_nt_discards = models.CharField(max_length=100, blank=True)
    play_nt_count = models.CharField(max_length=100, blank=True)
    play_nt_signal_on_partner_lead = models.CharField(max_length=100, blank=True)

    play_signal_declarer_lead = models.CharField(max_length=100, blank=True)
    play_notes = models.CharField(max_length=100, blank=True)

    # Slams
    slam_conventions = models.CharField(max_length=200, blank=True)

    # Other
    other_conventions = models.CharField(max_length=200, blank=True)

    # Responses
    # 1C
    response_1c_1d = models.CharField(max_length=20, blank=True)
    response_1c_1h = models.CharField(max_length=20, blank=True)
    response_1c_1s = models.CharField(max_length=20, blank=True)
    response_1c_1n = models.CharField(max_length=20, blank=True)
    response_1c_2c = models.CharField(max_length=20, blank=True)
    response_1c_2d = models.CharField(max_length=20, blank=True)
    response_1c_2h = models.CharField(max_length=20, blank=True)
    response_1c_2s = models.CharField(max_length=20, blank=True)
    response_1c_2n = models.CharField(max_length=20, blank=True)
    response_1c_3c = models.CharField(max_length=20, blank=True)
    response_1c_3d = models.CharField(max_length=20, blank=True)
    response_1c_3h = models.CharField(max_length=20, blank=True)
    response_1c_3s = models.CharField(max_length=20, blank=True)
    response_1c_3n = models.CharField(max_length=20, blank=True)
    response_1c_other = models.CharField(max_length=100, blank=True)

    # 1D
    response_1d_1h = models.CharField(max_length=20, blank=True)
    response_1d_1s = models.CharField(max_length=20, blank=True)
    response_1d_1n = models.CharField(max_length=20, blank=True)
    response_1d_2c = models.CharField(max_length=20, blank=True)
    response_1d_2d = models.CharField(max_length=20, blank=True)
    response_1d_2h = models.CharField(max_length=20, blank=True)
    response_1d_2s = models.CharField(max_length=20, blank=True)
    response_1d_2n = models.CharField(max_length=20, blank=True)
    response_1d_3c = models.CharField(max_length=20, blank=True)
    response_1d_3d = models.CharField(max_length=20, blank=True)
    response_1d_3h = models.CharField(max_length=20, blank=True)
    response_1d_3s = models.CharField(max_length=20, blank=True)
    response_1d_3n = models.CharField(max_length=20, blank=True)
    response_1d_other = models.CharField(max_length=100, blank=True)

    # 1H
    response_1h_1s = models.CharField(max_length=20, blank=True)
    response_1h_1n = models.CharField(max_length=20, blank=True)
    response_1h_2c = models.CharField(max_length=20, blank=True)
    response_1h_2d = models.CharField(max_length=20, blank=True)
    response_1h_2h = models.CharField(max_length=20, blank=True)
    response_1h_2s = models.CharField(max_length=20, blank=True)
    response_1h_2n = models.CharField(max_length=20, blank=True)
    response_1h_3c = models.CharField(max_length=20, blank=True)
    response_1h_3d = models.CharField(max_length=20, blank=True)
    response_1h_3h = models.CharField(max_length=20, blank=True)
    response_1h_3s = models.CharField(max_length=20, blank=True)
    response_1h_3n = models.CharField(max_length=20, blank=True)
    response_1h_other = models.CharField(max_length=100, blank=True)

    # 1S
    response_1s_1n = models.CharField(max_length=20, blank=True)
    response_1s_2c = models.CharField(max_length=20, blank=True)
    response_1s_2d = models.CharField(max_length=20, blank=True)
    response_1s_2h = models.CharField(max_length=20, blank=True)
    response_1s_2s = models.CharField(max_length=20, blank=True)
    response_1s_2n = models.CharField(max_length=20, blank=True)
    response_1s_3c = models.CharField(max_length=20, blank=True)
    response_1s_3d = models.CharField(max_length=20, blank=True)
    response_1s_3h = models.CharField(max_length=20, blank=True)
    response_1s_3s = models.CharField(max_length=20, blank=True)
    response_1s_3n = models.CharField(max_length=20, blank=True)
    response_1s_other = models.CharField(max_length=100, blank=True)

    # 1N
    response_1n_3c = models.CharField(max_length=20, blank=True)
    response_1n_3d = models.CharField(max_length=20, blank=True)
    response_1n_3h = models.CharField(max_length=20, blank=True)
    response_1n_3s = models.CharField(max_length=20, blank=True)
    response_1n_3n = models.CharField(max_length=20, blank=True)
    response_1n_other = models.CharField(max_length=100, blank=True)

    # 2c
    response_2c_2d = models.CharField(max_length=20, blank=True)
    response_2c_2h = models.CharField(max_length=20, blank=True)
    response_2c_2s = models.CharField(max_length=20, blank=True)
    response_2c_2n = models.CharField(max_length=20, blank=True)
    response_2c_3c = models.CharField(max_length=20, blank=True)
    response_2c_3d = models.CharField(max_length=20, blank=True)
    response_2c_3h = models.CharField(max_length=20, blank=True)
    response_2c_3s = models.CharField(max_length=20, blank=True)
    response_2c_3n = models.CharField(max_length=20, blank=True)
    response_2c_other = models.CharField(max_length=100, blank=True)

    # 2d
    response_2d_2h = models.CharField(max_length=20, blank=True)
    response_2d_2s = models.CharField(max_length=20, blank=True)
    response_2d_2n = models.CharField(max_length=20, blank=True)
    response_2d_3c = models.CharField(max_length=20, blank=True)
    response_2d_3d = models.CharField(max_length=20, blank=True)
    response_2d_3h = models.CharField(max_length=20, blank=True)
    response_2d_3s = models.CharField(max_length=20, blank=True)
    response_2d_3n = models.CharField(max_length=20, blank=True)
    response_2d_other = models.CharField(max_length=100, blank=True)

    # 2h
    response_2h_2s = models.CharField(max_length=20, blank=True)
    response_2h_2n = models.CharField(max_length=20, blank=True)
    response_2h_3c = models.CharField(max_length=20, blank=True)
    response_2h_3d = models.CharField(max_length=20, blank=True)
    response_2h_3h = models.CharField(max_length=20, blank=True)
    response_2h_3s = models.CharField(max_length=20, blank=True)
    response_2h_3n = models.CharField(max_length=20, blank=True)
    response_2h_other = models.CharField(max_length=100, blank=True)

    # 2s
    response_2s_2n = models.CharField(max_length=20, blank=True)
    response_2s_3c = models.CharField(max_length=20, blank=True)
    response_2s_3d = models.CharField(max_length=20, blank=True)
    response_2s_3h = models.CharField(max_length=20, blank=True)
    response_2s_3s = models.CharField(max_length=20, blank=True)
    response_2s_3n = models.CharField(max_length=20, blank=True)
    response_2s_other = models.CharField(max_length=100, blank=True)

    # 2NT
    response_2n_3c = models.CharField(max_length=20, blank=True)
    response_2n_3d = models.CharField(max_length=20, blank=True)
    response_2n_3h = models.CharField(max_length=20, blank=True)
    response_2n_3s = models.CharField(max_length=20, blank=True)
    response_2n_3n = models.CharField(max_length=20, blank=True)
    response_2n_other = models.CharField(max_length=100, blank=True)

    # notes
    response_notes = models.CharField(max_length=200, blank=True)

    other_notes = models.CharField(max_length=400, blank=True)

    def __str__(self):
        local_datetime = timezone.localtime(self.save_date)
        return f"{self.user.full_name} - {self.card_name} - {local_datetime:%a %-d %b %Y %I:%M%p}"
