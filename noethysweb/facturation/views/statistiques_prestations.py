# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, decimal, base64, io, os, uuid, json, statistics
logger = logging.getLogger(__name__)
from django.conf import settings
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Activite, Prestation, Ventilation, Deduction, Facture, Quotient
from core.utils import utils_dates
from core.utils.utils_impression import Impression
from facturation.forms.statistiques_prestations import Formulaire

PERMISSION = "core.statistiques_prestations"
MOIS_ABREGES = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
LIBELLES_CATEGORIES = dict(Prestation.categorie_choix)
TRANCHES_FAMILLES = ((0, 50, "< 50 €"), (50, 100, "50-100 €"), (100, 250, "100-250 €"), (250, 500, "250-500 €"),
                     (500, 1000, "500-1 000 €"), (1000, 2000, "1 000-2 000 €"), (2000, None, "> 2 000 €"))
TRANCHES_QUOTIENTS = ((0, 400, "0-400"), (400, 600, "401-600"), (600, 800, "601-800"), (800, 1000, "801-1 000"),
                      (1000, 1200, "1 001-1 200"), (1200, 1500, "1 201-1 500"), (1500, None, "> 1 500"))
NBRE_ACTIVITES_AFFICHEES = 8
ZERO = decimal.Decimal(0)


# ---------------------------------------- Utilitaires ----------------------------------------

def Format_montant(valeur, decimales=2):
    return "{:,.{}f} €".format(float(valeur or 0), decimales).replace(",", " ").replace(".", ",")


def Format_nombre(valeur, decimales=0):
    return "{:,.{}f}".format(float(valeur or 0), decimales).replace(",", " ").replace(".", ",")


def Pourcentage(valeur, total, decimales=0):
    if not total:
        return None
    valeur = 100.0 * float(valeur) / float(total)
    return round(valeur, decimales) if decimales else round(valeur)


def Get_tranche(valeur, tranches):
    """ Index de la tranche (bornes basses exclues sauf pour la première) """
    for index, (mini, maxi, label) in enumerate(tranches):
        if (maxi is None or valeur <= maxi) and (valeur > mini or index == 0):
            return index
    return len(tranches) - 1


def Get_liste_mois(date_debut=None, date_fin=None):
    liste_mois, annee, mois = [], date_debut.year, date_debut.month
    while (annee, mois) <= (date_fin.year, date_fin.month):
        liste_mois.append((annee, mois))
        mois += 1
        if mois > 12:
            annee, mois = annee + 1, 1
    return liste_mois


def Get_prestations(parametres={}, date_debut=None, date_fin=None):
    """ Prestations de la période selon les catégories et les activités sélectionnées """
    prestations = Prestation.objects.filter(date__gte=date_debut, date__lte=date_fin, categorie__in=parametres["categories"])
    selection = json.loads(parametres["activites"])
    if selection["type"] == "toutes":
        # Toutes les activités des structures de l'utilisateur, ainsi que les prestations sans activité
        return prestations.filter(Q(activite__isnull=True) | Q(activite__structure__in=parametres["structures"]))
    if selection["type"] == "groupes_activites":
        activites = Activite.objects.filter(groupes_activites__in=selection["ids"])
    else:
        activites = Activite.objects.filter(pk__in=selection["ids"])
    return prestations.filter(activite__in=activites)


def Montant(queryset):
    return queryset.aggregate(total=Sum("montant"))["total"] or ZERO


# ---------------------------------------- Calculs ----------------------------------------

