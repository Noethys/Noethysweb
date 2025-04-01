# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import re
from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Famille, Rattachement
from core.forms.select2 import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    email_recus = forms.BooleanField(label="Activer l'envoi des reçus de règlements par Email", required=False, initial=False)
    adresses_individus = forms.MultipleChoiceField(label="Adresses existantes", help_text="Sélectionnez une ou plusieurs adresses parmi la liste des adresses de la famille.", widget=Select2MultipleWidget(), choices=[], required=False)
    adresses_autres = forms.CharField(label="Autres adresses", help_text="Saisissez une ou plusieurs autres adresses en les séparant par des points-virgules.", required=False)

    class Meta:
        model = Famille
        fields = ["email_recus", "email_recus_adresses"]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_abo_recus_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit la famille associée
        famille = Famille.objects.get(pk=idfamille)

        # Préparation des adresses existantes des individus
        rattachements = Rattachement.objects.select_related('individu').filter(famille=famille).order_by("individu__nom", "individu__prenom")
        liste_adresses_dispo = []
        for rattachement in rattachements:
            if rattachement.individu.mail: liste_adresses_dispo.append(("%s;perso;" % rattachement.individu.pk, "%s (Adresse perso de %s)" % (rattachement.individu.mail, rattachement.individu.prenom)))
            if rattachement.individu.travail_mail: liste_adresses_dispo.append(("%s;travail;" % rattachement.individu.pk, "%s (Adresse pro de %s)" % (rattachement.individu.travail_mail, rattachement.individu.prenom)))
        self.fields["adresses_individus"].choices = liste_adresses_dispo

        # Sélections initiales
        liste_adresses_existantes = []
        liste_adresses_autres = []
        if famille.email_recus:
            liste_adresses = famille.email_recus_adresses.split("##")
            for adresse in liste_adresses:
                if ";" in adresse:
                    id, categorie, adresse_manuelle = adresse.split(";")
                    if id:
                        liste_adresses_existantes.append(adresse)
                    else:
                        liste_adresses_autres.append(adresse_manuelle)

        self.fields["adresses_individus"].initial = liste_adresses_existantes
        self.fields["adresses_autres"].initial = ";".join(liste_adresses_autres)

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_reglements_liste' idfamille=idfamille %}", ajouter=False),
            Fieldset("Activation du service",
                Field("email_recus"),
            ),
            Fieldset("Adresses Emails",
                Field("adresses_individus"),
                Field("adresses_autres"),
            ),
        )

    def clean(self):
        if self.cleaned_data.get("email_recus"):
            # Récupération des adresses existantes
            liste_adresses = self.cleaned_data.get("adresses_individus")

            # Vérification et ajout des autres adresses
            if self.cleaned_data.get("adresses_autres"):
                for adresse in self.cleaned_data.get("adresses_autres").split(";"):
                    if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", adresse) == None:
                        self.add_error("adresses_autres", "La ou les adresses saisies manuellement ne sont pas valides.")
                        return
                    liste_adresses.append(";;%s" % adresse)

            # Vérifie qu'au moins une adresse a été saisie
            if not liste_adresses:
                self.add_error("email_recus", "Vous avez activé le service mais sans sélectionner d'adresse Email de destination.")
                return

            # Assemblage de toutes les adresses mail
            self.cleaned_data["email_recus_adresses"] = "##".join(liste_adresses)
        else:
            # Si non activé
            self.cleaned_data["email_recus_adresses"] = None
        return self.cleaned_data

