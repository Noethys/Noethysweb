# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0202_alter_utilisateur_options_alter_aide_jours_scolaires_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionnaireGroupe',
            fields=[
                ('idgroupe', models.AutoField(db_column='IDgroupe', primary_key=True, serialize=False, verbose_name='ID')),
                ('categorie', models.CharField(choices=[('individu', 'Individu'), ('famille', 'Famille'), ('categorie_produit', 'Catégorie de produits'), ('produit', 'Produit'), ('location', 'Location'), ('location_demande', 'Demande de location'), ('inscription', 'Inscription'), ('collaborateur', 'Collaborateur'), ('contrat_collaborateur', 'Contrat collaborateur'), ('consommation', 'Consommation')], max_length=200, verbose_name='Catégorie')),
                ('nom', models.CharField(max_length=200, verbose_name='Nom')),
                ('ordre', models.IntegerField(verbose_name='Ordre')),
            ],
            options={
                'verbose_name': 'catégorie de questions',
                'verbose_name_plural': 'catégories de questions',
                'db_table': 'questionnaire_groupes',
            },
        ),
        migrations.AddField(
            model_name='questionnairequestion',
            name='groupe',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.questionnairegroupe', verbose_name='Catégorie de questions'),
        ),
    ]
