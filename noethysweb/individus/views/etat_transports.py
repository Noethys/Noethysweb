# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from individus.forms.etat_transports import Formulaire

# Texte descriptif affiché sous la liste déroulante lorsque l'utilisateur sélectionne un état.
DESCRIPTIONS_ETATS = {
    "par_mode": "Regroupe les transports par mode (Car, Bus, Taxi, Pédibus, Train, Avion...).",
    "par_ligne": "Regroupe les transports par ligne (ex. Ligne A12, Ligne 4).",
    "par_arret": "Regroupe les transports par arrêt de prise en charge — pratique pour l'accompagnateur posté à un arrêt donné.",
    "par_ligne_arret": "Feuille de route hiérarchique : ligne → arrêts → individus, triés par heure.",
    "par_compagnie": "Regroupe les transports par prestataire (compagnie de transport).",
    "par_compagnie_ligne": "Détaille chaque compagnie puis ses lignes — pratique pour transmettre à un transporteur le détail de ses lignes du jour.",
    "par_activite": "Regroupe les transports par activité concernée (ALSH, périscolaire...). Un transport peut apparaître dans plusieurs groupes s'il concerne plusieurs activités.",
    "par_famille": "Regroupe les individus d'une même famille — utile pour le lien avec les parents.",
    "par_ecole": "Regroupe les transports par établissement scolaire d'origine (d'après la scolarité en cours à la date choisie).",
    "chrono_depart": "Liste unique triée par heure de départ, sans regroupement — feuille de route chronologique.",
    "chrono_arrivee": "Liste unique triée par heure d'arrivée — pour anticiper l'accueil des individus.",
    "par_sens": "Sépare les trajets du matin (Aller) et du soir (Retour), triés par heure à l'intérieur de chaque groupe.",
    "ponctuels": "N'affiche que les transports saisis avec une date précise (mode ponctuel).",
    "programmes": "N'affiche que les transports récurrents actifs à la date choisie (mode programmé).",
    "observations": "N'affiche que les transports ayant une observation renseignée (ex. PAI, transport médicalisé) — état de vigilance.",
    "anomalies_infos": "Repère les transports sans compagnie et/ou sans ligne renseignée, à corriger avant publication.",
    "statistique": "Tableau de synthèse chiffré (sans liste nominative) : compteurs par mode, par ligne et par compagnie.",
    "etiquettes": "Une vignette par individu/trajet (nom, ligne, arrêt, heures) — à découper ou coller sur un badge.",
    "aller_retour": "Une ligne par individu, avec le trajet Aller et le trajet Retour du jour côte à côte.",
    "par_transporteur": "Une section par compagnie avec ses coordonnées en en-tête — prête à être transmise au prestataire.",
    "par_lieu": "Regroupe par lieu (gare, aéroport, port) plutôt que par arrêt — pertinent pour les modes Train/Avion/Bateau.",
    "par_destination": "Regroupe les transports par point d'arrivée (symétrique de l'état « Par arrêt »).",
    "par_creneau": "Répartit les transports en trois créneaux : Matin (avant 12h), Après-midi (12h-17h), Soir (après 17h).",
    "par_duree": "Répartit les transports selon la durée du trajet : Court (< 15 min), Moyen (15-30 min), Long (> 30 min).",
    "chrono_global": "Tous les trajets (aller et retour confondus), triés chronologiquement, avec un bandeau de repère Matin/Après-midi/Soir.",
    "traca_prog": "Pour chaque transport ponctuel, indique la programmation dont il découle — utile pour repérer les exceptions au planning théorique.",
    "sans_transport": "Compare les présences prévues (réservations) aux transports trouvés, et signale les individus sans transport affecté ce jour.",
    "par_numero": "Regroupe par numéro de transport (n° de vol, de rotation, de car...) — surtout utile pour Train/Avion/Bateau.",
    "justif_jour": "Rappelle si la date est traitée comme un jour scolaire ou un jour de vacances, et les jours cochés appliqués pour chaque programmation.",
    "multi_trajets": "Une ligne par individu avec le détail de TOUS ses trajets du jour (au-delà d'un simple aller-retour).",
    "multi_activites": "N'affiche que les transports rattachés à plusieurs activités à la fois.",
    "emargement": "Format à imprimer avec des cases à cocher, pour un pointage manuel par l'accompagnateur au moment du trajet.",
    "ordre_arrets": "Pour chaque ligne, liste les individus dans l'ordre réel de passage du véhicule (d'après l'ordre paramétré des arrêts).",
    "pivot_ligne_creneau": "Tableau croisé : nombre d'individus par ligne et par créneau horaire.",
    "affichage_public": "Version simplifiée en grande police, pensée pour un affichage sur écran ou panneau à l'entrée.",
    "etiquettes_codebarres": "Comme les étiquettes nominatives, avec un code-barres par individu pour un pointage scanné.",
    "par_age": "Regroupe les individus par tranche d'âge — utile pour adapter l'encadrement du transport.",
    "prog_desactivees": "Recense les programmations désactivées qui, sans cette désactivation, se seraient appliquées à cette date.",
    "occupation_ligne": "Pour chaque ligne, liste chronologique des trajets et durée totale estimée d'occupation du véhicule.",
    "controle_presence": "Compare le transport prévu à la présence déclarée sur l'activité liée — signale les incohérences à vérifier avant le départ.",
}


def Generer_pdf(request):
    # Récupération et validation des paramètres saisis dans le formulaire
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        liste_erreurs = ["<b>%s</b> : %s" % (form.fields[nom_champ].label, erreur[0]) for nom_champ, erreur in form.errors.items()]
        return JsonResponse({"erreur": " - ".join(liste_erreurs) or "Veuillez compléter les paramètres"}, status=401)

    # Création du PDF
    from individus.utils import utils_impression_etat_transports
    impression = utils_impression_etat_transports.Impression(titre="Etat récapitulatif des transports", dict_donnees=form.cleaned_data)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    return JsonResponse({"nom_fichier": impression.Get_nom_fichier()})


class View(CustomView, TemplateView):
    menu_code = "etat_transports"
    template_name = "individus/etat_transports.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Etat récapitulatif des transports"
        context["box_titre"] = "Etat récapitulatif des transports"
        context["box_introduction"] = "Sélectionnez une date, un type d'état et les modes de transport souhaités, puis cliquez sur le bouton Générer le PDF."
        context["descriptions_etats"] = DESCRIPTIONS_ETATS
        if "form" not in kwargs:
            context["form"] = Formulaire(request=self.request)
        return context
