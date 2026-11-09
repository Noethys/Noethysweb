from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0219_adressemail_moteur_microsoft365"),
    ]

    operations = [
        migrations.AddField(
            model_name="pesmodele",
            name="detail_deductions",
            field=models.BooleanField(default=False, help_text="Cochez cette case pour faire apparaître les prestations à leur montant initial, suivies des aides et déductions appliquées sous forme de lignes négatives. Sinon, seul le montant net de chaque prestation est exporté.", verbose_name="Détailler les aides et déductions"),
        ),
    ]
