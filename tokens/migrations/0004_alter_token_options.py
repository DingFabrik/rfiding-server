# Generated by Django 5.0 on 2023-12-16 11:30

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tokens", "0003_alter_token_user"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="token",
            options={"verbose_name": "Token", "verbose_name_plural": "Tokens"},
        ),
    ]
