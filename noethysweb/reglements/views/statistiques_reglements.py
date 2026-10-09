# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, decimal, base64, io, os, uuid, statistics
logger = logging.getLogger(__name__)
from django.conf import settings
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Reglement, Ventilation, Paiement
from core.utils import utils_dates
from core.utils.utils_impression import Impression
from reglements.forms.statistiques_reglements import Formulaire

PERMISSION = "core.statistiques_reglements"
MOIS_ABREGES = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
TRANCHES_DELAIS = ((None, 0, "Avant échéance"), (0, 15, "1-15 j de retard"), (15, 30, "16-30 j"), (30, 60, "31-60 j"), (60, None, "> 60 j"))
LIBELLES_SYSTEMES = {"payfip": "PayFIP", "payzen": "Payzen", "helloasso": "HelloAsso"}
NBRE_MODES_AFFICHES = 6
NBRE_ACTIVITES_AFFICHEES = 8
ZERO = decimal.Decimal(0)
TOLERANCE = decimal.Decimal("0.005")


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


def Get_liste_mois(date_debut=None, date_fin=None):
    liste_mois, annee, mois = [], date_debut.year, date_debut.month
    while (annee, mois) <= (date_fin.year, date_fin.month):
        liste_mois.append((annee, mois))
        mois += 1
        if mois > 12:
            annee, mois = annee + 1, 1
    return liste_mois


def Get_tranche_delai(jours):
    """ Index de la tranche de délai (jours de retard par rapport à l'échéance) """
    for index, (mini, maxi, label) in enumerate(TRANCHES_DELAIS):
        if (mini is None or jours > mini) and (maxi is None or jours <= maxi):
            return index
    return len(TRANCHES_DELAIS) - 1


def Get_reglements(parametres={}, date_debut=None, date_fin=None):
    """ Règlements de la période selon les modes et le compte sélectionnés """
    reglements = Reglement.objects.filter(date__gte=date_debut, date__lte=date_fin, mode__in=parametres["modes"])
    if parametres.get("compte"):
        reglements = reglements.filter(compte=parametres["compte"])
    return reglements


def Montant(queryset):
    return queryset.aggregate(total=Sum("montant"))["total"] or ZERO


def Regrouper(liste=[], nbre_max=6, label_autres="Autres"):
    """ Conserve les nbre_max premiers éléments (label, valeur) et regroupe les suivants """
    liste = sorted(liste, key=lambda x: -x[1])
    resultat = {"labels": [label for label, valeur in liste[:nbre_max]], "valeurs": [valeur for label, valeur in liste[:nbre_max]]}
    if len(liste) > nbre_max:
        resultat["labels"].append(label_autres)
        resultat["valeurs"].append(sum([valeur for label, valeur in liste[nbre_max:]]))
    return resultat


# ---------------------------------------- Calculs ----------------------------------------

