# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.http import JsonResponse, HttpResponse
from django.template import Template, RequestContext
from django.views.generic import TemplateView
from django.core.management import call_command
from core.views.base import CustomView
from core.utils import utils_gnupg
from dbbackup.storage import get_storage, utils


def Sauvegarder_db(request):
    """ Créer une sauvegarde de la base de données """
    utils_gnupg.Importation_cles()
    try:
        call_command("dbbackup", "--encrypt", "--clean", verbosity=1)
    except Exception as err:
        return JsonResponse({"erreur": str(err)}, status=401)
    return JsonResponse({"success": True})


def Sauvegarder_media(request):
    """ Créer une sauvegarde des medias """
    utils_gnupg.Importation_cles()
    try:
        call_command("mediabackup", "--encrypt", "--clean", verbosity=3)
    except Exception as err:
        return JsonResponse({"erreur": str(err)}, status=401)
    return JsonResponse({"success": True})


def Get_liste_sauvegardes(request):
    mode = request.POST.get("mode")
    storage = get_storage()
    liste_fichiers = [utils.filename_to_date(nom_fichier) for nom_fichier in storage.list_backups(content_type=mode)]
    html = """
        {% if fichiers %}
            <p>Dernières sauvegardes :</p>
            <ul>
                {% for nom_fichier in fichiers %}
                    <li><i class="fa fa-file-zip-o margin-r-5"></i>{{ nom_fichier|date:'d/m/Y H:i:s' }}</li>
                {% endfor %}
            </ul>
        {% else %}
            <p>Aucune sauvegarde</p>
        {% endif %}
    """
    context = {"fichiers": liste_fichiers}
    resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)


class View(CustomView, TemplateView):
    menu_code = "sauvegarde_creer"
    template_name = "outils/sauvegarde_creer.html"
    compatible_demo = False

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Sauvegarde"
        context['box_titre'] = "Créer une sauvegarde"
        context['box_introduction'] = "_"
        context['afficher_menu_brothers'] = True

        # Récupération de la liste des dernières sauvegardes
        storage = get_storage()
        context["fichiers_db"] = [utils.filename_to_date(nom_fichier) for nom_fichier in storage.list_backups(content_type="db")]
        context["fichiers_media"] = [utils.filename_to_date(nom_fichier) for nom_fichier in storage.list_backups(content_type="media")]
        return context
