# Generated by Django 5.0 on 2023-12-15 23:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rfidinguser',
            name='email',
            field=models.EmailField(max_length=254, unique=True, verbose_name='E-Mail Address'),
        ),
    ]
