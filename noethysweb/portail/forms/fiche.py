# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.models import Individu, PortailRenseignement, Rattachement
from portail.utils import utils_champs
import json


class FormulaireBase():
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(FormulaireBase, self).__init__(*args, **kwargs)

    def Set_layout(self):
        # Récupération des variables
        if hasattr(self, "rattachement"):
            # Si fiche individuelle
            famille = self.rattachement.famille
            individu = self.rattachement.individu
            categorie = self.rattachement.categorie
        else:
            # Si fiche famille
            famille = self.famille
            individu = None
            categorie = "famille"

        # Importation des renseignements en attente de validation
        renseignements = PortailRenseignement.objects.filter(categorie=self.nom_page, famille=famille, individu=individu, etat="ATTENTE").order_by("date")
        dict_renseignements = {renseignement.code: json.loads(renseignement.valeur) for renseignement in renseignements}

        # Liste des champs à afficher
        liste_codes_champs = utils_champs.Get_codes_champs_page(page=self.nom_page, categorie=categorie)

        # Préparation du layout
        self.helper.layout = Layout()

        # Création des fields
        for dict_rubrique in self.liste_champs_possibles:
            champs = []
            for code in dict_rubrique["champs"]:
                if code in liste_codes_champs:
                    # Affiche les help_text si mode édition
                    if self.mode == "EDITION":
                        self.fields[code].help_text = self.help_texts.get(code, None)
                    # Recherche si une valeur existe déjà dans les renseignements modifiés
                    if code in dict_renseignements and self.initial[code] != dict_renseignements[code]:
                        self.initial[code] = dict_renseignements[code]
                        self.fields[code].help_text = "<span class='text-orange'><i class='fa fa-exclamation-circle margin-r-5'></i>Modification en attente de validation par l'administrateur.</span>"
                    # Génération du field
                    champs.append(Field(code, css_class="text-orange" if code in dict_renseignements else None))
            if champs:
                self.helper.layout.append(Fieldset(dict_rubrique["titre"], *champs))

        # Désactive les champs en mode consultation
        if self.mode == "CONSULTATION":
            for nom, field in self.fields.items():
                field.disabled = True

        # Ajout des commandes
        if hasattr(self, "rattachement"):
            texte_kwargs = "idrattachement=rattachement.pk"
        else:
            texte_kwargs = ""
        if self.mode == "CONSULTATION":
            self.helper.layout.append(ButtonHolder(HTML("""<a class="btn btn-primary" href="{% url 'portail_""" + self.nom_page + """_modifier' """ + texte_kwargs + """ %}" title="Modifier"><i class="fa fa-pencil margin-r-5"></i>Modifier cette page</a>"""), css_class="pull-right"))
        if self.mode == "EDITION":
            self.helper.layout.append(ButtonHolder(
                    StrictButton("<i class='fa fa-check margin-r-5'></i>Enregistrer les modifications", title="Enregistrer", name="enregistrer", type="submit", css_class="btn-primary"),
                    HTML("""<a class="btn btn-danger" href='{% url 'portail_""" + self.nom_page + """' """ + texte_kwargs + """ %}' title="Annuler"><i class="fa fa-ban margin-r-5"></i>Annuler</a>"""),
                    css_class="pull-right"))
