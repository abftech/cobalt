# Generated by Django 3.2.15 on 2023-03-02 03:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0059_delete_systemcard"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemCard",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("card_name", models.CharField(max_length=100)),
                ("player1", models.CharField(max_length=100)),
                ("player2", models.CharField(max_length=100)),
                (
                    "basic_system",
                    models.CharField(default="Standard American", max_length=50),
                ),
                (
                    "system_classification",
                    models.CharField(
                        choices=[
                            ("G", "Green"),
                            ("B", "Blue"),
                            ("Y", "Yellow"),
                            ("R", "Red"),
                        ],
                        default="G",
                        max_length=1,
                    ),
                ),
                ("brown_sticker", models.BooleanField(default=False)),
                ("brown_sticker_why", models.CharField(blank=True, max_length=50)),
                ("canape", models.BooleanField(default=False)),
                ("opening_1c", models.CharField(max_length=20)),
                ("opening_1d", models.CharField(max_length=20)),
                ("opening_1h", models.CharField(max_length=20)),
                ("opening_1s", models.CharField(max_length=20)),
                ("opening_1nt", models.CharField(max_length=20)),
                ("summary_bidding", models.CharField(max_length=100)),
                ("summary_carding", models.CharField(max_length=100)),
                ("pre_alerts", models.TextField(blank=True)),
                ("nt1_response_2c", models.CharField(blank=True, max_length=20)),
                ("nt1_response_2d", models.CharField(blank=True, max_length=20)),
                ("nt1_response_2h", models.CharField(blank=True, max_length=20)),
                ("nt1_response_2s", models.CharField(blank=True, max_length=20)),
                ("nt1_response_2nt", models.CharField(blank=True, max_length=20)),
                ("opening_2c", models.CharField(max_length=20)),
                ("opening_2d", models.CharField(max_length=20)),
                ("opening_2h", models.CharField(max_length=20)),
                ("opening_2s", models.CharField(max_length=20)),
                ("opening_2nt", models.CharField(max_length=20)),
                ("opening_3nt", models.CharField(blank=True, max_length=20)),
                ("opening_other", models.CharField(blank=True, max_length=20)),
                ("competitive_doubles", models.CharField(blank=True, max_length=100)),
                (
                    "competitive_lead_directing_doubles",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "competitive_jump_overcalls",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "competitive_unusual_nt",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "competitive_1nt_overcall_immediate",
                    models.CharField(blank=True, max_length=20),
                ),
                (
                    "competitive_1nt_overcall_reopening",
                    models.CharField(blank=True, max_length=20),
                ),
                (
                    "competitive_negative_double_through",
                    models.CharField(blank=True, max_length=20),
                ),
                (
                    "competitive_responsive_double_through",
                    models.CharField(blank=True, max_length=20),
                ),
                (
                    "competitive_immediate_cue_bid_minor",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "competitive_immediate_cue_bid_major",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "competitive_weak_2_defense",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "competitive_weak_3_defense",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "competitive_transfer_defense",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "competitive_nt_defense",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "basic_response_jump_raise_minor",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "basic_response_jump_raise_major",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "basic_response_jump_shift_minor",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "basic_response_jump_shift_major",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "basic_response_to_2c_opening",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "basic_response_to_strong_2_opening",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "basic_response_to_2nt_opening",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "play_suit_lead_sequence",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "play_suit_lead_4_or_more",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "play_suit_lead_4_small",
                    models.CharField(blank=True, max_length=100),
                ),
                ("play_suit_lead_3", models.CharField(blank=True, max_length=100)),
                (
                    "play_suit_lead_in_partners_suit",
                    models.CharField(blank=True, max_length=100),
                ),
                ("play_suit_discards", models.CharField(blank=True, max_length=100)),
                ("play_suit_count", models.CharField(blank=True, max_length=100)),
                (
                    "play_suit_signal_on_partner_lead",
                    models.CharField(blank=True, max_length=100),
                ),
                ("play_nt_lead_sequence", models.CharField(blank=True, max_length=100)),
                (
                    "play_nt_lead_4_or_more",
                    models.CharField(blank=True, max_length=100),
                ),
                ("play_nt_lead_4_small", models.CharField(blank=True, max_length=100)),
                ("play_nt_lead_3", models.CharField(blank=True, max_length=100)),
                (
                    "play_nt_lead_in_partners_suit",
                    models.CharField(blank=True, max_length=100),
                ),
                ("play_nt_discards", models.CharField(blank=True, max_length=100)),
                ("play_nt_count", models.CharField(blank=True, max_length=100)),
                (
                    "play_nt_signal_on_partner_lead",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "play_signal_declarer_lead",
                    models.CharField(blank=True, max_length=100),
                ),
                ("play_notes", models.CharField(blank=True, max_length=100)),
                ("slam_conventions", models.CharField(blank=True, max_length=200)),
                ("other_conventions", models.CharField(blank=True, max_length=200)),
                ("response_1c_1d", models.CharField(blank=True, max_length=20)),
                ("response_1c_1h", models.CharField(blank=True, max_length=20)),
                ("response_1c_1s", models.CharField(blank=True, max_length=20)),
                ("response_1c_1n", models.CharField(blank=True, max_length=20)),
                ("response_1c_2c", models.CharField(blank=True, max_length=20)),
                ("response_1c_2d", models.CharField(blank=True, max_length=20)),
                ("response_1c_2h", models.CharField(blank=True, max_length=20)),
                ("response_1c_2s", models.CharField(blank=True, max_length=20)),
                ("response_1c_2n", models.CharField(blank=True, max_length=20)),
                ("response_1c_3c", models.CharField(blank=True, max_length=20)),
                ("response_1c_3d", models.CharField(blank=True, max_length=20)),
                ("response_1c_3h", models.CharField(blank=True, max_length=20)),
                ("response_1c_3s", models.CharField(blank=True, max_length=20)),
                ("response_1c_3n", models.CharField(blank=True, max_length=20)),
                ("response_1c_other", models.CharField(blank=True, max_length=100)),
                ("response_1d_1h", models.CharField(blank=True, max_length=20)),
                ("response_1d_1s", models.CharField(blank=True, max_length=20)),
                ("response_1d_1n", models.CharField(blank=True, max_length=20)),
                ("response_1d_2c", models.CharField(blank=True, max_length=20)),
                ("response_1d_2d", models.CharField(blank=True, max_length=20)),
                ("response_1d_2h", models.CharField(blank=True, max_length=20)),
                ("response_1d_2s", models.CharField(blank=True, max_length=20)),
                ("response_1d_2n", models.CharField(blank=True, max_length=20)),
                ("response_1d_3c", models.CharField(blank=True, max_length=20)),
                ("response_1d_3d", models.CharField(blank=True, max_length=20)),
                ("response_1d_3h", models.CharField(blank=True, max_length=20)),
                ("response_1d_3s", models.CharField(blank=True, max_length=20)),
                ("response_1d_3n", models.CharField(blank=True, max_length=20)),
                ("response_1d_other", models.CharField(blank=True, max_length=100)),
                ("response_1h_1s", models.CharField(blank=True, max_length=20)),
                ("response_1h_1n", models.CharField(blank=True, max_length=20)),
                ("response_1h_2c", models.CharField(blank=True, max_length=20)),
                ("response_1h_2d", models.CharField(blank=True, max_length=20)),
                ("response_1h_2h", models.CharField(blank=True, max_length=20)),
                ("response_1h_2s", models.CharField(blank=True, max_length=20)),
                ("response_1h_2n", models.CharField(blank=True, max_length=20)),
                ("response_1h_3c", models.CharField(blank=True, max_length=20)),
                ("response_1h_3d", models.CharField(blank=True, max_length=20)),
                ("response_1h_3h", models.CharField(blank=True, max_length=20)),
                ("response_1h_3s", models.CharField(blank=True, max_length=20)),
                ("response_1h_3n", models.CharField(blank=True, max_length=20)),
                ("response_1h_other", models.CharField(blank=True, max_length=100)),
                ("response_1s_1n", models.CharField(blank=True, max_length=20)),
                ("response_1s_2c", models.CharField(blank=True, max_length=20)),
                ("response_1s_2d", models.CharField(blank=True, max_length=20)),
                ("response_1s_2h", models.CharField(blank=True, max_length=20)),
                ("response_1s_2s", models.CharField(blank=True, max_length=20)),
                ("response_1s_2n", models.CharField(blank=True, max_length=20)),
                ("response_1s_3c", models.CharField(blank=True, max_length=20)),
                ("response_1s_3d", models.CharField(blank=True, max_length=20)),
                ("response_1s_3h", models.CharField(blank=True, max_length=20)),
                ("response_1s_3s", models.CharField(blank=True, max_length=20)),
                ("response_1s_3n", models.CharField(blank=True, max_length=20)),
                ("response_1s_other", models.CharField(blank=True, max_length=100)),
                ("response_1n_3c", models.CharField(blank=True, max_length=20)),
                ("response_1n_3d", models.CharField(blank=True, max_length=20)),
                ("response_1n_3h", models.CharField(blank=True, max_length=20)),
                ("response_1n_3s", models.CharField(blank=True, max_length=20)),
                ("response_1n_3n", models.CharField(blank=True, max_length=20)),
                ("response_1n_other", models.CharField(blank=True, max_length=100)),
                ("response_2c_2d", models.CharField(blank=True, max_length=20)),
                ("response_2c_2h", models.CharField(blank=True, max_length=20)),
                ("response_2c_2s", models.CharField(blank=True, max_length=20)),
                ("response_2c_2n", models.CharField(blank=True, max_length=20)),
                ("response_2c_3c", models.CharField(blank=True, max_length=20)),
                ("response_2c_3d", models.CharField(blank=True, max_length=20)),
                ("response_2c_3h", models.CharField(blank=True, max_length=20)),
                ("response_2c_3s", models.CharField(blank=True, max_length=20)),
                ("response_2c_3n", models.CharField(blank=True, max_length=20)),
                ("response_2c_other", models.CharField(blank=True, max_length=100)),
                ("response_2d_2h", models.CharField(blank=True, max_length=20)),
                ("response_2d_2s", models.CharField(blank=True, max_length=20)),
                ("response_2d_2n", models.CharField(blank=True, max_length=20)),
                ("response_2d_3c", models.CharField(blank=True, max_length=20)),
                ("response_2d_3d", models.CharField(blank=True, max_length=20)),
                ("response_2d_3h", models.CharField(blank=True, max_length=20)),
                ("response_2d_3s", models.CharField(blank=True, max_length=20)),
                ("response_2d_3n", models.CharField(blank=True, max_length=20)),
                ("response_2d_other", models.CharField(blank=True, max_length=100)),
                ("response_2h_2s", models.CharField(blank=True, max_length=20)),
                ("response_2h_2n", models.CharField(blank=True, max_length=20)),
                ("response_2h_3c", models.CharField(blank=True, max_length=20)),
                ("response_2h_3d", models.CharField(blank=True, max_length=20)),
                ("response_2h_3h", models.CharField(blank=True, max_length=20)),
                ("response_2h_3s", models.CharField(blank=True, max_length=20)),
                ("response_2h_3n", models.CharField(blank=True, max_length=20)),
                ("response_2h_other", models.CharField(blank=True, max_length=100)),
                ("response_2s_2n", models.CharField(blank=True, max_length=20)),
                ("response_2s_3c", models.CharField(blank=True, max_length=20)),
                ("response_2s_3d", models.CharField(blank=True, max_length=20)),
                ("response_2s_3h", models.CharField(blank=True, max_length=20)),
                ("response_2s_3s", models.CharField(blank=True, max_length=20)),
                ("response_2s_3n", models.CharField(blank=True, max_length=20)),
                ("response_2s_other", models.CharField(blank=True, max_length=100)),
                ("response_2n_3c", models.CharField(blank=True, max_length=20)),
                ("response_2n_3d", models.CharField(blank=True, max_length=20)),
                ("response_2n_3h", models.CharField(blank=True, max_length=20)),
                ("response_2n_3s", models.CharField(blank=True, max_length=20)),
                ("response_2n_3n", models.CharField(blank=True, max_length=20)),
                ("response_2n_other", models.CharField(blank=True, max_length=100)),
                ("response_notes", models.CharField(blank=True, max_length=200)),
                ("other_notes", models.CharField(blank=True, max_length=400)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
