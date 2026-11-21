# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json, logging, time
logger = logging.getLogger(__name__)
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Nettoyage
from outils.utils import nettoyeur
from outils.utils.nettoyeur import utils_alerte, utils_delais
from outils.utils.nettoyeur.base import CHOIX_DELAIS, Formate_taille

MOT_CONFIRMATION = "NETTOYER"


def secure_nettoyeur(function):
    """ Les fonctions du nettoyeur sont réservées aux superutilisateurs """
    def _function(request, *args, **kwargs):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        if not request.user.is_superuser or settings.MODE_DEMO:
            return HttpResponseForbidden()
        return function(request, *args, **kwargs)
    return _function


def Get_date_limite_post(request=None, operation=None):
    """ Lit et contrôle la date limite transmise. Renvoie (date, message_erreur) """
    if operation.delai_defaut is None:
        return None, None
    try:
        date_limite = datetime.datetime.strptime(request.POST.get("date_limite", ""), "%Y-%m-%d").date()
    except ValueError:
        return None, "La date limite de l'opération '%s' n'est pas valide" % operation.titre
    return date_limite, operation.Check_date_limite(date_limite)


@secure_nettoyeur
def Analyser(request):
    operation = nettoyeur.Get_operation(code=request.POST.get("code"))
    if not operation:
        return JsonResponse({"erreur": "Opération inconnue"}, status=401)
    date_limite, erreur = Get_date_limite_post(request, operation)
    if erreur:
        return JsonResponse({"erreur": erreur}, status=401)
    try:
        resultat = operation.Analyser(date_limite=date_limite)
    except Exception as err:
        logger.exception("Nettoyeur : erreur lors de l'analyse de l'opération %s" % operation.code)
        return JsonResponse({"erreur": "Erreur lors de l'analyse de l'opération '%s' : %s" % (operation.titre, err)}, status=401)
    return JsonResponse({"code": operation.code, "resultat": resultat.To_dict(), "suggestion": operation.Is_suggestion(resultat)})


@secure_nettoyeur
def Nettoyer(request):
    if request.POST.get("confirmation", "").strip().upper() != MOT_CONFIRMATION:
        return JsonResponse({"erreur": "Tapez %s pour confirmer le nettoyage" % MOT_CONFIRMATION}, status=401)
    operation = nettoyeur.Get_operation(code=request.POST.get("code"))
    if not operation:
        return JsonResponse({"erreur": "Opération inconnue"}, status=401)
    date_limite, erreur = Get_date_limite_post(request, operation)
    if erreur:
        return JsonResponse({"erreur": erreur}, status=401)
    try:
        exclusions = set([str(valeur) for valeur in json.loads(request.POST.get("exclusions", "[]"))])
        inclusions = json.loads(request.POST.get("inclusions", "null"))
    except ValueError:
        return JsonResponse({"erreur": "Sélection invalide"}, status=401)

    # Sécurité : seuls les éléments présentés à l'utilisateur lors de l'analyse peuvent être traités.
    # Les éléments apparus depuis (changement de jour, nouvelles données...) sont exclus.
    if inclusions is not None:
        inclusions = set([str(valeur) for valeur in inclusions])
        resultat_analyse = operation.Analyser(date_limite=date_limite)
        if resultat_analyse.elements is not None:
            exclusions.update(set([element.id for element in resultat_analyse.elements]) - inclusions)

    # Exécution
    debut = time.time()
    try:
        resultat = operation.Executer(date_limite=date_limite, exclusions=exclusions, request=request)
    except Exception as err:
        logger.exception("Nettoyeur : erreur lors de l'exécution de l'opération %s" % operation.code)
        return JsonResponse({"erreur": "Erreur lors de l'opération '%s' : %s" % (operation.titre, err)}, status=401)
    duree = time.time() - debut

    # Enregistrement dans le registre
    Nettoyage.objects.create(utilisateur=request.user, code=operation.code, titre=operation.titre, categorie=operation.categorie,
                             date_limite=date_limite, nbre_elements=resultat.nbre, nbre_echecs=resultat.nbre_echecs,
                             nbre_exclus=resultat.nbre_exclus, octets_liberes=resultat.octets, duree=round(duree, 2),
                             detail="\n".join(resultat.lignes_detail)[:20000] or None)
    utils_alerte.Reinitialiser()
    logger.debug("Nettoyeur : opération %s effectuée par %s (%d éléments, %d octets)" % (operation.code, request.user, resultat.nbre, resultat.octets))

    dict_resultat = resultat.To_dict()
    dict_resultat["duree"] = round(duree, 1)
    return JsonResponse({"code": operation.code, "resultat": dict_resultat})


