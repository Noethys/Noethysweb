# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.utils.translation import gettext as _
from crispy_forms.layout import HTML, ButtonHolder
from crispy_forms.bootstrap import StrictButton


def Commandes(enregistrer=True, enregistrer_label="<i class='fa fa-check margin-r-5'></i>%s" % _("Enregistrer"), enregistrer_id=None, enregistrer_name="submit",
              commandes_principales=[],
              ajouter=True,
              annuler=True, annuler_url=None,
              modifier=False, modifier_url=None, modifier_args="",
              aide=True, aide_url="{% url 'aide_toc' %}",
              autres_commandes=[], css_class="commandes"):

    liste_commandes = []

    # Enregistrer
    if enregistrer:
        liste_commandes.append(StrictButton(enregistrer_label, title=_("Enregistrer"), name=enregistrer_name, type="submit", css_class="btn-primary", id=enregistrer_id))

    # Modifier page
    if modifier:
        liste_commandes.append(HTML("""<a class="btn btn-primary" href="{{% url '{modifier_url}' {modifier_args} %}}" title="{title}"><i class="fa fa-pencil margin-r-5"></i>{label}</a> """.format(
                                    modifier_url=modifier_url, modifier_args=modifier_args, title=_("Modifier"), label=_("Modifier cette page"))))

    # Autres commandes principales
    if commandes_principales:
        [liste_commandes.append(commande) for commande in commandes_principales]

    # Enregistrer et ajouter
    if ajouter:
        liste_commandes.append(StrictButton("<i class='fa fa-plus margin-r-5'></i>%s" % _("Enregistrer & Ajouter"), title=_("Enregistrer & Ajouter"), name="SaveAndNew", type="submit", css_class="btn-primary"))

    # Annuler
    if annuler:
        liste_commandes.append(HTML("""<a class="btn btn-danger" href='%s' title="%s"><i class="fa fa-ban margin-r-5"></i>%s</a> """ % (annuler_url, _("Annuler"), _("Annuler"))))

    # Autres commandes
    if autres_commandes:
        [liste_commandes.append(commande) for commande in autres_commandes]

    # Aide
    if aide:
        liste_commandes.append(HTML("""<a class="btn btn-default" href='%s' target="_blank" title="%s"><i class="fa fa-life-saver margin-r-5"></i>%s</a> """ % (aide_url, _("Consulter l'aide"), _("Aide"))))

    return ButtonHolder(*liste_commandes, css_class=css_class)
