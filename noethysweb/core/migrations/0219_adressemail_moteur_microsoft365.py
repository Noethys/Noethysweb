from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0218_statistiques_locations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="adressemail",
            name="moteur",
            field=models.CharField(choices=[("smtp", "SMTP"), ("microsoft365", "Microsoft 365 (OAuth)"), ("mailjet", "Mailjet"), ("brevo", "Brevo"), ("console", "Console")], help_text="Sélectionnez un moteur d'expédition.", max_length=200, verbose_name="Moteur"),
        ),
    ]
