# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, decimal, base64, io, os, uuid
logger = logging.getLogger(__name__)
from django.conf import settings
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Cotisation, Ventilation, Individu, Famille
from core.data import data_civilites
from core.utils import utils_dates
from core.utils.utils_impression import Impression
from cotisations.forms.statistiques_cotisations import Formulaire

MOIS_ABREGES = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
TRANCHES_AGES = ((0, 5, "0-5"), (6, 10, "6-10"), (11, 14, "11-14"), (15, 17, "15-17"), (18, 25, "18-25"),
                 (26, 40, "26-40"), (41, 60, "41-60"), (61, 200, "61 et +"))
NBRE_COMMUNES_AFFICHEES = 7
PERMISSION = "core.statistiques_cotisations"


def Get_sexes_civilites():
    """ Dictionnaire {IDcivilite: "M" ou "F"} """
    dict_sexes = {}
    for categorie, items in data_civilites.LISTE_CIVILITES:
        for civilite in items:
            dict_sexes[civilite["id"]] = civilite.get("sexe")
    return dict_sexes


def Get_cotisations(types_cotisations=None, date_debut=None, date_fin=None):
    """ Adhésions des types sélectionnés valides sur au moins une partie de la période """
    return Cotisation.objects.filter(type_cotisation__in=types_cotisations, date_debut__lte=date_fin, date_fin__gte=date_debut)


def Get_adherents(cotisations=None):
    """ Ensemble des adhérents : familles pour les adhésions familiales, individus pour les adhésions individuelles """
    adherents = set()
    for idfamille, idindividu in cotisations.values_list("famille_id", "individu_id"):
        if idindividu:
            adherents.add(("individu", idindividu))
        elif idfamille:
            adherents.add(("famille", idfamille))
    return adherents


def Get_taux_readhesion(adherents=set(), adherents_precedents=set()):
    if not adherents_precedents:
        return None
    return round(100.0 * len(adherents & adherents_precedents) / len(adherents_precedents))


def Get_liste_mois(date_debut=None, date_fin=None):
    """ Liste des (année, mois) couverts par la période """
    liste_mois = []
    annee, mois = date_debut.year, date_debut.month
    while (annee, mois) <= (date_fin.year, date_fin.month):
        liste_mois.append((annee, mois))
        mois += 1
        if mois > 12:
            annee, mois = annee + 1, 1
    return liste_mois


def Get_villes_individus(liste_idindividu=[]):
    """ Ville de résidence de chaque individu, en suivant l'adresse rattachée si besoin """
    dict_individus = {individu.pk: individu for individu in Individu.objects.filter(pk__in=liste_idindividu).only("pk", "adresse_auto", "ville_resid")}
    # Individus portant les adresses rattachées
    liste_adresses = [individu.adresse_auto for individu in dict_individus.values() if individu.adresse_auto and individu.adresse_auto not in dict_individus]
    for individu in Individu.objects.filter(pk__in=liste_adresses).only("pk", "ville_resid"):
        dict_individus[individu.pk] = individu
    dict_villes = {}
    for idindividu in liste_idindividu:
        individu = dict_individus.get(idindividu)
        if individu and individu.adresse_auto and individu.adresse_auto in dict_individus:
            individu = dict_individus[individu.adresse_auto]
        dict_villes[idindividu] = individu.ville_resid if individu else None
    return dict_villes


def Normaliser_ville(ville=None):
    ville = (ville or "").strip()
    return ville.upper() if ville else None


def Format_montant(valeur):
    return "{:,.2f} €".format(float(valeur or 0)).replace(",", " ").replace(".", ",")


