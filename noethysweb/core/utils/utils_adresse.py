# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import requests
from django.core.cache import cache
from core.models import Organisateur


def Get_gps_organisateur(organisateur=None):
    # Récupération de l'organisateur s'il n'est pas déjà donné
    if not organisateur:
        organisateur = cache.get("organisateur")
        if not organisateur:
            organisateur = Organisateur.objects.filter(pk=1).first()
            cache.set("organisateur", organisateur)

    # Récupération des coordonnées déjà enregistrées
    if organisateur and organisateur.gps:
        lon, lat = organisateur.gps.split(";")
        return {"lon": lon, "lat": lat}

    # Récupération et enregistrement des coordonnées auprès de api adresse
    if organisateur and organisateur.cp and organisateur.ville:
        q = "%s %s" % (organisateur.cp, organisateur.ville)
        r = requests.get("http://api-adresse.data.gouv.fr/search/", params={"q": q, "limit": 1, "autocomplete": 0, "type": "municipality"})
        r.raise_for_status()
        for feature in r.json().get("features"):
            lon, lat = feature.get("geometry").get("coordinates")
            organisateur.gps = "%s;%s" % (lon, lat)
            organisateur.save()
            return {"lon": str(lon), "lat": str(lat)}

    return None


def Get_gps_ville(cp=None, ville=None):
    # Récupération de coordonnées GPS à partir d'un CP et d'une ville
    if cp and ville:
        q = "%s %s" % (cp, ville)
        r = requests.get("http://api-adresse.data.gouv.fr/search/", params={"q": q, "limit": 1, "autocomplete": 0, "type": "municipality"})
        r.raise_for_status()
        for feature in r.json().get("features"):
            lon, lat = feature.get("geometry").get("coordinates")
            return {"lon": str(lon), "lat": str(lat)}
    return None
