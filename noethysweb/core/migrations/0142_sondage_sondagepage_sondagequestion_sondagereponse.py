# Generated by Django 3.2.21 on 2023-12-29 21:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0141_auto_20231225_2056'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sondage',
            fields=[
                ('idsondage', models.AutoField(db_column='IDsondage', primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=300, verbose_name='Titre')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('structure', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.structure', verbose_name='Structure')),
            ],
            options={
                'verbose_name': 'sondage',
                'verbose_name_plural': 'sondages',
                'db_table': 'sondages',
            },
        ),
        migrations.CreateModel(
            name='SondagePage',
            fields=[
                ('idpage', models.AutoField(db_column='IDpage', primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=300, verbose_name='Titre')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('ordre', models.IntegerField(verbose_name='Ordre')),
                ('sondage', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.sondage', verbose_name='Sondage')),
            ],
            options={
                'verbose_name': 'page de sondage',
                'verbose_name_plural': 'pages de sondage',
                'db_table': 'sondages_pages',
            },
        ),
        migrations.CreateModel(
            name='SondageQuestion',
            fields=[
                ('idquestion', models.AutoField(db_column='IDquestion', primary_key=True, serialize=False, verbose_name='ID')),
                ('ordre', models.IntegerField(verbose_name='Ordre')),
                ('label', models.CharField(max_length=250, verbose_name='Label')),
                ('controle', models.CharField(choices=[('ligne_texte', 'Ligne de texte'), ('bloc_texte', 'Bloc de texte multiligne'), ('entier', 'Nombre entier'), ('decimal', 'Nombre décimal'), ('montant', 'Montant'), ('liste_deroulante', 'Liste déroulante'), ('liste_coches', 'Sélection multiple'), ('case_coche', 'Case à cocher'), ('date', 'Date'), ('slider', 'Réglette'), ('couleur', 'Couleur'), ('codebarres', 'Code-barres')], max_length=200, verbose_name='contrôle')),
                ('choix', models.CharField(blank=True, help_text="Saisissez les choix possibles séparés par un point-virgule. Exemple : 'Bananes;Pommes;Poires'", max_length=500, null=True, verbose_name='Choix')),
                ('texte_aide', models.CharField(blank=True, help_text="Vous pouvez saisir un texte d'aide qui apparaîtra sous le champ de saisie.", max_length=500, null=True, verbose_name="Texte d'aide")),
                ('obligatoire', models.BooleanField(default=False, help_text='Cochez cette case si la famille doit obligatoirement répondre à cette question.', verbose_name='Obligatoire')),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.sondagepage', verbose_name='Page')),
            ],
            options={
                'verbose_name': 'question de sondage',
                'verbose_name_plural': 'questions de sondage',
                'db_table': 'sondages_questions',
            },
        ),
        migrations.CreateModel(
            name='SondageReponse',
            fields=[
                ('idreponse', models.AutoField(db_column='IDreponse', primary_key=True, serialize=False, verbose_name='ID')),
                ('reponse', models.CharField(blank=True, max_length=450, null=True, verbose_name='Réponse')),
                ('famille', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='core.famille', verbose_name='Famille')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.sondagequestion', verbose_name='Question')),
            ],
            options={
                'verbose_name': 'réponse de sondage',
                'verbose_name_plural': 'réponses de sondages',
                'db_table': 'sondages_reponses',
            },
        ),
    ]
