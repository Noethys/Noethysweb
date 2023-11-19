# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
import datetime
from dateutil import rrule
from core.widgets import DatePickerWidget
from core.forms.select2 import Select2MultipleWidget
from core.models import TypeGroupeActivite, Unite, UniteRemplissage, Ouverture, Remplissage, NomTarif, Tarif, Structure
from parametrage.views.activites_assistant import Assistant_base, Page_responsable, Page_responsable, Page_renseignements, Page_categories, \
                                                    Page_categories_nombre, Page_tarifs, Page_conclusion, Page_groupes_nombre, Page_groupes_noms


class Page_introduction(forms.Form):
    intro = "Bienvenue dans l'assistant de paramétrage d'une activité de type stage (stage de théâtre, de danse, de gym, etc...)<br><br>Cliquez sur le bouton Suite pour commencer la saisie des informations."

class Page_generalites(forms.Form):
    nom_activite = forms.CharField(label="Quel est le nom du stage ?", required=True, max_length=300, help_text="Exemple: 'Stage de théâtre - Février 2020'.")
    date_debut = forms.DateField(label="Quelle est la date de début du stage ?", required=True, widget=DatePickerWidget(), help_text="Saisissez la date de début du stage.")
    date_fin = forms.DateField(label="Quelle est la date de fin du stage ?", required=True, widget=DatePickerWidget(), help_text="Saisissez la date de fin du stage.")
    nbre_inscrits_max = forms.IntegerField(label="Quel est le nombre maximal d'inscrits ?", initial=0, min_value=0, required=False, help_text="S'il n'existe aucune limitation du nombre d'inscrits, laisser la valeur à 0.")
    structure = forms.ModelChoiceField(label="Quelle est la structure associée à ce séjour ?", queryset=Structure.objects.all(), required=True, help_text="Sélectionnez une structure dans la liste proposée.")
    groupes_activites = forms.ModelMultipleChoiceField(label="Sélectionnez les groupes d'activités associés à ce stage", widget=Select2MultipleWidget(), queryset=TypeGroupeActivite.objects.all(), required=False, help_text="Les groupes d'activités permettent une sélection rapide d'un ensemble d'activités.")

    def clean(self):
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            raise forms.ValidationError("La date de fin doit être supérieure à la date de début")
        return self.cleaned_data

class Page_groupes(forms.Form):
    has_groupes = forms.ChoiceField(label="Le stage est-il constitué de groupes distincts ?", choices=[("oui", "Oui"), ("non", "Non")], widget=forms.RadioSelect, initial="non", help_text="")



class Assistant(Assistant_base):
    form_list = [
        ("introduction", Page_introduction),
        ("generalites", Page_generalites),
        ("responsable", Page_responsable),
        ("renseignements", Page_renseignements),
        ("groupes", Page_groupes),
        ("nbre_groupes", Page_groupes_nombre),
        ("noms_groupes", Page_groupes_noms),
        ("categories", Page_categories),
        ("nbre_categories", Page_categories_nombre),
        ("tarifs", Page_tarifs),
        ("conclusion", Page_conclusion),
    ]

    def get_context_data(self, **kwargs):
        context = super(Assistant, self).get_context_data(**kwargs)
        context['page_titre'] = "Activités"
        context['box_titre'] = "Assistant de paramétrage d'un stage"
        return context

    def Generation(self, donnees={}):
        # Enregistrement des données standard
        donnees = self.Enregistrement_donnees_standard(donnees)

        # Enregistrement de l'unité de conso
        unite = Unite.objects.create(activite=donnees["activite"], nom="Journée Stage", abrege="JS", ordre=1, type="Unitaire",
                                     date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))

        # Enregistrement de l'unité de remplissage
        unite_remplissage = UniteRemplissage.objects.create(activite=donnees["activite"], nom="Journée Stage", abrege="JS", ordre=1,
                                                            date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))
        unite_remplissage.unites.add(unite)

        # Calendrier
        liste_dates = list(rrule.rrule(rrule.DAILY, dtstart=donnees["date_debut"], until=donnees["date_fin"]))

        # Enregistrement des ouvertures
        for date in liste_dates:
            for groupe in donnees["groupes"]:
                Ouverture.objects.create(activite=donnees["activite"], date=date, groupe=groupe, unite=unite)

        # Enregistrement du remplissage
        if donnees["nbre_inscrits_max"]:
            for date in liste_dates:
                for groupe in donnees["groupes"]:
                    Remplissage.objects.create(activite=donnees["activite"], date=date, groupe=groupe, unite_remplissage=unite_remplissage, places=donnees["nbre_inscrits_max"])

        # Enregistrement du nom de tarif
        nom_tarif = NomTarif.objects.create(activite=donnees["activite"], nom=donnees["nom_activite"])

        # Enregistrement des tarifs et lignes de tarifs
        for index_categorie, categorie_tarif in enumerate(donnees["liste_categories"], 1):
            tarif = Tarif.objects.create(activite=donnees["activite"], type="FORFAIT", nom_tarif=nom_tarif, date_debut=donnees["date_debut"],
                                         forfait_saisie_auto=True, forfait_suppression_auto=True, label_prestation="nom_tarif", options="calendrier",
                                         methode=donnees["methode_tarif_%d" % index_categorie], type_quotient=donnees["type_quotient_tarif_%d" % index_categorie])
            tarif.categories_tarifs.add(categorie_tarif)
            self.Enregistrement_lignes_tarifs(index_categorie=index_categorie, tarif=tarif, donnees=donnees)
