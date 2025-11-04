from django.core.management import BaseCommand
from django.db.models import F, Value, CharField, Sum
from django.db.models.functions import Coalesce

from masterpoints.models import MPTran, Rank


class Command(BaseCommand):
    def handle(self, *args, **options):

        # # First SELECT (ba.Source = 'C', join Clubs)
        # qs_club = MPTran.objects.filter(
        #     mpbatch__source='C'
        # ).select_related(
        #     'mp_batch', 'player'
        # ).annotate(
        #     PlayerID=F('player__PlayerID'),
        #     postingmonth=F('mp_batch__postingmonth'),
        #     postingyear=F('mp_batch__postingyear'),
        #     surname=F('player__surname'),
        #     GivenNames=F('player__GivenNames'),
        #     ABFNumber=F('player__ABFNumber'),
        #     mps=F('mps'),
        #     MPBatchID=F('mp_batch__MPBatchID'),
        #     MPColour=F('MPColour'),
        #     EventDescription=F('mp_batch__eventorclub__ShortName'),
        #     EventCode=F('mp_batch__eventorclub__clubnumber')
        # ).values(
        #     'PlayerID', 'postingmonth', 'postingyear', 'surname', 'GivenNames',
        #     'ABFNumber', 'mps', 'MPBatchID', 'MPColour', 'EventDescription', 'EventCode'
        # )
        #
        # # Second SELECT (ba.Source = 'E', join Events)
        # qs_event = MPTran.objects.filter(
        #     mpbatch__source='E'
        # ).select_related(
        #     'mpbatch', 'player'
        # ).annotate(
        #     PlayerID=F('player__PlayerID'),
        #     postingmonth=F('mpbatch__postingmonth'),
        #     postingyear=F('mpbatch__postingyear'),
        #     surname=F('player__surname'),
        #     GivenNames=F('player__GivenNames'),
        #     ABFNumber=F('player__ABFNumber'),
        #     mps=F('mps'),
        #     MPBatchID=F('mpbatch__MPBatchID'),
        #     MPColour=F('MPColour'),
        #     EventDescription=F('mpbatch__eventorclub__EventName'),
        #     EventCode=F('mpbatch__eventorclub__eventcode')
        # ).values(
        #     'PlayerID', 'postingmonth', 'postingyear', 'surname', 'GivenNames',
        #     'ABFNumber', 'mps', 'MPBatchID', 'MPColour', 'EventDescription', 'EventCode'
        # )
        #
        # # Combine with union
        # view_player_trans = qs_club.union(qs_event)
        #
        # print(view_player_trans)


        player = 620246

        total_mps = MPTran.objects.filter(system_number=player).values("mp_colour").order_by("mp_colour").annotate(total=Sum("mp_amount"))
        print(total_mps)

        green = 0
        red = 0
        gold = 0

        for item in total_mps:
            if item["mp_colour"] == "G":
                green = item["total"]
            elif item["mp_colour"] == "R":
                red = item["total"]
            if item["mp_colour"] == "Y":
                gold = item["total"]

        total = green + red + gold

        rank = Rank.objects.filter(total_needed__lte=total, gold_needed__lte=gold, red_gold_needed__lte=red+gold).last()

        print(rank)