# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import d'un fichier Iloise dans la base. Les fichiers XLSX enfants et responsables doivent se trouver à la racine."

    def add_arguments(self, parser):
        parser.add_argument("nom_fichier_enfants", type=str, help="Nom du fichier enfants")
        parser.add_argument("nom_fichier_responsables", type=str, help="Nom du fichier responsables")

    def handle(self, *args, **kwargs):
        from outils.utils import utils_import_iloise
        utils_import_iloise.Importer(nom_fichier_enfants=kwargs["nom_fichier_enfants"], nom_fichier_responsables=kwargs["nom_fichier_responsables"])
