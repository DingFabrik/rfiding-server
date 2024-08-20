# Generated by Django 4.2.10 on 2024-04-20 21:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('machines', '0004_alter_machine_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='machine',
            name='control_parameter',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='machine',
            name='min_power',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='machine',
            name='runtimer',
            field=models.IntegerField(default=0),
        ),
        migrations.DeleteModel(
            name='MachineConfig',
        ),
    ]
