# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, os, time
logger = logging.getLogger(__name__)
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.urls.base import set_script_prefix, get_script_prefix

try:
    import geoip2.database
    import geoip2.errors
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False


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


class GeoBlockMiddleware:
    """
    Bloque l'accès aux visiteurs dont le pays n'est pas dans ALLOWED_COUNTRIES.
    Désactivé automatiquement si :
    - le package geoip2 n'est pas installé
    - GEOIP_COUNTRY_DB ou GEOBLOCK_ALLOWED_COUNTRIES n'est pas défini dans les settings
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.reader = None

        if not GEOIP2_AVAILABLE:
            logger.info("GeoBlockMiddleware désactivé : le package geoip2 n'est pas installé")
            return

        self.max_db_age_days = 30
        geoip_db = getattr(settings, 'GEOIP_COUNTRY_DB', None)
        allowed_countries = getattr(settings, 'GEOBLOCK_ALLOWED_COUNTRIES', None)

        if not geoip_db or not allowed_countries:
            logger.info("GeoBlockMiddleware désactivé : GEOIP_COUNTRY_DB et/ou GEOBLOCK_ALLOWED_COUNTRIES non configurés")
            return

        try:
            self.reader = geoip2.database.Reader(geoip_db)
        except FileNotFoundError:
            logger.error("Base GeoIP introuvable : %s — GeoBlockMiddleware désactivé", geoip_db)
            self.reader = None

        self.geoip_db_path = geoip_db

    def _is_db_stale(self):
        """Vérifie si la base GeoIP est plus vieille que le seuil autorisé."""
        try:
            age_days = (time.time() - os.path.getmtime(self.geoip_db_path)) / 86400
            return age_days > self.max_db_age_days, age_days
        except OSError:
            return True, None

    def get_client_ip(self, request):
        # Si Apache est en frontal direct (pas de proxy Cloudflare devant), REMOTE_ADDR suffit.
        # Si un reverse proxy est utilisé, il faudra lire X-Forwarded-For à la place.
        return request.META.get('REMOTE_ADDR')

    def __call__(self, request):
        if self.reader is None:
            return self.get_response(request)

        # Vérifie la fraîcheur de la base à chaque requête
        is_stale, age_days = self._is_db_stale()
        if is_stale:
            logger.warning(
                "Base GeoIP obsolète (%.0f jours, seuil %d) — blocage géographique désactivé temporairement",
                age_days if age_days is not None else -1, self.max_db_age_days)

        ip = self.get_client_ip(request)

        # IP locales (tests internes, health checks) : toujours autorisées
        if ip in ('127.0.0.1', 'localhost') or ip.startswith('192.168.') or ip.startswith('10.'):
            return self.get_response(request)

        try:
            result = self.reader.country(ip)
            country_code = result.country.iso_code
        except geoip2.errors.AddressNotFoundError:
            # IP non répertoriée dans la base (rare) : on laisse passer plutôt que bloquer à tort
            return self.get_response(request)
        except Exception as e:
            logger.warning("Erreur lookup GeoIP pour %s : %s", ip, e)
            return self.get_response(request)

        if country_code not in settings.GEOBLOCK_ALLOWED_COUNTRIES:
            logger.info("Accès bloqué : IP %s (pays: %s)", ip, country_code)
            return HttpResponseForbidden("Accès refusé.")

        return self.get_response(request)
