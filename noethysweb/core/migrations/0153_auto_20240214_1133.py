# Generated by Django 3.2.23 on 2024-02-14 11:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0152_merge_20240214_1004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activite',
            name='pay',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='URL complet de paiement'),
        ),
        migrations.AlterField(
            model_name='activite',
            name='pay_org',
            field=models.BooleanField(default=True, verbose_name='Activation paiement par lien externe'),
        ),
    ]