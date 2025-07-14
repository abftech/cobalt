"""Script to create cobalt test data from csv files

CSV Files are processed in sort order and depend upon data that is created in earlier steps.
For example, an Event needs to be created before an EventEntry.

File format is:

Row 1 - app, model [, duplicates]

    app - name of Django application, e.g. events
    model - Django model name e.g. EventEntry
    duplicates - optional literal. If the word duplicates is present then they are allowed

Row 2 - headings

    These map to the field names of the table.

Example:

accounts             , TeamMate
id.user.accounts.User, id.team_mate.accounts.User, make_payments
aa                   , mark                      , 0
bb                   , mark                      , 0



"""

import contextlib
from django.core.exceptions import SuspiciousOperation

from cobalt.settings import (
    RBAC_EVERYONE,
    TIME_ZONE,
    TBA_PLAYER,
    COBALT_HOSTNAME,
)
from accounts.models import User
from django.core.management.base import BaseCommand
from accounts.management.commands.accounts_core import create_fake_user
import datetime
import pytz
from django.utils.timezone import make_aware, now
import glob
import sys
from inspect import currentframe, getframeinfo

# This import is needed, although your IDE may disagree - it is used through exec
from importlib import import_module

TZ = pytz.timezone(TIME_ZONE)
DATA_DIR = "tests/test_data"
CORE_DATA_DIR = "tests/test_data_core"


def _get_instance_of_app_model(app, model):
    """See if a app model combination is valid, returns an instance of the model or None"""

    exec_cmd = "module = import_module('%s.models')\ninstance = module.%s()" % (
        app,
        model,
    )
    # Set local array before we call the exec command and its value will change when returned
    local_array = {}

    # Execute
    exec(exec_cmd, globals(), local_array)

    # Return what we got
    return local_array["instance"]


def _parse_csv(file):
    """
    try to sort out the mess Excel makes of CSV files.
    Requires csv files to have the app and model in the first row and
    the fieldnames in the second row.
    This works on a single CSV file
    """

    with open(file, encoding="utf-8") as csv_file:

        lines = []
        for line in csv_file:

            # skip line if it is commented out (# in first column)
            if line.find("#") == 0:
                continue

            # skip blank lines
            if line.strip() == "":
                continue

            # skip if line is only commas, can happen if edited by Excel
            if line.replace(",", "").strip() == "":
                continue

            # Add apparently valid lines
            lines.append(line)

    # Data will hold rows of data excluding the first two which are configuration info
    data = []

    try:
        # First line should be the app, model
        app, model = lines[0].split(",")[:2]
    except ValueError:
        print("\n\nError\n")
        print("Didn't find App, Model on first line of file")
        print(f"File is: {file}")
        print("Line is: %s\n" % lines[0])
        sys.exit()

    try:
        # Optional third parameter to allow duplicates
        allow_dupes = lines[0].split(",")[3] == "duplicates"
    except (ValueError, IndexError):
        allow_dupes = False

    # Second line should have the headers which define the fields and their type
    # We don't validate them here, we just load them
    headers = lines[1]
    header_list = [header.strip() for header in headers.split(",")]

    # loop through records, line 3 onwards
    for line in lines[2:]:

        # split to parts using commas
        columns = line.split(",")

        # loop through columns
        row = {}
        for i in range(len(header_list)):

            try:
                # Skip missing columns - Excel adds these at the end of the row
                if columns[i].strip() == "":
                    continue
                # use header name as index and this field as the data
                row[header_list[i]] = columns[i].strip()
            except IndexError:
                row[header_list[i]] = None

        data.append(row)

    return app.strip(), model.strip(), data, allow_dupes


def _handle_not_found_error(app, model, csv):

    print("\n\nError\n")
    print(f"Failed to create instance of {app}.{model}")
    print(f"Processing file: {csv}\n")
    frame_tags_info = getframeinfo(currentframe())
    print(
        "Error somewhere above: ",
        frame_tags_info.filename,
        frame_tags_info.lineno,
        "\n",
    )
    sys.exit()


def _print_error_and_exit(error, csv, key, value):
    print("\n\nError\n")
    print(error)
    print()
    print("Options are:")
    print("  d.  exact date YYYMMDD")
    print("  m.  exact time 24hr clock HH:MM")
    print("  id. Link to foreign key")
    print(
        "  t.  relative date integer. Positive is in the past, negative in the future."
    )
    print()
    print(f"CSV File: {csv}")
    print(f"Heading: {key}")
    print(f"Data: {value}")
    print()
    sys.exit()


