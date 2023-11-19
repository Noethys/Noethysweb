# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
import datetime
from core.utils import utils_dates
from dateutil import rrule
from core.widgets import DatePickerWidget
from core.forms.select2 import Select2MultipleWidget
from core.models import TypeGroupeActivite, Unite, UniteRemplissage, Ouverture, Remplissage, NomTarif, Tarif, Vacance, JOURS_SEMAINE, Structure
from parametrage.views.activites_assistant import Assistant_base, Page_responsable, Page_responsable, Page_renseignements, Page_categories, \
                                                    Page_categories_nombre, Page_tarifs, Page_conclusion


class Page_introduction(forms.Form):
    intro = "Bienvenue dans l'assistant de paramétrage d'une activité annuelle culturelle ou sportive (gym, yoga, art floral, foot, etc...)<br><br>Cliquez sur le bouton Suite pour commencer la saisie des informations."

class Page_generalites(forms.Form):
    nom_activite = forms.CharField(label="Quel est le nom l'activité ?", required=True, max_length=300, help_text="Exemple: 'Yoga - Saison 2017-18'.")
    date_debut = forms.DateField(label="Quelle est la date de début de l'activité ?", required=True, widget=DatePickerWidget(), help_text="Saisissez la date de début.")
    date_fin = forms.DateField(label="Quelle est la date de fin de l'activité ?", required=True, widget=DatePickerWidget(), help_text="Saisissez la date de fin.")
    nbre_inscrits_max = forms.IntegerField(label="Quel est le nombre maximal d'inscrits ?", initial=0, min_value=0, required=False, help_text="S'il n'existe aucune limitation du nombre d'inscrits, laisser la valeur à 0.")
    structure = forms.ModelChoiceField(label="Quelle est la structure associée à ce séjour ?", queryset=Structure.objects.all(), required=True, help_text="Sélectionnez une structure dans la liste proposée.")
    groupes_activites = forms.ModelMultipleChoiceField(label="Sélectionnez les groupes d'activités associés à cette activité", widget=Select2MultipleWidget(), queryset=TypeGroupeActivite.objects.all(), required=False, help_text="Les groupes d'activités permettent une sélection rapide d'un ensemble d'activités.")

    def clean(self):
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            raise forms.ValidationError("La date de fin doit être supérieure à la date de début")
        return self.cleaned_data

class Page_groupes(forms.Form):
    has_groupes = forms.ChoiceField(label="Cette activité est-elle constitué de plusieurs groupes ou plusieurs séances ?", choices=[("oui", "Oui"), ("non", "Non")], widget=forms.RadioSelect, initial="non", help_text="Exemples : Groupe du 'lundi soir', 'jeudi 18h15', 'Séniors', etc...")
    has_consommations = forms.ChoiceField(label="Souhaitez-vous pouvoir faire du pointage à chaque séance ?", choices=[("oui", "Oui"), ("non", "Non")], widget=forms.RadioSelect, initial="non", help_text="Noethysweb enregistrera alors des consommations pour chaque séance. Si vous ne savez pas, sélectionnez Non.")

class Page_groupes_nombre(forms.Form):
    nbre_groupes = forms.IntegerField(label="Quel est le nombre de groupes ou de séances ?", initial=2, min_value=2, required=True, help_text="")

