# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.views.generic import TemplateView
from django.db.models import Q, Exists, OuterRef
from core.views.base import CustomView
from core.models import ContratCollaborateur, GroupeCollaborateurs, DemandeAbsenceCollaborateur, TypeCongeCollaborateur, Ferie, Vacance
from core.utils import utils_dates
from collaborateurs.forms.planning_absences import Formulaire, Lire_mois, NOMS_MOIS
from collaborateurs.utils import utils_absences, utils_conges
from collaborateurs.views.planning_individuel import Collaborateurs_accessibles

JOURS_ABREGES = ("L", "M", "M", "J", "V", "S", "D")
NOMS_JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
LABELS_PORTIONS = {"JOURNEE": "journée", "MATIN": "matin", "APRES_MIDI": "après-midi"}


def Format_nombre(valeur=0):
    return ("%.1f" % valeur).rstrip("0").rstrip(".").replace(".", ",")


def Abrege(texte=""):
    """ Abréviation d'une catégorie sans abréviation : initiales (ou deux premières lettres) """
    mots = [mot for mot in texte.replace("'", " ").split() if len(mot) > 2]
    if len(mots) >= 2:
        return (mots[0][0] + mots[1][0]).upper()
    return texte[:2].upper()


def Get_data(parametres={}, user=None):
    date_debut = Lire_mois(parametres["mois"])
    index_fin = date_debut.year * 12 + date_debut.month - 1 + parametres["nbre_mois"]
    date_fin = datetime.date(index_fin // 12, index_fin % 12 + 1, 1) - datetime.timedelta(days=1)
    dates = [date_debut + datetime.timedelta(days=n) for n in range((date_fin - date_debut).days + 1)]
    aujourdhui = datetime.date.today()

    # Collaborateurs
    collaborateurs = Collaborateurs_accessibles(user)
    if parametres.get("groupes"):
        collaborateurs = collaborateurs.filter(groupes__in=parametres["groupes"])
    if parametres["situation"] == "en_poste":
        collaborateurs = collaborateurs.filter(Exists(ContratCollaborateur.objects.filter(Q(date_debut__lte=date_fin) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_debut)), collaborateur=OuterRef("pk"))))
    collaborateurs = list(collaborateurs.distinct().prefetch_related("groupes").order_by("nom", "prenom"))
    ids = [collaborateur.pk for collaborateur in collaborateurs]
    contrats = {}
    for contrat in ContratCollaborateur.objects.filter(collaborateur_id__in=ids).order_by("date_debut"):
        contrats.setdefault(contrat.collaborateur_id, []).append(contrat)

    # Catégories et abréviations (celle du type de congé si elle existe)
    toutes_categories = utils_absences.Get_categories_absence()
    ids_categories = [categorie.pk for categorie in parametres["categories"] if categorie.pk in toutes_categories]
    abreges = {}
    for type_conge in TypeCongeCollaborateur.objects.filter(categorie_id__in=ids_categories).order_by("-ordre"):
        if type_conge.abrege:
            abreges[type_conge.categorie_id] = type_conge.abrege
    categories = {}
    for idcategorie in ids_categories:
        categorie = toutes_categories[idcategorie]
        categories[idcategorie] = {"id": idcategorie, "nom": categorie.nom, "couleur": categorie.couleur or "#3c8dbc", "abrege": abreges.get(idcategorie) or Abrege(categorie.nom)}

    # Jours fériés et vacances
    liste_feries = list(Ferie.objects.all())
    vacances = list(Vacance.objects.filter(date_debut__lte=date_fin, date_fin__gte=date_debut))
    infos_dates = []
    for date in dates:
        ferie = utils_dates.EstFerie(date, liste_feries)
        vacance = next((vacance for vacance in vacances if vacance.date_debut <= date <= vacance.date_fin), None)
        classes = []
        if date.weekday() >= 5:
            classes.append("pa_we")
        if ferie:
            classes.append("pa_ferie")
        elif vacance:
            classes.append("pa_vacances")
        if date == aujourdhui:
            classes.append("pa_aujourdhui")
        titre = "%s %s" % (NOMS_JOURS[date.weekday()].capitalize(), date.strftime("%d/%m/%Y"))
        if ferie:
            titre += " - %s" % ferie.nom
        elif vacance:
            titre += " - %s %s" % (vacance.nom, vacance.annee)
        infos_dates.append({"date": date, "jour": date.day, "initiale": JOURS_ABREGES[date.weekday()], "classes": " ".join(classes), "titre": titre,
                            "debut_mois": date.day == 1 and date != date_debut, "ferie": bool(ferie)})
    mois = []
    for date in dates:
        if date.day == 1 or not mois:
            mois.append({"nom": "%s %d" % (NOMS_MOIS[date.month - 1], date.year), "nbre": 0})
        mois[-1]["nbre"] += 1

    # Absences planifiées
    minutes = utils_absences.Get_minutes_par_jour(ids, date_debut, date_fin, ids_categories)

    # Demandes en attente
    attentes = {}
    if parametres.get("afficher_attente"):
        for demande in DemandeAbsenceCollaborateur.objects.select_related("type_conge").filter(collaborateur_id__in=ids, etat="ATTENTE", date_debut__lte=date_fin, date_fin__gte=date_debut):
            if demande.type_conge.categorie_id not in categories:
                continue
            for date, portion in utils_absences.Get_jours_demande(demande, contrats.get(demande.collaborateur_id, []), liste_feries).items():
                if date_debut <= date <= date_fin:
                    attentes.setdefault((demande.collaborateur_id, date), []).append({"portion": portion, "idcategorie": demande.type_conge.categorie_id, "nom": demande.type_conge.nom})

    # Construction des lignes
    lignes, categories_utilisees = {}, set()
    for collaborateur in collaborateurs:
        liste_contrats = contrats.get(collaborateur.pk, [])
        cellules, total, total_attente = [], 0.0, 0.0
        for info in infos_dates:
            date = info["date"]
            contrat = utils_conges.Contrat_du_jour(liste_contrats, date)
            classes = [info["classes"]] if info["classes"] else []
            if info["debut_mois"]:
                classes.append("pa_debut_mois")
            if liste_contrats and not contrat:
                classes.append("pa_hors_contrat")
            elif date.weekday() < 5 and date.weekday() not in utils_conges.Jours_travailles(liste_contrats, date):
                classes.append("pa_non_travaille")
            reference = utils_conges.Minutes_reference(liste_contrats, date)

            # Portions de la journée occupées par des absences validées
            portions, textes = {}, []
            for idcategorie, valeurs in sorted(minutes.get((collaborateur.pk, date), {}).items(), key=lambda item: -item[1]["minutes"]):
                portion = utils_absences.Portion_journee(valeurs["minutes"], valeurs["debut"], valeurs["fin"], reference)
                cles = ("MATIN", "APRES_MIDI") if portion == "JOURNEE" else (portion,)
                for cle in cles:
                    portions.setdefault(cle, {"idcategorie": idcategorie, "attente": False})
                duree = valeurs["minutes"]
                textes.append("%s (%s, %dh%02d)" % (categories[idcategorie]["nom"], LABELS_PORTIONS[portion], duree // 60, duree % 60))
            valeur = 0.5 * len(portions)
            if valeur and not info["ferie"] and "pa_hors_contrat" not in classes:
                total += valeur

            # Demandes en attente (sur les demi-journées encore libres)
            for attente in attentes.get((collaborateur.pk, date), []):
                cles = ("MATIN", "APRES_MIDI") if attente["portion"] == "JOURNEE" else (attente["portion"],)
                ajout = False
                for cle in cles:
                    if cle not in portions:
                        portions[cle] = {"idcategorie": attente["idcategorie"], "attente": True}
                        total_attente += 0.5
                        ajout = True
                if ajout:
                    textes.append("%s (%s) - demande en attente" % (attente["nom"], LABELS_PORTIONS[attente["portion"]]))

            matin, apres_midi = portions.get("MATIN"), portions.get("APRES_MIDI")
            categories_utilisees.update(portion["idcategorie"] for portion in portions.values())
            cellule = {"classes": " ".join(classes), "valide": valeur}
            if textes:
                cellule["titre"] = "%s - %s : %s" % (collaborateur.Get_nom(), info["titre"], ", ".join(textes))
            if matin or apres_midi:
                cellule["matin"] = dict(matin, couleur=categories[matin["idcategorie"]]["couleur"]) if matin else None
                cellule["apres_midi"] = dict(apres_midi, couleur=categories[apres_midi["idcategorie"]]["couleur"]) if apres_midi else None
                if matin and apres_midi and matin["idcategorie"] == apres_midi["idcategorie"] and matin["attente"] == apres_midi["attente"]:
                    cellule["abrege"] = categories[matin["idcategorie"]]["abrege"]
            cellules.append(cellule)
        lignes[collaborateur.pk] = {"collaborateur": collaborateur, "cellules": cellules, "total": total, "total_str": Format_nombre(total) if total else "",
                                    "attente_str": Format_nombre(total_attente) if total_attente else ""}

    # Blocs (par groupe ou un seul bloc)
    def Bloc(nom="", ids_collaborateurs=[]):
        liste = [lignes[idcollaborateur] for idcollaborateur in ids_collaborateurs if idcollaborateur in lignes]
        compteurs = []
        for index, info in enumerate(infos_dates):
            nbre = sum(ligne["cellules"][index]["valide"] for ligne in liste)
            classes = (info["classes"] + (" pa_debut_mois" if info["debut_mois"] else "")).strip()
            compteurs.append({"nbre": nbre, "texte": Format_nombre(nbre) if nbre else "", "classes": classes,
                              "taux": round(100.0 * nbre / len(liste)) if liste else 0})
        return {"nom": nom, "lignes": liste, "compteurs": compteurs, "nbre": len(liste)}

    blocs = []
    if parametres.get("regrouper"):
        groupes = GroupeCollaborateurs.objects.order_by("nom")
        if parametres.get("groupes"):
            groupes = groupes.filter(pk__in=[groupe.pk for groupe in parametres["groupes"]])
        places = set()
        for groupe in groupes:
            membres = [collaborateur.pk for collaborateur in collaborateurs if groupe in collaborateur.groupes.all()]
            if membres:
                blocs.append(Bloc(groupe.nom, membres))
                places.update(membres)
        autres = [collaborateur.pk for collaborateur in collaborateurs if collaborateur.pk not in places]
        if autres:
            blocs.append(Bloc("Sans groupe" if blocs else "", autres))
    else:
        blocs.append(Bloc("", [collaborateur.pk for collaborateur in collaborateurs]))
    total_general = Bloc("Total", [collaborateur.pk for collaborateur in collaborateurs]) if len(blocs) > 1 else None

    # Navigation
    index_debut = date_debut.year * 12 + date_debut.month - 1
    precedent = "%04d-%02d" % ((index_debut - 1) // 12, (index_debut - 1) % 12 + 1)
    suivant = "%04d-%02d" % ((index_debut + 1) // 12, (index_debut + 1) % 12 + 1)

    return {
        "dates": infos_dates, "mois": mois, "blocs": blocs, "total_general": total_general, "nbre_collaborateurs": len(collaborateurs),
        "categories": [categories[idcategorie] for idcategorie in ids_categories if idcategorie in categories_utilisees], "afficher_attente": parametres.get("afficher_attente"),
        "periode": "du %s au %s" % (date_debut.strftime("%d/%m/%Y"), date_fin.strftime("%d/%m/%Y")), "precedent": precedent, "suivant": suivant,
        "vacances": bool(vacances), "nbre_colonnes": len(dates) + 2,
    }


class View(CustomView, TemplateView):
    menu_code = "planning_absences_collaborateurs"
    template_name = "collaborateurs/planning_absences.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Planning des absences"
        if "form_parametres" not in kwargs:
            form = Formulaire(request=self.request)
            context["form_parametres"] = form
            parametres = {nom: champ.initial for nom, champ in form.fields.items()}
            parametres.update({"groupes": [], "categories": list(form.fields["categories"].queryset)})
            context["data"] = Get_data(parametres, self.request.user)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        return self.render_to_response(self.get_context_data(form_parametres=form, data=Get_data(form.cleaned_data, request.user)))
