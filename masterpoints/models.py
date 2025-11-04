from django.contrib.auth.models import AbstractUser
from django.db import models

from accounts.models import User
from organisations.models import Organisation


class MPColours(models.TextChoices):
    GREEN = "G", "Green"
    RED = "R", "Red"
    GOLD = "Y", "Gold"

class MPSource(models.TextChoices):
    CLUB = "C", "Club"
    EVENT = "E", "Event"

class ChargeType(models.Model):
    """Different types of charges for Masterpoints"""

    """
    SQL Server definition - delete later
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"ChargeTypeID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    {"ORDINAL_POSITION":2,"COLUMN_NAME":"TypeName","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":3,"COLUMN_NAME":"FeeInclGST","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":4,"COLUMN_NAME":"MPsOrPlayers","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":5,"COLUMN_NAME":"QuickbooksCode","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":6,"COLUMN_NAME":"IsShowOnInvoice","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":7,"COLUMN_NAME":"IsGSTTaxable","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":8,"COLUMN_NAME":"InvoiceWords","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":9,"COLUMN_NAME":"IsShowOnPriceList","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":10,"COLUMN_NAME":"PriceListSequence","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"}]
    """

    old_mpc_id = models.PositiveIntegerField(unique=True)
    """ This is only needed while we still use the MPC as the source of truth. Delete later """
    type_name = models.CharField(max_length=50)
    fee_including_gst = models.DecimalField(decimal_places=2, max_digits=8, default=0)
    show_on_invoice = models.BooleanField(default=True)
    is_gst_taxable = models.BooleanField(default=True)
    invoice_words = models.CharField(max_length=50, null=True, blank=True)

    # These may not be needed
    show_on_price_list = models.BooleanField(default=True)
    price_list_sequence = models.PositiveIntegerField(null=True, blank=True)
    mps_or_player = models.CharField(max_length=1, null=True, blank=True)

    def __str__(self):
        return self.type_name


class MasterpointEvent(models.Model):
    """These represent the acceptable events for awarding masterpoints"""

    """
    SQL Server definition - delete later
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"EventID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    {"ORDINAL_POSITION":2,"COLUMN_NAME":"EventName","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":50,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":3,"COLUMN_NAME":"EventCode","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":6,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":4,"COLUMN_NAME":"MPColour","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":5,"COLUMN_NAME":"Comments","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":200,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":6,"COLUMN_NAME":"IsClosed","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":7,"COLUMN_NAME":"BillingClubID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":8,"COLUMN_NAME":"tGrade","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":3,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":9,"COLUMN_NAME":"Grade","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":3,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":10,"COLUMN_NAME":"AddedByUserID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":11,"COLUMN_NAME":"DateAdded","DATA_TYPE":"datetime","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":12,"COLUMN_NAME":"QuickBooksProductCode","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":20,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":13,"COLUMN_NAME":"GoldPointEventTier","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"}]
    """

    old_mpc_id = models.PositiveIntegerField(unique=True)
    """ This is only needed while we still use the MPC as the source of truth. Delete later """
    event_name = models.CharField(max_length=50)
    event_code = models.CharField(max_length=15)
    mp_colour = models.CharField(max_length=1)
    comments = models.TextField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    billing_club_id = models.IntegerField(null=True)
    """ Should only be needed for old MPC - billing_organisation is the real link """
    billing_organisation = models.ForeignKey(
        Organisation, on_delete=models.PROTECT, null=True, blank=True
    )
    t_grade = models.CharField(max_length=3, null=True, blank=True)
    grade = models.CharField(max_length=3, null=True, blank=True)
    gold_point_event_tier = models.CharField(max_length=3, null=True, blank=True)
    added_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_code} - {self.event_name}"


class GreenPointAchievementBand(models.Model):
    """Requirements for green point levels"""

    # SQL Server definition - delete later
    # {"ORDINAL_POSITION":1,"COLUMN_NAME":"BandID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    # {"ORDINAL_POSITION":2,"COLUMN_NAME":"LoPoints","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    # {"ORDINAL_POSITION":3,"COLUMN_NAME":"HiPoints","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"}

    old_mpc_id = models.PositiveIntegerField()
    """ temporary link with MPC """
    low_points = models.DecimalField(decimal_places=2, max_digits=10)
    high_points = models.DecimalField(decimal_places=2, max_digits=10)

    def __str__(self):
        return f"{self.low_points} to {self.high_points}"


