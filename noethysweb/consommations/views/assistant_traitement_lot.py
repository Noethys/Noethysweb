# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging, os, uuid
logger = logging.getLogger(__name__)
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from consommations.forms.assistant_traitement_lot import Formulaire_activite
from consommations.utils import utils_assistant_traitement_lot as moteur
from individus.utils.utils_inscriptions_assistant_lot import Get_listes_scolarite

PERMISSION = "core.assistant_traitement_lot"
ERREUR_PERMISSION = "Vous n'avez pas la permission d'accéder à cette fonctionnalité"


def Verifier_permission(fonction):
    """ Vérifie la permission puis transforme les erreurs du moteur en réponse JSON """
    def _fonction(request, *args, **kwargs):
        if not request.user.has_perm(PERMISSION):
            return JsonResponse({"erreur": ERREUR_PERMISSION}, status=401)
        try:
            return fonction(request, *args, **kwargs)
        except moteur.Erreur as err:
            return JsonResponse({"erreur": str(err)}, status=401)
    return _fonction


# ---------------------------------------- AJAX ----------------------------------------

@Verifier_permission
def Get_infos_activite(request):
    activite = moteur.Get_activite(request.POST.get("idactivite"), request)
    return JsonResponse({"activite": moteur.Get_infos_activite(activite)})


@Verifier_permission
def Get_calendrier(request):
    """ Dates retenues et calendrier de l'étape Période, plus les événements des dates retenues """
    p = moteur.Lire_parametres(request.POST.get("parametres"))
    activite = moteur.Get_activite(p.get("idactivite"), request)
    resultat = moteur.Calculer_dates(activite, p.get("periode") or {})
    unites_evenements = [unite["id"] for unite in moteur.Get_infos_activite(activite)["unites"] if unite["type"] == "Evenement"]
    return JsonResponse({
        "dates": [str(date) for date in resultat["dates"]],
        "jours": resultat["jours"],
        "feries_exclus": [moteur.Date_fr(date) for date in resultat["feries_exclus"]],
        "fermes_exclus": [moteur.Date_fr(date) for date in resultat["fermes_exclus"]],
        "evenements": moteur.Get_evenements(activite, resultat["dates"], unites_evenements),
    })


@Verifier_permission
def Compter(request):
    return JsonResponse(moteur.Compter(request.POST.get("parametres"), request))


@Verifier_permission
def Rechercher(request):
    activite = moteur.Get_activite(request.POST.get("idactivite"), request)
    return JsonResponse({"resultats": moteur.Rechercher_inscrits(activite, request.POST.get("texte", ""))})


@Verifier_permission
def Simuler(request):
    simulation = moteur.Simulation(request.POST.get("parametres"), request)
    return JsonResponse(simulation.Get_resultats())


@Verifier_permission
def Appliquer(request):
    return JsonResponse(moteur.Appliquer_paquet(request.POST.get("parametres"), request.POST.get("inscriptions"), request.POST.get("premier") == "true", request))


@Verifier_permission
def Annuler(request):
    return JsonResponse(moteur.Annuler_paquet(request))


@Verifier_permission
def Exporter_excel(request):
    """ Export du compte rendu au format Excel """
    try:
        compte_rendu = json.loads(request.POST.get("compte_rendu", "{}"))
        lignes = compte_rendu.get("lignes", [])
        statuts = compte_rendu.get("statuts", {})
    except (ValueError, AttributeError):
        return JsonResponse({"erreur": "Le compte rendu n'est pas valide"}, status=401)

    rep_temp = os.path.join("temp", str(uuid.uuid4()))
    rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
    os.makedirs(rep_destination, exist_ok=True)
    nom_fichier = "traitement_par_lot.xlsx"

    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    feuille = classeur.add_worksheet("Compte rendu")
    format_titre = classeur.add_format({"bold": True, "font_size": 14})
    format_entete = classeur.add_format({"bold": True, "bg_color": "#efefef", "border": 1})
    format_cellule = classeur.add_format({"border": 1})
    feuille.write_string(0, 0, str(compte_rendu.get("titre", moteur.LIBELLE_FONCTION))[:250], format_titre)
    codes = [code for code in moteur.STATUTS if any(ligne.get("compteurs", {}).get(code) for ligne in lignes)]
    entetes = ["Individu"] + [str(statuts.get(code, moteur.STATUTS[code])) for code in codes]
    for colonne, titre in enumerate(entetes):
        feuille.write_string(2, colonne, titre, format_entete)
        feuille.set_column(colonne, colonne, 34 if colonne == 0 else 18)
    for index, ligne in enumerate(lignes):
        feuille.write_string(3 + index, 0, str(ligne.get("nom", ""))[:200], format_cellule)
        for colonne, code in enumerate(codes):
            valeur = ligne.get("compteurs", {}).get(code, 0)
            feuille.write_number(3 + index, colonne + 1, int(valeur) if str(valeur).isdigit() else 0, format_cellule)
    feuille.autofilter(2, 0, 2 + len(lignes), len(entetes) - 1)
    classeur.close()
    return JsonResponse({"nom_fichier": os.path.join(settings.MEDIA_URL, rep_temp, nom_fichier)})


# ---------------------------------------- Vue ----------------------------------------

class View(CustomView, TemplateView):
    menu_code = "assistant_traitement_lot"
    template_name = "consommations/assistant_traitement_lot.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = moteur.LIBELLE_FONCTION
        context["form_activite"] = Formulaire_activite(request=self.request)
        context["config"] = {
            "taille_paquet": moteur.TAILLE_PAQUET,
            "statuts": moteur.STATUTS,
            "scolarite": Get_listes_scolarite(),
        }
        lot = self.request.session.get(moteur.CLE_SESSION)
        context["lot_precedent"] = bool(lot and lot.get("action") == "ajouter" and lot.get("consommations"))
        return context
