# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls.base import set_script_prefix, get_script_prefix


class URLPrefixMiddleware:
    """Middleware pour gérer le préfixe URL_ROOT"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if not settings.URL_ROOT:
            # Pas de préfixe, comportement normal
            return self.get_response(request)

        # Normaliser URL_ROOT
        url_prefix = settings.URL_ROOT.strip('/')
        if not url_prefix:
            return self.get_response(request)

        # Si l'URL commence déjà par le préfixe, on retire le préfixe pour le
        # traitement interne
        # Exemple: /app1/administrateur/ -> /administrateur/
        if request.path_info.startswith(f'/{url_prefix}/'):
            # Sauvegarde le chemin original pour une utilisation future
            request.original_path = request.path_info
            # Retire le préfixe du chemin
            request.path_info = request.path_info[len(f'/{url_prefix}'):]
            # Traite la requête normalement
            return self.get_response(request)

        # Si l'URL est exactement égale au préfixe (avec ou sans slash)
        elif (request.path_info == f'/{url_prefix}' or
              request.path_info == f'/{url_prefix}/'):
            request.original_path = request.path_info
            request.path_info = '/'
            return self.get_response(request)

        # Si l'URL est une URL standard (pas /static/ ou /media/), on la
        # redirige vers le préfixe
        elif not any(request.path_info.startswith(prefix)
                     for prefix in ['/static/', '/media/']):
            # Construction de l'URL avec le préfixe
            new_url = f'/{url_prefix}{request.path_info}'
            # Si l'URL se termine par un slash et que new_url a un double
            # slash, on le corrige
            new_url = new_url.replace('//', '/')
            # On ajoute le slash final si l'URL originale en avait un
            if request.path_info.endswith('/') and not new_url.endswith('/'):
                new_url += '/'
            # On ajoute les paramètres de requête s'il y en a
            if request.GET:
                new_url += '?' + request.META.get('QUERY_STRING', '')
            return HttpResponseRedirect(new_url)

        # Tout le reste passe normalement
        return self.get_response(request)


class URLPrefixReverseMiddleware:
    """Middleware pour configurer le préfixe URL utilisé par Django pour
    générer les URLs.
    Ce middleware utilise set_script_prefix() pour ajouter automatiquement le
    préfixe URL_ROOT à toutes les URLs générées par Django via la fonction
    reverse() et le tag template {% url %}."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Sauvegarder le préfixe d'origine pour le restaurer après le
        # traitement
        original_prefix = get_script_prefix()

        try:
            # Configurer le préfixe URL pour générer les URLs avec URL_ROOT
            if settings.URL_ROOT:
                # Normalisation du préfixe pour éviter les doubles slashes
                prefix = '/' + settings.URL_ROOT.strip('/') + '/'
                prefix = prefix.replace('//', '/')
                set_script_prefix(prefix)

            # Traiter la requête normalement
            response = self.get_response(request)
            return response
        finally:
            # Restaurer le préfixe d'origine une fois la requête traitée
            set_script_prefix(original_prefix)
