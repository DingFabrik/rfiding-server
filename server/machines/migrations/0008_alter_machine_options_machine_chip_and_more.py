# Generated by Django 5.1.1 on 2024-10-08 12:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("machines", "0007_alter_machine_options_machine_needs_qualification"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="machine",
            options={"ordering": ["pk"], "verbose_name": "Machine", "verbose_name_plural": "Machines"},
        ),
        migrations.AddField(
            model_name="machine",
            name="chip",
            field=models.CharField(choices=[("esp32", "ESP32"), ("esp8266", "ESP8266")], default="esp8266", max_length=100),
        ),
        migrations.AddField(
            model_name="machine",
            name="completed_setup",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="machine",
            name="firmware_version",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="machine",
            name="needs_qualification",
            field=models.BooleanField(default=True, help_text="If disabled, any active user can access this machine."),
        ),
    ]