@secure_nettoyeur
def Memoriser_delais(request):
    """ Enregistre les délais choisis pour toute l'instance. Les délais non valides sont ignorés. """
    try:
        delais_post = json.loads(request.POST.get("delais", "{}"))
    except ValueError:
        return JsonResponse({"erreur": "Délais invalides"}, status=401)
    if not isinstance(delais_post, dict):
        return JsonResponse({"erreur": "Délais invalides"}, status=401)
    delais, ignores = {}, []
    for operation in nettoyeur.Get_operations():
        if operation.code not in delais_post:
            continue
        delai = utils_delais.Valider_delai(operation, delais_post[operation.code])
        if delai:
            delais[operation.code] = delai
        else:
            ignores.append(operation.titre)
    utils_delais.Set_delais(delais)
    utils_alerte.Reinitialiser()
    return JsonResponse({"delais": delais, "ignores": ignores})


@secure_nettoyeur
def Get_alerte_accueil(request):
    """ Renvoie le HTML de l'encart de la page d'accueil (chargé en différé pour ne pas ralentir l'accueil) """
    alerte = utils_alerte.Get_alerte(request=request)
    if not alerte:
        return JsonResponse({"html": ""})
    return JsonResponse({"html": render_to_string("outils/nettoyeur_alerte_accueil.html", {"alerte": alerte, "octets_texte": Formate_taille(alerte["octets"])}, request=request)})


@secure_nettoyeur
def Masquer_alerte_accueil(request):
    utils_alerte.Masquer(request=request)
    return JsonResponse({"resultat": True})


class View(CustomView, TemplateView):
    template_name = "outils/nettoyeur.html"
    menu_code = "nettoyeur"
    compatible_demo = False

    def test_func_page(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Nettoyeur"
        context["box_titre"] = "Nettoyeur"
        # Délais mémorisés pour toute l'instance
        delais = utils_delais.Get_delais()
        categories = nettoyeur.Get_operations_par_categorie()
        for categorie in categories:
            for operation in categorie["operations"]:
                delai = utils_delais.Get_delai_operation(operation, delais) or {}
                operation.delai_mois = delai.get("mois")
                operation.delai_date = delai.get("date")
        context["categories"] = categories
        context["choix_delais"] = CHOIX_DELAIS
        context["date_jour"] = datetime.date.today()
        context["mot_confirmation"] = MOT_CONFIRMATION
        context["dernier_nettoyage"] = Nettoyage.objects.order_by("-horodatage").first()
        context["operations_json"] = json.dumps({operation.code: operation.To_dict() for operation in nettoyeur.Get_operations()})
        return context


# --------------------------------------------------------------------------------------------
# Registre des nettoyages
# --------------------------------------------------------------------------------------------

class Page(crud.Page):
    model = Nettoyage
    url_liste = "nettoyeur_registre"
    menu_code = "nettoyeur"
    description_liste = ("Registre des nettoyages effectués avec le Nettoyeur. Il permet de justifier de l'application de vos durées de conservation "
                         "des données personnelles (RGPD). Utilisez les boutons d'impression ou d'export pour en obtenir une copie PDF ou Excel.")
    objet_singulier = "un nettoyage"
    objet_pluriel = "des nettoyages"

    def test_func_page(self):
        return self.request.user.is_superuser


class Registre(Page, crud.Liste):
    model = Nettoyage

    def get_queryset(self):
        return Nettoyage.objects.select_related("utilisateur").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Registre, self).get_context_data(**kwargs)
        context["page_titre"] = "Nettoyeur"
        context["box_titre"] = "Registre des nettoyages"
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["afficher_menu_brothers"] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idnettoyage", "horodatage", "titre", "date_limite", "nbre_elements"]
        utilisateur = columns.TextColumn("Utilisateur", sources=["utilisateur__username"])
        octets = columns.TextColumn("Espace libéré", sources=["octets_liberes"], processor="Get_octets")
        date_limite = columns.TextColumn("Date limite", sources=["date_limite"], processor=helpers.format_date("%d/%m/%Y"))

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idnettoyage", "horodatage", "utilisateur", "titre", "date_limite", "nbre_elements", "nbre_echecs", "nbre_exclus", "octets", "detail"]
            ordering = ["-horodatage"]
            processors = {
                "horodatage": helpers.format_date("%d/%m/%Y %H:%M"),
            }

        def Get_octets(self, instance, *args, **kwargs):
            return Formate_taille(instance.octets_liberes) if instance.octets_liberes else ""
