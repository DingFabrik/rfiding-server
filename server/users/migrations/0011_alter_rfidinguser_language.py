# Generated by Django 5.1.1 on 2024-10-14 09:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_alter_rfidinguser_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rfidinguser",
            name="language",
            field=models.CharField(
                choices=[("de", "Deutsch"), ("en", "English")],
                default="en",
                max_length=10,
                verbose_name="Langauge",
            ),
        ),
    ]
