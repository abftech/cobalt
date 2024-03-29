# Generated by Django 3.2.15 on 2023-06-13 21:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0077_auto_20230608_0953"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="financeclassificationcategory",
            name="abstractfinanceclassification_ptr",
        ),
        migrations.RemoveField(
            model_name="financeclassificationsubcategory",
            name="abstractfinanceclassification_ptr",
        ),
        migrations.RemoveField(
            model_name="organisationtransaction",
            name="gl_category",
        ),
        migrations.RemoveField(
            model_name="organisationtransaction",
            name="gl_series",
        ),
        migrations.RemoveField(
            model_name="organisationtransaction",
            name="gl_sub_category",
        ),
        migrations.RemoveField(
            model_name="organisationtransaction",
            name="gl_transaction_type",
        ),
        migrations.DeleteModel(
            name="AbstractFinanceClassification",
        ),
        migrations.DeleteModel(
            name="FinanceClassificationCategory",
        ),
        migrations.DeleteModel(
            name="FinanceClassificationSubCategory",
        ),
    ]
