# Generated by Django 5.0.4 on 2024-08-20 16:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tokens", "0006_alter_token_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="token",
            name="serial",
            field=models.CharField(db_index=True, max_length=20),
        ),
    ]
