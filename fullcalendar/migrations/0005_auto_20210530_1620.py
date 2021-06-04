# Generated by Django 2.2.20 on 2021-05-30 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('league', '0009_auto_20210504_2046'),
        ('fullcalendar', '0004_auto_20210530_1609'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameappointmentevent',
            name='divisions',
            field=models.ManyToManyField(blank=True, to='league.Division'),
        ),
        migrations.AddField(
            model_name='gameappointmentevent',
            name='private',
            field=models.BooleanField(default=False),
        ),
    ]