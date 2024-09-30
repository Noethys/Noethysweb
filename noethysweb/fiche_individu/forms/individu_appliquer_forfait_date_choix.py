# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from core.models import Tarif, TarifLigne
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille")
        self.idindividu = kwargs.pop("idindividu")
        self.tarifs = [int(x) for x in kwargs.pop("tarifs").split(";")]
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_forfaits_form'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'individu_inscriptions_liste' idfamille=idfamille idindividu=idindividu %}",
                      ajouter=False, enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider"),
        )
        for index, idtarif in enumerate(self.tarifs, 1):
            tarif = Tarif.objects.select_related("activite").get(pk=idtarif)
            lignes_tarif = TarifLigne.objects.select_related("tarif", "activite").filter(tarif_id=idtarif).order_by("num_ligne")
            choix = [(ligne.pk, "%.02f %s  %s" % (ligne.montant_unique, utils_preferences.Get_symbole_monnaie(), ligne.label or "")) for ligne in lignes_tarif]
            self.fields["tarif_%d" % idtarif] = forms.ChoiceField(label="%s - Forfait %d" % (tarif.activite.nom, index), choices=choix, required=True, help_text="Sélectionnez un montant dans la liste déroulante.")
            self.helper.layout.append(Field("tarif_%d" % idtarif))
