# Generated by Django 3.2.7 on 2021-09-09 20:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20210909_2045'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='adressemail',
            name='defaut',
        ),
    ]