class Page_groupes_noms(forms.Form):
    def __init__(self, *args, **kwargs):
        nbre_groupes = kwargs.pop("nbre_groupes")
        has_consommations = kwargs.pop("has_consommations")
        super(Page_groupes_noms, self).__init__(*args, **kwargs)
        if nbre_groupes == 0 and has_consommations == "oui":
            nbre_groupes = 1
        for index in range(1, nbre_groupes+1):
            if nbre_groupes > 1:
                self.fields["nom_groupe_%d" % index] = forms.CharField(label="Quel est le nom du groupe ou de la séance n°%d ?" % index, max_length=300, help_text="Exemples : 'Lundi 18h15', 'Samedi 10h', 'Séniors', etc...")
                self.fields["nbre_inscrits_max_groupe_%d" % index] = forms.IntegerField(label="Quel est le nombre maximal d'inscrits du groupe ou de la séance n°%d ?" % index, initial=0, min_value=0, help_text="S'il n'existe aucune limitation du nombre d'inscrits, laisser la valeur à 0.")
            if has_consommations == "oui":
                choix_jours = [
                    ("SCOL_0", "Semaine scolaire : Lundi"), ("SCOL_1", "Semaine scolaire : Mardi"),
                    ("SCOL_2", "Semaine scolaire : Mercredi"), ("SCOL_3", "Semaine scolaire : Jeudi"),
                    ("SCOL_4", "Semaine scolaire : Vendredi"), ("SCOL_5", "Semaine scolaire : Samedi"),
                    ("SCOL_6", "Semaine scolaire : Dimanche"),
                    ("VACS_0", "Semaine de vacances : Lundi"), ("VACS_1", "Semaine de vacances : Mardi"),
                    ("VACS_2", "Semaine de vacances : Mercredi"), ("VACS_3", "Semaine de vacances : Jeudi"),
                    ("VACS_4", "Semaine de vacances : Vendredi"), ("VACS_5", "Semaine de vacances : Samedi"),
                    ("VACS_6", "Semaine de vacances : Dimanche"),
                ]
                label = "La séance n°%d a lieu quel(s) jour(s) de la semaine ?" % index if nbre_groupes > 1 else "La séance a lieu quel(s) jour(s) de la semaine ?"
                self.fields["jours_groupe_%d" % index] = forms.MultipleChoiceField(label=label, widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), choices=choix_jours, required=True, help_text="Noethysweb va créer des consommations sur chaque jour d'ouverture de la séance durant toute la durée de l'activité.")



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
        context['box_titre'] = "Assistant de paramétrage d'une activité annuelle"
        return context

    def Generation(self, donnees={}):
        # Enregistrement des données standard
        donnees = self.Enregistrement_donnees_standard(donnees)

        if donnees["has_consommations"] == "oui":

            # Enregistrement de l'unité de conso
            unite = Unite.objects.create(activite=donnees["activite"], nom="Séance", abrege="SEANCE", ordre=1, type="Unitaire",
                                         date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))

            # Enregistrement de l'unité de remplissage
            unite_remplissage = UniteRemplissage.objects.create(activite=donnees["activite"], nom="Séance", abrege="SEANCE", ordre=1,
                                                                date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))
            unite_remplissage.unites.add(unite)

            # Enregistrement des ouvertures
            liste_ajouts = []
            for index, groupe in enumerate(donnees["groupes"], 1):
                jours = donnees.get("jours_groupe_%d" % index, [])
                for date in self.Calc_dates_ouverture(jours=jours, donnees=donnees):
                    liste_ajouts.append(Ouverture(activite=donnees["activite"], date=date, groupe=groupe, unite=unite))
            if liste_ajouts:
                Ouverture.objects.bulk_create(liste_ajouts)

        # Enregistrement du nom de tarif
        nom_tarif = NomTarif.objects.create(activite=donnees["activite"], nom=donnees["nom_activite"])

        # Enregistrement des tarifs et lignes de tarifs
        for index_categorie, categorie_tarif in enumerate(donnees["liste_categories"], 1):
            tarif = Tarif.objects.create(activite=donnees["activite"], type="FORFAIT", nom_tarif=nom_tarif, date_debut=donnees["date_debut"],
                                         forfait_saisie_auto=True, forfait_suppression_auto=True, label_prestation="nom_tarif",
                                         options="calendrier" if donnees["has_consommations"] == "oui" else None,
                                         methode=donnees["methode_tarif_%d" % index_categorie], type_quotient=donnees["type_quotient_tarif_%d" % index_categorie])
            tarif.categories_tarifs.add(categorie_tarif)
            self.Enregistrement_lignes_tarifs(index_categorie=index_categorie, tarif=tarif, donnees=donnees)

    def Calc_dates_ouverture(self, jours=[], donnees={}):
        liste_vacances = Vacance.objects.filter(date_fin__gte=donnees["date_debut"], date_debut__lte=donnees["date_fin"])
        liste_jours_rrule = [rrule.MO, rrule.TU, rrule.WE, rrule.TH, rrule.FR, rrule.SA, rrule.SU]
        liste_dates = []
        for periode in ["SCOL", "VACS"]:
            liste_jours = []
            for jour in [jour for jour in jours if jour.startswith(periode)]:
                liste_jours.append(liste_jours_rrule[int(jour.split("_")[1])])
            if liste_jours:
                for date in list(rrule.rrule(rrule.WEEKLY, wkst=rrule.MO, byweekday=liste_jours, dtstart=donnees["date_debut"], until=donnees["date_fin"])):
                    date = date.date()
                    est_vacances = utils_dates.EstEnVacances(date=date, liste_vacances=liste_vacances)
                    if periode == "SCOL" and not est_vacances: liste_dates.append(date)
                    if periode == "VACS" and est_vacances: liste_dates.append(date)
        liste_dates.sort()
        return liste_dates