def Get_data(parametres={}):
    date_debut, date_fin = [utils_dates.ConvertDateENGtoDate(x) for x in parametres["periode"].split(";")]
    comparer = parametres.get("comparer", False)
    aujourdhui = datetime.date.today()
    selection = json.loads(parametres["activites"])

    # Période précédente de même durée et comparaison à date équivalente si la période est en cours
    duree = date_fin - date_debut
    fin_precedente = date_debut - datetime.timedelta(days=1)
    debut_precedente = fin_precedente - duree
    en_cours = date_debut <= aujourdhui < date_fin
    date_equivalente = aujourdhui - (date_debut - debut_precedente) if en_cours else fin_precedente

    if selection["type"] == "toutes":
        texte_activites = "Toutes les activités"
    elif selection["type"] == "groupes_activites":
        from core.models import TypeGroupeActivite
        texte_activites = "Groupes d'activités : %s" % ", ".join(sorted(TypeGroupeActivite.objects.filter(pk__in=selection["ids"]).values_list("nom", flat=True)))
    else:
        texte_activites = ", ".join(sorted(Activite.objects.filter(pk__in=selection["ids"]).values_list("nom", flat=True)))

    data = {
        "comparer": comparer, "en_cours": en_cours,
        "date_debut_str": utils_dates.ConvertDateToFR(date_debut), "date_fin_str": utils_dates.ConvertDateToFR(date_fin),
        "periode_str": "%s - %s" % (utils_dates.ConvertDateToFR(date_debut), utils_dates.ConvertDateToFR(date_fin)),
        "periode_precedente_str": "%s - %s" % (utils_dates.ConvertDateToFR(debut_precedente), utils_dates.ConvertDateToFR(fin_precedente)),
        "date_equivalente_str": utils_dates.ConvertDateToFR(date_equivalente),
        "activites": texte_activites,
        "categories": ", ".join([LIBELLES_CATEGORIES[code] for code in parametres["categories"]]),
        "type_quotient": parametres["type_quotient"].nom if parametres.get("type_quotient") else "Tous les types",
    }

    prestations = Get_prestations(parametres, date_debut, date_fin)
    prestations_precedentes = Get_prestations(parametres, debut_precedente, fin_precedente)

    # ------------------- Montant et évolution -------------------
    totaux = prestations.aggregate(montant=Sum("montant"), montant_initial=Sum("montant_initial"), nbre=Count("pk"), familles=Count("famille_id", distinct=True))
    data["montant"] = totaux["montant"] or ZERO
    data["montant_initial"] = totaux["montant_initial"] or ZERO
    data["nbre_prestations"] = totaux["nbre"]
    data["nbre_familles"] = totaux["familles"]
    if en_cours:
        montant_comparable, montant_precedent = Montant(prestations.filter(date__lte=aujourdhui)), Montant(prestations_precedentes.filter(date__lte=date_equivalente))
    else:
        montant_comparable, montant_precedent = data["montant"], Montant(prestations_precedentes)
    data["montant_precedent"] = montant_precedent
    data["evolution_montant"] = Pourcentage(montant_comparable - montant_precedent, montant_precedent) if montant_precedent else None
    data["montant_par_famille"] = Format_montant(data["montant"] / data["nbre_familles"], 0) if data["nbre_familles"] else Format_montant(0, 0)

    # ------------------- Règlements (ventilations, quelle que soit leur date) -------------------
    regle_prestations = {idprestation: total for idprestation, total in Ventilation.objects.filter(prestation__in=prestations).values_list("prestation_id").annotate(total=Sum("montant"))}
    data["regle"] = sum(regle_prestations.values(), ZERO)
    data["reste"] = data["montant"] - data["regle"]
    data["taux_regle"] = Pourcentage(data["regle"], data["montant"]) if data["montant"] > 0 else None

    # ------------------- Remises et aides -------------------
    data["remises"] = data["montant_initial"] - data["montant"]
    data["taux_remises"] = Format_nombre(Pourcentage(data["remises"], data["montant_initial"], 1) or 0, 1)
    data["aides"] = Deduction.objects.filter(prestation__in=prestations, aide__isnull=False).aggregate(total=Sum("montant"))["total"] or ZERO

    # ------------------- État de la facturation et totaux par famille (parcours unique des prestations) -------------------
    etat = {"regle": ZERO, "facture_non_regle": ZERO, "non_facture": ZERO}
    factures_annulees = set(Facture.objects.filter(pk__in=prestations.exclude(facture__isnull=True).values("facture_id"), etat="annulation").values_list("pk", flat=True))
    montants_familles = {}
    nbre_non_facturees = 0
    for idprestation, montant, idfacture, idfamille, date in prestations.values_list("pk", "montant", "facture_id", "famille_id", "date"):
        montant = montant or ZERO
        regle = min(regle_prestations.get(idprestation, ZERO), montant) if montant > 0 else ZERO
        facturee = bool(idfacture) and idfacture not in factures_annulees
        etat["regle"] += regle
        etat["facture_non_regle" if facturee else "non_facture"] += montant - regle
        if not facturee and date < aujourdhui and montant > 0:
            nbre_non_facturees += 1
        if idfamille:
            montants_familles[idfamille] = montants_familles.get(idfamille, ZERO) + montant
    graphe_etat = {"codes": [], "labels": [], "valeurs": []}
    for code, label in (("regle", "Réglé"), ("facture_non_regle", "Facturé non réglé"), ("non_facture", "Non facturé")):
        if etat[code] > 0:
            graphe_etat["codes"].append(code)
            graphe_etat["labels"].append(label)
            graphe_etat["valeurs"].append(float(etat[code]))

    # Montant facturé par famille
    graphe_familles = {"labels": [label for mini, maxi, label in TRANCHES_FAMILLES], "valeurs": [0] * len(TRANCHES_FAMILLES)}
    for montant in montants_familles.values():
        graphe_familles["valeurs"][Get_tranche(float(montant), TRANCHES_FAMILLES)] += 1
    data["mediane_famille"] = Format_montant(statistics.median([float(m) for m in montants_familles.values()]), 0) if montants_familles else None

    # ------------------- Quotient familial des familles facturées -------------------
    date_reference = max(date_debut, min(date_fin, aujourdhui))
    quotients = Quotient.objects.filter(famille_id__in=montants_familles.keys(), date_debut__lte=date_fin, date_fin__gte=date_debut)
    if parametres.get("type_quotient"):
        quotients = quotients.filter(type_quotient=parametres["type_quotient"])
    # Pour chaque famille : le quotient valide à la date de référence, sinon le plus récent de la période
    quotients_familles, quotients_valides = {}, {}
    for quotient in quotients.only("famille_id", "date_debut", "date_fin", "quotient").order_by("date_fin"):
        if quotient.quotient is None:
            continue
        quotients_familles[quotient.famille_id] = quotient.quotient
        if quotient.date_debut <= date_reference <= quotient.date_fin:
            quotients_valides[quotient.famille_id] = quotient.quotient
    quotients_familles.update(quotients_valides)
    graphe_quotients = {"labels": [label for mini, maxi, label in TRANCHES_QUOTIENTS] + ["Non renseigné"],
                        "familles": [0] * (len(TRANCHES_QUOTIENTS) + 1), "montants": [0.0] * (len(TRANCHES_QUOTIENTS) + 1)}
    for idfamille, montant in montants_familles.items():
        index = Get_tranche(float(quotients_familles[idfamille]), TRANCHES_QUOTIENTS) if idfamille in quotients_familles else len(TRANCHES_QUOTIENTS)
        graphe_quotients["familles"][index] += 1
        graphe_quotients["montants"][index] += float(montant)
    graphe_quotients["moyennes"] = [round(m / f) if f else 0 for m, f in zip(graphe_quotients["montants"], graphe_quotients["familles"])]
    data["nbre_familles_qf"] = len(quotients_familles)
    data["taux_familles_qf"] = Pourcentage(len(quotients_familles), len(montants_familles))
    data["qf_moyen"] = Format_nombre(sum([float(q) for q in quotients_familles.values()]) / len(quotients_familles)) if quotients_familles else None
    data["date_reference_str"] = utils_dates.ConvertDateToFR(date_reference)

    # ------------------- Montant par mois -------------------
    liste_mois = Get_liste_mois(date_debut, date_fin)
    afficher_annee = len(liste_mois) > 12
    labels_mois = [("%s %s" % (MOIS_ABREGES[m - 1], str(a)[2:])) if afficher_annee else MOIS_ABREGES[m - 1] for a, m in liste_mois]
    dict_mois = {(mois.year, mois.month): float(total or 0) for mois, total in prestations.annotate(mois=TruncMonth("date")).values_list("mois").annotate(total=Sum("montant"))}
    graphe_mois = {"labels": labels_mois, "valeurs": [round(dict_mois.get(mois, 0), 2) for mois in liste_mois], "valeurs_precedentes": []}
    if comparer:
        dict_mois_precedents = {(mois.year, mois.month): float(total or 0) for mois, total in prestations_precedentes.annotate(mois=TruncMonth("date")).values_list("mois").annotate(total=Sum("montant"))}
        graphe_mois["valeurs_precedentes"] = [round(dict_mois_precedents.get(mois, 0), 2) for mois in Get_liste_mois(debut_precedente, fin_precedente)][:len(liste_mois)]

    # ------------------- Répartition par catégorie -------------------
    categories = sorted(prestations.values_list("categorie").annotate(total=Sum("montant")), key=lambda x: -(x[1] or 0))
    graphe_categories = {"codes": [code for code, total in categories if total],
                         "labels": [LIBELLES_CATEGORIES.get(code, code) for code, total in categories if total],
                         "valeurs": [float(total) for code, total in categories if total]}

    # ------------------- Montant par activité -------------------
    repartition = sorted([(nom or "Sans activité", float(total or 0)) for nom, total in prestations.values_list("activite__nom").annotate(total=Sum("montant"))], key=lambda x: -x[1])
    graphe_activites = {"labels": [nom for nom, total in repartition[:NBRE_ACTIVITES_AFFICHEES]], "valeurs": [total for nom, total in repartition[:NBRE_ACTIVITES_AFFICHEES]]}
    if len(repartition) > NBRE_ACTIVITES_AFFICHEES:
        graphe_activites["labels"].append("Autres")
        graphe_activites["valeurs"].append(sum([total for nom, total in repartition[NBRE_ACTIVITES_AFFICHEES:]]))

    # ------------------- Détail par activité -------------------
    regle_activites = {idactivite: total for idactivite, total in Ventilation.objects.filter(prestation__in=prestations).values_list("prestation__activite_id").annotate(total=Sum("montant"))}
    aides_activites = {idactivite: total for idactivite, total in Deduction.objects.filter(prestation__in=prestations).values_list("prestation__activite_id").annotate(total=Sum("montant"))}
    data["lignes"] = []
    for idactivite, nom, nbre, familles, montant_initial, montant in prestations.values_list("activite_id", "activite__nom") \
            .annotate(nbre=Count("pk"), familles=Count("famille_id", distinct=True), montant_initial=Sum("montant_initial"), montant=Sum("montant")):
        montant, montant_initial = montant or ZERO, montant_initial or ZERO
        regle = regle_activites.get(idactivite, ZERO)
        data["lignes"].append({
            "activite": nom or "Sans activité (adhésions, locations, autres)", "sans_activite": not idactivite,
            "nbre": nbre, "familles": familles, "montant_initial": montant_initial, "remises": montant_initial - montant,
            "montant": montant, "regle": regle, "reste": montant - regle,
        })
    data["lignes"].sort(key=lambda ligne: (ligne["sans_activite"], ligne["activite"].lower()))
    for ligne in data["lignes"]:
        for key in ("montant_initial", "remises", "montant", "regle", "reste"):
            ligne["%s_str" % key] = Format_montant(ligne[key])
        ligne["nbre_str"], ligne["familles_str"] = Format_nombre(ligne["nbre"]), Format_nombre(ligne["familles"])

    # ------------------- Suivi administratif -------------------
    factures = Facture.objects.filter(pk__in=prestations.exclude(facture__isnull=True).values("facture_id")).exclude(etat="annulation") \
        .filter(date_echeance__lt=aujourdhui, solde_actuel__gt=0)
    totaux_factures = factures.aggregate(nbre=Count("pk"), solde=Sum("solde_actuel"))
    data["suivi"] = {
        "non_facturees": nbre_non_facturees,
        "factures_echues": totaux_factures["nbre"] or 0,
        "reste_echues": Format_montant(totaux_factures["solde"] or 0),
        "prestations_zero": prestations.filter(montant=0).count(),
    }

    # Valeurs formatées
    for key in ("montant", "montant_initial", "regle", "reste", "remises", "aides"):
        data["%s_str" % key] = Format_montant(data[key])
    data["nbre_prestations_str"] = Format_nombre(data["nbre_prestations"])
    data["nbre_familles_str"] = Format_nombre(data["nbre_familles"])
    data["graphes"] = {"mois": graphe_mois, "categories": graphe_categories, "activites": graphe_activites,
                       "etat": graphe_etat, "familles": graphe_familles, "quotients": graphe_quotients}
    return data


