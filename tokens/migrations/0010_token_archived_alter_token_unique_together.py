# Generated by Django 5.0.4 on 2024-09-05 17:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tokens", "0009_rename_note_token_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="token",
            name="archived",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name="token",
            unique_together={("serial", "archived")},
        ),
    ]
