# Generated by Django 5.0.4 on 2024-08-20 16:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("machines", "0005_machine_control_parameter_machine_min_power_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="machine",
            name="mac_address",
            field=models.CharField(db_index=True, max_length=17),
        ),
    ]
