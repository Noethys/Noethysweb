# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, re, json, shutil, uuid
from django.urls import reverse_lazy, reverse
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db.models import Q
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Individu
from individus.forms.importation_photos_selection import Formulaire as form_selection_individu
from core.forms.envoi_photos import Formulaire_envoi_photo, Get_contexte_zone_envoi
from individus.forms.importation_photos import Formulaire, Analyser_photo


def Importer_photos_individus(request):
    """ Reçoit une photo envoyée par la zone d'envoi et en extrait les visages """
    if request.method != "POST":
        return JsonResponse({"ok": False, "erreur": "Requête invalide"}, status=400)
    if not request.user.has_perm("core.importation_photos"):
        return JsonResponse({"ok": False, "erreur": "Vous n'avez pas l'autorisation d'importer des photos"}, status=403)
    try:
        uuid_lot = uuid.UUID(request.POST.get("lot", ""))
    except ValueError:
        return JsonResponse({"ok": False, "erreur": "Lot invalide"}, status=400)
    form = Formulaire_envoi_photo(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "erreur": form.Get_erreur()}, status=400)
    try:
        nbre_visages = Analyser_photo(fichier=form.cleaned_data["fichier"], uuid_lot=uuid_lot)
    except Exception:
        return JsonResponse({"ok": False, "erreur": "Analyse de la photo impossible"}, status=400)
    return JsonResponse({"ok": True, "nbre_visages": nbre_visages})


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
        context['box_introduction'] = "Importez des photos comportant un ou plusieurs individus (photo de groupe par exemple) : l'application détecte les visages, les découpe et vous propose de les associer aux fiches individuelles. Commencez par sélectionner la ou les photos à analyser et cliquez sur Analyser les photos."
        context['form'] = kwargs.get("form", Formulaire())
        context['form_selection_individu'] = form_selection_individu()

        # Zone d'envoi des photos : toutes les photos envoyées partagent le même lot
        uuid_lot = str(uuid.uuid4())
        context['zone_envoi'] = Get_contexte_zone_envoi(url=reverse("ajax_importer_photos_individus"), libelle_bouton="Analyser les photos",
                                                        url_fin=reverse("importation_photos", kwargs={"uuid_lot": uuid_lot}), extra={"lot": uuid_lot})

        # Lecture d'un lot de photos
        if "uuid_lot" in self.kwargs and "-" in self.kwargs["uuid_lot"]:
            try:
                rep = os.path.join(settings.MEDIA_ROOT, "temp", str(uuid.UUID(self.kwargs["uuid_lot"])))
            except ValueError:
                rep = None
            if rep and os.path.isdir(rep):
                context['liste_portraits'] = [os.path.join("temp", self.kwargs["uuid_lot"], str(fichier)) for fichier in os.listdir(rep)]
            else:
                context['liste_portraits'] = []
                messages.add_message(self.request, messages.ERROR, "Ce lot de photos est introuvable")

        return context

    def post(self, request, *args, **kwargs):
        # Validation du formulaire
        form = Formulaire(request.POST, request=self.request)
        validation = form.is_valid()

        # S'il manque le nom de fichier, on renvoie le form
        if not form.cleaned_data.get("data") and not validation:
            return self.render_to_response(self.get_context_data(form=form))

        # Vérification du lot
        try:
            uuid_lot = str(uuid.UUID(self.kwargs.get("uuid_lot", "")))
            data = json.loads(form.cleaned_data.get("data"))
        except (ValueError, TypeError):
            messages.add_message(request, messages.ERROR, "Données invalides")
            return HttpResponseRedirect(reverse_lazy("importation_photos"))
        rep_lot = os.path.join(settings.MEDIA_ROOT, "temp", uuid_lot)
        rep_individus = os.path.join(settings.MEDIA_ROOT, "individus")
        os.makedirs(rep_individus, exist_ok=True)

        # Enregistrement des photos
        nbre_photos = 0
        for dict_temp in data:
            # Le nom du portrait doit être celui généré lors de l'analyse : aucun autre chemin n'est accepté
            url = str(dict_temp.get("url", "")).replace("\\", "/")
            nom_portrait = url.rsplit("/", 1)[-1]
            if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg", nom_portrait) or \
                    url != "temp/%s/%s" % (uuid_lot, nom_portrait):
                continue
            image_origine = os.path.join(rep_lot, nom_portrait)
            if not os.path.isfile(image_origine):
                continue
            try:
                individu = Individu.objects.get(pk=int(dict_temp["idindividu"]))
            except (KeyError, ValueError, TypeError, Individu.DoesNotExist):
                continue
            # Envoi l'image vers le répertoire media/individus
            shutil.move(image_origine, os.path.join(rep_individus, nom_portrait))
            # Modifie l'image de la fiche individuelle
            individu.photo = "individus/%s" % nom_portrait
            individu.save()
            nbre_photos += 1

        # Suppression des portraits non attribués
        shutil.rmtree(rep_lot, ignore_errors=True)

        messages.add_message(request, messages.SUCCESS, "%d photos ont été importées avec succès" % nbre_photos)
        return HttpResponseRedirect(reverse_lazy("individus_toc"))