# ---------------------------------------- Exports ----------------------------------------

def Get_parametres(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return None
    parametres = form.cleaned_data
    parametres["structures"] = request.user.structures.all()
    return parametres


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
    nom_fichier = "statistiques_prestations.xlsx"

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

    # Indicateurs
    feuille = classeur.add_worksheet("Indicateurs")
    feuille.set_column(0, 0, 44)
    feuille.set_column(1, 1, 20)
    feuille.write(0, 0, "Statistiques des prestations", format_titre)
    feuille.write(1, 0, "Période : %s" % data["periode_str"])
    feuille.write(2, 0, "Catégories : %s" % data["categories"])
    feuille.write(3, 0, "Activités : %s" % data["activites"])
    lignes = [
        ("Nombre de prestations", data["nbre_prestations"], None),
        ("Familles facturées", data["nbre_familles"], None),
        ("Montant initial", float(data["montant_initial"]), format_euros),
        ("Remises et aides", float(data["remises"]), format_euros),
        ("Dont aides", float(data["aides"]), format_euros),
        ("Montant des prestations", float(data["montant"]), format_euros),
        ("Évolution par rapport à la période précédente (%)", data["evolution_montant"] if data["evolution_montant"] is not None else "", None),
        ("Montant réglé", float(data["regle"]), format_euros),
        ("Reste dû", float(data["reste"]), format_euros),
        ("Taux de règlement (%)", data["taux_regle"] if data["taux_regle"] is not None else "", None),
        ("Prestations passées non facturées", data["suivi"]["non_facturees"], None),
        ("Factures échues non soldées", data["suivi"]["factures_echues"], None),
        ("Prestations à 0 €", data["suivi"]["prestations_zero"], None),
    ]
    for num_colonne, label in enumerate(("Indicateur", "Valeur")):
        feuille.write(5, num_colonne, label, format_entete)
    for index, (label, valeur, format_cellule) in enumerate(lignes):
        feuille.write(6 + index, 0, label)
        feuille.write(6 + index, 1, valeur, format_cellule)

    # Détail par activité
    feuille = classeur.add_worksheet("Détail par activité")
    for num_colonne, largeur in enumerate((44, 13, 11, 16, 16, 16, 16, 14)):
        feuille.set_column(num_colonne, num_colonne, largeur)
    Ecrire_tableau(feuille, 0, ("Activité", "Prestations", "Familles", "Montant initial", "Remises / aides", "Montant", "Réglé", "Reste dû"),
                   [(l["activite"], l["nbre"], l["familles"], float(l["montant_initial"]), float(l["remises"]), float(l["montant"]), float(l["regle"]), float(l["reste"])) for l in data["lignes"]],
                   formats={3: format_euros, 4: format_euros, 5: format_euros, 6: format_euros, 7: format_euros})

    graphes = data["graphes"]
    feuille = classeur.add_worksheet("Par mois")
    feuille.set_column(0, 2, 18)
    lignes = []
    for index, label in enumerate(graphes["mois"]["labels"]):
        precedentes = graphes["mois"]["valeurs_precedentes"]
        lignes.append((label, graphes["mois"]["valeurs"][index], precedentes[index] if index < len(precedentes) else ""))
    Ecrire_tableau(feuille, 0, ("Mois", "Montant", "Période précédente"), lignes, formats={1: format_euros, 2: format_euros})

    feuille = classeur.add_worksheet("Catégories")
    feuille.set_column(0, 1, 20)
    Ecrire_tableau(feuille, 0, ("Catégorie", "Montant"), zip(graphes["categories"]["labels"], graphes["categories"]["valeurs"]), formats={1: format_euros})

    feuille = classeur.add_worksheet("Quotient familial")
    feuille.set_column(0, 3, 20)
    Ecrire_tableau(feuille, 0, ("Quotient familial", "Familles", "Montant facturé", "Montant moyen par famille"),
                   zip(graphes["quotients"]["labels"], graphes["quotients"]["familles"], graphes["quotients"]["montants"], graphes["quotients"]["moyennes"]),
                   formats={2: format_euros, 3: format_euros})

    feuille = classeur.add_worksheet("Montant par famille")
    feuille.set_column(0, 1, 20)
    Ecrire_tableau(feuille, 0, ("Montant facturé", "Familles"), zip(graphes["familles"]["labels"], graphes["familles"]["valeurs"]))

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
    for nom in ("mois", "categories", "activites", "etat", "quotients", "familles"):
        valeur = request.POST.get("graphique_%s" % nom, "")
        if valeur.startswith("data:image/png;base64,") and len(valeur) < 5000000:
            try:
                images[nom] = base64.b64decode(valeur.split(",", 1)[1])
            except Exception:
                logger.warning("Image du graphique '%s' invalide" % nom)

    impression = Impression_statistiques(titre="Statistiques des prestations", dict_donnees={"data": data, "images": images}, request=request)
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
        self.story.append(Paragraph("<b>Catégories :</b> %s" % data["categories"], style_texte))
        self.story.append(Paragraph("<b>Activités :</b> %s" % data["activites"], style_texte))
        self.story.append(Spacer(0, 6))

        evolution = ""
        if data["comparer"] and data["evolution_montant"] is not None:
            evolution = " (%s%s %%)" % ("+" if data["evolution_montant"] >= 0 else "", data["evolution_montant"])
        indicateurs = [
            ("Montant", "%s%s" % (data["montant_str"], evolution)),
            ("Familles facturées", "%s (%s prestations, %s par famille)" % (data["nbre_familles_str"], data["nbre_prestations_str"], data["montant_par_famille"])),
            ("Taux de règlement", "%s - reste dû %s" % ("%s %%" % data["taux_regle"] if data["taux_regle"] is not None else "-", data["reste_str"])),
            ("Remises et aides", "%s (%s %% du montant initial, dont %s d'aides)" % (data["remises_str"], data["taux_remises"], data["aides_str"])),
        ]
        suivi = [
            ("Prestations passées non facturées", Format_nombre(data["suivi"]["non_facturees"])),
            ("Factures échues non soldées", Format_nombre(data["suivi"]["factures_echues"])),
            ("Reste dû sur factures échues", data["suivi"]["reste_echues"]),
            ("Prestations à 0 €", Format_nombre(data["suivi"]["prestations_zero"])),
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

        titres = {"mois": "Montant des prestations par mois", "categories": "Répartition par catégorie", "activites": "Montant par activité",
                  "etat": "État de la facturation", "quotients": "Familles facturées par quotient familial", "familles": "Montant facturé par famille"}
        largeur_image = (largeur - 10) / 2
        for paire in (("mois", "categories"), ("activites", "etat"), ("quotients", "familles")):
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
            tableau = Table([cellules], [largeur_image + 5, largeur_image + 5])
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            self.story.append(tableau)

        lignes = [("Activité", "Prest.", "Familles", "Montant initial", "Remises", "Montant", "Réglé", "Reste dû")]
        for ligne in data["lignes"]:
            lignes.append((Paragraph(ligne["activite"], style_texte), ligne["nbre_str"], ligne["familles_str"], ligne["montant_initial_str"],
                           ligne["remises_str"], ligne["montant_str"], ligne["regle_str"], ligne["reste_str"]))
        lignes.append(("Total", data["nbre_prestations_str"], data["nbre_familles_str"], data["montant_initial_str"], data["remises_str"],
                       data["montant_str"], data["regle_str"], data["reste_str"]))
        proportions = (0.26, 0.08, 0.08, 0.12, 0.11, 0.12, 0.12, 0.11)
        tableau = Table(lignes, [largeur * p for p in proportions], repeatRows=1)
        tableau.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7.5), ("FONT", (0, 0), (-1, 0), utils_polices.FONT_BOLD, 7.5),
            ("FONT", (0, -1), (-1, -1), utils_polices.FONT_BOLD, 7.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8f9fa")), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, gris), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        self.story.append(KeepTogether([Paragraph("Détail par activité", style_titre), tableau]))


# ---------------------------------------- Vue ----------------------------------------

class View(CustomView, TemplateView):
    menu_code = "statistiques_prestations"
    template_name = "facturation/statistiques_prestations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Statistiques des prestations"
        if "form_parametres" not in kwargs:
            context["form_parametres"] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        parametres = form.cleaned_data
        parametres["structures"] = request.user.structures.all()
        return self.render_to_response(self.get_context_data(form_parametres=form, data=Get_data(parametres)))
