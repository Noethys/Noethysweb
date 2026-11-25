# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, os, uuid
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Collaborateur
from collaborateurs.utils import utils_encadrement
from collaborateurs.utils.utils_affectations import Arbre
from collaborateurs.utils.utils_accueil import Ids_visibles

PERMISSION = "core.encadrement_collaborateurs"
JOURS = ("Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim")
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")
LIBELLES_ETATS = {"ko": "Dépassement", "al": "Alerte", "ok": "Conforme"}


def Get_periode(request):
    """ Période demandée : semaine (du lundi au dimanche) ou mois contenant la date de référence """
    try:
        reference = datetime.datetime.strptime(request.POST.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        reference = datetime.date.today()
    if request.POST.get("mode") == "mois":
        date_debut = reference.replace(day=1)
        date_fin = (date_debut + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
        libelle = "%s %d" % (MOIS[date_debut.month - 1].capitalize(), date_debut.year)
    else:
        date_debut = reference - datetime.timedelta(days=reference.weekday())
        date_fin = date_debut + datetime.timedelta(days=6)
        libelle = "Semaine du %d %s au %d %s %d" % (date_debut.day, MOIS[date_debut.month - 1], date_fin.day, MOIS[date_fin.month - 1], date_fin.year)
    return date_debut, date_fin, libelle


def Get_idaffectation(request):
    valeur = request.POST.get("idaffectation", "")
    return int(valeur) if valeur.isdigit() else None


def Libelle_jour(date=None):
    return "%s %d" % (JOURS[date.weekday()], date.day)


def Calculer(request):
    date_debut, date_fin, libelle = Get_periode(request)
    resultats = utils_encadrement.Calculer(date_debut, date_fin, Get_idaffectation(request))
    resultats["libelle"] = libelle
    # Colonnes : uniquement les jours qui ont des consommations (les jours de fermeture sont masqués)
    resultats["colonnes"] = [date for date in resultats["dates"] if date in resultats["dates_avec_donnees"]]
    return resultats


def Get_donnees(request):
    """ Synthèse de la période pour la page """
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=403)
    resultats = Calculer(request)
    lignes = []
    for ligne in resultats["lignes"]:
        affectation = ligne["affectation"]
        lignes.append({
            "id": affectation.pk, "nom": affectation.nom, "niveau": ligne["niveau"], "seuil": ligne["seuil"],
            "cellules": {str(date): cellule for date, cellule in ligne["cellules"].items()},
        })
    return JsonResponse({
        "libelle": resultats["libelle"], "date_debut": str(resultats["date_debut"]), "date_fin": str(resultats["date_fin"]),
        "colonnes": [{"date": str(date), "libelle": Libelle_jour(date)} for date in resultats["colonnes"]],
        "lignes": lignes, "kpi": resultats["kpi"],
    })


def Get_detail(request):
    """ Collaborateurs planifiés sur une affectation pour une date (noms limités aux collaborateurs visibles par l'utilisateur) """
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=403)
    try:
        date = datetime.datetime.strptime(request.POST.get("date_detail", ""), "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"erreur": "Date non valide"}, status=400)
    arbre = Arbre()
    idaffectation = Get_idaffectation(request)
    if idaffectation not in arbre.affectations:
        return JsonResponse({"erreur": "Affectation inconnue"}, status=400)
    _, plages = utils_encadrement.Charger_collaborateurs(date, date)
    par_collaborateur = utils_encadrement.Get_collaborateurs_jour(plages, arbre, idaffectation, date)
    visibles = Ids_visibles(request.user)
    collaborateurs = []
    for collaborateur in Collaborateur.objects.filter(pk__in=[pk for pk in par_collaborateur if pk in visibles]).order_by("nom", "prenom"):
        liste = par_collaborateur[collaborateur.pk]
        collaborateurs.append({
            "nom": collaborateur.Get_nom(),
            "horaires": ", ".join("%s-%s" % (utils_encadrement.Format_heure(debut), utils_encadrement.Format_heure(fin)) for debut, fin, idaff in liste),
            "affectations": sorted({arbre.affectations[idaff].nom for debut, fin, idaff in liste if idaff != idaffectation and idaff in arbre.affectations}),
        })
    return JsonResponse({
        "collaborateurs": collaborateurs, "autres": len([pk for pk in par_collaborateur if pk not in visibles]),
        "url_planning": "%s?date=%s" % (reverse("planning_equipe"), date),
    })


def Exporter_excel(request):
    """ Export de la synthèse et du détail heure par heure au format Excel """
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=403)
    resultats = Calculer(request)

    rep_temp = os.path.join("temp", str(uuid.uuid4()))
    rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
    os.makedirs(rep_destination, exist_ok=True)
    nom_fichier = "taux_encadrement.xlsx"

    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    format_titre = classeur.add_format({"bold": True, "font_size": 14})
    format_entete = classeur.add_format({"bold": True, "bg_color": "#efefef", "border": 1, "align": "center"})
    format_groupe = classeur.add_format({"bold": True, "border": 1})
    format_nom = classeur.add_format({"border": 1})
    formats_etats = {
        "ko": classeur.add_format({"bg_color": "#f8d7da", "font_color": "#721c24", "border": 1, "align": "center"}),
        "al": classeur.add_format({"bg_color": "#fff3cd", "font_color": "#856404", "border": 1, "align": "center"}),
        "ok": classeur.add_format({"bg_color": "#d4edda", "font_color": "#155724", "border": 1, "align": "center"}),
        None: classeur.add_format({"font_color": "#999999", "border": 1, "align": "center"}),
    }

    def Texte_cellule(cellule):
        taux = utils_encadrement.Format_taux(cellule["taux"])
        return "%s (%s)" % (taux, "manque %d" % cellule["manque"] if cellule["manque"] else "pire à %dh" % cellule["heure"])

    # Synthèse
    feuille = classeur.add_worksheet("Synthèse")
    feuille.write(0, 0, "Taux d'encadrement", format_titre)
    feuille.write(1, 0, resultats["libelle"])
    kpi = resultats["kpi"]
    feuille.write(2, 0, "Dépassements : %d - Alertes : %d - Conformes : %d - Renforts manquants : %d" % (kpi["ko"], kpi["al"], kpi["ok"], kpi["manque"]))
    feuille.set_column(0, 0, 40)
    feuille.set_column(1, len(resultats["colonnes"]), 22)
    feuille.write(4, 0, "Affectation", format_entete)
    for num_colonne, date in enumerate(resultats["colonnes"], 1):
        feuille.write(4, num_colonne, date.strftime("%d/%m/%Y"), format_entete)
    num_ligne = 5
    for ligne in resultats["lignes"]:
        nom = "    " * ligne["niveau"] + ligne["affectation"].nom + (" (max 1 pour %d)" % ligne["seuil"] if ligne["seuil"] else "")
        feuille.write(num_ligne, 0, nom, format_nom if ligne["seuil"] else format_groupe)
        for num_colonne, date in enumerate(resultats["colonnes"], 1):
            cellule = ligne["cellules"].get(date)
            if ligne["seuil"]:
                feuille.write(num_ligne, num_colonne, Texte_cellule(cellule) if cellule else "-", formats_etats[cellule["etat"] if cellule else None])
        num_ligne += 1

    # Détail heure par heure
    feuille = classeur.add_worksheet("Détail horaire")
    entetes = ("Affectation", "Date", "Heure", "Individus", "Collaborateurs", "Taux maximal", "Capacité", "Taux", "Manque", "Etat")
    for num_colonne, entete in enumerate(entetes):
        feuille.write(0, num_colonne, entete, format_entete)
    feuille.set_column(0, 0, 40)
    feuille.set_column(1, len(entetes) - 1, 13)
    num_ligne = 1
    for ligne in resultats["lignes"]:
        for date in resultats["colonnes"]:
            cellule = ligne["cellules"].get(date)
            if not cellule:
                continue
            for heure in cellule["heures"]:
                taux = utils_encadrement.Format_taux(heure["e"] / heure["c"] if heure["c"] else None) if heure["e"] else "-"
                valeurs = (ligne["affectation"].nom, date.strftime("%d/%m/%Y"), "%dh" % heure["h"], heure["e"], heure["c"], ligne["seuil"],
                           heure["cap"], taux, heure["manque"], LIBELLES_ETATS.get(heure["etat"], ""))
                for num_colonne, valeur in enumerate(valeurs):
                    feuille.write(num_ligne, num_colonne, valeur, formats_etats[heure["etat"]] if num_colonne == len(valeurs) - 1 else None)
                num_ligne += 1
    classeur.close()
    return JsonResponse({"nom_fichier": os.path.join(rep_temp, nom_fichier)})


class View(CustomView, TemplateView):
    menu_code = "encadrement_collaborateurs"
    template_name = "collaborateurs/encadrement.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Taux d'encadrement"
        lignes = utils_encadrement.Get_lignes(Arbre())
        context["affectations"] = [{"id": ligne["affectation"].pk, "nom": ligne["affectation"].nom, "prefixe": "\u00a0" * 4 * ligne["niveau"]} for ligne in lignes]
        context["aujourdhui"] = str(datetime.date.today())
        return context
