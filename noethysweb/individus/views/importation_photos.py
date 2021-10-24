# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.models import Individu
from django.shortcuts import render
from individus.forms.importation_photos_selection import Formulaire as form_selection_individu
from individus.forms.importation_photos import Formulaire
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db.models import Q
import os, json, uuid, shutil


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
        context['box_titre'] = "Sélection d'une photo"
        context['box_introduction'] = "Vous pouvez ici importer une photo comportant un ou plusieurs individus. L'application va détecter les visages, les découper et les envoyer vers les fiches individuelles. Commencez par sélectionner la photo à analyser et cliquez sur le bouton Analyser."
        context['form'] = kwargs.get("form", Formulaire())
        context['form_selection_individu'] = form_selection_individu()
        return context

    def post(self, request, *args, **kwargs):
        # Validation du formulaire
        form = Formulaire(request.POST, request.FILES, request=self.request)
        validation = form.is_valid()

        # S'il manque le nom de fichier, on renvoie le form
        if not form.cleaned_data.get("data") and not validation:
            return self.render_to_response(self.get_context_data(form=form))

        # Si le form est valide, on renvoie les résultats
        if validation:
            context = self.get_context_data(**kwargs)
            context["form"] = form
            context["resultats"] = self.Get_resultats(photo=form.cleaned_data.get("photo"))
            return render(request, self.template_name, context)

        # Enregistrement des photos
        data = json.loads(form.cleaned_data.get("data"))
        for dict_temp in data:
            # Envoi l'image vers le répertoire media/individus
            image_origine = os.path.join(settings.MEDIA_ROOT, dict_temp["url"])
            url_destination = dict_temp["url"].replace("temp/", "individus/")
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

    def Get_resultats(self, photo):
        import cv2
        import numpy as np
        from PIL import Image

        # Recherche l'algorithme de détection
        face_detector = None
        try:
            face_detector = "{base_path}/data/haarcascade_frontalface_default.xml".format(base_path=cv2.__path__[0])
        except:
            pass
        if not face_detector:
            face_detector = "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml"

        # Charge l'algorithme de détection
        detector = cv2.CascadeClassifier(face_detector)

        # Charge l'image
        image = np.asarray(bytearray(photo.file.read()), dtype="uint8")
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        image_nb = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image_couleur = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(image_couleur)

        # Création du répertoire temp
        if not os.path.exists(os.path.join(settings.MEDIA_ROOT, "temp")):
            os.makedirs(os.path.join(settings.MEDIA_ROOT, "temp"))

        # Analyse l'image
        dict_resultats = {"image_originale": None, "portraits": []}
        rects = detector.detectMultiScale(image_nb, scaleFactor=1.1, minNeighbors=5)
        for (x, y, w, h) in rects:
            # Découpe chaque portrait
            img = image_pil.crop((x, y, x + w, y + h))
            nom_fichier = "temp/%s.jpg" % uuid.uuid4()
            img.save(os.path.join(settings.MEDIA_ROOT, nom_fichier))
            dict_resultats["portraits"].append(nom_fichier)

            # Tracé du cadre rouge sur la photo originale
            cv2.rectangle(image_couleur, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Dessin de l'image originale
        image_pil = Image.fromarray(image_couleur)
        nom_fichier = "temp/%s.jpg" % uuid.uuid4()
        dict_resultats["image_originale"] = nom_fichier
        image_pil.save(os.path.join(settings.MEDIA_ROOT, nom_fichier))

        return dict_resultats
