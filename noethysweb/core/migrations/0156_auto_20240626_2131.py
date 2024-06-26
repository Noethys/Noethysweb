# Generated by Django 3.2.21 on 2024-06-26 21:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0155_auto_20240611_1858'),
    ]

    operations = [
        migrations.AddField(
            model_name='consommation',
            name='options',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Options'),
        ),
        migrations.AlterField(
            model_name='tarif',
            name='methode',
            field=models.CharField(choices=[('montant_unique', 'Montant unique'), ('qf', 'En fonction du quotient familial'), ('horaire_montant_unique', "Montant unique en fonction d'une tranche horaire"), ('horaire_qf', "En fonction d'une tranche horaire et du quotient familial"), ('duree_montant_unique', "Montant unique en fonction d'une durée"), ('duree_qf', "En fonction d'une durée et du quotient familial"), ('montant_unique_date', 'Montant unique en fonction de la date'), ('qf_date', 'En fonction de la date et du quotient familial'), ('choix', "Tarif au choix (Sélectionné par l'utilisateur)"), ('montant_evenement', "Montant de l'évènement"), ('montant_unique_nbre_ind', "Montant unique en fonction du nombre d'individus de la famille présents"), ('qf_nbre_ind', "En fonction du quotient familial et du nombre d'individus de la famille présents"), ('horaire_montant_unique_nbre_ind', "Montant unique en fonction du nombre d'individus de la famille présents et de la tranche horaire"), ('montant_unique_nbre_ind_degr', "Montant dégressif en fonction du nombre d'individus de la famille présents"), ('qf_nbre_ind_degr', "Montant dégressif en fonction du quotient familial et du nombre d'individus de la famille présents"), ('horaire_montant_unique_nbre_ind_degr', "Montant dégressif en fonction du nombre d'individus de la famille présents et de la tranche horaire"), ('duree_coeff_montant_unique', "Montant au prorata d'une durée"), ('duree_coeff_qf', "Montant au prorata d'une durée et selon le quotient familial"), ('taux_montant_unique', "Par taux d'effort"), ('taux_qf', "Par taux d'effort et par tranches de QF"), ('taux_date', "Par taux d'effort et par date"), ('duree_taux_montant_unique', "Par taux d'effort et en fonction d'une durée"), ('duree_taux_qf', "Par taux d'effort et par tranches de QF en fonction d'une durée")], default='montant_unique', max_length=200, verbose_name='Méthode'),
        ),
        migrations.AlterField(
            model_name='tarifligne',
            name='code',
            field=models.CharField(blank=True, choices=[('montant_unique', 'Montant unique'), ('qf', 'En fonction du quotient familial'), ('horaire_montant_unique', "Montant unique en fonction d'une tranche horaire"), ('horaire_qf', "En fonction d'une tranche horaire et du quotient familial"), ('duree_montant_unique', "Montant unique en fonction d'une durée"), ('duree_qf', "En fonction d'une durée et du quotient familial"), ('montant_unique_date', 'Montant unique en fonction de la date'), ('qf_date', 'En fonction de la date et du quotient familial'), ('choix', "Tarif au choix (Sélectionné par l'utilisateur)"), ('montant_evenement', "Montant de l'évènement"), ('montant_unique_nbre_ind', "Montant unique en fonction du nombre d'individus de la famille présents"), ('qf_nbre_ind', "En fonction du quotient familial et du nombre d'individus de la famille présents"), ('horaire_montant_unique_nbre_ind', "Montant unique en fonction du nombre d'individus de la famille présents et de la tranche horaire"), ('montant_unique_nbre_ind_degr', "Montant dégressif en fonction du nombre d'individus de la famille présents"), ('qf_nbre_ind_degr', "Montant dégressif en fonction du quotient familial et du nombre d'individus de la famille présents"), ('horaire_montant_unique_nbre_ind_degr', "Montant dégressif en fonction du nombre d'individus de la famille présents et de la tranche horaire"), ('duree_coeff_montant_unique', "Montant au prorata d'une durée"), ('duree_coeff_qf', "Montant au prorata d'une durée et selon le quotient familial"), ('taux_montant_unique', "Par taux d'effort"), ('taux_qf', "Par taux d'effort et par tranches de QF"), ('taux_date', "Par taux d'effort et par date"), ('duree_taux_montant_unique', "Par taux d'effort et en fonction d'une durée"), ('duree_taux_qf', "Par taux d'effort et par tranches de QF en fonction d'une durée")], default='montant_unique', max_length=200, null=True, verbose_name='Méthode'),
        ),
    ]
