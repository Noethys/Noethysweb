# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import re
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import ProfilReglementaireCollaborateur


class DureeField(forms.CharField):
    """ Durée saisie en heures et minutes (10:00, 10h, 10h30, 0:20...) et stockée en minutes """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.TextInput(attrs={"placeholder": "hh:mm", "style": "max-width: 140px;"}))
        super(DureeField, self).__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, int):
            return "%d:%02d" % (value // 60, value % 60)
        return value

    def to_python(self, value):
        texte = (value or "").strip().lower().replace(" ", "")
        if not texte:
            return None
        resultat = re.fullmatch(r"(\d{1,3})(?:[:h](\d{0,2}))?", texte)
        if not resultat:
            raise forms.ValidationError("Saisissez une durée au format hh:mm (exemple : 10:00 ou 0:20)")
        minutes = int(resultat.group(2) or 0)
        if minutes >= 60:
            raise forms.ValidationError("Les minutes doivent être inférieures à 60")
        return int(resultat.group(1)) * 60 + minutes


class Formulaire(FormulaireBase, ModelForm):
    duree_max_jour = DureeField(label="Durée maximale par jour", help_text="Temps de travail maximal sur une journée. Exemple : 10:00.")
    amplitude_max_jour = DureeField(label="Amplitude maximale de la journée", help_text="Temps maximal entre le début du premier évènement et la fin du dernier évènement de la journée. Exemple : 12:00.")
    repos_quotidien_min = DureeField(label="Repos quotidien minimal", help_text="Temps de repos minimal entre deux journées de travail. Exemple : 11:00.")
    duree_max_semaine = DureeField(label="Durée maximale par semaine", help_text="Temps de travail maximal sur une semaine civile (lundi à dimanche). Exemple : 48:00.")
    moyenne_max_12_semaines = DureeField(label="Moyenne hebdomadaire maximale", help_text="Moyenne maximale du temps de travail hebdomadaire calculée sur 12 semaines consécutives. Exemple : 44:00.")
    repos_hebdo_min = DureeField(label="Repos hebdomadaire minimal", help_text="Repos continu minimal à trouver dans chaque semaine civile. Exemple : 35:00.")
    pause_duree = DureeField(label="Durée minimale de la pause", help_text="Durée de la pause obligatoire. Exemple : 0:20.")
    pause_apres = DureeField(label="Pause obligatoire après", help_text="Temps de travail continu au-delà duquel la pause est obligatoire. Exemple : 6:00.")

    class Meta:
        model = ProfilReglementaireCollaborateur
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={"rows": 3}),
            "jours_consecutifs_max": forms.NumberInput(attrs={"min": 1, "max": 31, "style": "max-width: 140px;"}),
        }
        help_texts = {
            "nom": "Saisissez le nom du profil. Exemples : Fonction publique territoriale, Code du travail, Contrat d'engagement éducatif...",
            "jours_consecutifs_max": "Nombre maximal de jours travaillés consécutifs. Exemple : 6.",
            "observations": "Vous pouvez noter ici les références réglementaires ou les dérogations applicables.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "profils_reglementaires_collaborateurs_form"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'profils_reglementaires_collaborateurs_liste' %}"),
            Fieldset("Généralités",
                Field("nom"),
                Field("defaut"),
                Field("utiliser_realise"),
                Field("observations"),
            ),
            Fieldset("Journée",
                Field("duree_max_jour"),
                Field("amplitude_max_jour"),
                Field("repos_quotidien_min"),
                Field("pause_duree"),
                Field("pause_apres"),
            ),
            Fieldset("Semaine",
                Field("duree_max_semaine"),
                Field("moyenne_max_12_semaines"),
                Field("repos_hebdo_min"),
                Field("jours_consecutifs_max"),
            ),
        )

    def clean(self):
        if bool(self.cleaned_data.get("pause_duree")) != bool(self.cleaned_data.get("pause_apres")):
            self.add_error("pause_apres", "Renseignez à la fois la durée de la pause et le temps de travail au-delà duquel elle est obligatoire, ou laissez les deux vides")
        return self.cleaned_data
