# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Collaborateur
from fiche_famille.widgets import Internet_identifiant, Internet_mdp


class Formulaire(FormulaireBase, ModelForm):
    internet_identifiant = forms.CharField(label="Identifiant", required=False, widget=Internet_identifiant(), help_text="Identifiant de connexion à l'espace collaborateur, généré automatiquement. Il est déconseillé de le modifier car le collaborateur ne pourrait plus se connecter avec l'ancien.")
    internet_mdp = forms.CharField(label="Mot de passe", required=False, widget=Internet_mdp(), help_text="Mot de passe provisoire à transmettre au collaborateur. Des étoiles ***** signifient qu'il a personnalisé son mot de passe lors de sa première connexion : il n'est alors plus consultable. S'il l'a oublié, générez-en un nouveau.")
    date_expiration_mdp = forms.DateTimeField(label="Date d'expiration", required=False)

    class Meta:
        model = Collaborateur
        fields = ["internet_actif", "internet_identifiant", "internet_mdp", "notifier_planning"]
        help_texts = {
            "internet_actif": "Décochez cette case pour empêcher le collaborateur de se connecter à son espace.",
            "notifier_planning": "Si l'option est activée dans les paramètres du portail, le collaborateur reçoit chaque soir un email récapitulant les changements de son planning sur les 14 prochains jours.",
        }

    def __init__(self, *args, **kwargs):
        idcollaborateur = kwargs.pop("idcollaborateur")
        collaborateur = Collaborateur.objects.select_related("utilisateur").get(pk=idcollaborateur)
        if "instance" not in kwargs:
            self.instance = collaborateur
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "collaborateur_espace_form"
        self.helper.form_method = "post"
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        date_expiration_mdp = collaborateur.utilisateur.date_expiration_mdp if collaborateur.utilisateur else None
        self.fields["internet_mdp"].widget.attrs["date_expiration_mdp"] = date_expiration_mdp

        autres_commandes = [HTML("""<a type='button' class='btn btn-default' title="Envoyer les codes par email" onclick="envoyer_codes()"><i class="fa fa-send-o margin-r-5"></i>Envoyer les codes par email</a>""")]
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="collaborateur_espace_modifier", modifier_args="idcollaborateur=idcollaborateur", modifier=True,
                                  enregistrer=False, annuler=False, ajouter=False, autres_commandes=autres_commandes)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'collaborateur_espace' idcollaborateur=idcollaborateur %}", ajouter=False, autres_commandes=autres_commandes)

        derniere_connexion = collaborateur.utilisateur.last_login.strftime("le %d/%m/%Y à %Hh%M") if collaborateur.utilisateur and collaborateur.utilisateur.last_login else "Jamais connecté"
        self.helper.layout = Layout(
            commandes,
            Hidden("idcollaborateur", value=idcollaborateur),
            Hidden("date_expiration_mdp", value=date_expiration_mdp),
            Fieldset("Activation",
                Field("internet_actif"),
                HTML("""<div class="form-group row"><label class="col-form-label col-md-2">Dernière connexion</label><div class="col-md-10"><p class="form-control-plaintext">%s</p></div></div>""" % derniere_connexion),
            ),
            Fieldset("Codes d'accès",
                Field("internet_identifiant"),
                Field("internet_mdp"),
                Field("date_expiration_mdp", type="hidden"),
            ),
            Fieldset("Notifications",
                Field("notifier_planning"),
            ),
        )
