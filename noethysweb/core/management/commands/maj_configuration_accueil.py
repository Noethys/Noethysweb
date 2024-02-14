# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "MAJ de la configuration de la page d'accueil"

    def handle(self, *args, **kwargs):
        """ Ajoute des widgets à la page d'accueil sur les configurations de tous les utilisateurs """
        from core.utils import utils_widgets

        # Ajout du widget Astuce du jour s'il n'est pas déjà sélectionné
        utils_widgets.Ajouter_widget_to_configuration(nom_widget="astuce", apres_widget="messages")

        self.stdout.write(self.style.SUCCESS("Ajout widgets page accueil ok."))