def Get_data(parametres={}):
    date_debut, date_fin = [utils_dates.ConvertDateENGtoDate(x) for x in parametres["periode"].split(";")]
    comparer = parametres.get("comparer", False)
    aujourdhui = datetime.date.today()

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
        "modes": ", ".join(sorted([mode.label for mode in parametres["modes"]])),
        "compte": parametres["compte"].nom if parametres.get("compte") else "Tous les comptes",
    }

    reglements = Get_reglements(parametres, date_debut, date_fin)
    reglements_precedents = Get_reglements(parametres, debut_precedente, fin_precedente)

    # ------------------- Montant et évolution -------------------
    totaux = reglements.aggregate(montant=Sum("montant"), nbre=Count("pk"), familles=Count("famille_id", distinct=True))
    data["montant"] = totaux["montant"] or ZERO
    data["nbre_reglements"] = totaux["nbre"]
    data["nbre_familles"] = totaux["familles"]
    if en_cours:
        montant_comparable, montant_precedent = Montant(reglements.filter(date__lte=aujourdhui)), Montant(reglements_precedents.filter(date__lte=date_equivalente))
    else:
        montant_comparable, montant_precedent = data["montant"], Montant(reglements_precedents)
    data["evolution_montant"] = Pourcentage(montant_comparable - montant_precedent, montant_precedent) if montant_precedent else None
    data["montant_moyen"] = Format_montant(data["montant"] / data["nbre_reglements"], 0) if data["nbre_reglements"] else Format_montant(0, 0)

    # ------------------- Ventilation par règlement -------------------
    ventile_reglements = {idreglement: total for idreglement, total in Ventilation.objects.filter(reglement__in=reglements).values_list("reglement_id").annotate(total=Sum("montant"))}

    # ------------------- Paiements en ligne (règlements issus d'un paiement en ligne) -------------------
    liens_paiements = Paiement.reglements.through.objects.filter(reglement_id__in=reglements.values("pk")).values_list("reglement_id", "paiement_id", "paiement__systeme_paiement")
    systemes_reglements, paiements = {}, set()
    for idreglement, idpaiement, systeme in liens_paiements:
        systemes_reglements[idreglement] = LIBELLES_SYSTEMES.get((systeme or "").lower(), (systeme or "Autre").capitalize())
        paiements.add(idpaiement)

    # ------------------- Parcours unique des règlements -------------------
    etat_depots = {"depose": ZERO, "non_depose": ZERO, "differe": ZERO}
    suivi = {"non_deposes": 0, "montant_non_depose": ZERO, "non_ventiles": 0, "differes": 0}
    modes, en_ligne = {}, {}
    data["ventile"], data["non_ventile"], data["montant_en_ligne"] = ZERO, ZERO, ZERO
    for idreglement, montant, mode, idfamille, iddepot, date_differe, encaissement_attente in reglements.values_list(
            "pk", "montant", "mode__label", "famille_id", "depot_id", "date_differe", "encaissement_attente"):
        montant = montant or ZERO
        ventile = ventile_reglements.get(idreglement, ZERO)
        non_ventile = max(montant - ventile, ZERO)
        data["ventile"] += montant - non_ventile
        data["non_ventile"] += non_ventile

        # Détail par mode
        ligne = modes.setdefault(mode, {"mode": mode, "nbre": 0, "familles": set(), "montant": ZERO, "ventile": ZERO, "non_ventile": ZERO, "non_depose": ZERO})
        ligne["nbre"] += 1
        ligne["familles"].add(idfamille)
        ligne["montant"] += montant
        ligne["ventile"] += montant - non_ventile
        ligne["non_ventile"] += non_ventile

        # État des dépôts
        differe = encaissement_attente or (date_differe is not None and date_differe > aujourdhui)
        if iddepot:
            etat_depots["depose"] += montant
        elif differe:
            etat_depots["differe"] += montant
        else:
            etat_depots["non_depose"] += montant
            ligne["non_depose"] += montant
            suivi["non_deposes"] += 1
            suivi["montant_non_depose"] += montant
        if date_differe is not None and date_differe > aujourdhui:
            suivi["differes"] += 1

        # Règlements non (ou partiellement) ventilés
        if non_ventile > TOLERANCE:
            suivi["non_ventiles"] += 1

        # Paiements en ligne
        if idreglement in systemes_reglements:
            data["montant_en_ligne"] += montant
            systeme = systemes_reglements[idreglement]
            en_ligne[systeme] = en_ligne.get(systeme, ZERO) + montant

    data["taux_ventilation"] = Pourcentage(data["ventile"], data["montant"]) if data["montant"] > 0 else None
    data["taux_en_ligne"] = Pourcentage(data["montant_en_ligne"], data["montant"]) if data["montant"] > 0 else None
    data["nbre_paiements"] = len(paiements)
    data["suivi"] = {"non_deposes": suivi["non_deposes"], "montant_non_depose": Format_montant(suivi["montant_non_depose"]),
                     "non_ventiles": suivi["non_ventiles"], "differes": suivi["differes"]}

    graphe_depots = {"codes": [], "labels": [], "valeurs": []}
    for code, label in (("depose", "Déposé"), ("non_depose", "Non déposé"), ("differe", "Encaissement différé")):
        if etat_depots[code] > 0:
            graphe_depots["codes"].append(code)
            graphe_depots["labels"].append(label)
            graphe_depots["valeurs"].append(float(etat_depots[code]))

    # ------------------- Montant par mois -------------------
    liste_mois = Get_liste_mois(date_debut, date_fin)
    afficher_annee = len(liste_mois) > 12
    labels_mois = [("%s %s" % (MOIS_ABREGES[m - 1], str(a)[2:])) if afficher_annee else MOIS_ABREGES[m - 1] for a, m in liste_mois]
    dict_mois = {(mois.year, mois.month): float(total or 0) for mois, total in reglements.annotate(mois=TruncMonth("date")).values_list("mois").annotate(total=Sum("montant"))}
    graphe_mois = {"labels": labels_mois, "valeurs": [round(dict_mois.get(mois, 0), 2) for mois in liste_mois], "valeurs_precedentes": []}
    if comparer:
        dict_mois_precedents = {(mois.year, mois.month): float(total or 0) for mois, total in reglements_precedents.annotate(mois=TruncMonth("date")).values_list("mois").annotate(total=Sum("montant"))}
        graphe_mois["valeurs_precedentes"] = [round(dict_mois_precedents.get(mois, 0), 2) for mois in Get_liste_mois(debut_precedente, fin_precedente)][:len(liste_mois)]

    # ------------------- Répartition par mode -------------------
    graphe_modes = Regrouper([(mode, float(ligne["montant"])) for mode, ligne in modes.items() if ligne["montant"]], NBRE_MODES_AFFICHES)

    # ------------------- Montant réglé par activité (selon la ventilation) -------------------
    activites = Ventilation.objects.filter(reglement__in=reglements).values_list("prestation__activite__nom").annotate(total=Sum("montant"))
    graphe_activites = Regrouper([(nom or "Sans activité", float(total or 0)) for nom, total in activites if total], NBRE_ACTIVITES_AFFICHEES)

    # ------------------- Délai de paiement des factures (pondéré par le montant ventilé) -------------------
    graphe_delais = {"labels": [label for mini, maxi, label in TRANCHES_DELAIS], "valeurs": [0.0] * len(TRANCHES_DELAIS)}
    liste_delais = []
    ventilations_factures = Ventilation.objects.filter(reglement__in=reglements, prestation__facture__isnull=False) \
        .exclude(prestation__facture__etat="annulation") \
        .values_list("montant", "reglement__date", "prestation__facture__date_echeance", "prestation__facture__date_edition")
    for montant, date_reglement, date_echeance, date_edition in ventilations_factures:
        date_reference = date_echeance or date_edition
        if not date_reference or not montant:
            continue
        jours = (date_reglement - date_reference).days
        graphe_delais["valeurs"][Get_tranche_delai(jours)] += float(montant)
        liste_delais.append(jours)
    graphe_delais["valeurs"] = [round(valeur, 2) for valeur in graphe_delais["valeurs"]]
    data["delai_median"] = round(statistics.median(liste_delais)) if liste_delais else None
    data["taux_avant_echeance"] = Pourcentage(graphe_delais["valeurs"][0], sum(graphe_delais["valeurs"]))

    # ------------------- Paiements en ligne par système -------------------
    graphe_en_ligne = Regrouper([(systeme, float(montant)) for systeme, montant in en_ligne.items()], 5)

    # ------------------- Détail par mode -------------------
    data["lignes"] = sorted(modes.values(), key=lambda ligne: -ligne["montant"])
    for ligne in data["lignes"]:
        ligne["familles"] = len(ligne["familles"])
        for key in ("montant", "ventile", "non_ventile", "non_depose"):
            ligne["%s_str" % key] = Format_montant(ligne[key])
        ligne["nbre_str"], ligne["familles_str"] = Format_nombre(ligne["nbre"]), Format_nombre(ligne["familles"])

    # Valeurs formatées
    for key in ("montant", "ventile", "non_ventile", "montant_en_ligne"):
        data["%s_str" % key] = Format_montant(data[key])
    data["nbre_reglements_str"] = Format_nombre(data["nbre_reglements"])
    data["nbre_familles_str"] = Format_nombre(data["nbre_familles"])
    data["nbre_paiements_str"] = Format_nombre(data["nbre_paiements"])
    data["graphes"] = {"mois": graphe_mois, "modes": graphe_modes, "activites": graphe_activites,
                       "depots": graphe_depots, "delais": graphe_delais, "en_ligne": graphe_en_ligne}
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
    nom_fichier = "statistiques_reglements.xlsx"

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
    feuille.write(0, 0, "Statistiques des règlements", format_titre)
    feuille.write(1, 0, "Période : %s" % data["periode_str"])
    feuille.write(2, 0, "Modes de règlement : %s" % data["modes"])
    feuille.write(3, 0, "Compte bancaire : %s" % data["compte"])
    lignes = [
        ("Nombre de règlements", data["nbre_reglements"], None),
        ("Familles payeuses", data["nbre_familles"], None),
        ("Montant encaissé", float(data["montant"]), format_euros),
        ("Évolution par rapport à la période précédente (%)", data["evolution_montant"] if data["evolution_montant"] is not None else "", None),
        ("Montant ventilé", float(data["ventile"]), format_euros),
        ("Montant non ventilé", float(data["non_ventile"]), format_euros),
        ("Taux de ventilation (%)", data["taux_ventilation"] if data["taux_ventilation"] is not None else "", None),
        ("Montant issu des paiements en ligne", float(data["montant_en_ligne"]), format_euros),
        ("Part des paiements en ligne (%)", data["taux_en_ligne"] if data["taux_en_ligne"] is not None else "", None),
        ("Délai médian de paiement des factures (jours)", data["delai_median"] if data["delai_median"] is not None else "", None),
        ("Règlements non déposés", data["suivi"]["non_deposes"], None),
        ("Règlements non ventilés", data["suivi"]["non_ventiles"], None),
        ("Encaissements différés à venir", data["suivi"]["differes"], None),
    ]
    for num_colonne, label in enumerate(("Indicateur", "Valeur")):
        feuille.write(5, num_colonne, label, format_entete)
    for index, (label, valeur, format_cellule) in enumerate(lignes):
        feuille.write(6 + index, 0, label)
        feuille.write(6 + index, 1, valeur, format_cellule)

    # Détail par mode
    feuille = classeur.add_worksheet("Détail par mode")
    for num_colonne, largeur in enumerate((30, 13, 11, 16, 16, 16, 16)):
        feuille.set_column(num_colonne, num_colonne, largeur)
    Ecrire_tableau(feuille, 0, ("Mode de règlement", "Règlements", "Familles", "Montant", "Ventilé", "Non ventilé", "Non déposé"),
                   [(l["mode"], l["nbre"], l["familles"], float(l["montant"]), float(l["ventile"]), float(l["non_ventile"]), float(l["non_depose"])) for l in data["lignes"]],
                   formats={3: format_euros, 4: format_euros, 5: format_euros, 6: format_euros})

    graphes = data["graphes"]
    feuille = classeur.add_worksheet("Par mois")
    feuille.set_column(0, 2, 18)
    lignes = []
    for index, label in enumerate(graphes["mois"]["labels"]):
        precedentes = graphes["mois"]["valeurs_precedentes"]
        lignes.append((label, graphes["mois"]["valeurs"][index], precedentes[index] if index < len(precedentes) else ""))
    Ecrire_tableau(feuille, 0, ("Mois", "Montant", "Période précédente"), lignes, formats={1: format_euros, 2: format_euros})

    feuille = classeur.add_worksheet("Par activité")
    feuille.set_column(0, 1, 30)
    Ecrire_tableau(feuille, 0, ("Activité", "Montant réglé"), zip(graphes["activites"]["labels"], graphes["activites"]["valeurs"]), formats={1: format_euros})

    feuille = classeur.add_worksheet("Délai de paiement")
    feuille.set_column(0, 1, 22)
    Ecrire_tableau(feuille, 0, ("Délai par rapport à l'échéance", "Montant réglé"), zip(graphes["delais"]["labels"], graphes["delais"]["valeurs"]), formats={1: format_euros})

    feuille = classeur.add_worksheet("Paiements en ligne")
    feuille.set_column(0, 1, 22)
    Ecrire_tableau(feuille, 0, ("Système de paiement", "Montant"), zip(graphes["en_ligne"]["labels"], graphes["en_ligne"]["valeurs"]), formats={1: format_euros})

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
    for nom in ("mois", "modes", "activites", "depots", "delais", "en_ligne"):
        valeur = request.POST.get("graphique_%s" % nom, "")
        if valeur.startswith("data:image/png;base64,") and len(valeur) < 5000000:
            try:
                images[nom] = base64.b64decode(valeur.split(",", 1)[1])
            except Exception:
                logger.warning("Image du graphique '%s' invalide" % nom)

    impression = Impression_statistiques(titre="Statistiques des règlements", dict_donnees={"data": data, "images": images}, request=request)
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
        self.story.append(Paragraph("<b>Modes de règlement :</b> %s" % data["modes"], style_texte))
        self.story.append(Paragraph("<b>Compte bancaire :</b> %s" % data["compte"], style_texte))
        self.story.append(Spacer(0, 6))

        evolution = ""
        if data["comparer"] and data["evolution_montant"] is not None:
            evolution = " (%s%s %%)" % ("+" if data["evolution_montant"] >= 0 else "", data["evolution_montant"])
        indicateurs = [
            ("Montant encaissé", "%s%s" % (data["montant_str"], evolution)),
            ("Familles payeuses", "%s (%s règlements, %s en moyenne)" % (data["nbre_familles_str"], data["nbre_reglements_str"], data["montant_moyen"])),
            ("Taux de ventilation", "%s - non ventilé %s" % ("%s %%" % data["taux_ventilation"] if data["taux_ventilation"] is not None else "-", data["non_ventile_str"])),
            ("Paiements en ligne", "%s (%s, %s paiements)" % ("%s %%" % data["taux_en_ligne"] if data["taux_en_ligne"] is not None else "-", data["montant_en_ligne_str"], data["nbre_paiements_str"])),
        ]
        suivi = [
            ("Règlements non déposés", Format_nombre(data["suivi"]["non_deposes"])),
            ("Montant en attente de dépôt", data["suivi"]["montant_non_depose"]),
            ("Règlements non ventilés", Format_nombre(data["suivi"]["non_ventiles"])),
            ("Encaissements différés à venir", Format_nombre(data["suivi"]["differes"])),
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

        titres = {"mois": "Montant encaissé par mois", "modes": "Répartition par mode de règlement", "activites": "Montant réglé par activité",
                  "depots": "État des dépôts", "delais": "Délai de paiement des factures", "en_ligne": "Paiements en ligne par système"}
        largeur_image = (largeur - 10) / 2
        for paire in (("mois", "modes"), ("activites", "depots"), ("delais", "en_ligne")):
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

        lignes = [("Mode de règlement", "Règl.", "Familles", "Montant", "Ventilé", "Non ventilé", "Non déposé")]
        for ligne in data["lignes"]:
            lignes.append((Paragraph(ligne["mode"], style_texte), ligne["nbre_str"], ligne["familles_str"], ligne["montant_str"],
                           ligne["ventile_str"], ligne["non_ventile_str"], ligne["non_depose_str"]))
        lignes.append(("Total", data["nbre_reglements_str"], data["nbre_familles_str"], data["montant_str"], data["ventile_str"],
                       data["non_ventile_str"], data["suivi"]["montant_non_depose"]))
        proportions = (0.25, 0.09, 0.09, 0.15, 0.14, 0.14, 0.14)
        tableau = Table(lignes, [largeur * p for p in proportions], repeatRows=1)
        tableau.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7.5), ("FONT", (0, 0), (-1, 0), utils_polices.FONT_BOLD, 7.5),
            ("FONT", (0, -1), (-1, -1), utils_polices.FONT_BOLD, 7.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8f9fa")), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, gris), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        self.story.append(KeepTogether([Paragraph("Détail par mode de règlement", style_titre), tableau]))


# ---------------------------------------- Vue ----------------------------------------

class View(CustomView, TemplateView):
    menu_code = "statistiques_reglements"
    template_name = "reglements/statistiques_reglements.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Statistiques des règlements"
        if "form_parametres" not in kwargs:
            context["form_parametres"] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        return self.render_to_response(self.get_context_data(form_parametres=form, data=Get_data(form.cleaned_data)))
