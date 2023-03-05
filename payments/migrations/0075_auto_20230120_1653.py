# Generated by Django 3.2.15 on 2023-01-20 05:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0074_alter_abstractfinanceclassification_organisation"),
    ]

    operations = [
        migrations.RenameField(
            model_name="abstractfinanceclassification",
            old_name="category",
            new_name="gl_category",
        ),
        migrations.RenameField(
            model_name="abstractfinanceclassification",
            old_name="description",
            new_name="gl_description",
        ),
        migrations.RenameField(
            model_name="abstractfinanceclassification",
            old_name="transaction_type",
            new_name="gl_transaction_type",
        ),
        migrations.RenameField(
            model_name="financeclassificationsubcategory",
            old_name="sub_category",
            new_name="gl_sub_category",
        ),
        migrations.RenameField(
            model_name="organisationtransaction",
            old_name="category",
            new_name="gl_category",
        ),
        migrations.RenameField(
            model_name="organisationtransaction",
            old_name="sub_category",
            new_name="gl_sub_category",
        ),
        migrations.RenameField(
            model_name="organisationtransaction",
            old_name="transaction_type",
            new_name="gl_transaction_type",
        ),
        migrations.AddField(
            model_name="organisationtransaction",
            name="gl_series",
            field=models.PositiveIntegerField(default=0),
        ),
    ]