# Generated by Django 5.0.4 on 2024-09-05 17:35

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tokens", "0008_token_note"),
    ]

    operations = [
        migrations.RenameField(
            model_name="token",
            old_name="note",
            new_name="notes",
        ),
    ]
