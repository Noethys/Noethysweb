# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, decimal, base64, io, os, uuid, json
logger = logging.getLogger(__name__)
from django.conf import settings
from django.db.models import Sum, Count, Value, IntegerField
from django.db.models.functions import Coalesce, TruncMonth
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Activite, Consommation, Prestation, Individu
from core.data import data_civilites
from core.utils import utils_dates
from core.utils.utils_impression import Impression
from consommations.forms.statistiques_consommations import Formulaire

PERMISSION = "core.statistiques_consommations"
MOIS_ABREGES = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
JOURS_ABREGES = ("Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim.")
TRANCHES_AGES = ((0, 2, "0-2"), (3, 5, "3-5"), (6, 8, "6-8"), (9, 11, "9-11"), (12, 14, "12-14"), (15, 17, "15-17"), (18, 200, "18 et +"))
NBRE_ACTIVITES_AFFICHEES = 8
ETATS_POINTES = ("present", "absentj", "absenti")
LIBELLES_ETATS = {"reservation_future": "Réservation à venir", "reservation_passee": "Réservation non pointée", "present": "Présent",
                  "absentj": "Absence justifiée", "absenti": "Absence injustifiée", "attente": "Attente", "refus": "Refus"}
QUANTITE = Coalesce("quantite", Value(1), output_field=IntegerField())


# ---------------------------------------- Utilitaires ----------------------------------------

def Format_montant(valeur):
    return "{:,.2f} €".format(float(valeur or 0)).replace(",", " ").replace(".", ",")


def Format_nombre(valeur, decimales=0):
    texte = "{:,.{}f}".format(float(valeur or 0), decimales)
    return texte.replace(",", " ").replace(".", ",")


def Pourcentage(valeur, total, decimales=0):
    if not total:
        return None
    return round(100.0 * valeur / total, decimales) if decimales else round(100.0 * valeur / total)


def Get_sexes_civilites():
    dict_sexes = {}
    for categorie, items in data_civilites.LISTE_CIVILITES:
        for civilite in items:
            dict_sexes[civilite["id"]] = civilite.get("sexe")
    return dict_sexes


def Get_activites(selection_json=""):
    selection = json.loads(selection_json)
    if selection["type"] == "groupes_activites":
        return Activite.objects.filter(groupes_activites__in=selection["ids"]).distinct()
    if selection["type"] == "groupes":
        return Activite.objects.filter(groupe__in=selection["ids"]).distinct()
    return Activite.objects.filter(pk__in=selection["ids"])


def Get_liste_mois(date_debut=None, date_fin=None):
    liste_mois, annee, mois = [], date_debut.year, date_debut.month
    while (annee, mois) <= (date_fin.year, date_fin.month):
        liste_mois.append((annee, mois))
        mois += 1
        if mois > 12:
            annee, mois = annee + 1, 1
    return liste_mois


def Total(queryset):
    return queryset.aggregate(total=Sum(QUANTITE))["total"] or 0


# ---------------------------------------- Calculs ----------------------------------------

