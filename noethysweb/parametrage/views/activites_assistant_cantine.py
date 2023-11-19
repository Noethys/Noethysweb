# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
import datetime
from core.forms.select2 import Select2MultipleWidget
from core.models import TypeGroupeActivite, Unite, UniteRemplissage, Ouverture, Remplissage, NomTarif, Tarif, Structure
from parametrage.views.activites_assistant import Assistant_base, Page_responsable, Page_responsable, Page_renseignements, Page_categories, \
                                                    Page_categories_nombre, Page_tarifs


class Page_introduction(forms.Form):
    intro = "Bienvenue dans l'assistant de paramétrage d'une activité de type cantine scolaire.<br><br>Cliquez sur le bouton Suite pour commencer la saisie des informations."

class Page_generalites(forms.Form):
    nom_activite = forms.CharField(label="Quel est le nom de la cantine ?", required=True, max_length=300, help_text="Exemple: 'Cantine scolaire'.")
    structure = forms.ModelChoiceField(label="Quelle est la structure associée à ce séjour ?", queryset=Structure.objects.all(), required=True, help_text="Sélectionnez une structure dans la liste proposée.")
    groupes_activites = forms.ModelMultipleChoiceField(label="Sélectionnez les groupes d'activités associés à cette activité", widget=Select2MultipleWidget(), queryset=TypeGroupeActivite.objects.all(), required=False, help_text="Les groupes d'activités permettent une sélection rapide d'un ensemble d'activités.")

class Page_groupes(forms.Form):
    has_groupes = forms.ChoiceField(label="Le temps de cantine est-il constitué de plusieurs services ?", choices=[("oui", "Oui"), ("non", "Non")], widget=forms.RadioSelect, initial="non", help_text="Exemple : Service 1 et service 2.")

class Page_groupes_nombre(forms.Form):
    nbre_groupes = forms.IntegerField(label="Combien y a t-il de services ?", initial=1, min_value=1, required=True, help_text="")

class Page_groupes_noms(forms.Form):
    def __init__(self, *args, **kwargs):
        nbre_groupes = kwargs.pop("nbre_groupes")
        super(Page_groupes_noms, self).__init__(*args, **kwargs)
        for index in range(1, nbre_groupes+1):
            self.fields["nom_groupe_%d" % index] = forms.CharField(label="Quel est le nom du service n°%d ?" % index, max_length=300, help_text="")

class Page_conclusion(forms.Form):
    intro = "Vous avez terminé de renseigner les paramètres de l'activité.<br><br>Cliquez maintenant sur le bouton Suite pour finaliser la création de l'activité."
    intro += "<br><br><i class='fa fa-warning text-orange'></i> Après la génération de l'activité, vous devrez aller dans le paramétrage de l'activité > Onglet Calendrier pour paramétrer les dates d'ouverture. Cliquez simplement dans les cases pour ouvrir les dates souhaitées."


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
        context['box_titre'] = "Assistant de paramétrage d'une cantine"
        return context

    def Generation(self, donnees={}):
        # Enregistrement des données standard
        donnees = self.Enregistrement_donnees_standard(donnees)

        # Enregistrement de l'unité de conso
        unite = Unite.objects.create(activite=donnees["activite"], nom="Repas", abrege="R", ordre=1, type="Unitaire",
                                     date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))

        # Enregistrement de l'unité de remplissage
        unite_remplissage = UniteRemplissage.objects.create(activite=donnees["activite"], nom="Repas", abrege="R", ordre=1,
                                                            date_debut=datetime.date(1977, 1, 1), date_fin=datetime.date(2999, 1, 1))
        unite_remplissage.unites.add(unite)

        # Enregistrement du nom de tarif
        nom_tarif = NomTarif.objects.create(activite=donnees["activite"], nom="Repas")

        # Enregistrement des tarifs et lignes de tarifs
        for index_categorie, categorie_tarif in enumerate(donnees["liste_categories"], 1):
            tarif = Tarif.objects.create(activite=donnees["activite"], type="JOURN", nom_tarif=nom_tarif, date_debut=datetime.date(datetime.date.today().year, 1, 1),
                                         etats="reservation,present,absenti", label_prestation="nom_tarif", methode=donnees["methode_tarif_%d" % index_categorie],
                                         type_quotient=donnees["type_quotient_tarif_%d" % index_categorie])
            tarif.categories_tarifs.add(categorie_tarif)
            self.Enregistrement_lignes_tarifs(index_categorie=index_categorie, tarif=tarif, donnees=donnees)
            self.Enregistrement_combi_tarifs(liste_combi_tarifs=[{"type": "JOURN", "unites": [unite]}], tarif=tarif)