class Command(BaseCommand):
    def __init__(self):
        super().__init__()

        # we map the Django id of the table to the object
        # e.g. self.id_array["accounts.User"][1] = Everyone user
        self.id_array = {}

    def add_arguments(self, parser):
        parser.add_argument(
            "--core_test_files",
            action="store_true",
            help="Use the core files directory instead of default",
        )

    def handle(self, *args, **options):

        # see which directory to use to find the files
        data_dir = CORE_DATA_DIR if options["core_test_files"] else DATA_DIR

        # Check we aren't in production
        if COBALT_HOSTNAME in ["myabf.com.au", "www.myabf.com.au"]:
            raise SuspiciousOperation(
                "Not for use in production. This cannot be used in a production system."
            )

        print("Running add_test_data")

        try:
            for file_name in sorted(glob.glob(f"{data_dir}/*.csv")):
                print("\n#########################################################")
                print(f"Processing: {file_name}")
                self.process_csv(file_name)

        except KeyboardInterrupt:
            print("\n\nTest data loading interrupted by user\n")
            sys.exit(0)

    def process_csv(self, csv):
        """do the work on the csv data"""

        # get the data from the file
        app, model, data, allow_dupes = _parse_csv(csv)
        print(f"App Model is: {app}.{model}\n")

        # special case for creating users
        if app == "accounts" and model == "User":
            self.accounts_user(app, model, data)
            return

        # Pass dictionary of app models through process_csv_row to build it up
        app_model_dic = {}
        for row in data:
            self.process_csv_row(row, app, model, allow_dupes, csv, app_model_dic)

        # Add this app model dictionary to the global list for use later
        self.id_array[f"{app}.{model}"] = app_model_dic

    def process_csv_row(self, row, app, model, allow_dupes, csv, app_model_dic):
        """handles processing a single row of data from the CSV"""

        # Get instance of app model - effectively an empty database row
        instance = self._get_instance_from_db(row, app, model)

        # Check and process instance
        self._check_if_exists_or_add(
            instance, allow_dupes, app, model, row, app_model_dic, csv
        )

    def _check_if_exists_or_add(
        self, instance, allow_dupes, app, model, row, app_model_dic, csv
    ):

        if instance and not allow_dupes:
            print(f"already present: {instance}")
        else:
            instance = self._add_row_to_db(app, model, row, csv)

        # add to dic if we have an id field
        if "id" in row.keys():
            app_model_dic[row["id"]] = instance

        return app_model_dic

    def _add_row_to_db(self, app, model, row, csv):

        # See if this is a valid app model combination
        app_model_instance = _get_instance_of_app_model(app, model)

        if not app_model_instance:
            # This will sys.exit()
            _handle_not_found_error(app, model, csv)

        # key is the field, value is what to put in it
        for key, value in row.items():

            # CSV can use ^ symbol to represent a comma
            with contextlib.suppress(AttributeError):
                value = value.replace("^", ",")

            # id is assigned by Django, the id field in the CSV is what we refer to it as so skip
            if key == "id":
                continue

            # Foreign key
            if len(key) > 3 and key[:3] == "id.":  # foreign key
                foreign_key, foreign_key_value = self._handle_foreign_key(
                    key, row, value, app, model
                )
                setattr(app_model_instance, foreign_key, foreign_key_value)

            # Relative date, X days ago or if negative X days in the future
            elif key[:2] == "t.":
                field = key[2:]
                try:
                    adjusted_date = now() - datetime.timedelta(days=int(value))
                except ValueError:
                    _print_error_and_exit(
                        "Relative date (t.) is not an integer.", csv, key, value
                    )
                datetime_local = adjusted_date.astimezone(TZ)
                setattr(app_model_instance, field, datetime_local)

            # Specific date YYYYMMDD
            elif key[:2] == "d.":
                field = key[2:]
                val_str = f"{value}"

                try:
                    year = val_str[:4]
                    month = val_str[4:6]
                    day = val_str[6:8]
                    this_date = make_aware(
                        datetime.datetime(int(year), int(month), int(day), 0, 0),
                        TZ,
                    )
                except ValueError:
                    _print_error_and_exit(
                        "Exact date (d.) is not in format YYYYMMDD.", csv, key, value
                    )
                setattr(app_model_instance, field, this_date)

            # Time
            elif key[:2] == "m.":
                field = key[2:]
                try:
                    date_field = datetime.datetime.strptime(value, "%H:%M").time()
                except ValueError:
                    _print_error_and_exit(
                        "Time (m.) is not in format HH:MM", csv, key, value
                    )
                setattr(app_model_instance, field, date_field)

            # Any other normal field
            else:
                setattr(app_model_instance, key, value)

        app_model_instance.save()
        print(f"Added: {app_model_instance}")
        return app_model_instance

    def _get_instance_from_db(self, row, app, model):
        """see if this data is already present. We go through the headings found in row and build a query
        string to call using exec. We ignore the fields that aren't fieldnames - t. d. m. and id
        For foreign keys (id.) we build a slightly different query.
        """

        # build up a string of Python commands to execute
        exec_cmd = (
            f"module = import_module('{app}.models')\ninstance = module.{model}.objects"
        )

        # Go through each value - key is the field name, value is the data
        for key, value in row.items():

            # Ignore unset values
            if not value:
                continue

            # Ignore id fields
            if key == "id":
                continue

            # Ignore fields that aren't field names
            if key[:2] in ["d.", "m.", "t."]:
                continue

            # Foreign key queries
            if key[:3] == "id.":

                parts = key.split(".")
                foreign_key = parts[1]
                foreign_key_app = parts[2]
                foreign_key_model = parts[3]

                exec_cmd += f".filter({foreign_key}=this_array[f'{foreign_key_app}.{foreign_key_model}']['{value}'])"

            # The only other case is normal fields where the heading is the field name
            else:
                exec_cmd2 = f"module = import_module('{app}.models')\nfield_type=module.{model}._meta.get_field('{key}').get_internal_type()"
                exec(exec_cmd2, globals())
                if field_type in ["CharField", "TextField"]:  # noqa: F821
                    exec_cmd += f".filter({key}='{value}')"
                else:
                    exec_cmd += f".filter({key}={value})"

        # Complete the query by getting the first match
        exec_cmd += ".first()"

        # execute dynamic Python and pass in out local data
        this_array = self.id_array
        local_array = {"this_array": this_array}
        try:
            exec(exec_cmd, globals(), local_array)
        except (KeyError, NameError) as exc:
            self.print_error_found_and_exit(exc, exec_cmd)

        # Return the instance, should be an app model instance or None
        return local_array["instance"]

    def print_error_found_and_exit(self, exc, exec_cmd):
        """This handles exceptions"""
        print("\n\nError\n")
        print(f"{exc}")
        for block in self.id_array:
            for key2, val2 in self.id_array[block].items():
                print(block, key2, val2)
        print("\nStatement was:")
        print(exec_cmd)
        print(exc)
        sys.exit()

    def accounts_user(self, app, model, data):
        """Accounts get created first (must be first file) and we
        keep a reference to them for use when processing the other files"""

        # Dictionary to store users Django id of user maps to user object
        user_dic = {}

        # Process each row to create a user
        for row in data:

            # Handle the about section and picture file not being provided
            if "about" not in row:
                row["about"] = None
            if "pic" not in row:
                row["pic"] = None

            # Get or Create user
            user = create_fake_user(
                self,
                row["system_number"],
                row["first_name"],
                row["last_name"],
                row["about"],
                row["pic"],
            )
            user_dic[row["id"]] = user

        # also get the "system" accounts
        user_dic["TBA"] = User.objects.filter(pk=TBA_PLAYER).first()
        user_dic["EVERYONE"] = User.objects.filter(pk=RBAC_EVERYONE).first()
        user_dic["mark"] = User.objects.filter(system_number="620246").first()
        user_dic["julian"] = User.objects.filter(system_number="518891").first()

        # Add the user dictionary to our id_array
        self.id_array["accounts.User"] = user_dic

    def _handle_foreign_key(self, key, row, value, app, model):
        """helper to deal with data that points to a foreign key"""
        parts = key.split(".")
        foreign_key = parts[1]
        foreign_key_app = parts[2]
        foreign_key_model = parts[3]
        try:
            field_value = self.id_array[f"{foreign_key_app}.{foreign_key_model}"][value]
        except KeyError:
            print("\n\nError\n")
            print(row)
            print(
                f"Foreign key not found: {foreign_key_app}.{foreign_key_model}: {value}"
            )
            print(
                f"Check that the file with {app}.{model} has id {value} and that it is loaded before this file.\n"
            )
            sys.exit()

        return foreign_key, field_value
