# Generated by Django 5.1.1 on 2024-09-16 14:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_alter_rfidinguser_language_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="rfidinguser",
            options={"verbose_name": "User", "verbose_name_plural": "Users"},
        ),
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
