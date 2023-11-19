# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
import datetime
from core.forms.select2 import Select2MultipleWidget
from core.models import TypeGroupeActivite, Unite, UniteRemplissage, Ouverture, Remplissage, NomTarif, Tarif, CategorieTarif, TarifLigne, Structure
from parametrage.views.activites_assistant import Assistant_base, Page_responsable, Page_responsable, Page_renseignements


class Page_introduction(forms.Form):
    intro = "Bienvenue dans l'assistant de paramétrage d'une activité de type sorties familiales.<br><br>Cliquez sur le bouton Suite pour commencer la saisie des informations."

class Page_generalites(forms.Form):
    nom_activite = forms.CharField(label="Quel est le nom de l'activité ?", required=True, max_length=300, help_text="Exemple: 'Sorties familiales'.")
    structure = forms.ModelChoiceField(label="Quelle est la structure associée à ce séjour ?", queryset=Structure.objects.all(), required=True, help_text="Sélectionnez une structure dans la liste proposée.")
    groupes_activites = forms.ModelMultipleChoiceField(label="Sélectionnez les groupes d'activités associés à cette activité", widget=Select2MultipleWidget(), queryset=TypeGroupeActivite.objects.all(), required=False, help_text="Les groupes d'activités permettent une sélection rapide d'un ensemble d'activités.")

class Page_conclusion(forms.Form):
    intro = "Vous avez terminé de renseigner les paramètres de l'activité.<br><br>Cliquez maintenant sur le bouton Suite pour finaliser la création de l'activité."
    intro += """<br><br><i class='fa fa-warning text-orange'></i> Après la génération de l'activité, vous devrez aller dans le paramétrage de l'activité > Onglet Calendrier
pour paramétrer les sorties. Celles-ci doivent être enregistrées en tant qu'évènements dans Noethys. 
Pour saisir votre première sortie depuis le calendrier des ouvertures, cliquez sur la case de la date souhaitée 
pour ouvrir l'unité de consommation 'Sortie' puis cliquez sur le '+' de la case pour saisir une ou plusieurs sorties."""


class Assistant(Assistant_base):
    form_list = [
        ("introduction", Page_introduction),
        ("generalites", Page_generalites),
        ("responsable", Page_responsable),
        ("renseignements", Page_renseignements),
        ("conclusion", Page_conclusion),
    ]

    def get_context_data(self, **kwargs):
        context = super(Assistant, self).get_context_data(**kwargs)
        context['page_titre'] = "Activités"
        context['box_titre'] = "Assistant de paramétrage de sorties familiales"
        return context

    def Generation(self, donnees={}):
        # Enregistrement des données standard
        donnees = self.Enregistrement_donnees_standard(donnees)

        # Enregistrement de l'unité de conso
        unite = Unite.objects.create(activite=donnees["activite"], nom="Sortie", abrege="SORTIE", ordre=1, type="Evenement",
                                     date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))

        # Enregistrement de l'unité de remplissage
        unite_remplissage = UniteRemplissage.objects.create(activite=donnees["activite"], nom="Sortie", abrege="SORTIE", ordre=1,
                                                            date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))
        unite_remplissage.unites.add(unite)

        # Enregistrement du nom de tarif
        nom_tarif = NomTarif.objects.create(activite=donnees["activite"], nom="Sortie")

        # Enregistrement de la catégorie
        categorie_tarif = CategorieTarif.objects.create(activite=donnees["activite"], nom="Catégorie unique")

        # Enregistrement des tarifs et lignes de tarifs
        tarif = Tarif.objects.create(activite=donnees["activite"], type="JOURN", nom_tarif=nom_tarif, date_debut=datetime.date(datetime.date.today().year, 1, 1),
                                     etats="reservation,present,absenti", label_prestation="nom_tarif", methode="montant_evenement")
        tarif.categories_tarifs.add(categorie_tarif)
        TarifLigne.objects.create(activite=donnees["activite"], tarif=tarif, code="montant_evenement", num_ligne=0, tranche="1")
        self.Enregistrement_combi_tarifs(liste_combi_tarifs=[{"type": "JOURN", "unites": [unite]}], tarif=tarif)
