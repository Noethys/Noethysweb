# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging
logger = logging.getLogger(__name__)
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import TemplateView
from core.models import Activite
from parametrage.views.activites import Onglet
from parametrage.utils import utils_import_evenements as moteur

PERMISSION = "core.activites_liste"


def Get_activite(request, idactivite=None):
    """ Activité accessible par l'utilisateur (structures autorisées) """
    try:
        idactivite = int(idactivite)
    except (TypeError, ValueError):
        raise moteur.Erreur("L'activité n'est pas valide")
    activite = Activite.objects.filter(pk=idactivite, structure__in=request.user.structures.all()).first()
    if not activite:
        raise moteur.Erreur("Vous n'avez pas accès à cette activité")
    return activite


def Verifier_permission(fonction):
    """ Vérifie la permission puis transforme les erreurs du moteur en réponse JSON """
    def _fonction(request, *args, **kwargs):
        if not request.user.has_perm(PERMISSION):
            return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=401)
        try:
            return fonction(request, *args, **kwargs)
        except moteur.Erreur as err:
            return JsonResponse({"erreur": str(err)}, status=401)
    return _fonction


def Get_feuille(request, activite=None, parametres={}):
    """ Feuille du fichier mémorisé en session pour cet onglet et cette activité """
    donnees = moteur.Get_fichier_session(request.session, parametres.get("jeton"), activite.pk)
    try:
        return donnees, donnees["feuilles"][int(parametres.get("feuille", 0))]
    except (IndexError, TypeError, ValueError):
        raise moteur.Erreur("La feuille sélectionnée n'est pas valide")


def Get_parametres(request):
    try:
        return json.loads(request.POST.get("parametres", "{}"))
    except ValueError:
        raise moteur.Erreur("Les paramètres ne sont pas valides")


# ---------------------------------------- AJAX ----------------------------------------

@Verifier_permission
def Lire_fichier(request):
    """ Lecture du fichier envoyé et mémorisation en session """
    activite = Get_activite(request, request.POST.get("idactivite"))
    donnees = moteur.Lire_fichier(request.FILES.get("fichier"))
    jeton = moteur.Memoriser_fichier(request.session, activite.pk, donnees)
    return JsonResponse({"jeton": jeton, "nom_fichier": donnees["nom_fichier"], "feuilles": [moteur.Get_infos_feuille(feuille) for feuille in donnees["feuilles"]]})


@Verifier_permission
def Get_apercu(request):
    parametres = Get_parametres(request)
    activite = Get_activite(request, parametres.get("idactivite"))
    donnees, feuille = Get_feuille(request, activite, parametres)
    return JsonResponse(moteur.Get_apercu(activite, feuille, parametres))


@Verifier_permission
def Importer(request):
    parametres = Get_parametres(request)
    activite = Get_activite(request, parametres.get("idactivite"))
    donnees, feuille = Get_feuille(request, activite, parametres)
    resultat = moteur.Importer(activite, feuille, parametres, request=request, nom_fichier=donnees.get("nom_fichier", ""))
    moteur.Oublier_fichier(request.session, parametres.get("jeton"))
    return JsonResponse(resultat)


# ---------------------------------------- Pages ----------------------------------------

class View(Onglet, TemplateView):
    template_name = "parametrage/activite_evenements_import.html"

    def test_func_page(self):
        return Activite.objects.filter(pk=self.Get_idactivite(), structure__in=self.request.user.structures.all()).exists()

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["box_titre"] = "Importer des événements depuis un fichier Excel"
        context["onglet_actif"] = "evenements"
        context["box_conclusion"] = True  # Affiche le pied du cadre, qui contient la barre des boutons de l'assistant
        referentiel = moteur.Referentiel(context["activite"])
        context["unites"] = referentiel.unites
        context["groupes"] = referentiel.groupes
        context["categories"] = referentiel.categories
        context["champs"] = moteur.CHAMPS
        context["champs_json"] = json.dumps([{"code": champ["code"], "label": champ["label"], "obligatoire": champ.get("obligatoire", False)} for champ in moteur.CHAMPS])
        context["max_lignes"] = moteur.MAX_LIGNES
        return context


class Exemple(Onglet, TemplateView):
    """ Téléchargement du fichier XLSX exemple """

    def test_func_page(self):
        return Activite.objects.filter(pk=self.Get_idactivite(), structure__in=self.request.user.structures.all()).exists()

    def get(self, request, *args, **kwargs):
        activite = Activite.objects.filter(pk=self.Get_idactivite()).first()
        if not activite:
            raise Http404
        reponse = HttpResponse(moteur.Get_fichier_exemple(activite), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        reponse["Content-Disposition"] = 'attachment; filename="modele_import_evenements.xlsx"'
        return reponse
