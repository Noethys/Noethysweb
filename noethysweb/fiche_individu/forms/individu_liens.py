# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, Div, ButtonHolder
from core.utils.utils_commandes import Commandes
from core.models import Individu, Famille, Rattachement, Lien, CATEGORIES_RATTACHEMENT, CHOIX_AUTORISATIONS
from core.data.data_liens import DICT_TYPES_LIENS
from core.data import data_civilites
from core.forms.base import FormulaireBase
import operator


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille")
        self.idindividu = kwargs.pop("idindividu")

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_liens_form'
        self.helper.form_method = 'post'

        # Importation
        rattachements = Rattachement.objects.prefetch_related('individu').filter(famille_id=self.idfamille).exclude(individu_id=self.idindividu).order_by("individu__civilite")
        liens = Lien.objects.filter(famille_id=self.idfamille, individu_objet_id=self.idindividu)
        dict_liens = {lien.individu_sujet_id: {"lien": lien.idtype_lien, "autorisation": lien.autorisation} for lien in liens}

        # Initialisation de l'affichage du formulaire
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="individu_liens_modifier", modifier_args="idfamille=idfamille idindividu=idindividu",
                                  modifier=self.request.user.has_perm("core.individu_liens_modifier"), enregistrer=False, annuler=False, ajouter=False)
        else:
            commandes = Commandes(annuler_url="{% url 'individu_liens' idfamille=idfamille idindividu=idindividu %}", ajouter=False)
        self.helper.layout = Layout(commandes)

        # Si aucun autre membre dans cette famille
        if not rattachements:
            self.helper.layout.append(HTML("<strong>Aucun autre membre n'existe dans cette famille.</strong>"))

        # Sinon on affiche les membres de la famille
        else:
            for num_categorie, nom_categorie in CATEGORIES_RATTACHEMENT:
                liste_ctrl = []
                for rattachement in rattachements:
                    if rattachement.categorie == num_categorie:

                        # Création du ctrl Lien
                        dict_civilite = data_civilites.GetCiviliteForIndividu(rattachement.individu)
                        type_individu = "E" if dict_civilite["categorie"] == "ENFANT" else "A"
                        sexe_individu = dict_civilite["sexe"]

                        choix_lien = []
                        for IDtypeLien, valeurs in DICT_TYPES_LIENS.items():
                            if type_individu in valeurs["public"] and sexe_individu:
                                texte = valeurs["texte"][sexe_individu]
                                choix_lien.append((IDtypeLien, texte))
                        choix_lien = sorted(choix_lien, key=operator.itemgetter(1))
                        choix_lien.insert(0, (None, "n'a aucun lien"))

                        nom_ctrl_lien = "%d-lien" % rattachement.individu_id
                        self.fields[nom_ctrl_lien] = forms.ChoiceField(choices=choix_lien, required=False)
                        self.fields[nom_ctrl_lien].label = False

                        # Création du ctrl Autorisation
                        nom_ctrl_autorisation = "%d-autorisation" % rattachement.individu_id
                        self.fields[nom_ctrl_autorisation] = forms.ChoiceField(choices=CHOIX_AUTORISATIONS, required=False)
                        self.fields[nom_ctrl_autorisation].label = False

                        # Valeurs importées
                        if rattachement.individu_id in dict_liens:
                            self.fields[nom_ctrl_lien].initial = dict_liens[rattachement.individu_id]["lien"]
                            self.fields[nom_ctrl_autorisation].initial = dict_liens[rattachement.individu_id]["autorisation"]

                        # Affichage des contrôles
                        liste_ctrl.append(
                            Div(
                                HTML("<label class='col-form-label col-md-2' style='padding-top: 8px;'><b>%s</b></label>" % rattachement.individu.prenom),
                                Div(nom_ctrl_lien, css_class="controls col-md-5", id=nom_ctrl_lien),
                                Div(nom_ctrl_autorisation, css_class="controls col-md-5", id=nom_ctrl_autorisation),
                                css_class="row form-group",
                            )
                        )

                if liste_ctrl:
                    item = Fieldset(nom_categorie + "s", *liste_ctrl)
                    self.helper.layout.append(item)

            if self.mode == "CONSULTATION":
                self.Set_mode_consultation()
