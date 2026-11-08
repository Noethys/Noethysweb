# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, decimal, base64, io, os, uuid, statistics
logger = logging.getLogger(__name__)
from django.conf import settings
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Location, Produit, Prestation, Ventilation
from core.utils import utils_dates
from core.utils.utils_impression import Impression
from locations.forms.statistiques_locations import Formulaire

PERMISSION = "core.statistiques_locations"
MOIS_ABREGES = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
JOURS_SEMAINE = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")
TRANCHES_DUREES = ((None, 4, "≤ 4 h"), (4, 24, "4 h à 1 jour"), (24, 72, "1 à 3 jours"), (72, 168, "3 à 7 jours"), (168, None, "> 7 jours"))
NBRE_CATEGORIES_AFFICHEES = 6
NBRE_PRODUITS_AFFICHES = 10
ZERO = decimal.Decimal(0)


# ---------------------------------------- Utilitaires ----------------------------------------

def Format_montant(valeur, decimales=2):
    return "{:,.{}f} €".format(float(valeur or 0), decimales).replace(",", " ").replace(".", ",")


def Format_nombre(valeur, decimales=0):
    return "{:,.{}f}".format(float(valeur or 0), decimales).replace(",", " ").replace(".", ",")


def Format_duree(heures):
    """ Durée lisible : en heures sous 24 h, en jours au-delà """
    if heures is None:
        return "-"
    if heures < 24:
        return "%s h" % Format_nombre(heures, 1 if heures < 10 and heures != int(heures) else 0)
    return "%s j" % Format_nombre(heures / 24.0, 1)


def Pourcentage(valeur, total, decimales=0):
    if not total:
        return None
    valeur = 100.0 * float(valeur) / float(total)
    return round(valeur, decimales) if decimales else round(valeur)


def Get_liste_mois(date_debut=None, date_fin=None):
    liste_mois, annee, mois = [], date_debut.year, date_debut.month
    while (annee, mois) <= (date_fin.year, date_fin.month):
        liste_mois.append((annee, mois))
        mois += 1
        if mois > 12:
            annee, mois = annee + 1, 1
    return liste_mois


def Get_tranche_duree(heures):
    for index, (mini, maxi, label) in enumerate(TRANCHES_DUREES):
        if (mini is None or heures > mini) and (maxi is None or heures <= maxi):
            return index
    return len(TRANCHES_DUREES) - 1


def Regrouper(liste=[], nbre_max=6, label_autres="Autres"):
    """ Conserve les nbre_max premiers éléments (label, valeur) et regroupe les suivants """
    liste = sorted(liste, key=lambda x: -x[1])
    resultat = {"labels": [label for label, valeur in liste[:nbre_max]], "valeurs": [valeur for label, valeur in liste[:nbre_max]]}
    if len(liste) > nbre_max:
        resultat["labels"].append(label_autres)
        resultat["valeurs"].append(sum([valeur for label, valeur in liste[nbre_max:]]))
    return resultat


def Get_locations(parametres={}, date_debut=None, date_fin=None):
    """ Locations des catégories sélectionnées qui se déroulent au moins en partie sur la période """
    debut = datetime.datetime.combine(date_debut, datetime.time.min)
    fin = datetime.datetime.combine(date_fin, datetime.time.max)
    return Location.objects.filter(Q(date_fin__gte=debut) | Q(date_fin__isnull=True), date_debut__isnull=False, date_debut__lte=fin,
                                   produit__categorie__in=parametres["categories_produits"])


def Get_jours_location(date_debut_location, date_fin_location, date_debut, date_fin):
    """ Premier et dernier jour occupés par la location sur la période (None si aucun) """
    premier = max(date_debut_location.date(), date_debut)
    if date_fin_location is None:
        dernier = date_fin  # Location sans date de fin : en cours jusqu'à la fin de la période
    elif date_fin_location.time() == datetime.time.min and date_fin_location > date_debut_location:
        dernier = date_fin_location.date() - datetime.timedelta(days=1)  # Fin à minuit : le dernier jour est la veille
    else:
        dernier = date_fin_location.date()
    dernier = min(dernier, date_fin)
    return (premier, dernier) if premier <= dernier else None


