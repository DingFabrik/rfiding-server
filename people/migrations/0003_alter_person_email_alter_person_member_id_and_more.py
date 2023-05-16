# Generated by Django 4.2.1 on 2023-05-16 11:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("machines", "0003_machine_is_active"),
        ("people", "0002_alter_person_is_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="person",
            name="email",
            field=models.CharField(blank=True, max_length=100, verbose_name="E-Mail"),
        ),
        migrations.AlterField(
            model_name="person",
            name="member_id",
            field=models.CharField(max_length=8, verbose_name="Member ID"),
        ),
        migrations.AlterField(
            model_name="person",
            name="name",
            field=models.CharField(max_length=100, verbose_name="Full Name"),
        ),
        migrations.CreateModel(
            name="Qualification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "machine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="qualified_people",
                        to="machines.machine",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="qualifications",
                        to="people.person",
                    ),
                ),
            ],
        ),
    ]
