# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json, os, uuid
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Q, Count
from django.shortcuts import render
from django.conf import settings
from core.models import Activite, Inscription, Groupe
from core.views.base import CustomView
from core.utils import utils_parametres
from core.forms.selection_activites import Formulaire as Form_activites


def Get_form_activites(request):
    """ Renvoie une liste d'activités """
    activites = json.loads(request.POST.get("activites", None))
    context = {"form_activites": Form_activites(defaut=activites, request=request)}
    return render(request, "individus/suivi_inscriptions_activites.html", context)


def Valider_form_activites(request):
    form = Form_activites(request.POST)
    if not form.is_valid():
        return JsonResponse({"erreur": "Il y a une erreur dans la sélection des activités"}, status=401)
    return JsonResponse({"activites": form.cleaned_data["activites"]})


def Get_parametres(request=None):
    """ Renvoie les paramètres d'affichage """
    parametres = utils_parametres.Get_categorie(categorie="suivi_inscriptions", utilisateur=request.user, parametres={
        "activites": {},
        "masquer_activites_obsoletes": True,
        "masquer_individus_partis": True,
        "tri": "date_fin+nom",
    })
    parametres["activites_inscriptions_json"] = json.dumps(parametres["activites"])
    return parametres


def Get_suivi_inscriptions(request):
    """ Renvoie le contenu de la table """
    parametres = json.loads(request.POST.get("parametres", None))
    filtre = request.POST.get("filtre", None)

    # Si demande de modification des paramètres
    if parametres:
        utils_parametres.Set_categorie(categorie="suivi_inscriptions", utilisateur=request.user, parametres=parametres)

    # Importation des paramètres
    parametres = Get_parametres(request=request)
    context = {"data_suivi_inscriptions": Get_data(parametres=parametres, filtre=filtre, request=request)}
    context.update(parametres)
    return render(request, "individus/suivi_inscriptions_tableau.html", context)


def Get_tarifs_activite(request):
    """ Renvoie le contenu de la modale affichant les tarifs de l'activité """
    idactivite = request.POST.get("idactivite")
    activite = Activite.objects.get(pk=int(idactivite))
    from facturation.views.liste_tarifs import Get_html_tarifs_activite
    return JsonResponse({"html": Get_html_tarifs_activite(activite=activite)})


