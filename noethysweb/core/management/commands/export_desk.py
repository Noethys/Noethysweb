# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Export Noethysweb Desk"

    def add_arguments(self, parser):
        parser.add_argument("--mdp", type=str, help="Mot de passe", nargs="?", default="")
        parser.add_argument("--envoyer", action="store_true", dest="envoyer", default=False, help="Envoyer sur le storage")

    def handle(self, *args, **kwargs):
        from outils.utils import utils_export_desk
        desk = utils_export_desk.Desk()
        desk.Generer(mdp=kwargs["mdp"])
        if kwargs["envoyer"]:
            desk.Envoyer_storage()
        self.stdout.write(self.style.SUCCESS("Export terminé"))
