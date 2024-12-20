# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import d'un fichier Noethys dans la base"

    def add_arguments(self, parser):
        parser.add_argument('fichier', type=str, help='Nom du fichier')
        parser.add_argument('--mdp', type=str, help='Mot de passe', nargs="?", default="")
        parser.add_argument('--conserve_mdp_internet', action='store_true', help='Conserve les mots de passe internet')

    def handle(self, *args, **kwargs):
        nom_fichier = kwargs["fichier"]
        mdp = kwargs["mdp"]
        conserve_mdp_internet = kwargs["conserve_mdp_internet"]

        from outils.utils import utils_sauvegarde
        resultat = utils_sauvegarde.Restauration(nom_fichier=nom_fichier, mdp=mdp, conserve_mdp_internet=conserve_mdp_internet)
        print("resultat=", resultat)
