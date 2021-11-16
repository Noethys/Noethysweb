# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, json, shutil
from django.urls import reverse_lazy
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db.models import Q
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Individu
from individus.forms.importation_photos_selection import Formulaire as form_selection_individu
from individus.forms.importation_photos import Formulaire, Formulaire_importation


def Importer_photos_individus(request):
    assert request.method == 'POST'
    assert request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    form = Formulaire_importation(request.POST, request.FILES)
    if form.is_valid():
        uuid_lot = form.form_valid(request)
        url = reverse_lazy("importation_photos", kwargs={"uuid_lot": uuid_lot})
        return JsonResponse({'action': 'redirect', 'url': url})
    else:
        return JsonResponse({'action': 'replace', 'html': form.as_html(request)})


def Get_individus(request):
    """ Renvoie une liste d'individus pour le Select2 """
    recherche = request.GET.get("term", "")
    liste_individus = []
    for individu in Individu.objects.all().filter(Q(nom__icontains=recherche) | Q(prenom__icontains=recherche)).order_by("nom", "prenom"):
        liste_individus.append({"id": individu.pk, "text": individu.Get_nom() })
    return JsonResponse({"results": liste_individus, "pagination": {"more": True}})


class View(CustomView, TemplateView):
    menu_code = "importation_photos"
    template_name = "individus/importation_photos.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Importer des photos individuelles"
        context['box_titre'] = "Sélection des photos"
        context['box_introduction'] = "Vous pouvez ici importer des photos comportant un ou plusieurs individus. L'application va détecter les visages, les découper et les envoyer vers les fiches individuelles. Commencez par sélectionner la ou les photos à analyser et cliquez sur Envoyer."
        context['form'] = kwargs.get("form", Formulaire())
        context['form_selection_individu'] = form_selection_individu()
        context['formulaire_upload'] = Formulaire_importation()
        context['formulaire_upload_as_html'] = context['formulaire_upload'].as_html(self.request)

        # Lecture d'un lot de photos
        if "uuid_lot" in self.kwargs and "-" in self.kwargs["uuid_lot"]:
            rep = os.path.join(settings.MEDIA_ROOT, "temp", self.kwargs["uuid_lot"])
            context['liste_portraits'] = [os.path.join("temp", self.kwargs["uuid_lot"], str(fichier)) for fichier in os.listdir(rep)]

        return context

    def post(self, request, *args, **kwargs):
        # Validation du formulaire
        form = Formulaire(request.POST, request=self.request)
        validation = form.is_valid()

        # S'il manque le nom de fichier, on renvoie le form
        if not form.cleaned_data.get("data") and not validation:
            return self.render_to_response(self.get_context_data(form=form))

        # Enregistrement des photos
        data = json.loads(form.cleaned_data.get("data"))
        for dict_temp in data:
            # Envoi l'image vers le répertoire media/individus
            image_origine = os.path.join(settings.MEDIA_ROOT, dict_temp["url"])
            url_destination = dict_temp["url"].replace("temp/%s" % self.kwargs["uuid_lot"], "individus/")
            if not os.path.isdir(os.path.join(settings.MEDIA_ROOT, "individus")):
                os.mkdir(os.path.join(settings.MEDIA_ROOT, "individus"))
            image_destination = os.path.join(settings.MEDIA_ROOT, url_destination)
            shutil.move(image_origine, image_destination, url_destination)
            # Modifie l'image de la fiche individuelle
            individu = Individu.objects.get(pk=int(dict_temp["idindividu"]))
            individu.photo = url_destination
            individu.save()

        messages.add_message(request, messages.SUCCESS, "%d photos ont été importées avec succès" % len(data))
        return HttpResponseRedirect(reverse_lazy("individus_toc"))
