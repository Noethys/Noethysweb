# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import requests, json, urllib.parse
from django.urls import reverse_lazy
from django.http import JsonResponse
from core.views import crud
from core.models import Collaborateur
from collaborateurs.forms.collaborateur_coords import Formulaire
from collaborateurs.views.collaborateur import Onglet


def Get_coords_gps(request):
    rue = request.POST.get("rue")
    cp = request.POST.get("cp")
    ville = request.POST.get("ville")
    try:
        adresse = "%s %s %s" % (rue, cp, ville)
        req = requests.get("https://api-adresse.data.gouv.fr/search/?q=" + urllib.parse.quote(adresse))
        resultat = json.loads(req.content.decode('unicode_escape'))
        coords = resultat["features"][0]["geometry"]["coordinates"]
        coords = {"lon": coords[0], "lat": coords[1]}
    except:
        return JsonResponse({"erreur": "Localisation introuvable"}, status=401)
    return JsonResponse({"coords": json.dumps(coords)})


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Coordonnées"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        context['onglet_actif'] = "coords"
        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez les coordonnées du collaborateur."
        return context

    def get_success_url(self):
        return reverse_lazy("collaborateur_coords", kwargs={'idcollaborateur': self.kwargs['idcollaborateur']})