def Compter_par_mois(liste_jours=[], liste_mois=[]):
    """ Nombre de locations en cours dans chaque mois """
    compteur = {mois: 0 for mois in liste_mois}
    for premier, dernier in liste_jours:
        for mois in Get_liste_mois(premier, dernier):
            if mois in compteur:
                compteur[mois] += 1
    return [compteur[mois] for mois in liste_mois]


# ---------------------------------------- Calculs ----------------------------------------

def Get_data(parametres={}):
    date_debut, date_fin = [utils_dates.ConvertDateENGtoDate(x) for x in parametres["periode"].split(";")]
    comparer = parametres.get("comparer", False)
    maintenant = datetime.datetime.now()
    aujourdhui = maintenant.date()
    nbre_jours_periode = (date_fin - date_debut).days + 1

    # Période précédente de même durée et comparaison à date équivalente si la période est en cours
    duree = date_fin - date_debut
    fin_precedente = date_debut - datetime.timedelta(days=1)
    debut_precedente = fin_precedente - duree
    en_cours = date_debut <= aujourdhui < date_fin
    date_equivalente = aujourdhui - (date_debut - debut_precedente) if en_cours else fin_precedente

    data = {
        "comparer": comparer, "en_cours": en_cours,
        "date_debut_str": utils_dates.ConvertDateToFR(date_debut), "date_fin_str": utils_dates.ConvertDateToFR(date_fin),
        "periode_str": "%s - %s" % (utils_dates.ConvertDateToFR(date_debut), utils_dates.ConvertDateToFR(date_fin)),
        "categories": ", ".join(sorted([categorie.nom for categorie in parametres["categories_produits"]])),
    }

    locations = list(Get_locations(parametres, date_debut, date_fin).values_list("pk", "famille_id", "produit_id", "date_debut", "date_fin", "quantite"))
    data["nbre_locations"] = len(locations)
    data["nbre_familles"] = len({idfamille for idlocation, idfamille, idproduit, debut, fin, quantite in locations})
    data["locations_par_famille"] = Format_nombre(data["nbre_locations"] / data["nbre_familles"], 1) if data["nbre_familles"] else "0"

    # ------------------- Évolution du nombre de locations -------------------
    locations_precedentes = list(Get_locations(parametres, debut_precedente, fin_precedente).values_list("date_debut", "date_fin"))
    if en_cours:
        limite, limite_precedente = datetime.datetime.combine(aujourdhui, datetime.time.max), datetime.datetime.combine(date_equivalente, datetime.time.max)
        nbre_comparable = len([1 for location in locations if location[3] <= limite])
        nbre_precedent = len([1 for debut, fin in locations_precedentes if debut <= limite_precedente])
    else:
        nbre_comparable, nbre_precedent = data["nbre_locations"], len(locations_precedentes)
    data["evolution_locations"] = Pourcentage(nbre_comparable - nbre_precedent, nbre_precedent) if nbre_precedent else None

    # ------------------- Produits des catégories sélectionnées -------------------
    produits = {produit.pk: {"produit": produit.nom, "categorie": produit.categorie.nom, "capacite": max(produit.quantite or 1, 1),
                             "nbre": 0, "familles": set(), "jours": {}, "durees": [], "montant": ZERO, "regle": ZERO}
                for produit in Produit.objects.select_related("categorie").filter(categorie__in=parametres["categories_produits"])}

    # ------------------- Parcours unique des locations -------------------
    liste_jours, liste_durees = [], []
    categories, jours_semaine = {}, [0] * 7
    graphe_durees = {"labels": [label for mini, maxi, label in TRANCHES_DUREES], "valeurs": [0] * len(TRANCHES_DUREES)}
    for idlocation, idfamille, idproduit, debut, fin, quantite in locations:
        produit = produits[idproduit]
        produit["nbre"] += 1
        produit["familles"].add(idfamille)
        categories[produit["categorie"]] = categories.get(produit["categorie"], 0) + 1
        jours_semaine[debut.weekday()] += 1

        # Durée de la location (si une date de fin est saisie)
        if fin and fin > debut:
            heures = (fin - debut).total_seconds() / 3600.0
            liste_durees.append(heures)
            produit["durees"].append(heures)
            graphe_durees["valeurs"][Get_tranche_duree(heures)] += 1

        # Jours occupés sur la période (quantité louée par jour, plafonnée ensuite à la quantité du produit)
        jours = Get_jours_location(debut, fin, date_debut, date_fin)
        if jours:
            liste_jours.append(jours)
            jour = jours[0]
            while jour <= jours[1]:
                produit["jours"][jour] = produit["jours"].get(jour, 0) + max(quantite or 1, 1)
                jour += datetime.timedelta(days=1)

    # ------------------- Taux d'occupation (jours occupés) -------------------
    total_occupe, total_disponible = 0, 0
    for produit in produits.values():
        produit["jours_occupes"] = sum([min(quantite, produit["capacite"]) for quantite in produit["jours"].values()])  # Jours × unités louées
        produit["jours_loues"] = len(produit["jours"])  # Jours où au moins une unité du produit est louée
        produit["jours_disponibles"] = produit["capacite"] * nbre_jours_periode
        produit["taux_occupation"] = Pourcentage(produit["jours_occupes"], produit["jours_disponibles"])
        total_occupe += produit["jours_occupes"]
        total_disponible += produit["jours_disponibles"]
    data["jours_occupes"] = total_occupe
    data["nbre_produits_loues"] = len([produit for produit in produits.values() if produit["nbre"]])
    data["nbre_produits"] = len(produits)
    data["taux_occupation"] = Pourcentage(total_occupe, total_disponible) if total_disponible else None
    data["duree_moyenne"] = Format_duree(statistics.mean(liste_durees)) if liste_durees else "-"
    data["duree_mediane"] = Format_duree(statistics.median(liste_durees)) if liste_durees else "-"

    # ------------------- Montants facturés (prestations rattachées aux locations) -------------------
    liste_idlocations = [location[0] for location in locations]
    prestations = Prestation.objects.filter(location_id__in=liste_idlocations)
    regle_prestations = {idprestation: total for idprestation, total in Ventilation.objects.filter(prestation__in=prestations).values_list("prestation_id").annotate(total=Sum("montant"))}
    data["montant"], data["regle"] = ZERO, ZERO
    locations_avec_prestation, non_facturees = set(), {"nbre": 0, "montant": ZERO}
    for idprestation, idlocation, idproduit, montant, idfacture in prestations.values_list("pk", "location_id", "location__produit_id", "montant", "facture_id"):
        montant = montant or ZERO
        regle = regle_prestations.get(idprestation, ZERO)
        data["montant"] += montant
        data["regle"] += regle
        locations_avec_prestation.add(idlocation)
        if idproduit in produits:
            produits[idproduit]["montant"] += montant
            produits[idproduit]["regle"] += regle
        if not idfacture:
            non_facturees["nbre"] += 1
            non_facturees["montant"] += montant
    data["restant"] = max(data["montant"] - data["regle"], ZERO)
    data["taux_regle"] = Pourcentage(data["regle"], data["montant"]) if data["montant"] > 0 else None

    # ------------------- Suivi administratif -------------------
    en_cours_aujourdhui = Location.objects.filter(Q(date_fin__gte=maintenant) | Q(date_fin__isnull=True), date_debut__lte=maintenant,
                                                  produit__categorie__in=parametres["categories_produits"]).count()
    data["suivi"] = {
        "en_cours": en_cours_aujourdhui,
        "sans_prestation": len(set(liste_idlocations) - locations_avec_prestation),
        "non_facturees": non_facturees["nbre"],
        "montant_non_facture": Format_montant(non_facturees["montant"]),
        "restant": Format_montant(data["restant"]),
    }

    # ------------------- Graphiques -------------------
    liste_mois = Get_liste_mois(date_debut, date_fin)
    afficher_annee = len(liste_mois) > 12
    labels_mois = [("%s %s" % (MOIS_ABREGES[m - 1], str(a)[2:])) if afficher_annee else MOIS_ABREGES[m - 1] for a, m in liste_mois]
    graphe_mois = {"labels": labels_mois, "valeurs": Compter_par_mois(liste_jours, liste_mois), "valeurs_precedentes": []}
    if comparer:
        jours_precedents = [jours for jours in [Get_jours_location(debut, fin, debut_precedente, fin_precedente) for debut, fin in locations_precedentes] if jours]
        graphe_mois["valeurs_precedentes"] = Compter_par_mois(jours_precedents, Get_liste_mois(debut_precedente, fin_precedente))[:len(liste_mois)]

    graphe_categories = Regrouper([(nom, nbre) for nom, nbre in categories.items()], NBRE_CATEGORIES_AFFICHEES)
    produits_loues = [produit for produit in produits.values() if produit["nbre"]]
    produits_tries = sorted(produits_loues, key=lambda p: (-(p["taux_occupation"] or 0), p["produit"]))[:NBRE_PRODUITS_AFFICHES]
    graphe_occupation = {"labels": [p["produit"] for p in produits_tries], "valeurs": [p["taux_occupation"] or 0 for p in produits_tries]}
    graphe_jours = {"labels": list(JOURS_SEMAINE), "valeurs": jours_semaine}

    # ------------------- Détail par produit (tous les produits des catégories, même non loués) -------------------
    data["lignes"] = sorted(produits.values(), key=lambda p: (p["categorie"], p["produit"]))
    for ligne in data["lignes"]:
        ligne["familles"] = len(ligne["familles"])
        ligne["nbre_str"], ligne["familles_str"] = Format_nombre(ligne["nbre"]), Format_nombre(ligne["familles"])
        ligne["jours_loues_str"] = Format_nombre(ligne["jours_loues"])
        ligne["duree_moyenne"] = Format_duree(statistics.mean(ligne["durees"])) if ligne["durees"] else "-"
        ligne["montant_str"], ligne["regle_str"] = Format_montant(ligne["montant"]), Format_montant(ligne["regle"])
        del ligne["jours"], ligne["durees"]

    # Valeurs formatées
    for key in ("montant", "regle", "restant"):
        data["%s_str" % key] = Format_montant(data[key])
    data["nbre_locations_str"] = Format_nombre(data["nbre_locations"])
    data["nbre_familles_str"] = Format_nombre(data["nbre_familles"])
    data["graphes"] = {"mois": graphe_mois, "categories": graphe_categories, "occupation": graphe_occupation,
                       "jours": graphe_jours, "durees": graphe_durees}
    return data


