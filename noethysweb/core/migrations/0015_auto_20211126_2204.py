# Generated by Django 3.2.9 on 2021-11-26 22:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_portailrenseignement_rattachement'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='portailrenseignement',
            name='objet',
        ),
        migrations.RemoveField(
            model_name='portailrenseignement',
            name='rattachement',
        ),
    ]
