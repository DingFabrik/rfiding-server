# Generated by Django 5.1.1 on 2024-10-08 12:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("machines", "0008_alter_machine_options_machine_chip_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="machine",
            name="chip",
            field=models.CharField(choices=[("esp32", "ESP32"), ("esp8266", "ESP8266")], default="esp32", max_length=100),
        ),
        migrations.AlterField(
            model_name="machine",
            name="completed_setup",
            field=models.BooleanField(default=False),
        ),
    ]
