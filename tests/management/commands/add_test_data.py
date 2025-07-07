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
from accounts.management.commands.accounts_core import get_or_create_fake_user
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


def _handle_foreign_key(key, id_array, value, app, model, row):
    """helper to deal with data that points to a foreign key"""

    parts = key.split(".")
    foreign_key = parts[1]
    print(foreign_key)
    foreign_key_app = parts[2]
    foreign_key_model = parts[3]
    try:
        val = id_array[f"{foreign_key_app}.{foreign_key_model}"][value]
    except KeyError:
        print("\n\nError\n")
        print(row)
        print(f"Foreign key not found: {foreign_key_app}.{foreign_key_model}: {value}")
        print(
            f"Check that the file with {app}.{model} has id '{value}' and that it is loaded before this file.\n"
        )
        sys.exit()

    return val


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


def _instance_creation_print_error_and_exit(app, model, csv):
    print("\n\nError\n")
    print(f"Failed to create instance of {app}.{model}")
    print(f"Processing file: {csv}\n")
    frame_info = getframeinfo(currentframe())
    print(
        "Error somewhere above: ",
        frame_info.filename,
        frame_info.lineno,
        "\n",
    )
    sys.exit()


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

        dic = {}
        this_array = None
        for row in data:
            dic = self.process_csv_row(
                row, app, model, allow_dupes, this_array, csv, dic
            )

        # Update id_array as these objects may be referenced later,
        # e.g. if we create an event, that will be needed later to add an EventEntry
        self.id_array[f"{app}.{model}"] = dic

    def process_csv_row(self, row, app, model, allow_dupes, this_array, csv, dic):
        """handles processing a single row of data from the CSV"""

        print(row)
        # see if already present
        exec_cmd = (
            "module = import_module('%s.models')\ninstance = module.%s.objects"
            % (app, model)
        )

        for key, value in row.items():
            if value and key != "id" and key[:2] != "d." and key[:2] != "m.":
                if key[:3] == "id.":  # foreign key

                    parts = key.split(".")

                    fkey = parts[1]
                    fapp = parts[2]
                    fmodel = parts[3]
                    this_array = self.id_array
                    exec_cmd += (
                        f".filter({fkey}=this_array[f'{fapp}.{fmodel}']['{value}'])"
                    )
                elif key[:2] != "t.":  # exclude time
                    exec_cmd2 = f"module = import_module(f'{app}.models')\nfield_type=module.{model}._meta.get_field('{key}').get_internal_type()"
                    exec(exec_cmd2, globals())
                    if field_type in ["CharField", "TextField"]:  # noqa: F821
                        exec_cmd += f".filter({key}='{value}')"
                    else:
                        exec_cmd += f".filter({key}={value})"
        exec_cmd += ".first()"

        local_array = {"this_array": this_array}
        try:
            exec(exec_cmd, globals(), local_array)
        except (KeyError, NameError) as exc:
            print("\n\nError\n")
            print(str(exc))
            for block in self.id_array:
                for key2, val2 in self.id_array[block].items():
                    print(block, key2, val2)
            print("\nStatement was:")
            print(exec_cmd)
            print(exc)
            sys.exit()
        instance = local_array["instance"]
        print(instance)

        return dic

    def add_instance_to_db(self, app, model, csv, row):
        """This function creates an entry in the database and handles the field level logic
        to set the values
        """

        # Get an instance of the db model asked for
        instance = _get_instance_of_app_model(app, model)

        # handle not found
        if not instance:
            _instance_creation_print_error_and_exit(app, model, csv)

        # Go through the fields
        for key, value in row.items():

            # Don't know what this code is doing - might be an Excel problem
            with contextlib.suppress(AttributeError):
                value = value.replace("^", ",")

            # If the key is id then this a pointer to something that already exists,
            # so no need to do anything
            if key == "id":
                continue

            # Foreign keys start with "id."
            if key[:3] == "id.":
                # This function will sys.exit if there are problems
                foreign_key = _handle_foreign_key(
                    key, self.id_array, value, app, model, row
                )
                print(foreign_key)
                setattr(instance, foreign_key, value)
            else:
                setattr(instance, key, value)

            # first 2 characters can be an identifier specifying the type of field
            # t. = datetime
            # d. = date
            # m. = time

            field_type = key[:2]

            if field_type == "d.":
                field = key[2:]
                #                            dy, mt, yr = value.split("/")
                val_str = f"{value}"
                yr = val_str[:4]
                mt = val_str[4:6]
                dy = val_str[6:8]
                print(yr, mt, dy)
                this_date = make_aware(
                    datetime.datetime(int(yr), int(mt), int(dy), 0, 0),
                    TZ,
                )
                setattr(instance, field, this_date)
            elif field_type == "m.":
                field = key[2:]
                dt = datetime.datetime.strptime(value, "%H:%M").time()
                setattr(instance, field, dt)

            elif field_type == "t.":
                field = key[2:]
                adjusted_date = now() - datetime.timedelta(days=int(value))
                datetime_local = adjusted_date.astimezone(TZ)
                setattr(instance, field, datetime_local)
        instance.save()
        print(f"Added: {instance}")

        return instance

    def get_instance_from_db(self, row, app, model, this_array):
        """see if this data is already present"""

        # build up a string of Python commands to execute
        exec_cmd = (
            "module = import_module('%s.models')\ninstance = module.%s.objects"
            % (app, model)
        )

        for key, value in row.items():

            if value and key != "id" and key[:2] != "d." and key[:2] != "m.":
                if key[:3] == "id.":  # foreign key

                    parts = key.split(".")

                    fkey = parts[1]
                    fapp = parts[2]
                    fmodel = parts[3]
                    this_array = self.id_array
                    exec_cmd += (
                        f".filter({fkey}=this_array[f'{fapp}.{fmodel}']['{value}'])"
                    )
                elif key[:2] != "t.":  # exclude time
                    exec_cmd2 = f"module = import_module('{app}.models')\nfield_type=module.{model}._meta.get_field('{key}').get_internal_type()"
                    exec(exec_cmd2, globals())
                    if field_type in ["CharField", "TextField"]:  # noqa: F821
                        exec_cmd += f".filter({key}='{value}')"
                    else:
                        exec_cmd += f".filter({key}={value})"
        exec_cmd += ".first()"

        local_array = {"this_array": this_array}
        try:
            exec(exec_cmd, globals(), local_array)
        except (KeyError, NameError) as exc:
            self.print_error_found_and_exit(exc, exec_cmd)
        return local_array["instance"]

    def print_error_found_and_exit(self, exc, exec_cmd):
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
            user = get_or_create_fake_user(
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
