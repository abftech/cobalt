# Generated by Django 3.2.4 on 2021-06-28 05:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("support", "0004_alter_incident_reported_by_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="incident",
            name="severity",
            field=models.CharField(
                choices=[
                    ("Low", "Low"),
                    ("Medium", "Medium"),
                    ("High", "High"),
                    ("Critical", "Critical"),
                ],
                default="Medium",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="incident",
            name="status",
            field=models.CharField(
                choices=[
                    ("Unassigned", "Unassigned"),
                    ("In Progress", "In Progress"),
                    ("Pending User Feedback", "Awaiting User Feedback"),
                    ("Closed", "Closed"),
                ],
                default="Unassigned",
                max_length=30,
            ),
        ),
    ]
