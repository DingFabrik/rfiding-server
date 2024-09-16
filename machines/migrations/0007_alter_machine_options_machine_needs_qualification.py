# Generated by Django 5.1.1 on 2024-09-16 14:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("machines", "0006_alter_machine_mac_address"),
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
            name="needs_qualification",
            field=models.BooleanField(default=True),
        ),
    ]
