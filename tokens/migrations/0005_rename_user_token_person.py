# Generated by Django 5.0 on 2023-12-16 11:33

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tokens", "0004_alter_token_options"),
    ]

    operations = [
        migrations.RenameField(
            model_name="token",
            old_name="user",
            new_name="person",
        ),
    ]
