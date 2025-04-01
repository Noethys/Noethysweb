# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.utils.translation import gettext as _
from crispy_forms.layout import Layout, HTML, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.models import PortailRenseignement
from portail.utils import utils_champs


class FormulaireBase():
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        if not hasattr(self, "mode"):
            self.mode = kwargs.pop("mode", None)
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
        renseignements = PortailRenseignement.objects.filter(categorie=self.nom_page, famille=famille, individu=individu, etat="ATTENTE", validation_auto=False).order_by("date")
        dict_renseignements = {renseignement.code: json.loads(renseignement.nouvelle_valeur) for renseignement in renseignements}

        # Liste des champs à afficher
        self.dict_champs = utils_champs.Get_champs_page(page=self.nom_page, categorie=categorie)

        # Préparation du layout
        self.helper.layout = Layout()

        # Création des fields
        liste_renseignements_manquants = []
        for dict_rubrique in self.liste_champs_possibles:
            champs = []
            for code in dict_rubrique["champs"]:
                statut_champ = self.dict_champs.get(code, "MASQUER")

                if statut_champ in ("AFFICHER", "MODIFIABLE", "OBLIGATOIRE"):

                    # Affiche les help_text si mode édition
                    if self.mode == "EDITION":
                        self.fields[code].help_text = self.help_texts.get(code, None)

                    # Recherche si une valeur existe déjà dans les renseignements modifiés
                    if code in dict_renseignements:# and self.initial.get(code, None) != dict_renseignements.get(code, None): Ne fonctionne pas sur la page famille_caisse !
                        self.initial[code] = dict_renseignements[code]
                        self.fields[code].help_text = "<span class='text-orange'><i class='fa fa-exclamation-circle margin-r-5'></i>%s</span>" % _("Modification en attente de validation par l'administrateur.")

                    # Si champ en lecture seule
                    if self.dict_champs[code] == "AFFICHER":
                        self.fields[code].disabled = True
                        if self.mode == "EDITION":
                            self.fields[code].help_text = _("Ce champ n'est pas modifiable.")

                    # Obligatoire
                    if self.dict_champs[code] == "OBLIGATOIRE" and code not in ("rue_resid", "cp_resid", "ville_resid", "nom_jfille"):
                        self.fields[code].required = True

                    if self.dict_champs[code] == "OBLIGATOIRE" and not self.initial[code] and (code != "nom_jfille" or (code == "nom_jfille" and self.initial.get("civilite") == 3)):
                        liste_renseignements_manquants.append(str(self.fields[code].label))

                    # Génération du field
                    champs.append(Field(code, css_class="text-orange" if code in dict_renseignements else None))

            if champs:
                self.helper.layout.append(Fieldset(dict_rubrique["titre"], *champs))

        # Affichage des renseignements manquants en haut du formulaire
        if liste_renseignements_manquants:
            self.helper.layout.insert(0, HTML("""<div class='alerte'><i class='icon fa fa-warning text-danger'></i> <b>Renseignements manquants : %s</b></div>""" % ", ".join(liste_renseignements_manquants)))

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
            self.helper.layout.append(ButtonHolder(HTML("""<a class="btn btn-primary" href="{{% url 'portail_{nom_page}_modifier' {texte_kwargs} %}}" title="{title}"><i class="fa fa-pencil margin-r-5"></i>{label}</a>""".format(
                nom_page=self.nom_page, texte_kwargs=texte_kwargs, title=_("Modifier"), label=_("Modifier cette page"))
            ), css_class="pull-right"))

        if self.mode == "EDITION":
            self.helper.layout.append(ButtonHolder(
                    StrictButton("<i class='fa fa-check margin-r-5'></i>%s" % _("Enregistrer les modifications"), title=_("Enregistrer"), name="enregistrer", type="submit", css_class="btn-primary"),
                    HTML("""<a class="btn btn-danger" href='{{% url 'portail_{nom_page}' {texte_kwargs} %}}' title="{title}"><i class="fa fa-ban margin-r-5"></i>{label}</a>""".format(
                        nom_page=self.nom_page, texte_kwargs=texte_kwargs, title=_("Annuler"), label=_("Annuler"))
                    ), css_class="pull-right"))
