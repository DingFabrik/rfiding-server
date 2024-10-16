# Generated by Django 5.1.1 on 2024-10-14 09:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("machines", "0010_rename_machinetimes_machinetime"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="machine",
            options={
                "ordering": ["pk"],
                "verbose_name": "Maschine",
                "verbose_name_plural": "Maschinen",
            },
        ),
        migrations.AddField(
            model_name="machine",
            name="access_control_module",
            field=models.IntegerField(
                choices=[(0, "None"), (1, "RFID Reader")], default=0
            ),
        ),
        migrations.AddField(
            model_name="machine",
            name="access_control_module_settings",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="machine",
            name="actor_module",
            field=models.IntegerField(
                choices=[
                    (0, "None"),
                    (3, "Lock"),
                    (1, "Relay"),
                    (2, "Relay with power meter"),
                ],
                default=0,
            ),
        ),
        migrations.AddField(
            model_name="machine",
            name="actor_module_settings",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="machine",
            name="status_display_module",
            field=models.IntegerField(
                choices=[
                    (2, "Double LEDs"),
                    (1, "Onboard LED"),
                    (5, "RGB Ring LED"),
                    (3, "Red/Green LED"),
                    (0, "None"),
                    (4, "Single RGB LED"),
                ],
                default=0,
            ),
        ),
        migrations.AddField(
            model_name="machine",
            name="status_display_module_settings",
            field=models.JSONField(default=dict),
        ),
    ]
