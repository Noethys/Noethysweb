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
from core.models import Activite
from individus.forms.inscriptions_assistant_lot import Formulaire_activite
from individus.utils import utils_inscriptions_assistant_lot as moteur

PERMISSION = "core.inscriptions_assistant_lot"
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
    """ Résumé de l'activité de destination et, si demandé, de l'activité d'origine avec les correspondances """
    activite = moteur.Get_activite(request.POST.get("idactivite"), request)
    resultat = {"activite": moteur.Get_infos_activite(activite)}
    if request.POST.get("idsource"):
        activite_source = moteur.Get_activite(request.POST.get("idsource"), request, nom="l'activité d'origine")
        resultat["source"] = moteur.Get_infos_source(activite_source, activite)
    return JsonResponse(resultat)


@Verifier_permission
def Compter(request):
    """ Compteur de l'étape Individus """
    recherche = moteur.Recherche(request.POST.get("parametres"), request)
    return JsonResponse(recherche.Get_compteurs())


@Verifier_permission
def Get_apercu(request):
    """ Liste des individus à inscrire avec le groupe et la catégorie proposés """
    return JsonResponse(moteur.Get_apercu(request.POST.get("parametres"), request))


@Verifier_permission
def Rechercher_individus(request):
    return JsonResponse({"resultats": moteur.Rechercher_individus(request.POST.get("texte", ""))})


@Verifier_permission
def Get_villes(request):
    return JsonResponse({"villes": moteur.Get_villes()})


@Verifier_permission
def Generer(request):
    resultat = moteur.Generer(request.POST.get("parametres"), request.POST.get("lignes"), request)
    logger.debug("Assistant inscriptions par lot : %d inscriptions créées." % resultat["nbre"])
    return JsonResponse(resultat)


@Verifier_permission
def Annuler(request):
    return JsonResponse(moteur.Annuler_lot(request))


@Verifier_permission
def Exporter_excel(request):
    """ Export du compte rendu au format Excel """
    try:
        compte_rendu = json.loads(request.POST.get("compte_rendu", "{}"))
        lignes = compte_rendu.get("lignes", [])
    except (ValueError, AttributeError):
        return JsonResponse({"erreur": "Le compte rendu n'est pas valide"}, status=401)

    rep_temp = os.path.join("temp", str(uuid.uuid4()))
    rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
    os.makedirs(rep_destination, exist_ok=True)
    nom_fichier = "inscriptions_par_lot.xlsx"

    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    feuille = classeur.add_worksheet("Inscriptions")
    format_titre = classeur.add_format({"bold": True, "font_size": 14})
    format_entete = classeur.add_format({"bold": True, "bg_color": "#efefef", "border": 1})
    format_cellule = classeur.add_format({"border": 1})
    feuille.write(0, 0, "Inscriptions créées : %s" % str(compte_rendu.get("activite", {}).get("nom", ""))[:200], format_titre)
    feuille.write(1, 0, "À partir du %s" % str(compte_rendu.get("date_debut", ""))[:20])
    for colonne, (titre, largeur) in enumerate((("Individu", 34), ("Groupe", 24), ("Catégorie de tarif", 24), ("Statut", 24))):
        feuille.write(3, colonne, titre, format_entete)
        feuille.set_column(colonne, colonne, largeur)
    for index, ligne in enumerate(lignes):
        for colonne, cle in enumerate(("nom", "groupe", "categorie", "statut")):
            feuille.write_string(4 + index, colonne, str(ligne.get(cle, ""))[:300], format_cellule)
    feuille.autofilter(3, 0, 3 + len(lignes), 3)
    classeur.close()
    return JsonResponse({"nom_fichier": os.path.join(settings.MEDIA_URL, rep_temp, nom_fichier)})


# ---------------------------------------- Vue ----------------------------------------

class View(CustomView, TemplateView):
    menu_code = "inscriptions_assistant_lot"
    template_name = "individus/inscriptions_assistant_lot.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = moteur.LIBELLE_FONCTION
        context["form_activite"] = Formulaire_activite(request=self.request)
        activites = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom")
        context["activites_source"] = [(activite.pk, activite.nom, activite.Is_active()) for activite in activites]
        context["config"] = {
            "profils": moteur.PROFILS,
            "scolarite": moteur.Get_listes_scolarite(),
            "nbre_max_apercu": moteur.NBRE_MAX_APERCU,
        }
        lot = self.request.session.get(moteur.CLE_SESSION)
        context["lot_precedent"] = bool(lot and lot.get("inscriptions"))
        return context
