# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json, logging, os, uuid
logger = logging.getLogger(__name__)
from django.conf import settings
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Regime, Parametre
from core.utils import utils_dates
from core.utils.utils_impression import Impression
from consommations.forms.frequentation_caf import Form_selection, Form_profil, Get_profils, CATEGORIE_PROFIL
from consommations.utils import utils_frequentation_caf as moteur

PERMISSION = "core.frequentation_caf"
ERREUR_PERMISSION = "Vous n'avez pas la permission d'accéder à cette fonctionnalité"


def Verifier_permission(request):
    return request.user.has_perm(PERMISSION)


def Get_parametres(request):
    """ Lit et valide les paramètres envoyés par la page. Retourne (parametres, JsonResponse d'erreur) """
    try:
        return moteur.Normaliser_parametres(request.POST.get("parametres", "{}"), request=request), None
    except moteur.Erreur_parametres as err:
        return None, JsonResponse({"erreur": str(err)}, status=401)


# ---------------------------------------- AJAX ----------------------------------------

def Get_unites(request):
    """ Unités des activités sélectionnées avec les méthodes de calcul suggérées """
    if not Verifier_permission(request):
        return JsonResponse({"erreur": ERREUR_PERMISSION}, status=401)
    try:
        donnees = json.loads(request.POST.get("parametres", "{}"))
        date_debut = datetime.date.fromisoformat(donnees["date_debut"])
        date_fin = datetime.date.fromisoformat(donnees["date_fin"])
        activites = moteur.Get_activites_autorisees(donnees["activites"], request=request)
    except (KeyError, TypeError, ValueError):
        return JsonResponse({"erreur": "Sélectionnez une période et des activités"}, status=401)
    liste_activites = moteur.Get_unites(activites=activites, date_debut=date_debut, date_fin=date_fin)
    if not liste_activites:
        return JsonResponse({"erreur": "Aucune unité de consommation n'a été trouvée pour ces activités sur cette période"}, status=401)
    return JsonResponse({"activites": liste_activites})


def Compter_population(request):
    """ Compteur "X enfants retenus sur Y" de l'étape Qui compter ? """
    if not Verifier_permission(request):
        return JsonResponse({"erreur": ERREUR_PERMISSION}, status=401)
    parametres, erreur = Get_parametres(request)
    if erreur:
        return erreur
    return JsonResponse(moteur.Compter_population(parametres))


def Get_exemple(request):
    """ Exemple de calcul sur une consommation réelle pour une unité et une colonne """
    if not Verifier_permission(request):
        return JsonResponse({"erreur": ERREUR_PERMISSION}, status=401)
    try:
        donnees = json.loads(request.POST.get("parametres", "{}"))
        idunite = int(request.POST.get("idunite"))
        colonne = request.POST.get("colonne")
        date_debut = datetime.date.fromisoformat(donnees["date_debut"])
        date_fin = datetime.date.fromisoformat(donnees["date_fin"])
        donnees_colonne = donnees["colonnes"][colonne]
        parametres_unite = donnees_colonne["unites"][str(idunite)]
    except (KeyError, TypeError, ValueError):
        return JsonResponse({"texte": ""})

    # Vérifie que l'unité appartient à une activité accessible
    activites = moteur.Get_activites_autorisees(donnees.get("activites", {"type": "activites", "ids": []}), request=request)
    if not activites.filter(unite=idunite).exists():
        return JsonResponse({"texte": ""})

    try:
        # Validation de la méthode de cette seule unité
        donnees_test = dict(donnees, colonnes={colonne: {"active": True, "etats": donnees_colonne.get("etats") or ["present"], "unites": {str(idunite): parametres_unite}}})
        parametres = moteur.Normaliser_parametres(dict(donnees_test, filtres=[]), request=request)
        parametres_unite = parametres["colonnes"][colonne]["unites"][idunite]
        etats = [e for e in parametres["colonnes"][colonne]["etats"] if e != "reservation"] or parametres["colonnes"][colonne]["etats"]
        return JsonResponse(moteur.Get_exemple(parametres_unite, idunite, date_debut, date_fin, etats))
    except moteur.Erreur_parametres as err:
        return JsonResponse({"texte": str(err), "erreur": True})


