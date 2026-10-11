# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Activite, Organisateur
from core.utils import utils_parametres, utils_preferences
from outils.forms.rapport_activite import Formulaire, CATEGORIE_PARAMETRES
from outils.utils.utils_rapport_activite import RUBRIQUES, Rapport, ETATS_LABELS

PERMISSION = "core.rapport_activite"
TAILLE_MAX_LOGO = 3 * 1024 * 1024


def Get_activites(request, selection={}):
    """ Renvoie (liste des activités, toutes_activites) en tenant compte des structures de l'utilisateur """
    activites = Activite.objects.filter(structure__in=request.user.structures.all())
    if selection.get("type") == "groupes_activites":
        activites = activites.filter(groupes_activites__in=selection.get("ids", []))
    elif selection.get("type") == "activites":
        activites = activites.filter(pk__in=selection.get("ids", []))
    activites = list(activites.distinct().order_by("nom"))
    # Les données financières ne sont prises en compte globalement que si l'utilisateur a accès à toutes les activités
    toutes = selection.get("type") == "toutes" and len(activites) == Activite.objects.count()
    return activites, toutes


def Get_logo(form, organisateur=None):
    """ Renvoie le contenu binaire du logo à intégrer ou None """
    source = form.cleaned_data.get("logo_source")
    try:
        if source == "personnalise" and form.cleaned_data.get("logo_fichier"):
            fichier = form.cleaned_data["logo_fichier"]
            if fichier.size <= TAILLE_MAX_LOGO:
                return fichier.read()
        if source == "organisateur" and organisateur and organisateur.logo:
            with organisateur.logo.open("rb") as fichier:
                return fichier.read()
    except Exception:
        logger.exception("Rapport d'activité : impossible de lire le logo")
    return None


def Generer_pdf(request):
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=401)

    form = Formulaire(request.POST, request.FILES, request=request)
    if not form.is_valid():
        erreurs = ["%s : %s" % (form.fields[champ].label if champ in form.fields else champ, " ".join(messages)) for champ, messages in form.errors.items()]
        return JsonResponse({"erreur": "Veuillez vérifier les paramètres. " + " ".join(erreurs)}, status=401)
    donnees = form.cleaned_data

    # Période
    date_debut, date_fin, label_n, label_n1 = form.Get_periode()
    if date_fin < date_debut:
        return JsonResponse({"erreur": "La date de fin doit être postérieure à la date de début"}, status=401)
    if (date_fin - date_debut).days > 366 * 5:
        return JsonResponse({"erreur": "La période ne peut pas dépasser 5 ans"}, status=401)

    # Activités
    activites, toutes_activites = Get_activites(request, json.loads(donnees["activites"]))
    if not activites:
        return JsonResponse({"erreur": "Aucune activité ne correspond à la sélection"}, status=401)

    # Mémorisation des réglages
    if donnees.get("memoriser"):
        utils_parametres.Set_categorie(categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, parametres=form.Get_parametres_a_memoriser())

    # Calcul des données
    symbole = utils_preferences.Get_symbole_monnaie()
    rapport = Rapport(date_debut=date_debut, date_fin=date_fin, activites=activites, toutes_activites=toutes_activites, etats=donnees["etats"],
                      rubriques=donnees["rubriques"], comparer=donnees["comparer"], annexes=donnees["annexes"], analyses=donnees["analyses"],
                      tranches_qf=donnees["tranches_qf"], label_periode=label_n, label_periode_n1=label_n1, symbole_monnaie=symbole)
    rubriques = rapport.Generer()

    # Textes
    organisateur = Organisateur.objects.filter(pk=1).first()
    nom_organisateur = organisateur.nom if organisateur and organisateur.nom else ""
    titre = donnees["titre"] or ("Rapport d'activité %s" % label_n if label_n[0].isdigit() else "Rapport d'activité")
    texte_periode = "Période du %s au %s" % (date_debut.strftime("%d/%m/%Y"), date_fin.strftime("%d/%m/%Y"))
    texte_comparaison = "Comparaison avec la période du %s au %s" % (rapport.p1.strftime("%d/%m/%Y"), rapport.p2.strftime("%d/%m/%Y")) if donnees["comparer"] else ""
    if toutes_activites or len(activites) > 8:
        texte_activites = "Activités : %s" % ("toutes les activités" if toutes_activites else "%d activités sélectionnées" % len(activites))
    else:
        texte_activites = "Activités : %s" % ", ".join(activite.nom for activite in activites)
    texte_activites += " · Consommations : %s" % ", ".join(ETATS_LABELS.get(etat, etat).lower() for etat in donnees["etats"])

    # Création du PDF
    from outils.utils import utils_impression_rapport_activite
    options = utils_impression_rapport_activite.Options(
        titre=titre, sous_titre=donnees["sous_titre"], introduction=donnees["introduction"], pied_page=donnees["pied_page"],
        organisateur=nom_organisateur, auteur=request.user.get_full_name() or request.user.username,
        couleur_principale=donnees["couleur_principale"], couleur_comparaison=donnees["couleur_comparaison"],
        police=donnees["police"], taille=donnees["taille"], style_garde=donnees["style_garde"], logo=Get_logo(form, organisateur),
        sommaire=donnees["sommaire"], numeros_page=donnees["numeros_page"], valeurs_graphiques=donnees["valeurs_graphiques"],
        periode=texte_periode, periode_comparaison=texte_comparaison, activites=texte_activites, symbole=symbole)
    impression = utils_impression_rapport_activite.Impression(rubriques=rubriques, options=options)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    return JsonResponse({"nom_fichier": impression.Get_nom_fichier()})


class View(CustomView, TemplateView):
    menu_code = "rapport_activite"
    template_name = "outils/rapport_activite.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Rapport d'activité"
        context["form"] = kwargs.get("form", Formulaire(request=self.request))
        rubriques_cochees = context["form"]["rubriques"].value() or []
        context["rubriques"] = [{"code": code, "titre": titre, "description": description, "coche": code in rubriques_cochees} for code, titre, description in RUBRIQUES]
        return context
