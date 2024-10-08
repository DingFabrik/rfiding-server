# Generated by Django 5.1.1 on 2024-09-17 10:38

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0007_alter_rfidinguser_options_alter_rfidinguser_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="rfidinguser",
            name="theme",
            field=models.CharField(
                choices=[("default", "Default")], default="default", max_length=10
            ),
        ),
        migrations.AddField(
            model_name="rfidinguser",
            name="theme_mode",
            field=models.CharField(
                choices=[("light", "Light"), ("dark", "Dark"), ("auto", "Auto")],
                default="auto",
                max_length=10,
            ),
        ),
    ]
