# Generated by Django 5.0 on 2023-12-16 11:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0003_alter_qualification_machine_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='qualification',
            options={'permissions': (('qualify_person', 'Can manage qualifications'),), 'verbose_name': 'Qualification', 'verbose_name_plural': 'Qualifications'},
        ),
    ]
