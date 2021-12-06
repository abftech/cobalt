""" Script to create cobalt test data """
from django.core.exceptions import SuspiciousOperation

from cobalt.settings import (
    RBAC_EVERYONE,
    TIME_ZONE,
    DUMMY_DATA_COUNT,
    TBA_PLAYER,
    COBALT_HOSTNAME,
)
from accounts.models import User
from django.core.management.base import BaseCommand
from accounts.management.commands.accounts_core import create_fake_user
from forums.models import Post, Comment1, Comment2, LikePost, LikeComment1, LikeComment2
import random
from essential_generators import DocumentGenerator
import datetime
import pytz
from django.utils.timezone import make_aware, now
import glob
import sys
from inspect import currentframe, getframeinfo
from importlib import import_module

TZ = pytz.timezone(TIME_ZONE)
DATA_DIR = "tests/test_data"


class Command(BaseCommand):
    def __init__(self):
        super().__init__()
        self.gen = DocumentGenerator()
        self.id_array = {}

    def add_comments(self, post, user_list):
        """add comments to a forum post"""

        liker_list = list(set(user_list) - set([post.author]))
        sample_size = random.randrange(int(len(liker_list) * 0.8))
        for liker in random.sample(liker_list, sample_size):
            like = LikePost(post=post, liker=liker)
            like.save()
        for c1_counter in range(random.randrange(10)):
            text = self.random_paragraphs()
            c1 = Comment1(post=post, text=text, author=random.choice(user_list))
            c1.save()
            liker_list = list(set(user_list) - set([c1.author]))
            sample_size = random.randrange(int(len(liker_list) * 0.8))
            for liker in random.sample(liker_list, sample_size):
                like = LikeComment1(comment1=c1, liker=liker)
                like.save()
            post.comment_count += 1
            post.save()
            for c2_counter in range(random.randrange(10)):
                text = self.random_paragraphs()
                c2 = Comment2(
                    post=post, comment1=c1, text=text, author=random.choice(user_list)
                )
                c2.save()
                post.comment_count += 1
                post.save()
                c1.comment1_count += 1
                c1.save()
                liker_list = list(set(user_list) - set([c2.author]))
                sample_size = random.randrange(int(len(liker_list) * 0.8))
                for liker in random.sample(liker_list, sample_size):
                    like = LikeComment2(comment2=c2, liker=liker)
                    like.save()

    def random_paragraphs(self):
        """generate a random paragraph"""
        text = self.gen.paragraph()
        for counter in range(random.randrange(10)):
            text += "\n\n" + self.gen.paragraph()
        return text

    def random_sentence(self):
        """generate a random sentence"""
        return self.gen.sentence()

    def random_paragraphs_with_stuff(self):
        """generate a more realistic rich test paragraph with headings and pics"""

        sizes = [
            ("400x500", "400px"),
            ("400x300", "400px"),
            ("700x300", "700px"),
            ("900x500", "900px"),
            ("200x200", "200px"),
            ("800x200", "800px"),
            ("500x400", "500px"),
        ]

        text = self.gen.paragraph()
        for counter in range(random.randrange(10)):
            type = random.randrange(8)
            if type == 5:  # no good reason
                text += "<h2>%s</h2>" % self.gen.sentence()
            elif type == 7:
                index = random.randrange(len(sizes))
                text += (
                    "<p><img src='https://source.unsplash.com/random/%s' style='width: %s;'><br></p>"
                    % (sizes[index][0], sizes[index][1])
                )
            else:
                text += "<p>%s</p>" % self.gen.paragraph()
        return text

    def parse_csv(self, file):
        """try to sort out the mess Excel makes of CSV files.
        Requires csv files to have the app and model in the first row and
        the fieldnames in the second row."""

        f = open(file, encoding="utf-8")

        all_lines = f.readlines()

        lines = []

        for line in all_lines:
            # skip empty rows
            if (
                line.find("#") == 0
                or line.strip() == ""
                or line.replace(",", "").strip() == ""
            ):
                continue
            lines.append(line)

        data = []

        try:
            app, model = lines[0].split(",")[:2]
        except ValueError:
            print("\n\nError\n")
            print("Didn't find App, Model on first line of file")
            print("File is: %s" % file)
            print("Line is: %s\n" % lines[0])
            sys.exit()

        try:
            allow_dupes = lines[0].split(",")[3] == "duplicates"
        except (ValueError, IndexError):
            allow_dupes = False

        headers = lines[1]
        header_list = [header.strip() for header in headers.split(",")]

        # loop through records
        for line in lines[2:]:

            # split to parts
            columns = line.split(",")

            # loop through columns
            row = {}
            for i in range(len(header_list)):
                try:
                    if columns[i].strip() != "":
                        row[header_list[i]] = columns[i].strip()
                except IndexError:
                    row[header_list[i]] = None
            data.append(row)

        return app.strip(), model.strip(), data, allow_dupes

    def process_csv(self, csv):
        """do the work on the csv data"""

        app, model, data, allow_dupes = self.parse_csv(csv)
        print(f"App Model is: {app}.{model}\n")

        # special cases
        if app == "accounts" and model == "User":
            self.accounts_user(app, model, data)
            return

        dic = {}
        this_array = None
        for row in data:
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

            # that was hard, now check it
            if instance and not allow_dupes:
                print("already present: %s" % instance)
            else:
                exec_cmd = (
                    "module = import_module('%s.models')\ninstance = module.%s()"
                    % (app, model)
                )
                local_array = {}
                exec(exec_cmd, globals(), local_array)
                instance = local_array["instance"]

                if not instance:
                    print("\n\nError\n")
                    print(f"Failed to create instance of {app}.{model}")
                    print(f"Processing file: {csv}\n")
                    frameinfo = getframeinfo(currentframe())
                    print(
                        "Error somewhere above: ",
                        frameinfo.filename,
                        frameinfo.lineno,
                        "\n",
                    )
                    sys.exit()
                for key, value in row.items():
                    try:
                        value = value.replace("^", ",")
                    except AttributeError:
                        pass
                    if key != "id" and key[:2] != "t.":
                        if len(key) > 3 and key[:3] == "id.":  # foreign key
                            parts = key.split(".")
                            fkey = parts[1]
                            fapp = parts[2]
                            fmodel = parts[3]
                            try:
                                val = self.id_array[f"{fapp}.{fmodel}"][value]
                            except KeyError:
                                print("\n\nError\n")
                                print(row)
                                print(
                                    f"Foreign key not found: {fapp}.{fmodel}: {value}"
                                )
                                print(
                                    f"Check that the file with {app}.{model} has id {value} and that it is loaded before this file.\n"
                                )
                                sys.exit()
                            setattr(instance, fkey, val)
                        else:
                            setattr(instance, key, value)
                    if key[:2] == "t.":
                        field = key[2:]
                        adjusted_date = now() - datetime.timedelta(days=int(value))
                        datetime_local = adjusted_date.astimezone(TZ)
                        setattr(instance, field, datetime_local)
                    if key[:2] == "d.":
                        field = key[2:]
                        #                            dy, mt, yr = value.split("/")
                        val_str = "%s" % value
                        yr = val_str[:4]
                        mt = val_str[4:6]
                        dy = val_str[6:8]
                        this_date = make_aware(
                            datetime.datetime(int(yr), int(mt), int(dy), 0, 0),
                            TZ,
                        )
                        setattr(instance, field, this_date)
                    if key[:2] == "m.":
                        field = key[2:]
                        dt = datetime.datetime.strptime(value, "%H:%M").time()
                        setattr(instance, field, dt)

                instance.save()
                print("Added: %s" % instance)
            # add to dic if we have an id field
            if "id" in row.keys():
                dic[row["id"]] = instance

        self.id_array[f"{app}.{model}"] = dic

    def accounts_user(self, app, model, data):
        dic = {}
        for row in data:
            if "about" not in row:
                row["about"] = None
            if "pic" not in row:
                row["pic"] = None

            user = create_fake_user(
                self,
                row["system_number"],
                row["first_name"],
                row["last_name"],
                row["about"],
                row["pic"],
            )
            dic[row["id"]] = user
            dic["TBA"] = User.objects.filter(pk=TBA_PLAYER).first()
            dic["EVERYONE"] = User.objects.filter(pk=RBAC_EVERYONE).first()
            dic["mark"] = User.objects.filter(system_number="620246").first()
            dic["julian"] = User.objects.filter(system_number="518891").first()
        self.id_array["accounts.User"] = dic

    def handle(self, *args, **options):
        if COBALT_HOSTNAME in ["myabf.com.au", "www.myabf.com.au"]:
            raise SuspiciousOperation(
                "Not for use in production. This cannot be used in a production system."
            )

        print("Running add_rbac_test_data")

        try:
            for fname in sorted(glob.glob(DATA_DIR + "/*.csv")):
                print("\n#########################################################")
                print("Processing: %s" % fname)
                self.process_csv(fname)

            # create dummy Posts
            print("\nCreating dummy forum posts")
            print("Running", end="", flush=True)
            for count, _ in enumerate(range(DUMMY_DATA_COUNT * 10), start=1):

                user_list = list(self.id_array["accounts.User"].values())
                user_list.remove(self.id_array["accounts.User"]["EVERYONE"])

                post = Post(
                    forum=random.choice(list(self.id_array["forums.Forum"].values())),
                    title=self.random_sentence(),
                    text=self.random_paragraphs_with_stuff(),
                    author=random.choice(user_list),
                )
                post.save()
                print(".", end="", flush=True)
                self.add_comments(post, user_list)
                if count % 100 == 0:
                    print(count, flush=True)
            print("\n")

        except KeyboardInterrupt:
            print("\n\nTest data loading interrupted by user\n")
            sys.exit(0)