def Get_data(parametres={}):
    """ Calcul de toutes les statistiques des adhésions """
    date_debut, date_fin = [utils_dates.ConvertDateENGtoDate(x) for x in parametres["periode"].split(";")]
    types_cotisations = parametres["types_cotisations"]
    comparer = parametres.get("comparer", False)
    aujourdhui = datetime.date.today()

    # Périodes précédentes de même durée
    duree = date_fin - date_debut
    fin_precedente = date_debut - datetime.timedelta(days=1)
    debut_precedente = fin_precedente - duree
    fin_precedente_2 = debut_precedente - datetime.timedelta(days=1)
    debut_precedente_2 = fin_precedente_2 - duree

    # Si la période est en cours, la comparaison se fait à date équivalente sur les périodes précédentes
    en_cours = date_debut <= aujourdhui < date_fin
    decalage = date_debut - debut_precedente
    date_equivalente = aujourdhui - decalage if en_cours else fin_precedente
    date_equivalente_2 = aujourdhui - 2 * decalage if en_cours else fin_precedente_2

    data = {
        "date_debut": date_debut, "date_fin": date_fin, "comparer": comparer, "en_cours": en_cours,
        "date_debut_str": utils_dates.ConvertDateToFR(date_debut), "date_fin_str": utils_dates.ConvertDateToFR(date_fin),
        "periode_str": "%s - %s" % (utils_dates.ConvertDateToFR(date_debut), utils_dates.ConvertDateToFR(date_fin)),
        "periode_precedente_str": "%s - %s" % (utils_dates.ConvertDateToFR(debut_precedente), utils_dates.ConvertDateToFR(fin_precedente)),
        "types": ", ".join([type_cotisation.nom for type_cotisation in types_cotisations]),
    }

    cotisations = Get_cotisations(types_cotisations, date_debut, date_fin).select_related("type_cotisation", "unite_cotisation", "prestation")
    liste_cotisations = list(cotisations)
    data["nbre_cotisations"] = len(liste_cotisations)

    # ------------------- Adhérents -------------------
    adherents = Get_adherents(cotisations)
    data["nbre_familles"] = len([1 for categorie, id in adherents if categorie == "famille"])
    data["nbre_individus"] = len([1 for categorie, id in adherents if categorie == "individu"])
    data["nbre_adherents"] = len(adherents)

    # ------------------- Comparaison et réadhésions -------------------
    cotisations_precedentes = Get_cotisations(types_cotisations, debut_precedente, fin_precedente)
    adherents_precedents = Get_adherents(cotisations_precedentes)
    # Pour l'évolution : adhésions de la période précédente déjà enregistrées à date équivalente
    cotisations_precedentes_equivalentes = cotisations_precedentes.filter(date_debut__lte=date_equivalente)
    data["nbre_cotisations_precedentes"] = cotisations_precedentes_equivalentes.count()
    data["date_equivalente_str"] = utils_dates.ConvertDateToFR(date_equivalente)
    data["evolution_cotisations"] = None
    if data["nbre_cotisations_precedentes"]:
        data["evolution_cotisations"] = round(100.0 * (data["nbre_cotisations"] - data["nbre_cotisations_precedentes"]) / data["nbre_cotisations_precedentes"])
    data["taux_readhesion"] = Get_taux_readhesion(adherents, adherents_precedents)
    data["nbre_nouveaux"] = len(adherents - adherents_precedents)
    data["evolution_taux_readhesion"] = None
    if data["taux_readhesion"] is not None:
        # Taux de la période précédente, mesuré à date équivalente
        taux_precedent = Get_taux_readhesion(Get_adherents(cotisations_precedentes_equivalentes), Get_adherents(Get_cotisations(types_cotisations, debut_precedente_2, fin_precedente_2)))
        if taux_precedent is not None:
            data["evolution_taux_readhesion"] = data["taux_readhesion"] - taux_precedent

    # ------------------- Montants -------------------
    liste_idprestation = [cotisation.prestation_id for cotisation in liste_cotisations if cotisation.prestation_id]
    dict_regle = {idprestation: total for idprestation, total in Ventilation.objects.filter(prestation_id__in=liste_idprestation).values_list("prestation_id").annotate(total=Sum("montant"))}

    def Get_montants(cotisation):
        montant = cotisation.prestation.montant if cotisation.prestation else decimal.Decimal(0)
        regle = dict_regle.get(cotisation.prestation_id, decimal.Decimal(0)) if cotisation.prestation_id else decimal.Decimal(0)
        return montant, regle

    data["montant"] = data["regle"] = decimal.Decimal(0)
    nbre_non_reglees = 0
    dict_unites = {}
    for cotisation in liste_cotisations:
        montant, regle = Get_montants(cotisation)
        data["montant"] += montant
        data["regle"] += regle
        if montant > regle:
            nbre_non_reglees += 1
        # Détail par unité
        key = (cotisation.type_cotisation.nom, cotisation.unite_cotisation.nom, cotisation.unite_cotisation_id)
        dict_unites.setdefault(key, {"type": key[0], "unite": key[1], "nbre": 0, "montant": decimal.Decimal(0), "regle": decimal.Decimal(0)})
        dict_unites[key]["nbre"] += 1
        dict_unites[key]["montant"] += montant
        dict_unites[key]["regle"] += regle
    data["reste"] = data["montant"] - data["regle"]
    data["taux_regle"] = round(100.0 * float(data["regle"]) / float(data["montant"])) if data["montant"] else None
    data["unites"] = []
    for key in sorted(dict_unites.keys(), key=lambda x: (x[0].lower(), x[1].lower())):
        dict_unite = dict_unites[key]
        dict_unite["reste"] = dict_unite["montant"] - dict_unite["regle"]
        data["unites"].append(dict_unite)

    # ------------------- Nouvelles adhésions par mois -------------------
    liste_mois = Get_liste_mois(date_debut, date_fin)
    dict_mois = {mois: 0 for mois in liste_mois}
    for cotisation in liste_cotisations:
        key = (cotisation.date_debut.year, cotisation.date_debut.month)
        if key in dict_mois and cotisation.date_debut >= date_debut:
            dict_mois[key] += 1
    graphe_mois = {"labels": [], "valeurs": [], "valeurs_precedentes": []}
    afficher_annee = len(liste_mois) > 12
    for annee, mois in liste_mois:
        graphe_mois["labels"].append("%s %s" % (MOIS_ABREGES[mois - 1], str(annee)[2:]) if afficher_annee else MOIS_ABREGES[mois - 1])
        graphe_mois["valeurs"].append(None if (annee, mois) > (aujourdhui.year, aujourdhui.month) else dict_mois[(annee, mois)])
    if comparer:
        liste_mois_precedents = Get_liste_mois(debut_precedente, fin_precedente)
        dict_mois_precedents = {mois: 0 for mois in liste_mois_precedents}
        for date_cotisation in cotisations_precedentes.filter(date_debut__gte=debut_precedente).values_list("date_debut", flat=True):
            key = (date_cotisation.year, date_cotisation.month)
            if key in dict_mois_precedents:
                dict_mois_precedents[key] += 1
        # Alignement mois par mois sur la période actuelle
        graphe_mois["valeurs_precedentes"] = [dict_mois_precedents[mois] for mois in liste_mois_precedents][:len(liste_mois)]

    # ------------------- Répartition par type -------------------
    dict_types = {}
    for cotisation in liste_cotisations:
        dict_types[cotisation.type_cotisation.nom] = dict_types.get(cotisation.type_cotisation.nom, 0) + 1
    liste_types = sorted(dict_types.items(), key=lambda x: -x[1])
    graphe_types = {"labels": [nom for nom, nbre in liste_types], "valeurs": [nbre for nom, nbre in liste_types]}

    # ------------------- Âge et sexe des adhérents individuels -------------------
    liste_idindividu = [id for categorie, id in adherents if categorie == "individu"]
    dict_sexes = Get_sexes_civilites()
    graphe_ages = {"labels": [label for mini, maxi, label in TRANCHES_AGES], "femmes": [0] * len(TRANCHES_AGES), "hommes": [0] * len(TRANCHES_AGES)}
    liste_ages, nbre_ages_inconnus = [], 0
    for individu in Individu.objects.filter(pk__in=liste_idindividu).only("pk", "civilite", "date_naiss"):
        age = individu.Get_age(today=date_fin)
        if age is None or age < 0:
            nbre_ages_inconnus += 1
            continue
        liste_ages.append(age)
        for index, (mini, maxi, label) in enumerate(TRANCHES_AGES):
            if mini <= age <= maxi:
                graphe_ages["femmes" if dict_sexes.get(individu.civilite) == "F" else "hommes"][index] += 1
                break
    data["age_moyen"] = round(sum(liste_ages) / len(liste_ages)) if liste_ages else None
    data["nbre_ages_inconnus"] = nbre_ages_inconnus

    # ------------------- Communes de résidence -------------------
    dict_communes = {}
    nbre_communes_inconnues = 0
    villes_individus = Get_villes_individus(liste_idindividu)
    liste_villes = list(villes_individus.values())
    liste_idfamille = [id for categorie, id in adherents if categorie == "famille"]
    liste_villes += [famille.ville_resid for famille in Famille.objects.filter(pk__in=liste_idfamille).only("pk", "ville_resid")]
    for ville in liste_villes:
        ville = Normaliser_ville(ville)
        if not ville:
            nbre_communes_inconnues += 1
            continue
        dict_communes[ville] = dict_communes.get(ville, 0) + 1
    liste_communes = sorted(dict_communes.items(), key=lambda x: (-x[1], x[0]))
    graphe_communes = {"labels": [ville.title() for ville, nbre in liste_communes[:NBRE_COMMUNES_AFFICHEES]],
                       "valeurs": [nbre for ville, nbre in liste_communes[:NBRE_COMMUNES_AFFICHEES]]}
    if len(liste_communes) > NBRE_COMMUNES_AFFICHEES:
        graphe_communes["labels"].append("Autres")
        graphe_communes["valeurs"].append(sum([nbre for ville, nbre in liste_communes[NBRE_COMMUNES_AFFICHEES:]]))
    data["nbre_communes"] = len(liste_communes)
    data["nbre_communes_inconnues"] = nbre_communes_inconnues

    # ------------------- Suivi administratif -------------------
    data["suivi"] = {
        "cartes": len([1 for cotisation in liste_cotisations if cotisation.type_cotisation.carte and not cotisation.date_creation_carte]),
        "non_deposees": len([1 for cotisation in liste_cotisations if not cotisation.depot_cotisation_id]),
        "non_reglees": nbre_non_reglees,
        "expirant": Cotisation.objects.filter(type_cotisation__in=types_cotisations, date_fin__gte=aujourdhui, date_fin__lte=aujourdhui + datetime.timedelta(days=30)).count(),
    }

    # Montants formatés pour l'affichage
    for key in ("montant", "regle", "reste"):
        data["%s_str" % key] = Format_montant(data[key])
    for dict_unite in data["unites"]:
        for key in ("montant", "regle", "reste"):
            dict_unite["%s_str" % key] = Format_montant(dict_unite[key])

    data["graphes"] = {"mois": graphe_mois, "types": graphe_types, "ages": graphe_ages, "communes": graphe_communes}
    return data


