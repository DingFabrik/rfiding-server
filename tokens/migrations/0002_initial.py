# Generated by Django 5.0 on 2023-12-15 22:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("machines", "0001_initial"),
        ("tokens", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="token",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="unknowntoken",
            name="machine",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="machines.machine"
            ),
        ),
    ]
