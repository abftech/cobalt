from django.db import models

from accounts.models import User
from organisations.models import Organisation


#     "ChargeTypeID": 1,
#     "TypeName": "Annual capitation - full year",
#     "FeeInclGST": 23.3,
#     "MPsOrPlayers": "P",
#     "QuickbooksCode": "4018",
#     "IsShowOnInvoice": "Y",
#     "IsGSTTaxable": "Y",
#     "InvoiceWords": "New year capitation",
#     "IsShowOnPriceList": "Y",
#     "PriceListSequence": 101


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
    billing_club_id = models.PositiveIntegerField(null=True)
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