# ---------------------------------------- Exports ----------------------------------------

def Get_parametres(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return None
    return form.cleaned_data


def Exporter_excel(request):
    """ Export des statistiques au format Excel """
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=401)
    parametres = Get_parametres(request)
    if not parametres:
        return JsonResponse({"erreur": "Les paramètres saisis ne sont pas valides"}, status=401)
    data = Get_data(parametres)

    rep_temp = os.path.join("temp", str(uuid.uuid4()))
    rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
    os.makedirs(rep_destination, exist_ok=True)
    nom_fichier = "statistiques_locations.xlsx"

    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    format_titre = classeur.add_format({"bold": True, "font_size": 14})
    format_entete = classeur.add_format({"bold": True, "bg_color": "#efefef", "border": 1})
    format_euros = classeur.add_format({"num_format": "#,##0.00 €"})

    def Ecrire_tableau(feuille, ligne, colonnes, lignes, formats={}):
        for num_colonne, label in enumerate(colonnes):
            feuille.write(ligne, num_colonne, label, format_entete)
        for valeurs in lignes:
            ligne += 1
            for num_colonne, valeur in enumerate(valeurs):
                feuille.write(ligne, num_colonne, valeur, formats.get(num_colonne))
        return ligne + 2

    def Ou_vide(valeur):
        return valeur if valeur is not None else ""

    # Indicateurs
    feuille = classeur.add_worksheet("Indicateurs")
    feuille.set_column(0, 0, 46)
    feuille.set_column(1, 1, 20)
    feuille.write(0, 0, "Statistiques des locations", format_titre)
    feuille.write(1, 0, "Période : %s" % data["periode_str"])
    feuille.write(2, 0, "Catégories de produits : %s" % data["categories"])
    lignes = [
        ("Nombre de locations", data["nbre_locations"], None),
        ("Évolution par rapport à la période précédente (%)", Ou_vide(data["evolution_locations"]), None),
        ("Familles locataires", data["nbre_familles"], None),
        ("Produits loués", "%d sur %d" % (data["nbre_produits_loues"], data["nbre_produits"]), None),
        ("Taux d'occupation (%)", Ou_vide(data["taux_occupation"]), None),
        ("Durée moyenne d'une location", data["duree_moyenne"], None),
        ("Durée médiane d'une location", data["duree_mediane"], None),
        ("Montant facturé", float(data["montant"]), format_euros),
        ("Montant réglé", float(data["regle"]), format_euros),
        ("Restant dû", float(data["restant"]), format_euros),
        ("Locations en cours aujourd'hui", data["suivi"]["en_cours"], None),
        ("Locations sans prestation", data["suivi"]["sans_prestation"], None),
        ("Prestations non facturées", data["suivi"]["non_facturees"], None),
    ]
    for num_colonne, label in enumerate(("Indicateur", "Valeur")):
        feuille.write(4, num_colonne, label, format_entete)
    for index, (label, valeur, format_cellule) in enumerate(lignes):
        feuille.write(5 + index, 0, label)
        feuille.write(5 + index, 1, valeur, format_cellule)

    # Détail par produit
    feuille = classeur.add_worksheet("Détail par produit")
    for num_colonne, largeur in enumerate((30, 24, 12, 11, 14, 16, 16, 14, 14)):
        feuille.set_column(num_colonne, num_colonne, largeur)
    Ecrire_tableau(feuille, 0, ("Produit", "Catégorie", "Locations", "Familles", "Jours loués", "Taux d'occupation (%)", "Durée moyenne", "Facturé", "Réglé"),
                   [(l["produit"], l["categorie"], l["nbre"], l["familles"], l["jours_loues"], Ou_vide(l["taux_occupation"]), l["duree_moyenne"],
                     float(l["montant"]), float(l["regle"])) for l in data["lignes"]],
                   formats={7: format_euros, 8: format_euros})

    graphes = data["graphes"]
    feuille = classeur.add_worksheet("Par mois")
    feuille.set_column(0, 2, 20)
    lignes = []
    for index, label in enumerate(graphes["mois"]["labels"]):
        precedentes = graphes["mois"]["valeurs_precedentes"]
        lignes.append((label, graphes["mois"]["valeurs"][index], precedentes[index] if index < len(precedentes) else ""))
    Ecrire_tableau(feuille, 0, ("Mois", "Locations en cours", "Période précédente"), lignes)

    feuille = classeur.add_worksheet("Par catégorie")
    feuille.set_column(0, 1, 26)
    Ecrire_tableau(feuille, 0, ("Catégorie de produits", "Locations"), zip(graphes["categories"]["labels"], graphes["categories"]["valeurs"]))

    feuille = classeur.add_worksheet("Jours et durées")
    feuille.set_column(0, 4, 18)
    Ecrire_tableau(feuille, 0, ("Jour de début", "Locations"), zip(graphes["jours"]["labels"], graphes["jours"]["valeurs"]))
    Ecrire_tableau(feuille, 9, ("Durée", "Locations"), zip(graphes["durees"]["labels"], graphes["durees"]["valeurs"]))

    classeur.close()
    return JsonResponse({"nom_fichier": os.path.join(rep_temp, nom_fichier)})


