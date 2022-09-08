# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Récupération du token refresh de Dropbox "

    def handle(self, *args, **kwargs):
        from dropbox import DropboxOAuth2FlowNoRedirect

        # Récupération des key dropbox
        APP_KEY = getattr(settings, "DROPBOX_APP_KEY", None) or input("Saisissez l'app_key :").strip()
        APP_SECRET = getattr(settings, "DROPBOX_APP_SECRET", None) or input("Saisissez l'app_secret :").strip()

        # Récupération du code d'autorisation
        auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET, token_access_type='offline')

        print("1. Allez à la page : " + auth_flow.start())
        print("2. Cliquez sur \"Autoriser\" (vous devez être connecté à Dropbox au préalable).")
        print("3. Copiez le code d'autorisation.")
        auth_code = input("Saisissez le code d'autorisation ici : ").strip()

        try:
            oauth_result = auth_flow.finish(auth_code)
        except Exception as e:
            print('Error: %s' % (e,))
            exit(1)

        # Affichage du refresh_token
        print("access_token =", oauth_result.access_token)
        print("expires_at =", oauth_result.expires_at)
        print("refresh_token =", oauth_result.refresh_token)