def Get_data(parametres={}, filtre=None, request=None):
    """ Création des valeurs pour le suivi des consommations """
    # Importation des activités
    activites = parametres.get("activites", {"type": None, "ids": []})
    if "type" not in activites:
        return {}

    # vérifie que l'activité est bien accessible pour l'utilisateur
    conditions = Q()
    if request:
        conditions &= Q(structure__in=request.user.structures.all())
    if activites["type"] == "groupes_activites":
        conditions &= Q(groupes_activites__in=activites["ids"])
    if activites["type"] == "activites":
        conditions &= Q(pk__in=activites["ids"])

    if parametres["masquer_activites_obsoletes"]:
        conditions &= Q(date_fin__gte=datetime.date.today())

    if filtre:
        conditions &= Q(nom__icontains=filtre)

    tri = parametres.get("tri", "date_fin+nom")
    param_tri = ("-date_fin", "nom") if tri == "date_fin+nom" else ("nom",)
    liste_activites = Activite.objects.filter(conditions).order_by(*param_tri)

    # Importation des groupes
    dict_groupes = {}
    for groupe in Groupe.objects.filter(activite__in=liste_activites).order_by("ordre"):
        dict_groupes.setdefault(groupe.activite_id, [])
        dict_groupes[groupe.activite_id].append(groupe)

    # Importation des inscriptions
    conditions = Q(activite__in=liste_activites)
    if parametres["masquer_individus_partis"]:
        conditions &= (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
    inscriptions = Inscription.objects.values('activite', 'statut', 'groupe').filter(conditions).annotate(nbre=Count('pk'))
    dict_inscriptions = {}
    for inscription in inscriptions:
        key = (inscription["activite"], inscription["statut"], inscription["groupe"])
        dict_inscriptions[key] = inscription["nbre"]

    liste_resultats = []
    for activite in liste_activites:
        dict_activite = {"activite": activite, "groupes": [], "nbre_max": activite.nbre_inscrits_max, "nbre_inscrits": 0, "nbre_attente": 0, "nbre_refus": 0, "nbre_dispo": 0}
        for groupe in dict_groupes.get(activite.pk, []):
            nbre_max = groupe.nbre_inscrits_max
            nbre_inscrits = dict_inscriptions.get((activite.pk, "ok", groupe.pk), 0)
            nbre_attente = dict_inscriptions.get((activite.pk, "attente", groupe.pk), 0)
            nbre_refus = dict_inscriptions.get((activite.pk, "refus", groupe.pk), 0)
            nbre_dispo = nbre_max - nbre_inscrits if nbre_max else 0

            classe = ""
            if nbre_max and nbre_dispo > 5: classe = "disponible"
            if nbre_max and 0 < nbre_dispo <= 5: classe = "dernieresplaces"
            if nbre_max and nbre_dispo <= 0: classe = "complet"

            dict_activite["nbre_inscrits"] += nbre_inscrits
            dict_activite["nbre_attente"] += nbre_attente
            dict_activite["nbre_refus"] += nbre_refus
            if activite.nbre_inscrits_max:
                dict_activite["nbre_dispo"] = activite.nbre_inscrits_max - dict_activite["nbre_inscrits"]

            dict_activite["groupes"].append({"groupe": groupe, "nbre_max": groupe.nbre_inscrits_max, "nbre_inscrits": nbre_inscrits,
                                             "nbre_attente": nbre_attente, "nbre_refus": nbre_refus, "nbre_dispo": nbre_dispo, "classe": classe})

        if activite.nbre_inscrits_max:
            for dict_groupe in dict_activite["groupes"]:
                if dict_activite["nbre_dispo"] > 5 and not dict_groupe["classe"]: dict_groupe["classe"] = "disponible"
                if 0 < dict_activite["nbre_dispo"] <= 5 and dict_groupe["classe"] != "complet": dict_groupe["classe"] = "dernieresplaces"
                if dict_activite["nbre_dispo"] <= 0: dict_groupe["classe"] = "complet"

        liste_resultats.append(dict_activite)

    return liste_resultats


def Exporter_excel(request):
    """ Exporte le contenu du widget Suivi des inscriptions au format Excel """
    filtre = request.POST.get("filtre", None)
    parametres = Get_parametres(request=request)
    liste_resultats = Get_data(parametres=parametres, filtre=filtre, request=request)

    if not liste_resultats:
        return JsonResponse({"erreur": "Aucune donnée à exporter"}, status=401)

    # Création du répertoire et du nom du fichier
    rep_temp = os.path.join("temp", str(uuid.uuid4()))
    rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
    if not os.path.isdir(rep_destination):
        os.makedirs(rep_destination)
    nom_fichier = "suivi_inscriptions.xlsx"

    # Création du classeur
    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    feuille = classeur.add_worksheet("Suivi des inscriptions")
    format_entete = classeur.add_format({"bold": True, "bg_color": "#efefef", "border": 1})
    format_activite = classeur.add_format({"bold": True})

    # Entêtes
    colonnes = ("Activité/Groupe", "Inscrits", "Max.", "Dispo.", "Attente", "Refus")
    for num_colonne, label_colonne in enumerate(colonnes):
        feuille.set_column(num_colonne, num_colonne, 30 if num_colonne == 0 else 12)
        feuille.write(0, num_colonne, label_colonne, format_entete)

    # Lignes
    num_ligne = 1
    for activite in liste_resultats:
        feuille.write(num_ligne, 0, activite["activite"].nom, format_activite)
        feuille.write(num_ligne, 1, activite["nbre_inscrits"], format_activite)
        feuille.write(num_ligne, 2, activite["nbre_max"] or "", format_activite)
        feuille.write(num_ligne, 3, activite["nbre_dispo"] or "", format_activite)
        feuille.write(num_ligne, 4, activite["nbre_attente"], format_activite)
        feuille.write(num_ligne, 5, activite["nbre_refus"], format_activite)
        num_ligne += 1
        for groupe in activite["groupes"]:
            feuille.write(num_ligne, 0, groupe["groupe"].nom)
            feuille.write(num_ligne, 1, groupe["nbre_inscrits"])
            feuille.write(num_ligne, 2, groupe["nbre_max"] or "")
            feuille.write(num_ligne, 3, groupe["nbre_dispo"] or "")
            feuille.write(num_ligne, 4, groupe["nbre_attente"])
            feuille.write(num_ligne, 5, groupe["nbre_refus"])
            num_ligne += 1

    classeur.close()

    return JsonResponse({"nom_fichier": os.path.join(rep_temp, nom_fichier)})


class View(CustomView, TemplateView):
    menu_code = "suivi_inscriptions"
    template_name = "individus/suivi_inscriptions_view.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Suivi des inscriptions"
        context['suivi_inscriptions_parametres'] = Get_parametres(request=self.request)
        return context
