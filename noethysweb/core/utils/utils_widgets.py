# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.cache import cache
from core.models import Parametre


def Ajouter_widget_to_configuration(nom_widget=None, apres_widget=None):
    """ Exemple d'utilisation : Ajouter_widget_to_configuration(nom_widget='astuce', apres_widget='messages') """
    for parametre in Parametre.objects.filter(nom="configuration_accueil"):
        if nom_widget not in parametre.parametre and apres_widget in parametre.parametre:
            parametre.parametre = parametre.parametre.replace('"%s"' % apres_widget, '"%s","%s"' % (apres_widget, nom_widget))
            parametre.save()
            cache.delete("options_interface_user%d" % parametre.utilisateur_id)
