# Generated by Django 3.2.4 on 2021-09-26 09:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organisations", "0034_organisationfrontpage"),
        ("payments", "0059_auto_20210714_1446"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organisationtransaction",
            name="organisation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="primary_org",
                to="organisations.organisation",
            ),
        ),
    ]