def Generer_pdf(request):
    """ Export des statistiques au format PDF (avec les graphiques envoyés par la page) """
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=401)
    parametres = Get_parametres(request)
    if not parametres:
        return JsonResponse({"erreur": "Les paramètres saisis ne sont pas valides"}, status=401)
    data = Get_data(parametres)

    images = {}
    for nom in ("mois", "categories", "occupation", "jours", "durees"):
        valeur = request.POST.get("graphique_%s" % nom, "")
        if valeur.startswith("data:image/png;base64,") and len(valeur) < 5000000:
            try:
                images[nom] = base64.b64decode(valeur.split(",", 1)[1])
            except Exception:
                logger.warning("Image du graphique '%s' invalide" % nom)

    impression = Impression_statistiques(titre="Statistiques des locations", dict_donnees={"data": data, "images": images}, request=request)
    return JsonResponse({"nom_fichier": impression.Get_nom_fichier()})


class Impression_statistiques(Impression):
    def Draw(self):
        from reportlab.platypus import Table, TableStyle, Spacer, Paragraph, Image, KeepTogether
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib import colors
        from core.utils import utils_polices

        data = self.dict_donnees["data"]
        images = self.dict_donnees["images"]
        largeur = self.taille_page[0] - 75
        self.doc.leftMargin = self.doc.rightMargin = (self.taille_page[0] - largeur) / 2.0
        bleu, gris = colors.HexColor("#3c8dbc"), colors.HexColor("#dee2e6")
        style_titre = ParagraphStyle("titre", fontName=utils_polices.FONT_BOLD, fontSize=11, textColor=bleu, spaceBefore=4, spaceAfter=4)
        style_texte = ParagraphStyle("texte", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=10)

        self.Insert_header(detail="Période : %s" % data["periode_str"])
        self.story.append(Paragraph("<b>Catégories de produits :</b> %s" % data["categories"], style_texte))
        self.story.append(Spacer(0, 6))

        evolution = ""
        if data["comparer"] and data["evolution_locations"] is not None:
            evolution = " (%s%s %%)" % ("+" if data["evolution_locations"] >= 0 else "", data["evolution_locations"])
        indicateurs = [
            ("Locations", "%s%s" % (data["nbre_locations_str"], evolution)),
            ("Familles locataires", "%s (%s locations par famille)" % (data["nbre_familles_str"], data["locations_par_famille"])),
            ("Taux d'occupation", "%s - %d produits loués sur %d, durée moyenne %s" % ("%s %%" % data["taux_occupation"] if data["taux_occupation"] is not None else "-",
                                                                                      data["nbre_produits_loues"], data["nbre_produits"], data["duree_moyenne"])),
            ("Montant facturé", "%s (%s réglé)" % (data["montant_str"], "%s %%" % data["taux_regle"] if data["taux_regle"] is not None else "-")),
        ]
        suivi = [
            ("Locations en cours aujourd'hui", Format_nombre(data["suivi"]["en_cours"])),
            ("Locations sans prestation", Format_nombre(data["suivi"]["sans_prestation"])),
            ("Prestations non facturées", Format_nombre(data["suivi"]["non_facturees"])),
            ("Restant dû", data["suivi"]["restant"]),
        ]
        lignes = [(Paragraph("<b>%s</b>" % label, style_texte), Paragraph(valeur, style_texte), "", label_suivi, valeur_suivi)
                  for (label, valeur), (label_suivi, valeur_suivi) in zip(indicateurs, suivi)]
        lignes.insert(0, (Paragraph("Indicateurs clés", style_titre), "", "", Paragraph("Suivi administratif", style_titre), ""))
        tableau = Table(lignes, [95, largeur * 0.6 - 95, 12, largeur * 0.4 - 72, 60])
        tableau.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)), ("SPAN", (3, 0), (4, 0)),
            ("FONT", (3, 1), (3, -1), utils_polices.FONT_NORMAL, 8), ("FONT", (4, 1), (4, -1), utils_polices.FONT_BOLD, 8),
            ("ALIGN", (4, 1), (4, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 1), (1, -1), 0.25, gris), ("LINEBELOW", (3, 1), (4, -1), 0.25, gris),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ]))
        self.story.append(tableau)
        self.story.append(Spacer(0, 6))

        titres = {"mois": "Locations en cours par mois", "categories": "Répartition par catégorie de produits", "occupation": "Taux d'occupation par produit",
                  "jours": "Jour de début des locations", "durees": "Durée des locations"}
        largeur_image = (largeur - 10) / 2
        for paire in (("mois", "categories"), ("occupation", "jours"), ("durees",)):
            cellules = []
            for nom in paire:
                contenu = [Paragraph(titres[nom], style_titre)]
                if nom in images:
                    image = Image(io.BytesIO(images[nom]))
                    ratio = image.imageHeight / float(image.imageWidth)
                    hauteur = min(largeur_image * ratio, 150)
                    image.drawWidth, image.drawHeight = hauteur / ratio, hauteur
                    contenu.append(image)
                else:
                    contenu.append(Paragraph("Graphique non disponible", style_texte))
                cellules.append(contenu)
            if len(cellules) == 1:
                cellules.append("")
            tableau = Table([cellules], [largeur_image + 5, largeur_image + 5])
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            self.story.append(tableau)

        lignes = [("Produit", "Catégorie", "Loc.", "Familles", "Jours loués", "Occupation", "Durée moy.", "Facturé", "Réglé")]
        for ligne in data["lignes"]:
            lignes.append((Paragraph(ligne["produit"], style_texte), Paragraph(ligne["categorie"], style_texte), ligne["nbre_str"], ligne["familles_str"],
                           ligne["jours_loues_str"], "%s %%" % ligne["taux_occupation"] if ligne["taux_occupation"] is not None else "-",
                           ligne["duree_moyenne"], ligne["montant_str"], ligne["regle_str"]))
        lignes.append(("Total", "", data["nbre_locations_str"], data["nbre_familles_str"], "",
                       "%s %%" % data["taux_occupation"] if data["taux_occupation"] is not None else "-", data["duree_moyenne"], data["montant_str"], data["regle_str"]))
        proportions = (0.2, 0.15, 0.07, 0.08, 0.09, 0.1, 0.1, 0.11, 0.1)
        tableau = Table(lignes, [largeur * p for p in proportions], repeatRows=1)
        tableau.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7.5), ("FONT", (0, 0), (-1, 0), utils_polices.FONT_BOLD, 7.5),
            ("FONT", (0, -1), (-1, -1), utils_polices.FONT_BOLD, 7.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8f9fa")), ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, gris), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        self.story.append(KeepTogether([Paragraph("Détail par produit", style_titre), tableau]))


# ---------------------------------------- Vue ----------------------------------------

class View(CustomView, TemplateView):
    menu_code = "statistiques_locations"
    template_name = "locations/statistiques_locations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Statistiques des locations"
        if "form_parametres" not in kwargs:
            context["form_parametres"] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        return self.render_to_response(self.get_context_data(form_parametres=form, data=Get_data(form.cleaned_data)))