def Calculer(request):
    """ Calcul et rendu des résultats """
    if not Verifier_permission(request):
        return JsonResponse({"erreur": ERREUR_PERMISSION}, status=401)
    parametres, erreur = Get_parametres(request)
    if erreur:
        return erreur
    calcul = moteur.Calcul(parametres, request=request)
    resultats = calcul.Calculer()
    if calcul.erreurs:
        return JsonResponse({"erreur": calcul.erreurs[0]}, status=401)
    html = render_to_string("consommations/frequentation_caf_resultats.html", {"resultats": resultats, "resume": calcul.Get_resume_parametres()}, request=request)
    return JsonResponse({"html": html, "graphe": resultats["graphe"]})


def Exporter_excel(request):
    """ Export des résultats au format Excel """
    if not Verifier_permission(request):
        return JsonResponse({"erreur": ERREUR_PERMISSION}, status=401)
    parametres, erreur = Get_parametres(request)
    if erreur:
        return erreur
    calcul = moteur.Calcul(parametres, request=request)
    resultats = calcul.Calculer()
    if calcul.erreurs:
        return JsonResponse({"erreur": calcul.erreurs[0]}, status=401)

    rep_temp = os.path.join("temp", str(uuid.uuid4()))
    rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
    os.makedirs(rep_destination, exist_ok=True)
    nom_fichier = "frequentation_caf.xlsx"

    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    horaire = resultats["format"] == "horaire"
    formats = {
        "titre": classeur.add_format({"bold": True, "font_size": 14}),
        "gras": classeur.add_format({"bold": True}),
        "entete": classeur.add_format({"bold": True, "bg_color": "#efefef", "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True}),
        "groupe": classeur.add_format({"bold": True, "bg_color": "#3c8dbc", "font_color": "#ffffff", "border": 1}),
        "age": classeur.add_format({"bold": True, "bg_color": "#d9d9d9", "border": 1}),
        "label": classeur.add_format({"border": 1}),
        "dont": classeur.add_format({"border": 1, "italic": True}),
        "valeur": classeur.add_format({"border": 1, "num_format": "[h]:mm" if horaire else "#,##0.00"}),
        "valeur_dont": classeur.add_format({"border": 1, "italic": True, "num_format": "[h]:mm" if horaire else "#,##0.00"}),
        "total_label": classeur.add_format({"bold": True, "border": 1, "bg_color": "#f2f2f2"}),
        "total": classeur.add_format({"bold": True, "border": 1, "bg_color": "#f2f2f2", "num_format": "[h]:mm" if horaire else "#,##0.00"}),
    }

    def Nombre(valeur):
        """ Durée -> nombre Excel (fraction de jour en mode horaire, heures décimales sinon) """
        secondes = (valeur or moteur.ZERO).total_seconds()
        return secondes / 86400.0 if horaire else round(secondes / 3600.0, 2)

    colonnes = resultats["colonnes"]
    regimes = resultats["regimes"] if resultats["regroupement_regime"] else []

    # Feuille des résultats
    feuille = classeur.add_worksheet("Résultats")
    feuille.set_column(0, 0, 38)
    feuille.set_column(1, 30, 14)
    feuille.write(0, 0, "Fréquentation CAF", formats["titre"])
    ligne = 1
    for label, valeur in calcul.Get_resume_parametres():
        feuille.write(ligne, 0, label, formats["gras"])
        feuille.write(ligne, 1, valeur)
        ligne += 1
    feuille.write(ligne, 0, "Unité", formats["gras"])
    feuille.write(ligne, 1, "Heures au format hh:mm" if horaire else "Heures décimales")
    ligne += 2

    # En-têtes
    entetes = []
    for idregime, nom_regime in regimes:
        for code, label in colonnes:
            entetes.append("%s\n%s" % (nom_regime, label))
    for code, label in colonnes:
        entetes.append("Total\n%s" % label)
    nbre_colonnes = len(entetes)

    def Ecrire_valeurs(num_ligne, valeurs_colonnes, format_valeur):
        num_colonne = 1
        for index_regime in range(len(regimes)):
            for code, label in colonnes:
                feuille.write_number(num_ligne, num_colonne, Nombre(valeurs_colonnes[code]["regimes"][index_regime]), format_valeur)
                num_colonne += 1
        for code, label in colonnes:
            feuille.write_number(num_ligne, num_colonne, Nombre(valeurs_colonnes[code]["total"]), format_valeur)
            num_colonne += 1

    for tableau in resultats["tableaux"]:
        if tableau["label"]:
            feuille.merge_range(ligne, 0, ligne, nbre_colonnes, tableau["label"], formats["groupe"])
            ligne += 1
        feuille.write(ligne, 0, "Période", formats["entete"])
        for index, entete in enumerate(entetes):
            feuille.write(ligne, index + 1, entete, formats["entete"])
        feuille.set_row(ligne, 30)
        ligne += 1
        for bloc in tableau["blocs"]:
            if bloc["label"]:
                feuille.merge_range(ligne, 0, ligne, nbre_colonnes, bloc["label"], formats["age"])
                ligne += 1
            for ligne_periode in bloc["lignes"]:
                feuille.write(ligne, 0, "%s%s" % (ligne_periode["label"], " (%s)" % ligne_periode["detail"] if ligne_periode["detail"] else ""), formats["label"])
                Ecrire_valeurs(ligne, ligne_periode["valeurs"], formats["valeur"])
                ligne += 1
            if tableau["multi_blocs"]:
                feuille.write(ligne, 0, "Total %s" % bloc["label"].lower() if bloc["label"] else "Total", formats["total_label"])
                Ecrire_valeurs(ligne, bloc["total"], formats["total"])
                ligne += 1
        feuille.write(ligne, 0, "Total", formats["total_label"])
        Ecrire_valeurs(ligne, tableau["total"], formats["total"])
        ligne += 1
        for dont in tableau["dont"]:
            feuille.write(ligne, 0, dont["label"], formats["dont"])
            num_colonne = 1 + len(regimes) * len(colonnes)
            for code, label in colonnes:
                feuille.write_number(ligne, num_colonne, Nombre(dont["valeurs"][code]), formats["valeur_dont"])
                num_colonne += 1
            ligne += 1
        ligne += 1

    if len(resultats["tableaux"]) > 1:
        feuille.write(ligne, 0, "Total général", formats["total_label"])
        Ecrire_valeurs(ligne, resultats["total_general"], formats["total"])

    # Feuille des indicateurs
    feuille = classeur.add_worksheet("Indicateurs")
    feuille.set_column(0, 0, 50)
    feuille.set_column(1, 1, 18)
    kpi = resultats["kpi"]
    num_ligne = 0
    for code, label in colonnes:
        feuille.write(num_ligne, 0, moteur.LABELS_HEURES[code])
        feuille.write_number(num_ligne, 1, Nombre(kpi["totaux"][code]), formats["valeur"])
        num_ligne += 1
    if kpi["taux"] is not None:
        feuille.write(num_ligne, 0, "Taux réalisé / facturé (%)")
        feuille.write_number(num_ligne, 1, kpi["taux"])
        num_ligne += 1
    for label, valeur in (("Individus distincts", kpi["individus"]), ("Familles distinctes", kpi["familles"]),
                          ("Journées-enfants (%s)" % kpi["colonne_journees"], kpi["journees"])):
        feuille.write(num_ligne, 0, label)
        feuille.write_number(num_ligne, 1, valeur)
        num_ligne += 1
    for dont in kpi["dont"]:
        feuille.write(num_ligne, 0, "%s : individus" % dont["label"])
        feuille.write_number(num_ligne, 1, dont["individus"])
        num_ligne += 1

    # Feuille mensuelle
    feuille = classeur.add_worksheet("Par mois")
    feuille.set_column(0, 2, 16)
    feuille.write(0, 0, "Mois", formats["entete"])
    for index, serie in enumerate(resultats["graphe"]["series"]):
        feuille.write(0, index + 1, serie["label_heures"], formats["entete"])
    for num_ligne, label in enumerate(resultats["graphe"]["labels"]):
        feuille.write(num_ligne + 1, 0, label)
        for index, serie in enumerate(resultats["graphe"]["series"]):
            feuille.write_number(num_ligne + 1, index + 1, serie["valeurs"][num_ligne])

    # Feuille des contrôles
    if resultats["controles"]:
        feuille = classeur.add_worksheet("Contrôles")
        feuille.set_column(0, 0, 110)
        num_ligne = 0
        for controle in resultats["controles"]:
            feuille.write(num_ligne, 0, controle["message"], formats["gras"])
            num_ligne += 1
            for detail in controle["details"]:
                feuille.write(num_ligne, 0, "    %s" % detail["label"])
                num_ligne += 1
            num_ligne += 1

    classeur.close()
    return JsonResponse({"nom_fichier": os.path.join(rep_temp, nom_fichier)})


def Generer_pdf(request):
    """ Export des résultats au format PDF """
    if not Verifier_permission(request):
        return JsonResponse({"erreur": ERREUR_PERMISSION}, status=401)
    parametres, erreur = Get_parametres(request)
    if erreur:
        return erreur
    calcul = moteur.Calcul(parametres, request=request)
    resultats = calcul.Calculer()
    if calcul.erreurs:
        return JsonResponse({"erreur": calcul.erreurs[0]}, status=401)
    from reportlab.lib.pagesizes import A4, landscape, portrait
    nbre_colonnes = len(resultats["colonnes"]) * (len(resultats["regimes"]) + 1 if resultats["regroupement_regime"] else 1)
    taille_page = landscape(A4) if nbre_colonnes > 4 else portrait(A4)
    impression = Impression_frequentation(titre="Fréquentation CAF", dict_donnees={"resultats": resultats, "resume": calcul.Get_resume_parametres()},
                                          taille_page=taille_page, request=request)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    return JsonResponse({"nom_fichier": impression.Get_nom_fichier()})


class Impression_frequentation(Impression):
    def Draw(self):
        from reportlab.platypus import Table, TableStyle, Spacer, Paragraph, KeepTogether
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib import colors
        from core.utils import utils_polices

        resultats = self.dict_donnees["resultats"]
        mode = resultats["format"]
        colonnes = resultats["colonnes"]
        regimes = resultats["regimes"] if resultats["regroupement_regime"] else []
        largeur = self.taille_page[0] - 75
        # Marges alignées sur l'en-tête et les tableaux (qui occupent la largeur de la page moins 75)
        self.doc.leftMargin = self.doc.rightMargin = (self.taille_page[0] - largeur) / 2.0
        bleu, gris = colors.HexColor("#3c8dbc"), colors.HexColor("#c8ced3")
        style_intro = ParagraphStyle("intro", fontName=utils_polices.FONT_NORMAL, fontSize=7, leading=9)
        style_cellule = ParagraphStyle("cellule", fontName=utils_polices.FONT_NORMAL, fontSize=7, leading=8)
        style_titre = ParagraphStyle("titre", fontName=utils_polices.FONT_BOLD, fontSize=9, textColor=bleu, spaceBefore=6, spaceAfter=3)

        self.Insert_header()
        for label, valeur in self.dict_donnees["resume"]:
            self.story.append(Paragraph("<b>%s :</b> %s" % (label, valeur), style_intro))
        kpi = resultats["kpi"]
        textes_kpi = ["%s : %s" % (moteur.LABELS_HEURES[code], moteur.Formater_duree(kpi["totaux"][code], mode)) for code, label in colonnes]
        if kpi["taux"] is not None:
            textes_kpi.append("Taux réalisé / facturé : %s %%" % str(kpi["taux"]).replace(".", ","))
        textes_kpi.append("%d individus, %d familles, %d journées-enfants" % (kpi["individus"], kpi["familles"], kpi["journees"]))
        self.story.append(Paragraph("<b>Résultats :</b> %s" % " | ".join(textes_kpi), style_intro))
        self.story.append(Spacer(0, 8))

        entetes = ["Période"]
        for idregime, nom_regime in regimes:
            for code, label in colonnes:
                entetes.append(Paragraph("<para align='center'>%s<br/>%s</para>" % (nom_regime, label), style_cellule))
        for code, label in colonnes:
            entetes.append(Paragraph("<para align='center'><b>Total</b><br/>%s</para>" % label, style_cellule))
        largeur_valeur = min(70, (largeur - 160) / max(1, len(entetes) - 1))
        largeurs = [largeur - largeur_valeur * (len(entetes) - 1)] + [largeur_valeur] * (len(entetes) - 1)

        def Valeurs(valeurs_colonnes):
            ligne = []
            for index_regime in range(len(regimes)):
                for code, label in colonnes:
                    ligne.append(moteur.Formater_duree(valeurs_colonnes[code]["regimes"][index_regime], mode))
            for code, label in colonnes:
                ligne.append(moteur.Formater_duree(valeurs_colonnes[code]["total"], mode))
            return ligne

        for tableau in resultats["tableaux"]:
            donnees, styles = [entetes], [
                ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7), ("FONT", (0, 0), (-1, 0), utils_polices.FONT_BOLD, 7),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")), ("GRID", (0, 0), (-1, -1), 0.25, gris),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
            for bloc in tableau["blocs"]:
                if bloc["label"]:
                    donnees.append([bloc["label"]] + [""] * (len(entetes) - 1))
                    index = len(donnees) - 1
                    styles.extend([("SPAN", (0, index), (-1, index)), ("FONT", (0, index), (-1, index), utils_polices.FONT_BOLD, 7),
                                   ("BACKGROUND", (0, index), (-1, index), colors.HexColor("#d9d9d9"))])
                for ligne_periode in bloc["lignes"]:
                    label = ligne_periode["label"]
                    if ligne_periode["detail"]:
                        label = "%s<br/><font size=5>%s</font>" % (label, ligne_periode["detail"])
                    donnees.append([Paragraph(label, style_cellule)] + Valeurs(ligne_periode["valeurs"]))
                if tableau["multi_blocs"]:
                    donnees.append(["Total %s" % bloc["label"].lower() if bloc["label"] else "Total"] + Valeurs(bloc["total"]))
                    index = len(donnees) - 1
                    styles.extend([("FONT", (0, index), (-1, index), utils_polices.FONT_BOLD, 7), ("BACKGROUND", (0, index), (-1, index), colors.HexColor("#f2f2f2"))])
            donnees.append(["Total"] + Valeurs(tableau["total"]))
            index = len(donnees) - 1
            styles.extend([("FONT", (0, index), (-1, index), utils_polices.FONT_BOLD, 7), ("BACKGROUND", (0, index), (-1, index), colors.HexColor("#e8eef3"))])
            for dont in tableau["dont"]:
                ligne = [Paragraph("<i>%s</i>" % dont["label"], style_cellule)] + [""] * (len(regimes) * len(colonnes))
                ligne += [moteur.Formater_duree(dont["valeurs"][code], mode) for code, label in colonnes]
                donnees.append(ligne)
            table = Table(donnees, largeurs, repeatRows=1)
            table.setStyle(TableStyle(styles))
            elements = [Paragraph(tableau["label"], style_titre)] if tableau["label"] else []
            elements.append(table)
            self.story.append(KeepTogether(elements) if len(donnees) < 40 else table)
            self.story.append(Spacer(0, 10))

        if resultats["controles"]:
            self.story.append(Paragraph("Points de vigilance", style_titre))
            for controle in resultats["controles"]:
                self.story.append(Paragraph("• %s" % controle["message"], style_intro))


# ---------------------------------------- Profils ----------------------------------------

def get_data_profil(donnees=None, request=None):
    """ Données à mémoriser dans le profil (appelée par le widget Profil_configuration) """
    try:
        dict_donnees = json.loads(donnees)
        # Validation complète pour ne pas enregistrer un profil inutilisable
        moteur.Normaliser_parametres(dict_donnees, request=request)
    except moteur.Erreur_parametres as err:
        return JsonResponse({"erreur": str(err)}, status=401)
    except (TypeError, ValueError):
        return JsonResponse({"erreur": "Les paramètres ne sont pas valides"}, status=401)
    # La période et les activités sont mémorisées mais seront remplacées par la sélection en cours si besoin
    return dict_donnees


def Get_profil(request):
    """ Retourne les paramètres d'un profil (de l'assistant ou de l'état global) """
    if not Verifier_permission(request):
        return JsonResponse({"erreur": ERREUR_PERMISSION}, status=401)
    try:
        idprofil = int(request.POST.get("idprofil"))
    except (TypeError, ValueError):
        return JsonResponse({"erreur": "Profil inconnu"}, status=401)
    source = request.POST.get("source", "assistant")
    categorie = "profil_etat_global" if source == "etat_global" else CATEGORIE_PROFIL
    profil = Get_profils(request, categorie=categorie).filter(pk=idprofil).first()
    if not profil or not profil.parametre:
        return JsonResponse({"erreur": "Ce profil est vide ou n'est pas accessible"}, status=401)
    donnees = json.loads(profil.parametre)
    if source == "etat_global":
        donnees = moteur.Convertir_profil_etat_global(donnees)
    return JsonResponse({"parametres": donnees, "nom": profil.nom})


# ---------------------------------------- Vue ----------------------------------------

class View(CustomView, TemplateView):
    menu_code = "frequentation_caf"
    template_name = "consommations/frequentation_caf.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Fréquentation CAF"
        context["form_selection"] = Form_selection(request=self.request)
        context["form_profil"] = Form_profil(request=self.request)
        context["profils_etat_global"] = Get_profils(self.request, categorie="profil_etat_global")
        context["config"] = {
            "etats": moteur.ETATS,
            "etats_defaut": moteur.ETATS_DEFAUT,
            "types_calcul": moteur.TYPES_CALCUL,
            "arrondis": moteur.ARRONDIS,
            "ventilations": moteur.VENTILATIONS_PERIODES,
            "regroupements": moteur.REGROUPEMENTS + sorted(moteur.Get_questions_regroupement().items(), key=lambda x: x[1]),
            "operateurs": moteur.OPERATEURS,
            "champs_filtres": moteur.Get_champs_filtres(),
            "regimes": [(r.pk, r.nom) for r in Regime.objects.all().order_by("nom")],
        }
        return context
