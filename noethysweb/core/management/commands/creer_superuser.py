# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Créer manuellement un superuser."

    def add_arguments(self, parser):
        parser.add_argument("nom", type=str, help="Nom")
        parser.add_argument("mdp", type=str, help="MDP")

    def handle(self, *args, **kwargs):
        User = get_user_model()
        User.objects.create_superuser(username=kwargs["nom"], password=kwargs["mdp"])