class Rank(models.Model):
    """Different levels within Masterpoint ranking"""

    """
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"RankID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    {"ORDINAL_POSITION":2,"COLUMN_NAME":"RankName","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":15,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":3,"COLUMN_NAME":"RankOldName","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":15,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":4,"COLUMN_NAME":"RankSequence","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":5,"COLUMN_NAME":"TotalNeeded","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":6,"COLUMN_NAME":"RedGoldNeeded","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":7,"COLUMN_NAME":"GoldNeeded","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"}]
    """

    old_mpc_id = models.PositiveIntegerField(db_index=True)
    rank_name = models.CharField(max_length=15)
    rank_old_name = models.CharField(max_length=15)
    rank_sequence = models.CharField(max_length=1)
    total_needed = models.PositiveIntegerField()
    red_gold_needed = models.PositiveIntegerField()
    gold_needed = models.PositiveIntegerField()

    def __str__(self):
        return self.rank_name


class Period(models.Model):
    """Not sure yet if we need this"""

    """
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"PeriodID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    {"ORDINAL_POSITION":2,"COLUMN_NAME":"PeriodMonth","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":3,"COLUMN_NAME":"PeriodYear","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":4,"COLUMN_NAME":"PeriodEnd","DATA_TYPE":"datetime","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":5,"COLUMN_NAME":"IsCurrent","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"}]
    """

    old_mpc_id = models.PositiveIntegerField(db_index=True)
    period_month = models.PositiveIntegerField()
    period_year = models.PositiveIntegerField()
    period_end = models.DateTimeField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.period_year}-{self.period_month}"


class Promotion(models.Model):
    """record of when players where promoted"""

    """
    SQL Server definition - delete later
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"PromotionID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    {"ORDINAL_POSITION":2,"COLUMN_NAME":"PlayerID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":3,"COLUMN_NAME":"RankID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":4,"COLUMN_NAME":"PeriodID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":5,"COLUMN_NAME":"RecordDate","DATA_TYPE":"datetime","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"}]
    """

    old_mpc_id = models.PositiveIntegerField()
    system_number = models.PositiveIntegerField()
    """ ideally this would be a foreign key but we can't link to both User and UnregisteredUser """
    rank = models.ForeignKey(Rank, on_delete=models.PROTECT, null=True, blank=True)
    period = models.ForeignKey(Period, on_delete=models.PROTECT, null=True, blank=True)
    record_date = models.DateTimeField()

    def __str__(self):
        return f"{self.system_number} - {self.rank}"