def Get_parametres(request):
    """ Validation du formulaire envoyé par les boutons d'export """
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
    nom_fichier = "statistiques_adhesions.xlsx"

    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    format_titre = classeur.add_format({"bold": True, "font_size": 14})
    format_entete = classeur.add_format({"bold": True, "bg_color": "#efefef", "border": 1})
    format_total = classeur.add_format({"bold": True, "top": 1})
    format_euros = classeur.add_format({"num_format": "#,##0.00 €"})
    format_euros_total = classeur.add_format({"num_format": "#,##0.00 €", "bold": True, "top": 1})

    def Ecrire_tableau(feuille, ligne, colonnes, lignes):
        for num_colonne, label in enumerate(colonnes):
            feuille.write(ligne, num_colonne, label, format_entete)
        for valeurs in lignes:
            ligne += 1
            for num_colonne, valeur in enumerate(valeurs):
                feuille.write(ligne, num_colonne, valeur)
        return ligne + 2

    # Feuille des indicateurs
    feuille = classeur.add_worksheet("Indicateurs")
    feuille.set_column(0, 0, 38)
    feuille.set_column(1, 1, 18)
    feuille.write(0, 0, "Statistiques des adhésions", format_titre)
    feuille.write(1, 0, "Période : %s" % data["periode_str"])
    feuille.write(2, 0, "Types d'adhésions : %s" % data["types"])
    indicateurs = [
        ("Nombre d'adhésions", data["nbre_cotisations"]),
        ("Nombre d'adhésions sur la période précédente", data["nbre_cotisations_precedentes"]),
        ("Nombre d'adhérents", data["nbre_adherents"]),
        ("Dont familles", data["nbre_familles"]),
        ("Dont individus", data["nbre_individus"]),
        ("Nouveaux adhérents", data["nbre_nouveaux"]),
        ("Taux de réadhésion (%)", data["taux_readhesion"] if data["taux_readhesion"] is not None else ""),
        ("Âge moyen des adhérents individuels", data["age_moyen"] if data["age_moyen"] is not None else ""),
        ("Cartes d'adhérent à éditer", data["suivi"]["cartes"]),
        ("Adhésions non déposées", data["suivi"]["non_deposees"]),
        ("Adhésions non réglées", data["suivi"]["non_reglees"]),
        ("Adhésions expirant sous 30 jours", data["suivi"]["expirant"]),
    ]
    ligne = Ecrire_tableau(feuille, 4, ("Indicateur", "Valeur"), indicateurs)
    for label, valeur in (("Montant des adhésions", data["montant"]), ("Montant réglé", data["regle"]), ("Reste dû", data["reste"])):
        feuille.write(ligne - 1, 0, label)
        feuille.write(ligne - 1, 1, float(valeur), format_euros)
        ligne += 1

    # Détail par unité
    feuille = classeur.add_worksheet("Unités d'adhésion")
    for num_colonne, largeur in enumerate((32, 28, 12, 14, 14, 14)):
        feuille.set_column(num_colonne, num_colonne, largeur)
    for num_colonne, label in enumerate(("Type", "Unité", "Adhésions", "Montant", "Réglé", "Reste dû")):
        feuille.write(0, num_colonne, label, format_entete)
    ligne = 1
    for unite in data["unites"]:
        feuille.write(ligne, 0, unite["type"])
        feuille.write(ligne, 1, unite["unite"])
        feuille.write(ligne, 2, unite["nbre"])
        for num_colonne, key in ((3, "montant"), (4, "regle"), (5, "reste")):
            feuille.write(ligne, num_colonne, float(unite[key]), format_euros)
        ligne += 1
    feuille.write(ligne, 0, "Total", format_total)
    feuille.write(ligne, 1, "", format_total)
    feuille.write(ligne, 2, data["nbre_cotisations"], format_total)
    for num_colonne, key in ((3, "montant"), (4, "regle"), (5, "reste")):
        feuille.write(ligne, num_colonne, float(data[key]), format_euros_total)

    # Graphiques sous forme de tableaux
    graphes = data["graphes"]
    feuille = classeur.add_worksheet("Par mois")
    feuille.set_column(0, 2, 18)
    colonnes = ("Mois", "Nouvelles adhésions") + (("Période précédente",) if data["comparer"] else ())
    lignes = []
    for index, label in enumerate(graphes["mois"]["labels"]):
        valeurs = [label, graphes["mois"]["valeurs"][index]]
        if data["comparer"]:
            precedentes = graphes["mois"]["valeurs_precedentes"]
            valeurs.append(precedentes[index] if index < len(precedentes) else "")
        lignes.append(valeurs)
    Ecrire_tableau(feuille, 0, colonnes, lignes)

    feuille = classeur.add_worksheet("Par type")
    feuille.set_column(0, 0, 36)
    feuille.set_column(1, 1, 14)
    Ecrire_tableau(feuille, 0, ("Type d'adhésion", "Adhésions"), zip(graphes["types"]["labels"], graphes["types"]["valeurs"]))

    feuille = classeur.add_worksheet("Âges")
    feuille.set_column(0, 3, 16)
    Ecrire_tableau(feuille, 0, ("Tranche d'âge", "Filles / femmes", "Garçons / hommes", "Total"),
                   [(label, f, h, f + h) for label, f, h in zip(graphes["ages"]["labels"], graphes["ages"]["femmes"], graphes["ages"]["hommes"])])

    feuille = classeur.add_worksheet("Communes")
    feuille.set_column(0, 0, 30)
    feuille.set_column(1, 1, 14)
    Ecrire_tableau(feuille, 0, ("Commune", "Adhérents"), zip(graphes["communes"]["labels"], graphes["communes"]["valeurs"]))

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

    # Images des graphiques générées par Chart.js
    images = {}
    for nom in ("mois", "types", "ages", "communes"):
        valeur = request.POST.get("graphique_%s" % nom, "")
        if valeur.startswith("data:image/png;base64,") and len(valeur) < 5000000:
            try:
                images[nom] = base64.b64decode(valeur.split(",", 1)[1])
            except Exception:
                logger.warning("Image du graphique '%s' invalide" % nom)

    impression = Impression_statistiques(titre="Statistiques des adhésions", dict_donnees={"data": data, "images": images}, request=request)
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
        # Marges alignées sur la largeur de l'en-tête standard
        self.doc.leftMargin = self.doc.rightMargin = (self.taille_page[0] - largeur) / 2.0
        bleu = colors.HexColor("#3c8dbc")
        style_titre = ParagraphStyle("titre", fontName=utils_polices.FONT_BOLD, fontSize=11, textColor=bleu, spaceBefore=6, spaceAfter=6)
        style_texte = ParagraphStyle("texte", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=11)

        self.Insert_header(detail="Période : %s" % data["periode_str"])
        self.story.append(Paragraph("<b>Types d'adhésions :</b> %s" % data["types"], style_texte))
        self.story.append(Spacer(0, 10))

        # Indicateurs clés
        def Evolution(valeur, unite="%"):
            if valeur is None or not data["comparer"]:
                return ""
            return " (%s%s %s)" % ("+" if valeur >= 0 else "", valeur, unite)
        indicateurs = [
            ("Adhésions", "%s%s" % (data["nbre_cotisations"], Evolution(data["evolution_cotisations"]))),
            ("Adhérents", "%s (%s familles, %s individus)" % (data["nbre_adherents"], data["nbre_familles"], data["nbre_individus"])),
            ("Montant", "%s (réglé : %s, reste : %s)" % (Format_montant(data["montant"]), Format_montant(data["regle"]), Format_montant(data["reste"]))),
            ("Taux de réadhésion", "%s%s - %s nouveaux adhérents" % ("%s %%" % data["taux_readhesion"] if data["taux_readhesion"] is not None else "-", Evolution(data["evolution_taux_readhesion"], "pts"), data["nbre_nouveaux"])),
        ]
        suivi = [
            ("Cartes d'adhérent à éditer", data["suivi"]["cartes"]),
            ("Adhésions non déposées", data["suivi"]["non_deposees"]),
            ("Adhésions non réglées", data["suivi"]["non_reglees"]),
            ("Adhésions expirant sous 30 jours", data["suivi"]["expirant"]),
        ]
        lignes = [(Paragraph("<b>%s</b>" % label, style_texte), Paragraph(valeur, style_texte), "", label_suivi, valeur_suivi)
                  for (label, valeur), (label_suivi, valeur_suivi) in zip(indicateurs, suivi)]
        lignes.insert(0, (Paragraph("Indicateurs clés", style_titre), "", "", Paragraph("Suivi administratif", style_titre), ""))
        tableau = Table(lignes, [90, largeur * 0.62 - 90, 12, largeur * 0.38 - 52, 40])
        tableau.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)), ("SPAN", (3, 0), (4, 0)),
            ("FONT", (3, 1), (3, -1), utils_polices.FONT_NORMAL, 8), ("FONT", (4, 1), (4, -1), utils_polices.FONT_BOLD, 8),
            ("ALIGN", (4, 1), (4, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 1), (1, -1), 0.25, colors.HexColor("#dee2e6")), ("LINEBELOW", (3, 1), (4, -1), 0.25, colors.HexColor("#dee2e6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ]))
        self.story.append(tableau)
        self.story.append(Spacer(0, 8))

        # Graphiques (deux par ligne)
        titres = {"mois": "Nouvelles adhésions par mois", "types": "Répartition par type d'adhésion",
                  "ages": "Âge des adhérents individuels", "communes": "Communes de résidence"}
        largeur_image = (largeur - 10) / 2
        for paire in (("mois", "types"), ("ages", "communes")):
            cellules = []
            for nom in paire:
                contenu = [Paragraph(titres[nom], style_titre)]
                if nom in images:
                    image = Image(io.BytesIO(images[nom]))
                    ratio = image.imageHeight / float(image.imageWidth)
                    image.drawWidth, image.drawHeight = largeur_image, largeur_image * ratio
                    contenu.append(image)
                else:
                    contenu.append(Paragraph("Graphique non disponible", style_texte))
                cellules.append(contenu)
            tableau = Table([cellules], [largeur_image + 5, largeur_image + 5])
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            self.story.append(tableau)
            self.story.append(Spacer(0, 6))

        # Détail par unité
        lignes = [("Type", "Unité", "Adhésions", "Montant", "Réglé", "Reste dû")]
        for unite in data["unites"]:
            lignes.append((Paragraph(unite["type"], style_texte), Paragraph(unite["unite"], style_texte), unite["nbre"],
                           Format_montant(unite["montant"]), Format_montant(unite["regle"]), Format_montant(unite["reste"])))
        lignes.append(("Total", "", data["nbre_cotisations"], Format_montant(data["montant"]), Format_montant(data["regle"]), Format_montant(data["reste"])))
        tableau = Table(lignes, [largeur * 0.27, largeur * 0.25, largeur * 0.11, largeur * 0.125, largeur * 0.12, largeur * 0.125], repeatRows=1)
        tableau.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 8), ("FONT", (0, 0), (-1, 0), utils_polices.FONT_BOLD, 8),
            ("FONT", (0, -1), (-1, -1), utils_polices.FONT_BOLD, 8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8f9fa")), ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dee2e6")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        self.story.append(KeepTogether([Paragraph("Détail par unité d'adhésion", style_titre), tableau]))



class View(CustomView, TemplateView):
    menu_code = "statistiques_cotisations"
    template_name = "cotisations/statistiques_cotisations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Statistiques des adhésions"
        if "form_parametres" not in kwargs:
            # Premier affichage : calcul avec les paramètres par défaut
            form = Formulaire(request=self.request)
            context["form_parametres"] = form
            parametres = {"periode": form.fields["periode"].initial, "types_cotisations": list(form.fields["types_cotisations"].initial), "comparer": True}
            if parametres["types_cotisations"]:
                context["data"] = Get_data(parametres)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        return self.render_to_response(self.get_context_data(form_parametres=form, data=Get_data(form.cleaned_data)))
