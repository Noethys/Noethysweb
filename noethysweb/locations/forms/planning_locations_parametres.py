# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes


class Formulaire(FormulaireBase, forms.Form):
    barre_afficher_heure = forms.BooleanField(label="Afficher les heures de début et de fin", required=False, initial=True)
    barre_label = forms.ChoiceField(label="Label", choices=[("famille", "Nom de la famille"), ("famille+produit", "Nom de la famille + nom du produit"), ("produit+famille", "Nom du produit + nom de la famille")], initial="famille+produit", required=False)
    barre_label_observations = forms.BooleanField(label="Afficher les observations de la location", required=False, initial=True)
    barre_couleur = forms.ChoiceField(label="Couleur", choices=[("famille", "Couleur de la famille"), ("produit", "Couleur du produit")], initial="famille", required=False)
    heure_min = forms.ChoiceField(label="Heure minimale affichée", choices=[("%02d:00:00" % x, "%02d:00" % x) for x in range(0, 24)], initial="00:00:00", required=False)
    heure_max = forms.ChoiceField(label="Heure maximale affichée", choices=[("%02d:00:00" % x, "%02d:00" % x) for x in range(1, 25)], initial="24:00:00", required=False)
    vue_favorite = forms.ChoiceField(label="Vue favorite", choices=[("resourceTimelineDay", "Jour"), ("resourceTimelineWeek", "Semaine"), ("dayGridMonth", "Mois"), ("multiMonthYear", "Année"), ("timeGridWeek", "Agenda"), ("listWeek", "Liste")], initial="resourceTimelineDay", required=False)
    graduations_duree = forms.ChoiceField(label="Durée d'une graduation", choices=[("00:15:00", "00:15"), ("00:30:00", "00:30"), ("01:00:00", "01:00"), ("02:00:00", "02:00")], initial="01:00:00", required=False)
    graduations_largeur = forms.ChoiceField(label="Largeur minimale d'une graduation (en pixels)", choices=[("5", "5"), ("10", "10"), ("15", "15"), ("20", "20"), ("30", "30"), ("40", "40"), ("50", "50"), ("60", "60")], initial="40", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_planning_locations_parametres'
        self.helper.form_method = 'post'

        # Affichage
        self.helper.layout = Layout(
            Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False,
                autres_commandes=[
                    HTML("""<button type="submit" name="enregistrer" title="Enregistrer" class="btn btn-primary"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """),
                    HTML("""<a class="btn btn-danger" title="Annuler" onclick="$('#modal_parametres').modal('hide');"><i class="fa fa-ban margin-r-5"></i>Annuler</a> """),
                ],
            ),
            Fieldset("La barre de location",
                Field("barre_label"),
                Field("barre_label_observations"),
                Field("barre_afficher_heure"),
                Field("barre_couleur"),
            ),
            Fieldset("Vue",
                Field("vue_favorite"),
                Field("heure_min"),
                Field("heure_max"),
                Field("graduations_duree"),
                Field("graduations_largeur"),
            ),
        )

    def clean(self):
        if self.cleaned_data["heure_min"] >= self.cleaned_data["heure_max"]:
            self.add_error("heure_max", "L'heure maximale affichée doit être supérieure à l'heure minimale")
        return self.cleaned_data