class MPBatch(models.Model):
    """Basic unit of uploaded data with masterpoints"""

    """
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"MPBatchID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    {"ORDINAL_POSITION":2,"COLUMN_NAME":"MPsSubmittedGreen","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":3,"COLUMN_NAME":"MPsSubmittedRed","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":4,"COLUMN_NAME":"MPsSubmittedGold","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":5,"COLUMN_NAME":"PostedByUserID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":6,"COLUMN_NAME":"PostedDate","DATA_TYPE":"datetime","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":7,"COLUMN_NAME":"Source","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":8,"COLUMN_NAME":"EventOrClubID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":9,"COLUMN_NAME":"PostingMonth","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":10,"COLUMN_NAME":"PostingYear","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":11,"COLUMN_NAME":"IsMcCutcheonEligible","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":12,"COLUMN_NAME":"IsApproved","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":13,"COLUMN_NAME":"UploaderComments","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":200,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":14,"COLUMN_NAME":"AdminComments","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":200,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":15,"COLUMN_NAME":"IsCharged","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":16,"COLUMN_NAME":"AuthorisationNumber","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":100,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":17,"COLUMN_NAME":"UploadedFileName","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":100,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":18,"COLUMN_NAME":"HowSubmitted","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":19,"COLUMN_NAME":"EventMonth","DATA_TYPE":"varchar","CHARACTER_MAXIMUM_LENGTH":3,"IS_NULLABLE":"YES"}]
    """
    masterpoint_event = models.ForeignKey(MasterpointEvent, on_delete=models.PROTECT, null=True, blank=True)
    """ We link to either an Event (in Masterpoints terminology) or a club """
    club = models.ForeignKey(Organisation, on_delete=models.PROTECT, null=True, blank=True)
    """ We link to either an Event (in Masterpoints terminology) or a club """
    old_mpc_id = models.PositiveIntegerField(unique=True, db_index=True)
    mps_submitted_green = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    mps_submitted_red = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    mps_submitted_gold = models.DecimalField(
        decimal_places=2, max_digits=10, null=True, blank=True
    )
    old_mpc_posted_by_user_id = models.IntegerField(null=True, blank=True)
    posted_date = models.DateTimeField()
    source = models.CharField(max_length=1, choices=MPSource.choices)
    old_mpc_event_or_club_id = models.IntegerField()
    """ Can be removed when we no longer sync from the MPC """
    posting_month = models.IntegerField(null=True, blank=True)
    posting_year = models.IntegerField(null=True, blank=True)
    is_mccutcheon_eligible = models.BooleanField()
    is_approved = models.BooleanField()
    uploaded_comments = models.TextField(null=True, blank=True)
    admin_comments = models.TextField(null=True, blank=True)
    is_charged = models.BooleanField()
    authorisation_number = models.CharField(max_length=100, null=True, blank=True)
    uploaded_filename = models.CharField(max_length=100, null=True, blank=True)
    how_submitted = models.CharField(max_length=1)
    event_month = models.CharField(max_length=3, null=True, blank=True)

    check_flag = models.BooleanField(default=False)
    """ temporary. Used while we sync with the MPC. Can be removed later """

    class Meta:
        verbose_name_plural = "MP Batches"

    def __str__(self):
        return f"{self.old_mpc_id} {self.posted_date:%Y-%m-%d}"


class MPTran(models.Model):
    """
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"TranID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    {"ORDINAL_POSITION":2,"COLUMN_NAME":"PlayerID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":3,"COLUMN_NAME":"MPColour","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":4,"COLUMN_NAME":"MPs","DATA_TYPE":"money","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":5,"COLUMN_NAME":"Source","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":6,"COLUMN_NAME":"MPBatchID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":7,"COLUMN_NAME":"IsApproved","DATA_TYPE":"char","CHARACTER_MAXIMUM_LENGTH":1,"IS_NULLABLE":"YES"}]
    """

    old_mpc_id = models.PositiveIntegerField(db_index=True)
    old_mpc_player_id = models.PositiveIntegerField()
    """ temporary - here for any debugging """
    system_number = models.PositiveIntegerField(db_index=True)
    mp_colour = models.CharField(max_length=1, choices=MPColours.choices)
    mp_amount = models.DecimalField(decimal_places=2, max_digits=10)
    source = models.CharField(max_length=1, choices=MPSource.choices)
    old_mp_batch_id = models.PositiveIntegerField()
    """ temporary - here for any debugging """
    mp_batch = models.ForeignKey(MPBatch, on_delete=models.CASCADE)
    is_approved = models.BooleanField()

    def __str__(self):
        return f"{self.system_number} - {self.mp_colour} - {self.mp_amount}"


class ClubMembershipHistory(models.Model):
    """historic view of memberships"""

    """
    [{"ORDINAL_POSITION":1,"COLUMN_NAME":"RecordID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"NO"},
    {"ORDINAL_POSITION":2,"COLUMN_NAME":"BillingMonth","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":3,"COLUMN_NAME":"BillingYear","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":4,"COLUMN_NAME":"ClubID","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"},
    {"ORDINAL_POSITION":5,"COLUMN_NAME":"HomeMembers","DATA_TYPE":"int","CHARACTER_MAXIMUM_LENGTH":null,"IS_NULLABLE":"YES"}]
    """

    old_mpc_id = models.PositiveIntegerField()
    """ only needed temporarily """
    billing_month = models.PositiveIntegerField()
    billing_year = models.PositiveIntegerField()
    old_mpc_club_id = models.PositiveIntegerField()
    """ only needed temporarily """
    club = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    home_members = models.PositiveIntegerField()

    class Meta:
        verbose_name_plural = "Club Membership Histories"

    def __str__(self):
        return f"{self.club} - {self.billing_year}/{self.billing_month} - {self.home_members}"