def Get_data(parametres={}):
    date_debut, date_fin = [utils_dates.ConvertDateENGtoDate(x) for x in parametres["periode"].split(";")]
    etats = parametres["etats"]
    comparer = parametres.get("comparer", False)
    aujourdhui = datetime.date.today()
    activites = list(Get_activites(parametres["activites"]))

    # Période précédente de même durée et comparaison à date équivalente si la période est en cours
    duree = date_fin - date_debut
    fin_precedente = date_debut - datetime.timedelta(days=1)
    debut_precedente = fin_precedente - duree
    en_cours = date_debut <= aujourdhui < date_fin
    date_equivalente = aujourdhui - (date_debut - debut_precedente) if en_cours else fin_precedente

    data = {
        "comparer": comparer, "en_cours": en_cours, "nbre_activites": len(activites),
        "date_debut_str": utils_dates.ConvertDateToFR(date_debut), "date_fin_str": utils_dates.ConvertDateToFR(date_fin),
        "periode_str": "%s - %s" % (utils_dates.ConvertDateToFR(date_debut), utils_dates.ConvertDateToFR(date_fin)),
        "periode_precedente_str": "%s - %s" % (utils_dates.ConvertDateToFR(debut_precedente), utils_dates.ConvertDateToFR(fin_precedente)),
        "date_equivalente_str": utils_dates.ConvertDateToFR(date_equivalente),
        "activites": ", ".join(sorted([activite.nom for activite in activites])),
        "etats": ", ".join([label for code, label in Formulaire.base_fields["etats"].choices if code in etats]),
    }

    base = Consommation.objects.filter(activite__in=activites, date__gte=date_debut, date__lte=date_fin)
    consos = base.filter(etat__in=etats)
    base_precedente = Consommation.objects.filter(activite__in=activites, date__gte=debut_precedente, date__lte=fin_precedente)
    consos_precedentes = base_precedente.filter(etat__in=etats)

    # ------------------- Consommations et évolution -------------------
    data["nbre_consos"] = Total(consos)
    if en_cours:
        nbre_comparable, nbre_precedent = Total(consos.filter(date__lte=aujourdhui)), Total(consos_precedentes.filter(date__lte=date_equivalente))
    else:
        nbre_comparable, nbre_precedent = data["nbre_consos"], Total(consos_precedentes)
    data["nbre_consos_precedentes"] = nbre_precedent
    data["evolution_consos"] = Pourcentage(nbre_comparable - nbre_precedent, nbre_precedent) if nbre_precedent else None

    # ------------------- Individus et familles -------------------
    data["nbre_individus"] = consos.exclude(individu__isnull=True).values("individu_id").distinct().count()
    data["nbre_familles"] = consos.exclude(inscription__isnull=True).values("inscription__famille_id").distinct().count()
    data["consos_par_individu"] = Format_nombre(data["nbre_consos"] / data["nbre_individus"], 1) if data["nbre_individus"] else "0"

    # ------------------- Taux de présence (dates passées) -------------------
    pointees = {etat: total for etat, total in base.filter(date__lte=aujourdhui, etat__in=ETATS_POINTES).values_list("etat").annotate(total=Sum(QUANTITE))}
    total_pointees = sum(pointees.values())
    data["taux_presence"] = Pourcentage(pointees.get("present", 0), total_pointees)
    data["taux_absj"] = Format_nombre(Pourcentage(pointees.get("absentj", 0), total_pointees, 1) or 0, 1)
    data["taux_absi"] = Format_nombre(Pourcentage(pointees.get("absenti", 0), total_pointees, 1) or 0, 1)

    # ------------------- Prestations : montant facturé -------------------
    def Get_prestations(queryset):
        return Prestation.objects.filter(pk__in=queryset.exclude(prestation__isnull=True).values("prestation_id"))
    data["montant"] = Get_prestations(consos).aggregate(total=Sum("montant"))["total"] or decimal.Decimal(0)
    data["cout_moyen"] = Format_montant(data["montant"] / data["nbre_consos"]) if data["nbre_consos"] else Format_montant(0)
    consos_comparables = consos.filter(date__lte=aujourdhui) if en_cours else consos
    consos_precedentes_comparables = consos_precedentes.filter(date__lte=date_equivalente) if en_cours else consos_precedentes
    montant_comparable = Get_prestations(consos_comparables).aggregate(total=Sum("montant"))["total"] or decimal.Decimal(0)
    montant_precedent = Get_prestations(consos_precedentes_comparables).aggregate(total=Sum("montant"))["total"] or decimal.Decimal(0)
    data["evolution_montant"] = Pourcentage(float(montant_comparable - montant_precedent), float(montant_precedent)) if montant_precedent else None

    # ------------------- Graphique : consommations par mois -------------------
    liste_mois = Get_liste_mois(date_debut, date_fin)
    afficher_annee = len(liste_mois) > 12
    labels_mois = [("%s %s" % (MOIS_ABREGES[m - 1], str(a)[2:])) if afficher_annee else MOIS_ABREGES[m - 1] for a, m in liste_mois]
    dict_mois = {(mois.year, mois.month): total for mois, total in consos.annotate(mois=TruncMonth("date")).values_list("mois").annotate(total=Sum(QUANTITE))}
    graphe_mois = {"labels": labels_mois, "valeurs": [dict_mois.get(mois, 0) for mois in liste_mois], "valeurs_precedentes": []}
    if comparer:
        liste_mois_precedents = Get_liste_mois(debut_precedente, fin_precedente)
        dict_mois_precedents = {(mois.year, mois.month): total for mois, total in consos_precedentes.annotate(mois=TruncMonth("date")).values_list("mois").annotate(total=Sum(QUANTITE))}
        graphe_mois["valeurs_precedentes"] = [dict_mois_precedents.get(mois, 0) for mois in liste_mois_precedents][:len(liste_mois)]

    # ------------------- Graphique : états -------------------
    dict_etats = {}
    for etat, date_futur, total in [(etat, False, total) for etat, total in consos.filter(date__lte=aujourdhui).values_list("etat").annotate(total=Sum(QUANTITE))] + \
                                   [(etat, True, total) for etat, total in consos.filter(date__gt=aujourdhui).values_list("etat").annotate(total=Sum(QUANTITE))]:
        code = ("reservation_future" if date_futur else "reservation_passee") if etat == "reservation" else etat
        dict_etats[code] = dict_etats.get(code, 0) + total
    ordre_etats = ("present", "reservation_future", "reservation_passee", "absentj", "absenti", "attente", "refus")
    graphe_etats = {"codes": [code for code in ordre_etats if dict_etats.get(code)],
                    "labels": [LIBELLES_ETATS[code] for code in ordre_etats if dict_etats.get(code)],
                    "valeurs": [dict_etats[code] for code in ordre_etats if dict_etats.get(code)]}

    # ------------------- Graphique : répartition par activité (ou par unité si une seule activité) -------------------
    if len(activites) == 1:
        data["titre_repartition"] = "Répartition par unité"
        repartition = consos.values_list("unite__nom").annotate(total=Sum(QUANTITE)).order_by("-total")
    else:
        data["titre_repartition"] = "Répartition par activité"
        repartition = consos.values_list("activite__nom").annotate(total=Sum(QUANTITE)).order_by("-total")
    repartition = [(nom or "Non renseigné", total) for nom, total in repartition]
    graphe_repartition = {"labels": [nom for nom, total in repartition[:NBRE_ACTIVITES_AFFICHEES]], "valeurs": [total for nom, total in repartition[:NBRE_ACTIVITES_AFFICHEES]]}
    if len(repartition) > NBRE_ACTIVITES_AFFICHEES:
        graphe_repartition["labels"].append("Autres")
        graphe_repartition["valeurs"].append(sum([total for nom, total in repartition[NBRE_ACTIVITES_AFFICHEES:]]))

    # ------------------- Graphique : fréquentation moyenne par jour de la semaine -------------------
    totaux_jours, dates_jours = [0] * 7, [0] * 7
    for date, total in consos.values_list("date").annotate(total=Sum(QUANTITE)):
        totaux_jours[date.weekday()] += total
        dates_jours[date.weekday()] += 1
    graphe_jours = {"labels": list(JOURS_ABREGES), "valeurs": [round(totaux_jours[i] / dates_jours[i]) if dates_jours[i] else 0 for i in range(7)]}

    # ------------------- Graphique : âge et sexe des individus -------------------
    date_reference = max(date_debut, min(date_fin, aujourdhui))
    dict_sexes = Get_sexes_civilites()
    graphe_ages = {"labels": [label for mini, maxi, label in TRANCHES_AGES], "femmes": [0] * len(TRANCHES_AGES), "hommes": [0] * len(TRANCHES_AGES)}
    liste_ages, nbre_ages_inconnus = [], 0
    for individu in Individu.objects.filter(pk__in=consos.values("individu_id")).only("pk", "civilite", "date_naiss"):
        age = individu.Get_age(today=date_reference)
        if age is None or age < 0:
            nbre_ages_inconnus += 1
            continue
        liste_ages.append(age)
        for index, (mini, maxi, label) in enumerate(TRANCHES_AGES):
            if mini <= age <= maxi:
                graphe_ages["femmes" if dict_sexes.get(individu.civilite) == "F" else "hommes"][index] += 1
                break
    data["age_moyen"] = Format_nombre(sum(liste_ages) / len(liste_ages), 1) if liste_ages else None
    data["nbre_ages_inconnus"] = nbre_ages_inconnus

    # ------------------- Détail par activité et par unité -------------------
    dict_lignes = {}
    for idactivite, nom_activite, idunite, nom_unite, total, nbre_individus in consos.values_list("activite_id", "activite__nom", "unite_id", "unite__nom") \
            .annotate(total=Sum(QUANTITE), nbre_individus=Count("individu_id", distinct=True)):
        dict_lignes[(idactivite, idunite)] = {"activite": nom_activite or "", "unite": nom_unite or "", "nbre": total, "individus": nbre_individus,
                                              "pointees": {}, "montant": decimal.Decimal(0)}
    for idactivite, idunite, etat, total in base.filter(date__lte=aujourdhui, etat__in=ETATS_POINTES).values_list("activite_id", "unite_id", "etat").annotate(total=Sum(QUANTITE)):
        if (idactivite, idunite) in dict_lignes:
            dict_lignes[(idactivite, idunite)]["pointees"][etat] = total
    # Chaque prestation est rattachée à la première unité rencontrée (une prestation peut regrouper plusieurs unités)
    unites_prestations = {}
    for idprestation, idactivite, idunite in consos.exclude(prestation__isnull=True).values_list("prestation_id", "activite_id", "unite_id").order_by("prestation_id", "unite_id"):
        unites_prestations.setdefault(idprestation, (idactivite, idunite))
    for idprestation, montant in Prestation.objects.filter(pk__in=unites_prestations.keys()).values_list("pk", "montant"):
        ligne = dict_lignes.get(unites_prestations[idprestation])
        if ligne:
            ligne["montant"] += montant or decimal.Decimal(0)
    data["lignes"] = []
    for key in sorted(dict_lignes.keys(), key=lambda x: (dict_lignes[x]["activite"].lower(), dict_lignes[x]["unite"].lower())):
        ligne = dict_lignes[key]
        total_pointees = sum(ligne["pointees"].values())
        taux_presence = Pourcentage(ligne["pointees"].get("present", 0), total_pointees)
        taux_absi = Pourcentage(ligne["pointees"].get("absenti", 0), total_pointees, 1)
        ligne.update({
            "nbre_str": Format_nombre(ligne["nbre"]), "individus_str": Format_nombre(ligne["individus"]),
            "taux_presence_str": "%s %%" % taux_presence if taux_presence is not None else "-",
            "taux_absi_str": "%s %%" % Format_nombre(taux_absi, 1) if taux_absi is not None else "-",
            "montant_str": Format_montant(ligne["montant"]),
        })
        data["lignes"].append(ligne)

    # ------------------- Suivi administratif -------------------
    data["suivi"] = {
        "non_pointees": Total(base.filter(etat="reservation", date__lt=aujourdhui)),
        "demandes": Total(base.filter(etat="demande")),
        "attente": Total(base.filter(etat="attente")),
        "sans_prestation": Total(base.filter(etat__in=("reservation", "present", "absenti"), date__lt=aujourdhui, prestation__isnull=True)),
    }

    # Valeurs formatées
    data["nbre_consos_str"] = Format_nombre(data["nbre_consos"])
    data["nbre_individus_str"] = Format_nombre(data["nbre_individus"])
    data["nbre_familles_str"] = Format_nombre(data["nbre_familles"])
    data["montant_str"] = Format_montant(data["montant"])
    data["graphes"] = {"mois": graphe_mois, "etats": graphe_etats, "repartition": graphe_repartition, "jours": graphe_jours, "ages": graphe_ages}
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
    nom_fichier = "statistiques_consommations.xlsx"

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
    feuille.write(0, 0, "Statistiques des consommations", format_titre)
    feuille.write(1, 0, "Période : %s" % data["periode_str"])
    feuille.write(2, 0, "Activités : %s" % data["activites"])
    feuille.write(3, 0, "États pris en compte : %s" % data["etats"])
    indicateurs = [
        ("Nombre de consommations", data["nbre_consos"]),
        ("Évolution par rapport à la période précédente (%)", data["evolution_consos"] if data["evolution_consos"] is not None else ""),
        ("Individus accueillis", data["nbre_individus"]),
        ("Familles", data["nbre_familles"]),
        ("Taux de présence (%)", data["taux_presence"] if data["taux_presence"] is not None else ""),
        ("Réservations passées non pointées", data["suivi"]["non_pointees"]),
        ("Demandes du portail à traiter", data["suivi"]["demandes"]),
        ("Places en liste d'attente", data["suivi"]["attente"]),
        ("Consommations passées sans prestation", data["suivi"]["sans_prestation"]),
    ]
    ligne = Ecrire_tableau(feuille, 5, ("Indicateur", "Valeur"), indicateurs)
    feuille.write(ligne - 1, 0, "Montant facturé")
    feuille.write(ligne - 1, 1, float(data["montant"]), format_euros)

    # Détail par activité et par unité
    feuille = classeur.add_worksheet("Détail")
    for num_colonne, largeur in enumerate((34, 24, 14, 12, 12, 14, 14)):
        feuille.set_column(num_colonne, num_colonne, largeur)
    Ecrire_tableau(feuille, 0, ("Activité", "Unité", "Consommations", "Individus", "Présence (%)", "Abs. injust. (%)", "Montant"),
                   [(l["activite"], l["unite"], l["nbre"], l["individus"], l["taux_presence_str"].replace(" %", ""), l["taux_absi_str"].replace(" %", ""),
                     float(l["montant"])) for l in data["lignes"]],
                   formats={6: format_euros})

    # Données des graphiques
    graphes = data["graphes"]
    feuille = classeur.add_worksheet("Par mois")
    feuille.set_column(0, 2, 18)
    lignes = []
    for index, label in enumerate(graphes["mois"]["labels"]):
        precedentes = graphes["mois"]["valeurs_precedentes"]
        lignes.append((label, graphes["mois"]["valeurs"][index], precedentes[index] if index < len(precedentes) else ""))
    Ecrire_tableau(feuille, 0, ("Mois", "Consommations", "Période précédente"), lignes)

    feuille = classeur.add_worksheet("États")
    feuille.set_column(0, 1, 24)
    Ecrire_tableau(feuille, 0, ("État", "Consommations"), zip(graphes["etats"]["labels"], graphes["etats"]["valeurs"]))

    feuille = classeur.add_worksheet("Jours")
    feuille.set_column(0, 1, 20)
    Ecrire_tableau(feuille, 0, ("Jour", "Moyenne par jour d'activité"), zip(graphes["jours"]["labels"], graphes["jours"]["valeurs"]))

    feuille = classeur.add_worksheet("Âges")
    feuille.set_column(0, 3, 16)
    Ecrire_tableau(feuille, 0, ("Tranche d'âge", "Filles / femmes", "Garçons / hommes", "Total"),
                   [(label, f, h, f + h) for label, f, h in zip(graphes["ages"]["labels"], graphes["ages"]["femmes"], graphes["ages"]["hommes"])])

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
    for nom in ("mois", "etats", "repartition", "ages", "jours"):
        valeur = request.POST.get("graphique_%s" % nom, "")
        if valeur.startswith("data:image/png;base64,") and len(valeur) < 5000000:
            try:
                images[nom] = base64.b64decode(valeur.split(",", 1)[1])
            except Exception:
                logger.warning("Image du graphique '%s' invalide" % nom)

    impression = Impression_statistiques(titre="Statistiques des consommations", dict_donnees={"data": data, "images": images}, request=request)
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
        style_petit = ParagraphStyle("petit", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=10)

        self.Insert_header(detail="Période : %s" % data["periode_str"])
        self.story.append(Paragraph("<b>Activités :</b> %s" % data["activites"], style_texte))
        self.story.append(Paragraph("<b>États pris en compte :</b> %s" % data["etats"], style_texte))
        self.story.append(Spacer(0, 6))

        def Evolution(valeur):
            if valeur is None or not data["comparer"]:
                return ""
            return " (%s%s %%)" % ("+" if valeur >= 0 else "", valeur)

        # Indicateurs clés et suivi côte à côte
        indicateurs = [
            ("Consommations", "%s%s" % (data["nbre_consos_str"], Evolution(data["evolution_consos"]))),
            ("Individus accueillis", "%s (%s familles, %s consos / individu)" % (data["nbre_individus_str"], data["nbre_familles_str"], data["consos_par_individu"])),
            ("Taux de présence", "%s (abs. justifiées %s %%, injustifiées %s %%)" % ("%s %%" % data["taux_presence"] if data["taux_presence"] is not None else "-", data["taux_absj"], data["taux_absi"])),
            ("Montant facturé", "%s%s - %s par consommation" % (data["montant_str"], Evolution(data["evolution_montant"]), data["cout_moyen"])),
        ]
        suivi = [
            ("Réservations passées non pointées", data["suivi"]["non_pointees"]),
            ("Demandes du portail à traiter", data["suivi"]["demandes"]),
            ("Places en liste d'attente", data["suivi"]["attente"]),
            ("Consommations passées sans prestation", data["suivi"]["sans_prestation"]),
        ]
        lignes = [(Paragraph("<b>%s</b>" % label, style_texte), Paragraph(valeur, style_texte), "", label_suivi, valeur_suivi)
                  for (label, valeur), (label_suivi, valeur_suivi) in zip(indicateurs, suivi)]
        lignes.insert(0, (Paragraph("Indicateurs clés", style_titre), "", "", Paragraph("Suivi administratif", style_titre), ""))
        tableau = Table(lignes, [95, largeur * 0.6 - 95, 12, largeur * 0.4 - 52, 40])
        tableau.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)), ("SPAN", (3, 0), (4, 0)),
            ("FONT", (3, 1), (3, -1), utils_polices.FONT_NORMAL, 8), ("FONT", (4, 1), (4, -1), utils_polices.FONT_BOLD, 8),
            ("ALIGN", (4, 1), (4, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 1), (1, -1), 0.25, gris), ("LINEBELOW", (3, 1), (4, 4), 0.25, gris),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ]))
        self.story.append(tableau)
        self.story.append(Spacer(0, 6))

        # Graphiques (deux par ligne)
        titres = {"mois": "Consommations par mois", "etats": "États des consommations",
                  "repartition": data["titre_repartition"], "ages": "Âge des individus accueillis", "jours": "Fréquentation moyenne par jour"}
        largeur_image = (largeur - 10) / 2
        paires = (("mois", "etats"), ("repartition", "jours"), ("ages",))
        for paire in paires:
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

        # Détail par activité et par unité
        lignes = [("Activité", "Unité", "Consos", "Individus", "Présence", "Abs. inj.", "Montant")]
        for ligne in data["lignes"]:
            lignes.append((Paragraph(ligne["activite"], style_petit), Paragraph(ligne["unite"], style_petit), ligne["nbre_str"], ligne["individus_str"],
                           ligne["taux_presence_str"], ligne["taux_absi_str"], ligne["montant_str"]))
        lignes.append(("Total", "", data["nbre_consos_str"], data["nbre_individus_str"], "%s %%" % data["taux_presence"] if data["taux_presence"] is not None else "-",
                       "%s %%" % data["taux_absi"], data["montant_str"]))
        proportions = (0.30, 0.18, 0.10, 0.10, 0.10, 0.10, 0.12)
        tableau = Table(lignes, [largeur * p for p in proportions], repeatRows=1)
        tableau.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 8), ("FONT", (0, 0), (-1, 0), utils_polices.FONT_BOLD, 8),
            ("FONT", (0, -1), (-1, -1), utils_polices.FONT_BOLD, 8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8f9fa")), ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, gris), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        self.story.append(KeepTogether([Paragraph("Détail par activité et par unité", style_titre), tableau]))


# ---------------------------------------- Vue ----------------------------------------

class View(CustomView, TemplateView):
    menu_code = "statistiques_consommations"
    template_name = "consommations/statistiques_consommations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Statistiques des consommations"
        if "form_parametres" not in kwargs:
            context["form_parametres"] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        return self.render_to_response(self.get_context_data(form_parametres=form, data=Get_data(form.cleaned_data)))
