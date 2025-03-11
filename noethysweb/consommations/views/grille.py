# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime, time, decimal, math, copy
logger = logging.getLogger(__name__)
from uuid import uuid4
from colorhash import ColorHash
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.template.context_processors import csrf
from django.db.models import Q, Count
from django.core import serializers
from django.conf import settings
from crispy_forms.utils import render_crispy_form
from core.models import Ouverture, Remplissage, UniteRemplissage, Vacance, Unite, Consommation, MemoJournee, Evenement, Groupe, Ventilation, Famille, \
                        Tarif, CombiTarif, TarifLigne, Quotient, Prestation, Aide, Deduction, CombiAide, Individu, Activite, Scolarite, QuestionnaireReponse
from core.utils import utils_dates, utils_decimal, utils_historique, utils_parametres
from consommations.utils import utils_consommations
from consommations.forms.grille_questionnaire import Formulaire as Formulaire_questionnaire


def Memoriser_options(request):
    parametres = {"afficher_quantites": request.POST.get("afficher_quantites", False) == "true"}
    utils_parametres.Set_categorie(categorie="grille", utilisateur=request.user, parametres=parametres)
    return JsonResponse({"succes": True})


def Get_form_questionnaire(request):
    # Création du contexte
    context = {}
    context.update(csrf(request))

    # Formatage du form en html
    conso = json.loads(request.POST.get("conso", "{}"))
    idevenement = int(request.POST.get("idevenement", 0))
    form_detail = Formulaire_questionnaire(request=request, idevenement=idevenement, initial=json.loads((conso.get("extra", "{}")) or "{}") if conso else {})
    form_html = render_crispy_form(form_detail, context=context)
    return JsonResponse({"form_html": form_html})


def Valid_form_questionnaire(request):
    form = Formulaire_questionnaire(request.POST, idevenement=int(request.POST["idevenement"]), request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Vous devez obligatoirement renseigner les questions marquées d'une étoile (*)"}, status=401)
    return JsonResponse({"succes": True, "reponses": json.dumps(form.cleaned_data)})


def Get_individus(request):
    """ Renvoie une liste d'individus pour le Select2 """
    recherche = request.GET.get("term", "")
    liste_individus = []
    for individu in Individu.objects.all().filter(Q(nom__icontains=recherche) | Q(prenom__icontains=recherche), inscription__isnull=False).distinct().order_by("nom", "prenom"):
        liste_individus.append({"id": individu.pk, "text": individu.Get_nom()})
    return JsonResponse({"results": liste_individus, "pagination": {"more": True}})


def Get_periode(data):
    # Récupération de la période
    listes_dates = []
    if data["periode"] and data["periode"]["periodes"]:
        conditions_periodes = Q()
        for p in data["periode"]["periodes"]:
            date_debut = utils_dates.ConvertDateENGtoDate(p.split(";")[0])
            date_fin = utils_dates.ConvertDateENGtoDate(p.split(";")[1])
            listes_dates.extend([date_debut, date_fin])
            conditions_periodes |= Q(date__gte=date_debut) & Q(date__lte=date_fin)
    else:
        d = datetime.date(3000, 1, 1)
        conditions_periodes = Q(date__gte=d) & Q(date__lte=d)
        listes_dates.extend([d, d])
    data["conditions_periodes"] = conditions_periodes

    # Récupération des dates extrêmes
    date_min, date_max = min(listes_dates), max(listes_dates)
    data["date_min"] = date_min
    data["date_max"] = date_max
    return data


def Maj_tarifs_fratries(activite=None, prestations=[], liste_IDprestation_existants=[]):
    liste_tarifs_speciaux = Tarif.objects.filter(activite=activite, methode__contains="nbre_ind")
    if liste_tarifs_speciaux:
        prestations += list(Prestation.objects.filter(pk__in=liste_IDprestation_existants, facture__isnull=True))

        # Recherche les individus à modifier
        liste_modifications = []
        liste_id_tarif = [tarif.pk for tarif in liste_tarifs_speciaux]
        for prestation in prestations:
            if prestation.tarif_id in liste_id_tarif:
                key = (prestation.famille_id, prestation.tarif_id, str(prestation.date))
                if key not in liste_modifications:
                    liste_modifications.append(key)

        # Recherche les fratries
        if liste_modifications:
            for famille_id, tarif_id, date in liste_modifications:
                if settings.ATTRIBUTION_TARIF_FRATERIE_TARIF_IDENTIQUE:
                    # Recherche s'il existe des prestations ayant le même IDtarif sur la même date
                    condition = Q(famille_id=famille_id, tarif_id=tarif_id, date=date)
                else:
                    # Recherche s'il existe des prestations de la même activité sur la même date
                    condition = Q(famille_id=famille_id, activite=activite, date=date)
                liste_prestations_fratrie = Prestation.objects.select_related("tarif", "tarif_ligne", "individu").filter(condition).order_by("individu_id")
                liste_prestations_fratrie = sorted(list(liste_prestations_fratrie), key=lambda prestation: (prestation.individu.date_naiss or datetime.date(1950, 1, 1), prestation.individu.pk), reverse=not settings.ATTRIBUTION_TARIF_FRATERIE_AINES)
                for index, prestation in enumerate(liste_prestations_fratrie):
                    if "degr" in prestation.tarif.methode:
                        num_enfant = index + 1
                    else:
                        num_enfant = len(liste_prestations_fratrie)
                    montant_deductions = prestation.montant_initial - prestation.montant
                    nouveau_montant = getattr(prestation.tarif_ligne, "montant_enfant_%d" % min(num_enfant, 6), decimal.Decimal(0))
                    if prestation.montant_initial != nouveau_montant:
                        prestation.montant_initial = nouveau_montant
                        logger.debug("tarif selon le nbre d'individus : Prestation %d modifiée : montant=%s num_enfant=%d" % (prestation.pk, prestation.montant_initial, num_enfant))
                        prestation.montant = prestation.montant_initial - montant_deductions
                        prestation.save()
                        Ventilation.objects.filter(prestation=prestation).delete()


def Get_generic_data(data={}):
    """ Renvoie les données communes à la grille des conso et au gestionnaire des conso """
    # Création de listes de données
    data["liste_individus"] = []
    data["liste_familles"] = []
    data["liste_key_individus"] = []
    for inscription in data["liste_inscriptions"]:
        if inscription.individu not in data["liste_individus"]: data["liste_individus"].append(inscription.individu)
        if inscription.famille not in data["liste_familles"]: data["liste_familles"].append(inscription.famille)
        key = (inscription.individu_id, inscription.famille_id)
        if key not in data["liste_key_individus"]: data["liste_key_individus"].append(key)

    # Permet de trouver les différences entre les inscriptions multiples d'un seul individu
    # Pour afficher le texte d'informations complémentaires des inscriptions
    dict_differences = {}
    for inscription in data["liste_inscriptions"]:
        dict_differences.setdefault(inscription.individu, {})
        dict_differences[inscription.individu].setdefault(inscription.activite, {"groupe": [], "famille": [], "categorie_tarif": []})
        if inscription.groupe not in dict_differences[inscription.individu][inscription.activite]["groupe"]: dict_differences[inscription.individu][inscription.activite]["groupe"].append(inscription.groupe)
        if inscription.famille not in dict_differences[inscription.individu][inscription.activite]["famille"]: dict_differences[inscription.individu][inscription.activite]["famille"].append(inscription.famille)
        if inscription.categorie_tarif not in dict_differences[inscription.individu][inscription.activite]["categorie_tarif"]: dict_differences[inscription.individu][inscription.activite]["categorie_tarif"].append(inscription.categorie_tarif)

    # Importation de la scolarité
    dict_scolarites = {}
    if data["options"].get("afficher_classe", "non") == "oui" or data["options"].get("afficher_niveau_scolaire", "non") == "oui":
        conditions = Q(individu_id__in=data["liste_key_individus"]) & Q(date_debut__lte=data["date_max"]) & Q(date_fin__gte=data["date_min"])
        dict_scolarites = {scolarite.individu: scolarite for scolarite in Scolarite.objects.select_related("individu", "classe", "niveau").filter(conditions)}

    for inscription in data["liste_inscriptions"]:
        inscription.infos = []

        # Ajout des informations différentes
        for info in ("groupe", "famille", "categorie_tarif"):
            if len(dict_differences[inscription.individu][inscription.activite][info]) > 1:
                inscription.infos.append(getattr(inscription, info).nom)

        # Ajout d'autres informations
        if data["options"].get("afficher_date_naiss", "non") == "oui" and inscription.individu.date_naiss:
            inscription.infos.append(inscription.individu.date_naiss.strftime("%d/%m/%Y"))
        if data["options"].get("afficher_age", "non") == "oui" and inscription.individu.date_naiss:
            inscription.infos.append("%d ans" % inscription.individu.Get_age())
        if data["options"].get("afficher_groupe", "non") == "oui":
            inscription.infos.append(inscription.groupe.nom)
        if data["options"].get("afficher_classe", "non") == "oui" and inscription.individu in dict_scolarites and dict_scolarites[inscription.individu].classe:
            inscription.infos.append(dict_scolarites[inscription.individu].classe.nom)
        if data["options"].get("afficher_niveau_scolaire", "non") == "oui" and inscription.individu in dict_scolarites and dict_scolarites[inscription.individu].niveau:
            inscription.infos.append(dict_scolarites[inscription.individu].niveau.abrege)

        # Formatage des informations
        inscription.infos = " | ".join(inscription.infos)

    # Regroupe les inscriptions par individu
    dict_resultats = {}
    for inscription in data["liste_inscriptions"]:
        key = (inscription.individu, inscription.famille_id)
        dict_resultats.setdefault(key, [])
        dict_resultats[key].append(inscription)
    data['dict_inscriptions_by_individu'] = dict_resultats

    #-------------------------- Importation des données des individus ------------------------------

    # Importation des consommations existantes
    if "liste_conso_json" not in data:
        liste_conso = Consommation.objects.select_related("inscription").filter(data["conditions_periodes"] & Q(inscription__in=data["liste_inscriptions"]))
        data["liste_conso"] = liste_conso
        data["liste_conso_json"] = serializers.serialize('json', liste_conso)

    # Importation des mémos journaliers
    liste_memos = MemoJournee.objects.filter(date__gte=data["date_min"], date__lte=data["date_max"], inscription__in=data["liste_inscriptions"])
    data['liste_memos_json'] = serializers.serialize('json', liste_memos)

    # Importation des déductions
    dict_deductions = {}
    for deduction in Deduction.objects.filter(famille_id__in=data["liste_familles"], date__gte=data["date_min"], date__lte=data["date_max"]):
        dict_deductions.setdefault(deduction.prestation_id, [])
        dict_deductions[deduction.prestation_id].append({"label": deduction.label, "date": str(deduction.date), "aide": deduction.aide_id, "montant": float(deduction.montant)})

    # Importation des prestations
    conditions = Q(pk__in=[conso.prestation_id for conso in data.get("liste_conso", [])]) | Q(categorie="consommation") & (data["conditions_periodes"] | (Q(forfait_date_debut__lte=data["date_max"]) & Q(forfait_date_fin__gte=data["date_min"])))
    if data["mode"] in ("individu", "portail"):
        conditions &= Q(famille_id=data["idfamille"]) & Q(individu__in=data["liste_individus"])
    liste_prestations = Prestation.objects.filter(conditions)
    for p in liste_prestations:
        if p.pk not in data["dict_suppressions"]["prestations"]:
            data["prestations"][p.pk] = {
                "date": str(p.date), "categorie": p.categorie, "label": p.label, "montant_initial": float(p.montant_initial),
                "montant": float(p.montant), "activite": p.activite_id, "tarif": p.tarif_id, "facture": p.facture_id,
                "famille": p.famille_id, "individu": p.individu_id, "categorie_tarif": p.categorie_tarif_id, "temps_facture": utils_dates.DeltaEnStr(p.temps_facture, separateur=":"),
                "quantite": p.quantite, "tarif_ligne": p.tarif_ligne_id, "tva": float(p.tva) if p.tva else None, "code_compta": p.code_compta, "aides": [],
                "forfait_date_debut": str(p.forfait_date_debut) if p.forfait_date_debut else None, "forfait_date_fin": str(p.forfait_date_fin) if p.forfait_date_fin else None,
                "forfait": p.forfait, "dirty": False,
            }
            if p.pk in dict_deductions:
                data["prestations"][p.pk]["aides"] = dict_deductions[p.pk]

            if p.forfait_date_debut:
                # Création d'une couleur pour le forfait crédit
                data["prestations"][p.pk]["couleur"] = ColorHash(str(p.pk)).hex

    data['dict_prestations_json'] = mark_safe(json.dumps(data["prestations"]))
    #logger.debug("prestations=" + str(data['dict_prestations_json']))


    #-------------------------- Importation des données du calendrier ------------------------------

    # Importation des ouvertures
    list_groupes_inscriptions = list({inscription.groupe_id: None for inscription in data["liste_inscriptions"]}.keys())
    liste_ouvertures = []
    liste_dates = []
    liste_unites_ouvertes = []
    for ouverture in Ouverture.objects.filter(data["conditions_periodes"] & Q(activite=data['selection_activite'])):
        liste_ouvertures.append("%s_%s_%s" % (ouverture.date, ouverture.groupe_id, ouverture.unite_id))
        if ouverture.date not in liste_dates and ouverture.groupe_id in list_groupes_inscriptions:
            liste_dates.append(ouverture.date)
        if ouverture.unite_id not in liste_unites_ouvertes:
            liste_unites_ouvertes.append(ouverture.unite_id)
    data['liste_ouvertures'] = liste_ouvertures

    # Récupération des dates
    liste_dates.sort()
    data['liste_dates'] = liste_dates

    # Importation des vacances
    if "liste_vacances" not in data:
        liste_vacances = Vacance.objects.filter(date_fin__gte=data["date_min"], date_debut__lte=data["date_max"])
        data['liste_vacances'] = liste_vacances
    data['liste_vacances_json'] = mark_safe(json.dumps([(str(vac.date_debut), str(vac.date_fin)) for vac in data['liste_vacances']]))

    # Importation des événements
    liste_evenements = Evenement.objects.select_related("categorie").filter(data["conditions_periodes"] & Q(activite=data['selection_activite'])).order_by("date", "heure_debut")
    data["liste_evenements_json"] = serializers.serialize('json', liste_evenements)
    data["liste_evenements"] = liste_evenements
    data["liste_images_evenements"] = [evt for evt in liste_evenements if evt.image]
    data["liste_categories_evenements"] = list({evt.categorie: True for evt in liste_evenements if evt.categorie}.keys())
    data["dict_categories_evenements_json"] = json.dumps({categorie.pk: {"nom": categorie.nom, "image": categorie.get_nom_image(), "questions": categorie.questions, "limitations": categorie.limitations} for categorie in data["liste_categories_evenements"]})

    # Importation des remplissages
    liste_remplissage = Remplissage.objects.filter(data["conditions_periodes"] & Q(activite=data['selection_activite']))
    data['dict_capacite_json'] = mark_safe(json.dumps({'%s_%d_%d' % (r.date, r.unite_remplissage_id, r.groupe_id or 0): r.places for r in liste_remplissage}))

    # Importation des unités de remplissage
    liste_unites_remplissage = UniteRemplissage.objects.prefetch_related('unites').filter(activite=data['selection_activite']).order_by("ordre")
    data['liste_unites_remplissage'] = liste_unites_remplissage

    # Prépare un dict unités de remplissage par unité de conso pour le dict des unités de conso
    dict_unites_remplissage_unites = {}
    dict_unites_remplissage_json = {}
    for unite in liste_unites_remplissage:
        for unite_conso in unite.unites.all():
            dict_unites_remplissage_json.setdefault(unite.pk, {"unites_conso": [], "seuil_alerte": unite.seuil_alerte})
            dict_unites_remplissage_json[unite.pk]["unites_conso"].append(unite_conso.pk)
            dict_unites_remplissage_unites.setdefault(unite_conso.pk, [])
            dict_unites_remplissage_unites[unite_conso.pk].append(unite.pk)
    data['dict_unites_remplissage_json'] = mark_safe(json.dumps(dict_unites_remplissage_json))

    # Importation des places prises
    liste_places = list(Consommation.objects.values('pk', 'date', 'unite', 'groupe', 'quantite', 'evenement').annotate(nbre=Count('pk')).filter(data["conditions_periodes"] & Q(activite=data['selection_activite']) & Q(etat__in=("reservation", "present", "attente"))).exclude(inscription__in=data["liste_inscriptions"]))
    dict_places = {}

    if data.get("consommations", []):
        # Ajout des places prises masquées (notamment si fraterie masquée)
        inscriptions_affichees = [inscription.pk for inscription in data["liste_inscriptions"]]
        consommations_temp = [conso["pk"] for conso in liste_places]
        for key, liste_conso_temp in data.get("consommations", {}).items():
            for conso_temp in liste_conso_temp:
                if conso_temp["inscription"] not in inscriptions_affichees and conso_temp["pk"] not in consommations_temp:
                    conso_temp["nbre"] = 1
                    liste_places.append(conso_temp)

    for p in liste_places:
        for idgroupe in [p["groupe"], 0]:
            key = "%s_%d_%d" % (p["date"], p["unite"], idgroupe)
            quantite = p["nbre"] * p["quantite"] if p["quantite"] else p["nbre"]
            dict_places[key] = dict_places.get(key, 0) + quantite
            if p["evenement"]:
                key += "_%d" % p["evenement"]
                dict_places[key] = dict_places.get(key, 0) + quantite
    data['dict_places_json'] = mark_safe(json.dumps(dict_places))

    # Importation des groupes
    data['liste_groupes'] = Groupe.objects.filter(activite=data['selection_activite']).order_by("ordre")
    data['liste_groupes_json'] = serializers.serialize('json', data['liste_groupes'])

    # Sélection des groupes
    if data["mode"] in ("date", "pointeuse") and not data['selection_groupes']:
        data['selection_groupes'] = [groupe.pk for groupe in data['liste_groupes']]

    # Importation des unités de conso
    groupes_utilises = list({inscription.groupe: True for inscription in data['liste_inscriptions']}.keys()) + data.get("selection_groupes", [])
    categories_tarifs_utilisees = list({inscription.categorie_tarif: True for inscription in data['liste_inscriptions']}.keys())
    conditions = (Q(groupes__in=groupes_utilises) | Q(groupes__isnull=True)) & (Q(categories_tarifs__in=categories_tarifs_utilisees) | Q(categories_tarifs__isnull=True))
    data["liste_unites"] = Unite.objects.select_related('activite').prefetch_related('groupes', 'incompatibilites', 'dependances').filter(conditions, activite=data['selection_activite']).distinct().order_by("ordre")

    # Sélection des unités visibles
    data["liste_unites_visibles"] = [unite for unite in data["liste_unites"] if unite.pk in liste_unites_ouvertes and (unite.visible_portail or data["mode"] != "portail")]

    # Recherche s'il y a des forfaits crédit dans les tarifs de l'activité
    data["tarifs_credits_exists"] = Tarif.objects.filter(type="CREDIT", activite=data['selection_activite']).exists()
    data["liste_idinscription"] = [inscription.pk for inscription in data["liste_inscriptions"]]

    # Recherche les tarifs spéciaux (choix)
    conditions = Q(methode="choix", activite=data["selection_activite"], date_debut__lte=data["date_max"]) & (Q(date_fin__gte=data["date_min"]) | Q(date_fin__isnull=True))
    tarifs_choix = Tarif.objects.prefetch_related("categories_tarifs").filter(conditions)
    if tarifs_choix:
        tarifs_temp = {}
        for ligne in TarifLigne.objects.select_related("tarif").filter(tarif__in=tarifs_choix):
            tarifs_temp.setdefault(ligne.tarif_id, {"unites": [], "categories_tarifs": [], "lignes": []})
            tarifs_temp[ligne.tarif_id]["lignes"].append({"idligne": ligne.pk, "label": ligne.label, "montant": float(ligne.montant_unique)})

        for combi in CombiTarif.objects.prefetch_related("unites").filter(tarif__in=tarifs_choix):
            for unite in combi.unites.all():
                tarifs_temp[combi.tarif_id]["unites"].append(unite.pk)

        for tarif in tarifs_choix:
            for categorie in tarif.categories_tarifs.all():
                tarifs_temp[tarif.pk]["categories_tarifs"].append(categorie.pk)
        data["tarifs_speciaux_json"] = json.dumps(tarifs_temp)
    else:
        data["tarifs_speciaux_json"] = json.dumps({})

    # Conversion des unités de conso en JSON
    liste_unites_json = []
    for unite in data["liste_unites"]:
        liste_unites_json.append({
            "pk": unite.pk, "fields": {"activite": unite.activite_id, "nom": unite.nom, "abrege": unite.abrege, "type": unite.type,
            "heure_debut": str(unite.heure_debut or ""), "heure_fin": str(unite.heure_fin or ""), "heure_debut_fixe": unite.heure_debut_fixe,
            "heure_fin_fixe": unite.heure_fin_fixe, "touche_raccourci": unite.touche_raccourci, "largeur": unite.largeur,
            "groupes": [groupe.pk for groupe in unite.groupes.all()], "incompatibilites": [u.pk for u in unite.incompatibilites.all()],
            "visible_portail": unite.visible_portail, "imposer_saisie_valeur": unite.imposer_saisie_valeur,
            "unites_remplissage": dict_unites_remplissage_unites.get(unite.pk, []),
            "heure_debut_min": str(unite.heure_debut_min or ""), "heure_debut_max": str(unite.heure_debut_max or ""),
            "heure_fin_min": str(unite.heure_fin_min or ""), "heure_fin_max": str(unite.heure_fin_max or ""),
            "dependances": [u.pk for u in unite.dependances.all()]}})
    data['liste_unites_json'] = json.dumps(liste_unites_json)

    # Conversion au format json
    data["periode_json"] = mark_safe(json.dumps(data["periode"]))
    data["consommations_json"] = mark_safe(json.dumps(data["consommations"]))
    data["memos_json"] = mark_safe(json.dumps(data["memos"]))
    data["options_json"] = mark_safe(json.dumps(data.get("options", {})))
    data["dict_suppressions_json"] = mark_safe(json.dumps(data["dict_suppressions"]))
    # data["liste_idindividus_json"] = mark_safe(json.dumps(data["liste_idindividus"]))
    data["liste_key_individus_json"] = mark_safe(json.dumps(data["liste_key_individus"]))

    # Suppression de données inutiles
    for key in ("liste_familles", "periode", "consommations", "memos", "dict_suppressions", "liste_idindividus", "liste_key_individus", "liste_evenements", "prestations"):
        if key in data:
            del data[key]

    # Pour les tests de performance
    # Facturer()

    return data


def Save_grille(request=None, donnees={}):
    logger.debug("Sauvegarde de la grille...")
    #logger.debug("prestations : " + str(donnees["prestations"]))
    #logger.debug("suppressions : " + str(donnees["suppressions"]))
    chrono = time.time()

    liste_historique = []
    detail_evenements = {}

    # ----------------------------------- PRESTATIONS --------------------------------------

    # Enregistrement des prestations
    dict_idprestation = {}
    liste_nouvelles_prestations = []
    liste_IDprestation_existants = []
    for IDprestation, dict_prestation in donnees["prestations"].items():

        prestation_temp = {
            "date": dict_prestation["date"], "categorie": "consommation", "label": dict_prestation["label"], "montant_initial": dict_prestation["montant_initial"],
            "montant": dict_prestation["montant"], "activite_id": dict_prestation["activite"], "tarif_id": dict_prestation["tarif"], "famille_id": dict_prestation["famille"],
            "individu_id": dict_prestation["individu"], "temps_facture": utils_dates.HeureStrEnDelta(dict_prestation["temps_facture"]), "categorie_tarif_id": dict_prestation["categorie_tarif"],
            "quantite": dict_prestation["quantite"], "tarif_ligne_id": dict_prestation["tarif_ligne"], "tva": dict_prestation["tva"], "code_compta": dict_prestation["code_compta"],
            "forfait_date_debut": dict_prestation["forfait_date_debut"], "forfait_date_fin": dict_prestation["forfait_date_fin"],
        }

        # Enregistrement des nouvelles prestations
        if "-" in IDprestation:
            logger.debug("Prestation à ajouter : ID" + str(IDprestation) + " > " + str(dict_prestation))
            prestation = Prestation.objects.create(**prestation_temp)
            liste_nouvelles_prestations.append(prestation)

            liste_historique.append({"titre": "Ajout d'une prestation", "detail": "%s du %s" % (dict_prestation["label"], utils_dates.ConvertDateToFR(dict_prestation["date"])), "utilisateur": request.user if request else None,
                                     "famille_id": dict_prestation["famille"], "individu_id": dict_prestation["individu"], "objet": "Prestation", "idobjet": prestation.pk, "classe": "Prestation", "activite_id": dict_prestation["activite"]})

            # Mémorise la correspondante du nouvel IDprestation avec l'ancien IDprestation
            dict_idprestation[IDprestation] = prestation.pk

            # Enregistrement des aides
            for dict_aide in dict_prestation["aides"]:
                deduction = Deduction.objects.create(date=dict_prestation["date"], label=dict_aide["label"], aide_id=dict_aide["aide"], famille_id=dict_prestation["famille"], prestation=prestation, montant=dict_aide["montant"])
                liste_historique.append({"titre": "Ajout d'une déduction", "detail": "%s du %s" % (dict_aide["label"], utils_dates.ConvertDateToFR(dict_prestation["date"])), "utilisateur": request.user if request else None,
                                         "famille_id": dict_prestation["famille"], "individu_id": dict_prestation["individu"], "objet": "Déduction", "idobjet": deduction.pk, "classe": "Deduction", "activite_id": dict_prestation["activite"]})

        # Modification de prestations
        if "-" not in IDprestation:
            liste_IDprestation_existants.append(IDprestation)

            if dict_prestation.get("dirty", False):
                Prestation.objects.filter(pk=int(IDprestation)).update(**prestation_temp)

    # ---------------------------------- CONSOMMATIONS -------------------------------------

    dict_unites = {unite.pk: unite for unite in Unite.objects.all()}

    # Analyse et préparation des consommations
    liste_ajouts = []
    dict_modifications = {}
    dict_idconso = {}
    date_saisie = datetime.datetime.now()
    for key_case, consommations in donnees["consommations"].items():
        for dict_conso in consommations:
            # Recherche du nouvel IDprestation
            dict_conso["prestation"] = dict_idprestation.get(dict_conso["prestation"], dict_conso["prestation"])

            if "-" in str(dict_conso["pk"]):
                liste_ajouts.append(Consommation(
                    individu_id=dict_conso["individu"], inscription_id=dict_conso["inscription"], activite_id=dict_conso["activite"], date=dict_conso["date"],
                    unite_id=dict_conso["unite"], groupe_id=dict_conso["groupe"], heure_debut=dict_conso["heure_debut"], heure_fin=dict_conso["heure_fin"],
                    etat=dict_conso["etat"], categorie_tarif_id=dict_conso["categorie_tarif"], prestation_id=dict_conso["prestation"], quantite=dict_conso["quantite"],
                    evenement_id=dict_conso["evenement"], badgeage_debut=dict_conso["badgeage_debut"], badgeage_fin=dict_conso["badgeage_fin"],
                    options=dict_conso.get("options", None), extra=dict_conso.get("extra", None), date_saisie=date_saisie,
                ))
                logger.debug("Consommation à ajouter : " + str(dict_conso))
                label_conso = dict_conso["nom_evenement"] if "nom_evenement" in dict_conso else dict_unites[dict_conso["unite"]].nom
                liste_historique.append({"titre": "Ajout d'une consommation", "detail": "%s du %s (%s)" % (label_conso, utils_dates.ConvertDateToFR(dict_conso["date"]), utils_consommations.Get_label_etat(dict_conso["etat"])), "utilisateur": request.user if request else None,
                                         "famille_id": dict_conso["famille"], "individu_id": dict_conso["individu"], "objet": "Consommation", "idobjet": None, "classe": "Consommation", "activite_id": dict_conso["activite"], "date": dict_conso["date"]})
                detail_evenements[len(liste_historique)-1] = dict_conso.get("description_evenement", None)

                # Mode pointeuse pour récupérer l'idconso
                if donnees.get("mode", None) == "pointeuse":
                    liste_ajouts[0].save()
                    dict_idconso[dict_conso["pk"]] = liste_ajouts[0].pk
                    liste_ajouts = []

            elif dict_conso["dirty"]:
                dict_modifications[dict_conso["pk"]] = dict_conso
                logger.debug("Consommation à modifier : " + str(dict_conso))
                liste_historique.append({"titre": "Modification d'une consommation", "detail": "%s du %s (%s)" % (dict_unites[dict_conso["unite"]].nom, utils_dates.ConvertDateToFR(dict_conso["date"]), utils_consommations.Get_label_etat(dict_conso["etat"])), "utilisateur": request.user if request else None,
                                         "famille_id": dict_conso["famille"], "individu_id": dict_conso["individu"], "objet": "Consommation", "idobjet": dict_conso["pk"], "classe": "Consommation", "activite_id": dict_conso["activite"], "date": dict_conso["date"]})

    # Récupère la liste des conso à modifier
    liste_modifications = []
    for conso in Consommation.objects.filter(pk__in=dict_modifications.keys()):
        conso.groupe_id = dict_modifications[conso.pk]["groupe"]
        conso.heure_debut = dict_modifications[conso.pk]["heure_debut"]
        conso.heure_fin = dict_modifications[conso.pk]["heure_fin"]
        conso.etat = dict_modifications[conso.pk]["etat"]
        conso.categorie_tarif_id = dict_modifications[conso.pk]["categorie_tarif"]
        conso.prestation_id = dict_modifications[conso.pk]["prestation"]
        conso.quantite = dict_modifications[conso.pk]["quantite"]
        conso.options = dict_modifications[conso.pk]["options"]
        conso.extra = dict_modifications[conso.pk]["extra"]

        if conso.prestation_id in dict_idprestation:
            conso.prestation_id = dict_idprestation[conso.prestation_id]

        liste_modifications.append(conso)

    # Traitement dans la base
    texte_notification = []
    if liste_ajouts:
        Consommation.objects.bulk_create(liste_ajouts)
        texte_notification.append("%s ajout%s" % (len(liste_ajouts), "s" if len(liste_ajouts) > 1 else ""))
    if liste_modifications:
        Consommation.objects.bulk_update(liste_modifications, ["groupe", "heure_debut", "heure_fin", "etat", "categorie_tarif", "prestation", "quantite", "options", "extra"], batch_size=50)
        texte_notification.append("%s modification%s" % (len(liste_modifications), "s" if len(liste_modifications) > 1 else ""))
    if donnees["suppressions"]["consommations"]:
        logger.debug("Consommations à supprimer : " + str(donnees["suppressions"]["consommations"]))
        liste_conso_suppr = list(Consommation.objects.select_related("unite", "inscription", "evenement").filter(pk__in=donnees["suppressions"]["consommations"]))
        qs = Consommation.objects.filter(pk__in=donnees["suppressions"]["consommations"])
        qs._raw_delete(qs.db)
        texte_notification.append("%s suppression%s" % (len(donnees["suppressions"]["consommations"]), "s" if len(donnees["suppressions"]["consommations"]) > 1 else ""))
        for conso in liste_conso_suppr:
            label_conso = conso.evenement.nom if conso.evenement else conso.unite.nom
            liste_historique.append({"titre": "Suppression d'une consommation", "detail": "%s du %s (%s)" % (label_conso, utils_dates.ConvertDateToFR(conso.date), conso.get_etat_display()), "date": conso.date, "activite_id": conso.activite_id,
                                     "utilisateur": request.user if request else None, "famille_id": conso.inscription.famille_id, "individu_id": conso.individu_id, "objet": "Consommation", "idobjet": conso.pk, "classe": "Consommation"})

    # Notification d'enregistrement des consommations
    # if texte_notification and request:
    #     messages.add_message(request, messages.SUCCESS, "Consommations enregistrées : %s" % utils_texte.Convert_liste_to_texte_virgules(texte_notification))

    # Suppression des prestations obsolètes (après la suppression des consommations associées)
    logger.debug("Prestations à supprimer : " + str(donnees["suppressions"]["prestations"]))
    liste_prestations_suppr = []
    if donnees["suppressions"]["prestations"]:
        liste_prestations_suppr = list(Prestation.objects.filter(pk__in=donnees["suppressions"]["prestations"]))

        qs = Deduction.objects.filter(prestation_id__in=donnees["suppressions"]["prestations"])
        qs._raw_delete(qs.db)

        # Pour supprimer les consommations fantômes
        Consommation.objects.filter(prestation_id__in=donnees["suppressions"]["prestations"]).delete()

        Ventilation.objects.filter(prestation_id__in=donnees["suppressions"]["prestations"]).delete()
        qs = Prestation.objects.filter(pk__in=donnees["suppressions"]["prestations"])
        qs._raw_delete(qs.db)

        for prestation in liste_prestations_suppr:
            liste_historique.append({"titre": "Suppression d'une prestation", "detail": "%s du %s" % (prestation.label, utils_dates.ConvertDateToFR(prestation.date)),
                                     "utilisateur": request.user if request else None, "famille_id": prestation.famille_id, "individu_id": prestation.individu_id, "objet": "Prestation", "idobjet": prestation.pk, "classe": "Prestation", "activite_id": prestation.activite_id})

    # ------------------ TRAITEMENT DES TARIFS SELON NBRE INDIVIDUS PRESENTS -------------------

    Maj_tarifs_fratries(activite=donnees.get("selection_activite", None) or donnees.get("activite", None) or donnees.get("ancienne_activite", None), prestations=liste_nouvelles_prestations + liste_prestations_suppr, liste_IDprestation_existants=liste_IDprestation_existants)

    # ---------------------------------- MEMOS JOURNALIERS -------------------------------------

    if "memos" in donnees:

        # Analyse et préparation des mémos
        liste_ajouts = []
        dict_modifications = {}
        for key_case, dict_memo in donnees["memos"].items():
            if dict_memo["texte"]:
                if not dict_memo["pk"]:
                    liste_ajouts.append(MemoJournee(date=dict_memo["date"], inscription_id=dict_memo["inscription"], texte=dict_memo["texte"]))
                elif dict_memo["dirty"]:
                    dict_modifications[dict_memo["pk"]] = dict_memo

        # Récupère la liste des mémos à modifier
        liste_modifications = []
        for memo in MemoJournee.objects.filter(pk__in=dict_modifications.keys()):
            memo.texte = dict_modifications[memo.pk]["texte"]
            liste_modifications.append(memo)

        # Traitement dans la base
        if liste_ajouts:
            MemoJournee.objects.bulk_create(liste_ajouts)
        if liste_modifications:
            MemoJournee.objects.bulk_update(liste_modifications, ["texte"])
        if donnees["suppressions"]["memos"]:
            qs = MemoJournee.objects.filter(pk__in=donnees["suppressions"]["memos"])
            qs._raw_delete(qs.db)

    # Sauvegarde de l'historique
    utils_historique.Ajouter_plusieurs(liste_historique)

    # Affiche le chrono
    logger.debug("Temps d'enregistrement de la grille : " + str(time.time() - chrono))

    resultat = {
        "dict_idprestation": dict_idprestation,
        "dict_idconso": dict_idconso,
        "liste_historique": liste_historique,
        "detail_evenements": detail_evenements,
    }
    return resultat


def CompareDict(dict1={}, dict2={}, keys=[]):
    """ Compare les valeurs de 2 dictionnaires selon les clés données """
    for key in keys:
        if dict1[key] != dict2[key]:
            return False
    return True


def Facturer(request=None):
    donnees_aller = json.loads(request.POST.get("donnees", "{}"))
    logger.debug("============== Facturation ================")
    logger.debug("données aller : " + str(donnees_aller))
    facturation = Facturation(donnees=donnees_aller)
    donnees_retour = facturation.Facturer()
    #logger.debug("données retour : " + str(donnees_retour))

    # Si mode pointage, sauvegarde les données
    if donnees_aller.get("mode", None) == "pointeuse":

        # Attribue les nouvelles prestations aux consommations
        for key_case, idprestation in donnees_retour["modifications_idprestation"].items():
            for key_conso, liste_conso in donnees_aller["consommations"].items():
                for dict_conso in liste_conso:
                    if dict_conso["key_case"] == key_case:
                        dict_conso["prestation"] = idprestation
                        dict_conso["dirty"] = True

        # Ajouter les nouvelles prestations pour la sauvegarde
        donnees_aller["prestations"].update(donnees_retour["nouvelles_prestations"])
        donnees_save = {
            "mode": donnees_aller.get("mode", None),
            "consommations": donnees_aller["consommations"],
            "prestations": donnees_aller["prestations"],
            "suppressions": {
                "consommations": donnees_aller["dict_suppressions"]["consommations"],
                "prestations": [int(idprestation) for idprestation in donnees_retour["anciennes_prestations"] if "-" not in str(idprestation)],
                "memos": [],
            },
        }
        resultat = Save_grille(request=request, donnees=donnees_save)
        dict_idprestation = resultat["dict_idprestation"]
        dict_idconso = resultat["dict_idconso"]
        donnees_retour["modifications_idconso"] = dict_idconso

        # Attribue les nouvelles prestations aux consommations
        for key_case, idprestation in donnees_retour["modifications_idprestation"].items():
            if idprestation in dict_idprestation:
                donnees_retour["modifications_idprestation"][key_case] = dict_idprestation[idprestation]

        # Remplacement des anciens idprestation par les nouveaux idprestation
        for idprestation in list(donnees_retour["nouvelles_prestations"].keys()):
            if idprestation in dict_idprestation:
                nouvel_idprestation = dict_idprestation[idprestation]
                donnees_retour["nouvelles_prestations"][nouvel_idprestation] = donnees_retour["nouvelles_prestations"][idprestation]
                donnees_retour["nouvelles_prestations"][nouvel_idprestation]["prestation"] = nouvel_idprestation
                del donnees_retour["nouvelles_prestations"][idprestation]

    return JsonResponse(donnees_retour)



class Facturation():
    def __init__(self, donnees={}):
        self.donnees = donnees
        self.dict_modif_cases = {}
        self.liste_anciennes_prestations = []
        self.dict_nouvelles_prestations = {}
        self.dict_lignes_tarifs = {}
        self.dict_quotients = {}
        self.dict_tarifs = {}
        self.dict_combi_tarif = {}
        self.dict_aides = {}
        self.tarif_fratries_exists = False

    def Facturer(self):
        messages = []
        tout_recalculer = False
        for key_case, case_tableau in self.donnees["cases_touchees"].items():
            #logger.debug("Case étudiée : " + str(key_case))

            if key_case not in self.dict_modif_cases:

                action = "saisie" # todo : PROVISOIRE
                modeSilencieux = False # todo : PROVISOIRE
                dict_options_conso = {}

                # Recherche les unités utilisées de la ligne
                dictUnitesUtilisees = {}
                dictQuantites = {}
                for conso in self.donnees["consommations"].get("%s_%s" % (case_tableau["date"], case_tableau["inscription"]), []):
                    if not conso["forfait"] and (conso["unite"] not in dictUnitesUtilisees or dictUnitesUtilisees[conso["unite"]] in (None, "attente", "refus", "demande")):
                        dictUnitesUtilisees[conso["unite"]] = conso["etat"]
                    dictQuantites[conso["unite"]] = conso["quantite"]
                    options = conso.get("options", None)
                    if options:
                        dict_options_conso[conso["unite"]] = options
                #logger.debug("Unités utilisées sur la ligne : " + str(dictUnitesUtilisees))

                # Mémorise les tarifs
                key = (case_tableau["activite"], case_tableau["categorie_tarif"])
                if key not in self.dict_tarifs:
                    self.dict_tarifs[key] = Tarif.objects.prefetch_related('groupes', 'caisses', 'nom_tarif').filter(activite_id=case_tableau["activite"], categories_tarifs=case_tableau["categorie_tarif"]).order_by("date_debut")

                # Recherche un tarif valable pour cette date
                tarifs_valides1 = []
                liste_id_tarif = []
                for tarif in self.dict_tarifs[key]:
                    if self.Recherche_tarif_valide(tarif, case_tableau):
                        tarifs_valides1.append(tarif)
                        liste_id_tarif.append(str(tarif.pk))
                liste_id_tarif.sort()
                liste_id_tarif_str = ";".join(liste_id_tarif)

                # Importation des combi de ces tarifs
                self.dict_combi_by_activite = {}
                if liste_id_tarif_str not in self.dict_combi_tarif:
                    self.dict_combi_tarif[liste_id_tarif_str] = CombiTarif.objects.prefetch_related('unites').filter(tarif__in=tarifs_valides1)
                for combi in self.dict_combi_tarif[liste_id_tarif_str]:
                    self.dict_combi_by_activite.setdefault(combi.tarif_id, [])
                    self.dict_combi_by_activite[combi.tarif_id].append(combi)

                # Recherche des combinaisons présentes
                tarifs_valides2 = []
                for tarif in tarifs_valides1:
                    tarif.nbre_max_unites_combi = 0
                    for combinaison in self.dict_combi_by_activite.get(tarif.pk, []):
                        unites_combi = [unite.pk for unite in combinaison.unites.all()]
                        unites_combi.sort()
                        if self.Recherche_combinaison(dictUnitesUtilisees, unites_combi, tarif):
                            if len(unites_combi) > tarif.nbre_max_unites_combi:
                                tarif.nbre_max_unites_combi = len(unites_combi)
                                tarif.combi_retenue = unites_combi
                                tarif.combinaison = combinaison
                                tarifs_valides2.append(tarif)

                # Tri des tarifs par date de début puis par nbre d'unités
                tarifs_valides2.sort(key=lambda tarif: tarif.date_debut, reverse=True)
                tarifs_valides2.sort(key=lambda tarif: tarif.nbre_max_unites_combi, reverse=True)

                #-----------------------------------------------------------
                # Si forfaits au crédits présents dans les tarifs

                nbre_tarifs_forfait = len([tarif for tarif in tarifs_valides2 if tarif.type == "CREDIT"])
                if nbre_tarifs_forfait:
                    tarifs_valides3 = []
                    for tarif in tarifs_valides2:
                        if tarif.type == "CREDIT":
                            # tarif crédit
                            IDprestationForfait = self.Recherche_forfait_credit(tarif=tarif, case_tableau=case_tableau)

                            # Vérification des quantités max
                            if IDprestationForfait and tarif.combinaison.quantite_max and not tarif.forfait_auto:
                                dict_quantites = {}

                                # Recherche la quantité de conso dans la grille affichée
                                for key, liste_conso_temp in self.donnees["consommations"].items():
                                    for conso in liste_conso_temp:
                                        if (tarif.forfait_beneficiaire == "individu" and conso["inscription"] == case_tableau["inscription"]) or (tarif.forfait_beneficiaire == "famille" and conso["famille"] == case_tableau["famille"]):
                                            dict_quantites.setdefault(key, [])
                                            dict_quantites[key].append(conso["unite"])
                                            dict_quantites[key].sort()

                                # Recherche la quantité de conso déjà enregistrées dans la DB
                                if "-" not in IDprestationForfait:
                                    for conso in Consommation.objects.filter(prestation_id=IDprestationForfait):
                                        key = "%s_%d" % (conso.date, conso.inscription_id)
                                        dict_quantites.setdefault(key, [])
                                        dict_quantites[key].append(conso.unite_id)
                                        dict_quantites[key].sort()

                                # Compte la quantité de conso utilisées
                                quantite_forfait = len([key for key, unites in dict_quantites.items() if unites == tarif.combi_retenue])
                                if quantite_forfait > tarif.combinaison.quantite_max:
                                    IDprestationForfait = None
                                    messages.append(("info", "Il n'y a plus de crédit disponible dans le forfait !"))
                                    # if "blocage_plafond" in tarif.options:
                                    #     pass

                            # Recherche ici si ce forfait est applicable
                            if not IDprestationForfait and tarif.forfait_auto:
                                IDprestationForfait = self.Recherche_forfait_applicable(tarif=tarif, case_tableau=case_tableau)

                            if IDprestationForfait:
                                tarif.credit = IDprestationForfait
                                tarifs_valides3.append(tarif)

                        else:
                            # Tarif normal
                            tarifs_valides3.append(tarif)

                    # Met les forfaits crédit en premier
                    tarifs_valides3.sort(key=lambda tarif: tarif.type)

                    tarifs_valides2 = tarifs_valides3

                #-----------------------------------------------------------

                # Sélection des tarifs qui ont le plus grand nombre d'unités
                liste_tarifs_retenus = []
                liste_unites_traitees = []
                for tarif in tarifs_valides2:

                    # Recherche des unités non traitées
                    valide = True
                    for idunite in tarif.combi_retenue:
                        if idunite in liste_unites_traitees:
                            valide = False
                    # Si le tarif est finalement retenu
                    if valide:
                        liste_tarifs_retenus.append(tarif)
                        for idunite in tarif.combi_retenue:
                            liste_unites_traitees.append(idunite)

                # Calcul des tarifs des prestations
                dictUnitesPrestations = {}
                for tarif in liste_tarifs_retenus:

                    # Recherche des évènements dans une des cases de la combinaison
                    liste_evenements = [None,]
                    logger.debug("Méthode de calcul du tarif : " + tarif.methode)

                    if "evenement" in tarif.methode:
                        # Recherche les évènements pour lesquels une conso est saisie
                        liste_evenements = []
                        for conso in self.donnees["consommations"].get("%s_%s" % (case_tableau["date"], case_tableau["inscription"]), []):
                            if conso["evenement"] and conso["etat"] not in ("attente", "refus", "demande"):
                                idevenement = conso["evenement"]
                                evenement = Evenement.objects.filter(pk=idevenement).first()
                                liste_evenements.append(evenement)
                                logger.debug("Evenement trouvé sur la ligne : ID" + str(idevenement))


                    # Mémorise le tarif initial pour les évènements
                    tarif_base = copy.deepcopy(tarif)
                    for evenement in liste_evenements:
                        # Recherche un tarif spécial évènement
                        if evenement:
                            tarif = None
                            # tarif avancé
                            for tarif_evenement in Tarif.objects.filter(evenement=evenement, categories_tarifs=case_tableau["categorie_tarif"]).order_by("date_debut"):
                                if self.Recherche_tarif_valide(tarif_evenement, case_tableau):
                                    tarif = tarif_evenement
                                    tarif.nom_evenement = evenement.nom
                                    tarif.penalite = tarif_base.penalite
                                    tarif.penalite_pourcentage = tarif_base.penalite_pourcentage
                                    tarif.penalite_label = tarif_base.penalite_label
                                    logger.debug("Un tarif spécial événement a été trouvé : IDtarif " + str(tarif.pk))
                            # Tarif simple
                            if not tarif and evenement.montant:
                                tarif = tarif_base

                        # Forfait crédit
                        forfait_credit = getattr(tarif, "credit", None)

                        # Recherche du temps facturé par défaut
                        temps_facture = None
                        liste_temps = []
                        for conso in self.donnees["consommations"].get("%s_%s" % (case_tableau["date"], case_tableau["inscription"]), []):
                            if conso["unite"] in tarif_base.combi_retenue:
                                heure_debut = conso["heure_debut"]
                                heure_fin = conso["heure_fin"]
                                if heure_debut and heure_fin:
                                    liste_temps.append((heure_debut, heure_fin))
                        if liste_temps:
                            temps_facture = utils_dates.Additionne_intervalles_temps(liste_temps)

                        quantite = 0
                        for idunite in tarif_base.combi_retenue:
                            if idunite in dictQuantites:
                                if dictQuantites[idunite] and dictQuantites[idunite] > quantite:
                                    quantite = dictQuantites[idunite]

                        # Calcul du tarif
                        if not tarif and evenement:
                            continue
                        if not tarif:
                            break
                        resultat = self.Calcule_tarif(tarif, tarif_base.combi_retenue, case_tableau, temps_facture, quantite, evenement, modeSilencieux, action)
                        if resultat == False:
                            return False
                        elif resultat == "break":
                            break
                        else:
                            montant_tarif, nom_tarif, temps_facture, quantite, tarif_ligne = resultat

                        # Si tarif spécial
                        if dict_options_conso:
                            if len(tarif_base.combi_retenue) == 1 and tarif_base.combi_retenue[0] in dict_options_conso:
                                methode, id = dict_options_conso[tarif_base.combi_retenue[0]].split("=")
                                if methode == "choix_tarif":
                                    ligne = TarifLigne.objects.get(pk=int(id))
                                    montant_tarif, nom_tarif, tarif_ligne = ligne.montant_unique, ligne.label or tarif_base.nom_tarif.nom, ligne

                        logger.debug("Montant trouvé : Montant=%s (tarif=%s temps_facturé=%s Quantité=%d)" % (montant_tarif, nom_tarif, temps_facture, quantite))

                        # -------------------------------------------------------------------------
                        # ------------------- Déduction d'une aide journalière --------------------
                        # -------------------------------------------------------------------------

                        # Recherche si une aide est valable à cette date et pour cet individu et pour cette activité
                        key_aide = "%d_%d_%d" % (case_tableau["famille"], case_tableau["individu"], case_tableau["activite"])
                        if key_aide not in self.dict_aides:
                            self.dict_aides[key_aide] = Aide.objects.select_related("caisse").filter(famille_id=case_tableau["famille"], individus__pk=case_tableau["individu"], activite_id=case_tableau["activite"])

                        liste_aide_retenues = []
                        if key_aide in self.dict_aides:
                            if self.dict_aides[key_aide]:
                                logger.debug("Aides potentielles trouvées = " + str(self.dict_aides[key_aide]))

                            for aide in self.dict_aides[key_aide]:
                                if str(aide.date_debut) <= case_tableau["date"] and str(aide.date_fin) >= case_tableau["date"] and self.Verification_periodes(aide.jours_scolaires, aide.jours_vacances, case_tableau["date"]):
                                    liste_combi_valides = []

                                    # On recherche si des combinaisons sont présentes sur cette ligne
                                    for combi in CombiAide.objects.prefetch_related('unites').filter(aide=aide):
                                        if tarif_base.combi_retenue == [unite.pk for unite in combi.unites.all().order_by("pk")]:
                                            combi.nbre_max_unites = len(tarif_base.combi_retenue)
                                            liste_combi_valides.append(combi)

                                    if liste_combi_valides:
                                        # Tri des combinaisons par nombre d'unités et on garde la combi qui a le plus grand nombre d'unités
                                        liste_combi_valides.sort(key=lambda combi: combi.nbre_max_unites, reverse=True)
                                        combi_retenue = liste_combi_valides[0]
                                        logger.debug("Combi aide retenue : " + str(combi_retenue))

                                        # Vérifie que le montant max ou le nbre de dates max n'est pas déjà atteint avant application
                                        aide_valide = True
                                        liste_aides_utilisees = []
                                        if aide.nbre_dates_max or aide.montant_max:

                                            def Ajoute_aide(IDprestation, date, IDindividu, montant):
                                                if IDprestation not in self.liste_anciennes_prestations and (IDindividu != case_tableau["individu"] or date != case_tableau["date"]):
                                                    liste_aides_utilisees.append({"idprestation": IDprestation, "date": date, "montant": montant})

                                            # Recherche dans les nouvelles prestations
                                            for IDprestation, dict_prestation in self.dict_nouvelles_prestations.items():
                                                for dict_aide in dict_prestation["aides"]:
                                                    if dict_aide["aide"] == combi_retenue.aide_id:
                                                        Ajoute_aide(IDprestation, dict_prestation["date"], dict_prestation["individu"], dict_aide["montant"])

                                            # Recherche dans les aides affichées
                                            liste_id_temp = []
                                            for dict_aide in self.donnees["dict_aides"]:
                                                if dict_aide["famille"] == case_tableau["famille"] and dict_aide["aide"] == combi_retenue.aide_id:
                                                    Ajoute_aide(dict_aide["idprestation"], dict_aide["date"], dict_aide["individu"], dict_aide["montant"])
                                                    liste_id_temp.append(dict_aide["idprestation"])

                                            # Recherche dans la base de données
                                            for deduction in Deduction.objects.filter(famille_id=case_tableau["famille"], aide=combi_retenue.aide).prefetch_related('prestation'):
                                                if deduction.prestation_id not in self.donnees["dict_suppressions"]["prestations"] and deduction.prestation_id not in liste_id_temp:
                                                    Ajoute_aide(deduction.prestation_id, str(deduction.date), deduction.prestation.individu_id, float(deduction.montant))

                                            logger.debug("%d déductions utilisent déjà cette aide : %s" % (len(liste_aides_utilisees), liste_aides_utilisees))

                                            montant_total = decimal.Decimal(0.0)
                                            dict_dates = {}
                                            for dict_aide in liste_aides_utilisees:
                                                montant_total += decimal.Decimal(dict_aide["montant"])
                                                dict_dates[dict_aide["date"]] = None

                                            if aide.nbre_dates_max and (len(dict_dates.keys()) >= aide.nbre_dates_max):
                                                logger.debug("Le nombre de dates max de l'aide est dépassé. Aide non appliquée.")
                                                aide_valide = False

                                            if aide.montant_max and (montant_total + combi_retenue.montant > aide.montant_max):
                                                logger.debug("Le montant max de l'aide est dépassé. Aide non appliquée.")
                                                aide_valide = False

                                        # Mémorisation de l'aide retenue
                                        if aide_valide:
                                            liste_aide_retenues.append(combi_retenue)


                        if not forfait_credit:
                            # Application de la déduction
                            montant_initial = montant_tarif
                            montant_final = montant_initial
                            for combi_aide in liste_aide_retenues:
                                logger.debug("Déduction d'une aide de " + str(combi_aide.montant))
                                montant_final = montant_final - combi_aide.montant

                            # Formatage du temps facturé
                            if temps_facture != None:
                                temps_facture = time.strftime("%H:%M", time.gmtime(temps_facture.seconds))

                            # -------------------------Mémorisation de la prestation ---------------------------------------------
                            dict_resultat = self.Memorise_prestation(case_tableau, tarif, nom_tarif, montant_initial, montant_final, liste_aides=liste_aide_retenues, temps_facture=temps_facture, evenement=evenement, quantite=quantite, tarif_ligne=tarif_ligne)
                            IDprestation = dict_resultat["IDprestation"]
                            if dict_resultat["nouveau"]:
                                self.dict_nouvelles_prestations[IDprestation] = dict_resultat["dictPrestation"]
                                logger.debug("Ajout de la nouvelle prestation " + str(IDprestation))
                        else:
                            if isinstance(forfait_credit, tuple):
                                # Création d'un forfait crédit automatique
                                dict_resultat = self.Memorise_prestation(case_tableau, tarif, nom_tarif, montant_tarif, montant_tarif, quantite=1, tarif_ligne=tarif_ligne,
                                                                         forfait_date_debut=str(forfait_credit[0]), forfait_date_fin=str(forfait_credit[1]))
                                IDprestation = dict_resultat["IDprestation"]
                                if dict_resultat["nouveau"]:
                                    self.dict_nouvelles_prestations[IDprestation] = dict_resultat["dictPrestation"]
                                    logger.debug("Ajout de la nouvelle prestation FORFAIT " + str(IDprestation))
                                    tout_recalculer = True
                            else:
                                # Attribution d'un forfait existant
                                IDprestation = forfait_credit

                        # Attribue à chaque unité un IDprestation
                        for IDunite in tarif_base.combi_retenue:
                            IDevenement = evenement.pk if evenement else None
                            dictUnitesPrestations[(IDunite, IDevenement)] = IDprestation

                # 7 - Parcourt toutes les unités de la date pour modifier le IDprestation
                for conso in self.donnees["consommations"].get("%s_%s" % (case_tableau["date"], case_tableau["inscription"]), []):
                    if not conso["forfait"]:

                        # Retrouve le IDprestation
                        if (conso["unite"], conso["evenement"]) in list(dictUnitesPrestations.keys()):
                            IDprestation = dictUnitesPrestations[(conso["unite"], conso["evenement"])]
                        elif (conso["unite"], None) in list(dictUnitesPrestations.keys()):
                            IDprestation = dictUnitesPrestations[(conso["unite"], None)]
                        else:
                            IDprestation = None

                        # Modification de la case
                        self.dict_modif_cases[conso["key_case"]] = IDprestation

                # 8 - Supprime des prestations qui ne sont plus utilisées sur la ligne
                for idprestation, dict_prestation in self.donnees["prestations"].items():
                    if dict_prestation["famille"] == case_tableau["famille"] and dict_prestation["individu"] == case_tableau["individu"] and dict_prestation["activite"] == case_tableau["activite"]:
                        if idprestation not in dictUnitesPrestations.values() and idprestation not in self.liste_anciennes_prestations:
                            # Suppression d'une prestation standard
                            if dict_prestation["date"] == case_tableau["date"] and not dict_prestation["forfait_date_debut"] and not dict_prestation["forfait"]:
                                logger.debug("La prestation suivante ne semble plus utilisée, on la supprime : " + str(idprestation))
                                self.liste_anciennes_prestations.append(idprestation)
                            # Suppression d'une prestation forfait-crédit
                            if dict_prestation["forfait_date_debut"]:
                                if not dict_prestation["facture"] and self.Recherche_forfait_applicable(tarif=dict_prestation["tarif"], case_tableau=case_tableau, dict_prestation=dict_prestation) == False:
                                    self.liste_anciennes_prestations.append(idprestation)
                                    tout_recalculer = True

        # Messages d'information
        if self.tarif_fratries_exists and self.donnees["mode"] in ("individu", "date"):
            messages.append(("info", "Notez que les tarifs selon le nombre d'individus par famille seront calculés uniquement après l'enregistrement"))

        donnees_retour = {
            "anciennes_prestations": self.liste_anciennes_prestations,
            "nouvelles_prestations": self.dict_nouvelles_prestations,
            "modifications_idprestation": self.dict_modif_cases,
            "messages": messages,
            "tout_recalculer": tout_recalculer,
        }
        return donnees_retour

    def Recherche_forfait_credit(self, tarif=None, case_tableau=None):
        """ Recherche un forfait dans la liste des forfaits disponibles pour une consommation donnée """
        for dict_temp in (self.donnees["prestations"].items(), self.dict_nouvelles_prestations.items()):
            for IDprestation, dict_prestation in dict_temp:
                if dict_prestation["tarif"] == tarif.pk and dict_prestation["forfait_date_debut"] <= case_tableau["date"] and dict_prestation["forfait_date_fin"] >= case_tableau["date"] and dict_prestation["famille"] == case_tableau["famille"]:
                    if dict_prestation["individu"] == case_tableau["individu"] or not dict_prestation["individu"]:
                        return IDprestation
        return None

    def Recherche_forfait_applicable(self, tarif=None, case_tableau=None, dict_prestation=None):
        dict_quantites_dates = {}
        if isinstance(tarif, int):
            tarif = Tarif.objects.get(pk=tarif)

        if not tarif.forfait_auto:
            return None

        date = case_tableau["date"]
        if dict_prestation:
            date = dict_prestation["forfait_date_debut"]

        # Recherche des paramètres du tarif automatique
        parametres_tarif = json.loads(tarif.forfait_auto)
        forfait_date_debut, forfait_date_fin = utils_consommations.Calcule_dates_forfait_credit_auto(parametres_tarif=parametres_tarif, date_conso=date)
        # print("forfait_date_debut, forfait_date_fin=", forfait_date_debut, forfait_date_fin)
        # print("dict_conso=", len(self.donnees["dict_conso"]), self.donnees["dict_conso"])
        # print("consommations=", len(self.donnees["consommations"]), self.donnees["consommations"])

        # Recherche la quantité de conso dans la grille affichée
        for categorie_donnees in ("dict_conso", "consommations"):
            for key, liste_conso_temp in self.donnees.get(categorie_donnees, {}).items():
                for conso in liste_conso_temp:
                    if str(forfait_date_debut) <= conso["date"] <= str(forfait_date_fin):
                        if (tarif.forfait_beneficiaire == "individu" and conso["inscription"] == case_tableau["inscription"]) or (
                                tarif.forfait_beneficiaire == "famille" and conso["famille"] == case_tableau["famille"]):
                            key = "%s_%s" % (key.split("_")[0], key.split("_")[1])
                            dict_quantites_dates.setdefault(key, [])
                            if conso["unite"] not in dict_quantites_dates[key]:
                                dict_quantites_dates[key].append(conso["unite"])
                                dict_quantites_dates[key].sort()
        key_affichees = list(dict_quantites_dates.items())

        # Recherche la quantité de conso déjà enregistrées dans la DB
        for conso in Consommation.objects.filter(date__gte=forfait_date_debut, date__lte=forfait_date_fin, inscription=case_tableau["inscription"]):
            key = "%s_%d" % (conso.date, conso.inscription_id)
            if key not in key_affichees and conso.unite_id not in dict_quantites_dates.get(key, []):
                dict_quantites_dates.setdefault(key, [])
                dict_quantites_dates[key].append(conso.unite_id)
                dict_quantites_dates[key].sort()
        # print("dict_quantites_dates=", dict_quantites_dates)

        # Recherche les combinaisons d'unités du tarif
        combinaisons = []
        for combinaison in self.dict_combi_by_activite.get(tarif.pk, []):
            unites_combi = [unite.pk for unite in combinaison.unites.all()]
            unites_combi.sort()
            combinaisons.append(unites_combi)

        # Compte la quantité de conso utilisées
        quantites_dates = len([key for key, unites in dict_quantites_dates.items() if unites in combinaisons])
        # print("quantites_dates=", quantites_dates)
        if quantites_dates >= parametres_tarif["nbre_conso_min"]:
            return (forfait_date_debut, forfait_date_fin)

        return False

    def Memorise_prestation(self, case_tableau, tarif, nom_tarif, montant_initial, montant_final, liste_aides=[],
                           temps_facture=None, forfait_date_debut=None, forfait_date_fin=None, evenement=None, quantite=1, tarif_ligne=None):
        """ Mémorisation de la prestation """
        # Préparation des valeurs à mémoriser
        dictPrestation = {
            "date": case_tableau["date"], "categorie": "consommation", "label": nom_tarif, "montant_initial": float(montant_initial),
            "montant": float(montant_final), "activite": case_tableau["activite"], "tarif": tarif.pk, "facture": None,
            "famille": case_tableau["famille"], "individu": case_tableau["individu"], "temps_facture": temps_facture,
            "categorie_tarif": case_tableau["categorie_tarif"], "forfait_date_debut": forfait_date_debut,
            "forfait_date_fin": forfait_date_fin, "code_compta": tarif.code_compta, "tva": tarif.tva, "forfait": None, "aides": [],
            "quantite": quantite, "tarif_ligne": tarif_ligne.pk if tarif_ligne else None,
        }

        # Recherche si une prestation identique existe déjà en mémoire
        for dict_temp in (self.donnees["prestations"].items(), self.dict_nouvelles_prestations.items()):
            for IDprestation, dict_prestation_1 in dict_temp:
                dict_prestation_2 = dict_prestation_1.copy()

                # Renvoie prestation existante si la prestation apparaît déjà sur une facture même si le montant est différent
                keys = ["date", "individu", "tarif", "famille"]
                if evenement:
                    keys.append("label")
                if dict_prestation_2["facture"] != None and CompareDict(dictPrestation, dict_prestation_2, keys=keys) == True:
                    logger.debug("Récupération d'un IDprestation facturé existant : " + str(IDprestation))
                    return {"IDprestation": IDprestation, "dictPrestation": dict_prestation_2, "nouveau": False}

                # Renvoie prestation existante si la prestation semble identique avec montants identiques
                keys = ["date", "individu", "tarif", "montant_initial", "montant", "categorie_tarif", "famille", "label", "quantite", "tarif_ligne"]

                if dictPrestation["temps_facture"]: dictPrestation["temps_facture"] = dictPrestation["temps_facture"].lstrip("0")
                if dict_prestation_2["temps_facture"]: dict_prestation_2["temps_facture"] = dict_prestation_2["temps_facture"].lstrip("0")

                if CompareDict(dictPrestation, dict_prestation_2, keys=keys) == True:
                    logger.debug("Récupération d'un IDprestation existant : " + str(IDprestation))

                    # Met à jour le temps facturé de la prestation si besoin
                    is_nouveau = False
                    if dictPrestation["temps_facture"] != dict_prestation_2["temps_facture"]:
                        dict_prestation_2.update({"temps_facture": dictPrestation["temps_facture"], "dirty": True})
                        is_nouveau = True

                    return {"IDprestation": IDprestation, "dictPrestation": dict_prestation_2, "nouveau": is_nouveau}

        # Génération d'un nouvel IDprestation
        IDprestation = str(uuid4())
        logger.debug("Génération d'un nouveau IDprestation : " + str(IDprestation))

        # Mémorisation de la prestation
        dictPrestation["prestation"] = IDprestation

        # Si forfait, on applique une couleur
        if forfait_date_debut:
            dictPrestation["couleur"] = ColorHash(str(IDprestation)).hex

        # Création des déductions pour les aides journalières
        for combi in liste_aides:
            dictPrestation["aides"].append({"label": combi.aide.nom, "date": case_tableau["date"], "aide": combi.aide_id, "montant": float(combi.montant)})

        return {"IDprestation": IDprestation, "dictPrestation": dictPrestation, "nouveau": True}


    def Recherche_combinaison(self, dictUnitesUtilisees={}, unites_combi=[], tarif=None):
        """ Recherche une combinaison donnée dans une ligne de la grille """
        for idunite in unites_combi:
            # Vérifie si chaque unité est dans la combinaison
            if idunite not in dictUnitesUtilisees:
                return False
            if dictUnitesUtilisees[idunite] == None:
                return False
            # Vérifie si l'état est valide
            if tarif.type == "JOURN":
                etat = dictUnitesUtilisees[idunite]
                if etat not in tarif.etats:
                    return False
        return True


    def Recherche_tarif_valide(self, tarif=None, case_tableau=None):
        # Vérifie si dates validité ok
        date_fin = tarif.date_fin
        if not date_fin: date_fin = datetime.date(2999, 1, 1)
        if case_tableau["date"] < str(tarif.date_debut) or case_tableau["date"] > str(date_fin):
            return False

        # Vérifie si groupe ok
        if tarif.groupes.exists():
            if case_tableau["groupe"] not in [groupe.pk for groupe in tarif.groupes.all()]:
                return False

        # Vérifie si étiquette ok
        # listeEtiquettes = dictTarif["etiquettes"]
        # if listeEtiquettes != None:
        #     valide = False
        #     for IDetiquette in etiquettes:
        #         if IDetiquette in listeEtiquettes:
        #             valide = True
        #     if valide == False:
        #         return False

        # Vérifie si cotisation à jour
        # if dictTarif["cotisations"] != None:
        #     cotisationsValide = self.VerificationCotisations(listeCotisations=dictTarif["cotisations"], date=date, IDindividu=IDindividu, IDfamille=IDfamille)
        #     if cotisationsValide == False:
        #         return False

        # Vérifie si caisse ok
        if tarif.caisses.exists():
            famille = Famille.objects.prefetch_related("caisse").get(pk=case_tableau["famille"])
            if famille.caisse_id not in [caisse.pk for caisse in tarif.caisses.all()]:
                return False

        # Vérifie si période ok
        if tarif.jours_scolaires or tarif.jours_vacances:
            if self.Verification_periodes(tarif.jours_scolaires, tarif.jours_vacances, case_tableau["date"]) == False:
                return False

        # Vérifie si filtres de questionnaires ok
        # if len(dictTarif["filtres"]) > 0:
        #     filtresValide = self.VerificationFiltres(listeFiltres=dictTarif["filtres"], date=date, IDindividu=IDindividu, IDfamille=IDfamille)
        #     if filtresValide == False:
        #         return False

        return True

    def Recherche_QF(self, tarif=None, case_tableau=None):
        """ Recherche du QF de la famille """
        IDfamille = case_tableau["famille"]
        date = utils_dates.ConvertDateENGtoDate(case_tableau["date"])

        # Si la famille a un QF :
        if IDfamille not in self.dict_quotients:
            self.dict_quotients[IDfamille] = Quotient.objects.filter(famille_id=IDfamille).order_by("date_debut")
        for quotient in self.dict_quotients[IDfamille]:
            if quotient.date_debut <= date <= quotient.date_fin and (not tarif.type_quotient or tarif.type_quotient == quotient.type_quotient):
                return quotient.quotient
        return None

    def Verification_periodes(self, jours_scolaires, jours_vacances, date):
        """ Vérifie si jour est scolaire ou vacances """
        date = utils_dates.ConvertDateENGtoDate(date)
        valide = False
        if jours_scolaires:
            if not utils_dates.EstEnVacances(date, self.donnees["liste_vacances"]) and str(date.weekday()) in [x for x in jours_scolaires]:
                valide = True
        if jours_vacances:
            if utils_dates.EstEnVacances(date, self.donnees["liste_vacances"]) and str(date.weekday()) in [x for x in jours_vacances]:
                valide = True
        return valide

    def Calcule_duree(self, case_tableau=None, combinaisons_unites=[]):
        """ Pour Facturation """
        liste_temps = []
        heure_min = None
        heure_max = None
        for conso in self.donnees["consommations"].get("%s_%s" % (case_tableau["date"], case_tableau["inscription"]), []):
            if conso["unite"] in combinaisons_unites:
                if conso["etat"] in ("reservation", "present", "absenti"):
                    heure_debut = conso["heure_debut"]
                    heure_fin = conso["heure_fin"]
                    if heure_debut and heure_fin:
                        liste_temps.append((heure_debut, heure_fin))
                        if not heure_min or utils_dates.HeureStrEnDelta(heure_debut) < heure_min:
                            heure_min = utils_dates.HeureStrEnDelta(heure_debut)
                        if not heure_max or utils_dates.HeureStrEnDelta(heure_fin) > heure_max:
                            heure_max = utils_dates.HeureStrEnDelta(heure_fin)

        if not heure_min: heure_min = datetime.timedelta(hours=0, minutes=0)
        if not heure_max: heure_max = datetime.timedelta(hours=0, minutes=0)

        if liste_temps:
            duree = utils_dates.Additionne_intervalles_temps(liste_temps)
        else:
            duree = None
        return duree, heure_min, heure_max

    def Calcule_tarif(self, tarif=None, combinaisons_unites=[], case_tableau=None, temps_facture=None, quantite=None, evenement=None, modeSilencieux=False, action="saisie"):
        nom_tarif = tarif.nom_tarif.nom
        if hasattr(tarif, "nom_evenement"):
            nom_tarif = tarif.nom_evenement
        description_tarif = tarif.description
        montant_tarif = 0.0
        methode_calcul = tarif.methode
        ligne_calcul = None

        # Label de la prestation personnalisé
        if tarif.label_prestation == "description_tarif":
            nom_tarif = description_tarif
        if tarif.label_prestation and tarif.label_prestation.startswith("autre:"):
            nom_tarif = tarif.label_prestation[6:]

        # Récupération des lignes de tarifs mémorisés
        def Get_lignes_tarif():
            if tarif in self.dict_lignes_tarifs:
                return self.dict_lignes_tarifs[tarif]
            self.dict_lignes_tarifs[tarif] = TarifLigne.objects.filter(tarif=tarif).order_by("num_ligne").all()
            return self.dict_lignes_tarifs[tarif]


        # Recherche du montant du tarif : MONTANT UNIQUE
        if methode_calcul == "montant_unique":
            lignes_calcul = Get_lignes_tarif()
            ligne_calcul = lignes_calcul.first()
            montant_tarif = ligne_calcul.montant_unique
            if ligne_calcul.montant_questionnaire and ligne_calcul.montant_questionnaire != "0":
                montant_tarif = self.Get_montant_questionnaire(IDquestion=ligne_calcul.montant_questionnaire, case_tableau=case_tableau)

        # Recherche du montant à appliquer : QUOTIENT FAMILIAL
        if methode_calcul == "qf":
            lignes_calcul = Get_lignes_tarif()
            qf_famille = self.Recherche_QF(tarif, case_tableau)
            for ligne_calcul in lignes_calcul:
                montant_tarif = ligne_calcul.montant_unique
                if qf_famille != None and qf_famille >= ligne_calcul.qf_min and qf_famille <= ligne_calcul.qf_max:
                    break

        # Recherche du montant du tarif : HORAIRE - MONTANT UNIQUE OU SELON QF
        if methode_calcul in ("horaire_montant_unique", "horaire_qf"):
            montant_tarif = 0.0
            lignes_calcul = Get_lignes_tarif()

            # Recherche des heures debut et fin des unités cochées
            heure_debut = None
            heure_fin = None
            for conso in self.donnees["consommations"].get("%s_%s" % (case_tableau["date"], case_tableau["inscription"]), []):
                if conso["unite"] in combinaisons_unites:
                    heure_debut_temp = utils_dates.HeureStrEnTime(conso["heure_debut"])
                    heure_fin_temp = utils_dates.HeureStrEnTime(conso["heure_fin"])
                    if not heure_debut or heure_debut_temp < heure_debut:
                        heure_debut = heure_debut_temp
                    if not heure_fin or heure_fin_temp > heure_fin:
                        heure_fin = heure_fin_temp

            if "qf" in methode_calcul:
                qf_famille = self.Recherche_QF(tarif, case_tableau)

            for ligne_calcul in lignes_calcul:
                if ligne_calcul.heure_debut_min <= heure_debut <= ligne_calcul.heure_debut_max and ligne_calcul.heure_fin_min <= heure_fin <= ligne_calcul.heure_fin_max:
                    montant_tarif = ligne_calcul.montant_unique
                    if ligne_calcul.montant_questionnaire:
                        montant_tarif = self.Get_montant_questionnaire(IDquestion=ligne_calcul.montant_questionnaire, case_tableau=case_tableau)

                    if ligne_calcul.temps_facture:
                        temps_facture = datetime.timedelta(hours=ligne_calcul.temps_facture.hour, minutes=ligne_calcul.temps_facture.minute)
                    else:
                        temps_facture = utils_dates.SoustractionHeures(ligne_calcul.heure_fin_max, ligne_calcul.heure_debut_min)

                    heure_debut_delta = datetime.timedelta(hours=heure_debut.hour, minutes=heure_debut.minute)
                    heure_fin_delta = datetime.timedelta(hours=heure_fin.hour, minutes=heure_fin.minute)
                    duree_delta = heure_fin_delta - heure_debut_delta

                    # Création du label personnalisé
                    label = ligne_calcul.label
                    if label:
                        if "{TEMPS_REALISE}" in label: label = label.replace("{TEMPS_REALISE}", utils_dates.DeltaEnStr(duree_delta))
                        if "{TEMPS_FACTURE}" in label: label = label.replace("{TEMPS_FACTURE}", utils_dates.DeltaEnStr(temps_facture))
                        if "{HEURE_DEBUT}" in label: label = label.replace("{HEURE_DEBUT}", utils_dates.DeltaEnStr(heure_debut_delta))
                        if "{HEURE_FIN}" in label: label = label.replace("{HEURE_FIN}", utils_dates.DeltaEnStr(heure_fin_delta))
                        nom_tarif = label

                    if "qf" in methode_calcul:
                        if qf_famille and ligne_calcul.qf_min <= qf_famille <= ligne_calcul.qf_max:
                            break
                    else:
                        break

        # Recherche du montant du tarif : DUREE - MONTANT UNIQUE OU SELON QF
        if methode_calcul in ("duree_montant_unique", "duree_qf"):
            montant_tarif = 0.0
            lignes_calcul = Get_lignes_tarif()

            # Recherche des heures debut et fin des unités cochées
            duree, heure_debut_delta, heure_fin_delta = self.Calcule_duree(case_tableau, combinaisons_unites)
            duree_delta = heure_fin_delta - heure_debut_delta

            if "qf" in methode_calcul:
                qf_famille = self.Recherche_QF(tarif, case_tableau)

            for ligne_calcul in lignes_calcul:
                if utils_dates.TimeEnDelta(ligne_calcul.duree_min) <= duree <= utils_dates.TimeEnDelta(ligne_calcul.duree_max):
                    montant_tarif = ligne_calcul.montant_unique
                    if ligne_calcul.montant_questionnaire:
                        montant_tarif = self.Get_montant_questionnaire(IDquestion=ligne_calcul.montant_questionnaire, case_tableau=case_tableau)

                    if ligne_calcul.temps_facture:
                        temps_facture = datetime.timedelta(hours=ligne_calcul.temps_facture.hour, minutes=ligne_calcul.temps_facture.minute)
                    else:
                        temps_facture = datetime.timedelta(hours=ligne_calcul.duree_max.hour, minutes=ligne_calcul.duree_max.minute)

                    # Création du label personnalisé
                    label = ligne_calcul.label
                    if label:
                        if "{TEMPS_REALISE}" in label: label = label.replace("{TEMPS_REALISE}", utils_dates.DeltaEnStr(duree_delta))
                        if "{TEMPS_FACTURE}" in label: label = label.replace("{TEMPS_FACTURE}", utils_dates.DeltaEnStr(temps_facture))
                        if "{HEURE_DEBUT}" in label: label = label.replace("{HEURE_DEBUT}", utils_dates.DeltaEnStr(heure_debut_delta))
                        if "{HEURE_FIN}" in label: label = label.replace("{HEURE_FIN}", utils_dates.DeltaEnStr(heure_fin_delta))
                        nom_tarif = label

                    if "qf" in methode_calcul and qf_famille:
                        if ligne_calcul.qf_min <= qf_famille <= ligne_calcul.qf_max:
                            break


        # Recherche du montant du tarif : EN FONCTION DE LA DATE - MONTANT UNIQUE OU QF
        if methode_calcul in ("montant_unique_date", "qf_date"):
            montant_tarif = 0.0
            lignes_calcul = TarifLigne.objects.filter(tarif=tarif, date=case_tableau["date"]).order_by("num_ligne").all()

            if "qf" in methode_calcul:
                qf_famille = self.Recherche_QF(tarif, case_tableau)

            for ligne_calcul in lignes_calcul:
                montant_tarif = ligne_calcul.montant_unique
                if ligne_calcul.label:
                    nom_tarif = ligne_calcul.label

                if "qf" in methode_calcul and qf_famille:
                    if ligne_calcul.qf_min <= qf_famille <= ligne_calcul.qf_max:
                        break


        # Recherche du montant du tarif : MONTANT DE L'EVENEMENT
        if methode_calcul == "montant_evenement":
            if evenement:
                montant_tarif = evenement.montant
                nom_tarif = evenement.nom


        # Recherche du montant du tarif : EN FONCTION DU NBRE D'INDIVIDUS
        if "nbre_ind" in methode_calcul:
            self.tarif_fratries_exists = True
            montant_tarif = 0.0
            lignes_calcul = Get_lignes_tarif()

            if "montant_unique" in methode_calcul:
                ligne_calcul = lignes_calcul.first()

            if "qf" in methode_calcul:
                for ligne_calcul in lignes_calcul:
                    qf_famille = self.Recherche_QF(tarif, case_tableau)
                    if qf_famille and ligne_calcul.qf_min <= qf_famille <= ligne_calcul.qf_max:
                        break

            if "horaire" in methode_calcul:
                # Recherche des heures debut et fin des unités cochées
                heure_debut = None
                heure_fin = None
                for conso in self.donnees["consommations"].get("%s_%s" % (case_tableau["date"], case_tableau["inscription"]), []):
                    if conso["unite"] in combinaisons_unites:
                        heure_debut_temp = utils_dates.HeureStrEnTime(conso["heure_debut"])
                        heure_fin_temp = utils_dates.HeureStrEnTime(conso["heure_fin"])
                        if not heure_debut or heure_debut_temp < heure_debut:
                            heure_debut = heure_debut_temp
                        if not heure_fin or heure_fin_temp > heure_fin:
                            heure_fin = heure_fin_temp

                for ligne_calcul in lignes_calcul:
                    # montant_questionnaire = self.GetQuestionnaire(ligneCalcul["montant_questionnaire"], IDfamille, IDindividu)
                    # if montant_questionnaire not in (None, 0.0):
                    #     montant_tarif_ligne = montant_questionnaire

                    if ligne_calcul.heure_debut_min <= heure_debut <= ligne_calcul.heure_debut_max and ligne_calcul.heure_fin_min <= heure_fin <= ligne_calcul.heure_fin_max:
                        if ligne_calcul.temps_facture:
                            temps_facture = datetime.timedelta(hours=ligne_calcul.temps_facture.hour, minutes=ligne_calcul.temps_facture.minute)
                        else:
                            temps_facture = utils_dates.SoustractionHeures(ligne_calcul.heure_fin_max, ligne_calcul.heure_debut_min)

                        heure_debut_delta = datetime.timedelta(hours=heure_debut.hour, minutes=heure_debut.minute)
                        heure_fin_delta = datetime.timedelta(hours=heure_fin.hour, minutes=heure_fin.minute)
                        duree_delta = heure_fin_delta - heure_debut_delta

                        # Création du label personnalisé
                        label = ligne_calcul.label
                        if label:
                            if "{TEMPS_REALISE}" in label: label = label.replace("{TEMPS_REALISE}", utils_dates.DeltaEnStr(duree_delta))
                            if "{TEMPS_FACTURE}" in label: label = label.replace("{TEMPS_FACTURE}", utils_dates.DeltaEnStr(temps_facture))
                            if "{HEURE_DEBUT}" in label: label = label.replace("{HEURE_DEBUT}", utils_dates.DeltaEnStr(heure_debut_delta))
                            if "{HEURE_FIN}" in label: label = label.replace("{HEURE_FIN}", utils_dates.DeltaEnStr(heure_fin_delta))
                            nom_tarif = label

                        break

            # Applique le tarif par défaut avant le recalcul lors de l'enregistrement
            if ligne_calcul:
                montant_tarif = ligne_calcul.montant_enfant_1


        # Recherche du montant du tarif : AU PRORATA DE LA DUREE (Montant unique OU QF)
        if methode_calcul in ("duree_coeff_montant_unique", "duree_coeff_qf"):
            montant_tarif = 0.0
            lignes_calcul = Get_lignes_tarif()

            # Recherche des heures debut et fin des unités cochées
            duree, heure_debut_delta, heure_fin_delta = self.Calcule_duree(case_tableau, combinaisons_unites)
            if "qf" in methode_calcul:
                qf_famille = self.Recherche_QF(tarif, case_tableau)
                if qf_famille == None:
                    qf_famille = max([ligne_calcul.qf_max for ligne_calcul in lignes_calcul])

            for ligne_calcul in lignes_calcul:
                duree_min = utils_dates.TimeEnDelta(ligne_calcul.duree_min)
                duree_max = utils_dates.TimeEnDelta(ligne_calcul.duree_max)
                duree_seuil = utils_dates.TimeEnDelta(ligne_calcul.duree_seuil)
                duree_plafond = utils_dates.TimeEnDelta(ligne_calcul.duree_plafond)
                duree_arrondi = utils_dates.TimeEnDelta(ligne_calcul.duree_arrondi)
                unite_horaire = utils_dates.TimeEnDelta(ligne_calcul.unite_horaire)

                duree_temp = copy.copy(duree)

                # Arrondi inférieur de la durée
                if duree_arrondi:
                    duree_arrondie = utils_dates.ArrondirDelta(duree=duree_temp, delta_minutes=int(duree_arrondi.total_seconds() // 60), sens="inf")
                    if duree_arrondie > datetime.timedelta(0):
                        duree_temp = duree_arrondie

                # montant_questionnaire = self.GetQuestionnaire(ligneCalcul["montant_questionnaire"], IDfamille, IDindividu)
                # if montant_questionnaire not in (None, 0.0):
                #     montant_tarif_ligne = montant_questionnaire

                if duree_min == None:
                    duree_min = datetime.timedelta(0)
                if duree_max == None or duree_max == datetime.timedelta(0):
                    duree_max = datetime.timedelta(hours=23, minutes=59)

                # Condition QF
                conditionQF = True
                if "qf" in methode_calcul and qf_famille != None:
                    if qf_famille >= ligne_calcul.qf_min and qf_famille <= ligne_calcul.qf_max:
                        conditionQF = True
                    else:
                        conditionQF = False

                if duree_min <= duree_temp <= duree_max and conditionQF == True:
                    # Vérifie durées seuil et plafond
                    if duree_seuil:
                        if duree_temp < duree_seuil: duree_temp = duree_seuil
                    if duree_plafond and duree_plafond.seconds > 0:
                        if duree_temp > duree_plafond: duree_temp = duree_plafond

                    # Calcul du tarif
                    nbre = int(math.ceil(1.0 * duree_temp.seconds / unite_horaire.seconds))  # Arrondi à l'entier supérieur
                    if tarif.facturation_unite:
                        # Facturation par unité horaire (la quantité d'unités est intégrée dans la prestation)
                        montant_tarif = ligne_calcul.montant_unique
                        montant_tarif = float(decimal.Decimal(str(montant_tarif)))
                        quantite = nbre
                    else:
                        # Facturation normale
                        montant_tarif = nbre * ligne_calcul.montant_unique
                        montant_tarif = float(decimal.Decimal(str(montant_tarif)))

                    # Montants seuil et plafond
                    if ligne_calcul.montant_min:
                        if montant_tarif < ligne_calcul.montant_min:
                            montant_tarif = float(ligne_calcul.montant_min)
                    if ligne_calcul.montant_max:
                        if montant_tarif > ligne_calcul.montant_max:
                            montant_tarif = float(ligne_calcul.montant_max)

                    # Application de l'ajustement (majoration ou déduction)
                    if ligne_calcul.ajustement:
                        montant_tarif = montant_tarif + float(ligne_calcul.ajustement)
                        if montant_tarif < 0.0:
                            montant_tarif = 0.0

                    # Calcul du temps facturé
                    temps_facture = unite_horaire * nbre

                    # Création du label personnalisé
                    label = ligne_calcul.label
                    if label:
                        if "{QUANTITE}" in label: label = label.replace("{QUANTITE}", str(nbre))
                        if "{TEMPS_REALISE}" in label: label = label.replace("{TEMPS_REALISE}", utils_dates.DeltaEnStr(duree_temp))
                        if "{TEMPS_FACTURE}" in label: label = label.replace("{TEMPS_FACTURE}", utils_dates.DeltaEnStr(temps_facture))
                        if "{HEURE_DEBUT}" in label: label = label.replace("{HEURE_DEBUT}", utils_dates.DeltaEnStr(heure_debut_delta))
                        if "{HEURE_FIN}" in label: label = label.replace("{HEURE_FIN}", utils_dates.DeltaEnStr(heure_fin_delta))
                        nom_tarif = label
                    break

        # Recherche du montant du tarif : TAUX D'EFFORT
        if methode_calcul in ("taux_montant_unique", "taux_qf", "taux_date"):
            montant_tarif = 0.0
            lignes_calcul = Get_lignes_tarif()

            # Recherche QF de la famille
            qf_famille = self.Recherche_QF(tarif, case_tableau)

            for ligne_calcul in lignes_calcul:
                # Vérifie si QF ok pour le calcul basé également sur paliers de QF
                conditions = True
                if "qf" in methode_calcul:
                    if qf_famille != None:
                        if qf_famille >= ligne_calcul.qf_min and qf_famille <= ligne_calcul.qf_max:
                            conditions = True
                        else:
                            conditions = False
                    else:
                        # Sélectionne la dernière ligne pour les familles sans QF
                        if ligne_calcul.num_ligne < len(lignes_calcul)-1:
                            conditions = False

                if methode_calcul == "taux_date":
                    if ligne_calcul.date != case_tableau["date"]:
                        conditions = False

                if conditions == True:

                    # Calcul du tarif
                    if qf_famille != None:
                        montant_tarif = qf_famille * ligne_calcul.taux
                        montant_tarif = float(decimal.Decimal(str(montant_tarif)))
                    else:
                        if ligne_calcul.montant_max:
                            montant_tarif = float(ligne_calcul.montant_max)

                    # Montants seuil et plafond
                    if ligne_calcul.montant_min:
                        if montant_tarif < ligne_calcul.montant_min:
                            montant_tarif = float(ligne_calcul.montant_min)
                    if ligne_calcul.montant_max:
                        if montant_tarif > ligne_calcul.montant_max:
                            montant_tarif = float(ligne_calcul.montant_max)

                    # Application de l'ajustement (majoration ou déduction)
                    if ligne_calcul.ajustement:
                        montant_tarif = montant_tarif + float(ligne_calcul.ajustement)
                        if montant_tarif < 0.0:
                            montant_tarif = 0.0

                    # Création du label personnalisé
                    label = ligne_calcul.label
                    if label:
                        if "{TAUX}" in label: label = label.replace("{TAUX}", str(ligne_calcul.taux))
                        nom_tarif = label
                    break

        # Recherche du montant du tarif : PAR TAUX D'EFFORT ET PAR DUREE (+ QF)
        if methode_calcul in ("duree_taux_montant_unique", "duree_taux_qf"):
            montant_tarif = 0.0
            lignes_calcul = Get_lignes_tarif()

            # Recherche QF de la famille
            qf_famille = self.Recherche_QF(tarif, case_tableau)

            # Recherche de la durée
            duree, heure_debut_delta, heure_fin_delta = self.Calcule_duree(case_tableau, combinaisons_unites)

            for ligne_calcul in lignes_calcul:
                duree_min = utils_dates.TimeEnDelta(ligne_calcul.duree_min)
                duree_max = utils_dates.TimeEnDelta(ligne_calcul.duree_max)

                if not duree_min:
                    duree_min = datetime.timedelta(0)
                if not duree_max or duree_max == datetime.timedelta(0):
                    duree_max = datetime.timedelta(hours=23, minutes=59)

                # Vérifie si QF ok pour le calcul basé également sur paliers de QF
                conditionQF = True
                if "qf" in methode_calcul and qf_famille != None:
                    if qf_famille >= ligne_calcul.qf_min and qf_famille <= ligne_calcul.qf_max:
                        conditionQF = True
                    else:
                        conditionQF = False

                if duree_min <= duree <= duree_max and conditionQF == True:
                    # Calcul du tarif
                    if qf_famille != None:
                        montant_tarif = qf_famille * ligne_calcul.taux
                        montant_tarif = float(decimal.Decimal(str(montant_tarif)))
                    else:
                        if ligne_calcul.montant_max:
                            montant_tarif = float(ligne_calcul.montant_max)

                    # Montants seuil et plafond
                    if ligne_calcul.montant_min:
                        if montant_tarif < ligne_calcul.montant_min:
                            montant_tarif = float(ligne_calcul.montant_min)
                    if ligne_calcul.montant_max:
                        if montant_tarif > ligne_calcul.montant_max:
                            montant_tarif = float(ligne_calcul.montant_max)

                    # Application de l'ajustement (majoration ou déduction)
                    if ligne_calcul.ajustement:
                        montant_tarif = montant_tarif + float(ligne_calcul.ajustement)
                        if montant_tarif < 0.0:
                            montant_tarif = 0.0

                    # Calcul du temps facturé
                    if ligne_calcul.temps_facture:
                        temps_facture = datetime.timedelta(hours=ligne_calcul.temps_facture.hour, minutes=ligne_calcul.temps_facture.minute)
                    else:
                        temps_facture = duree_max

                    # Création du label personnalisé
                    label = ligne_calcul.label
                    if label != None and label != "":
                        if "{TAUX}" in label: label = label.replace("{TAUX}", str(ligne_calcul.taux))
                        if "{HEURE_DEBUT}" in label: label = label.replace("{HEURE_DEBUT}", utils_dates.DeltaEnStr(heure_debut_delta))
                        if "{HEURE_FIN}" in label: label = label.replace("{HEURE_FIN}", utils_dates.DeltaEnStr(heure_fin_delta))
                        nom_tarif = label
                    break

        # Si unité de type QUANTITE
        if quantite and quantite > 1:
            montant_tarif = montant_tarif * quantite

        # Application d'une pénalité financière
        if tarif.penalite:
            appliquer_penalite = False
            for conso in self.donnees["consommations"].get("%s_%s" % (case_tableau["date"], case_tableau["inscription"]), []):
                if conso["unite"] in combinaisons_unites and conso["etat"] == "absenti":
                    appliquer_penalite = True

            if appliquer_penalite:
                if tarif.penalite_pourcentage:
                    if isinstance(montant_tarif, float):
                        montant_tarif = decimal.Decimal(montant_tarif)
                    montant_tarif = montant_tarif * tarif.penalite_pourcentage / 100
                if tarif.penalite_label:
                    nom_tarif = tarif.penalite_label.replace("{LABEL_PRESTATION}", nom_tarif)

        # Arrondit le montant à pour enlever les décimales en trop. Ex : 3.05678 -> 3.05
        montant_tarif = utils_decimal.FloatToDecimal(montant_tarif, plusProche=True)

        return montant_tarif, nom_tarif, temps_facture, quantite, ligne_calcul

    def Get_montant_questionnaire(self, IDquestion=None, case_tableau=None):
        conditions = Q(question_id=IDquestion) & ((Q(question__categorie="famille") & Q(famille_id=case_tableau["famille"]) | Q(question__categorie="individu") & Q(individu_id=case_tableau["individu"])))
        reponse = QuestionnaireReponse.objects.filter(conditions).first()
        if reponse:
            return decimal.Decimal(reponse.reponse or 0.0)
        return decimal.Decimal(0.0)


def Valider_traitement_lot(request):
    parametres = {
        "action_type": request.POST.get("action_type"),
        "date_debut": utils_dates.ConvertDateFRtoDate(request.POST.get("date_debut")),
        "date_fin": utils_dates.ConvertDateFRtoDate(request.POST.get("date_fin")),
        "jours_scolaires": request.POST.getlist("jours_scolaires"),
        "jours_vacances": request.POST.getlist("jours_vacances"),
        "frequence_type": request.POST.get("frequence_type"),
        "inclure_feries": request.POST.get("inclure_feries") == "on",
    }
    from consommations.utils import utils_traitement_lot
    resultat = utils_traitement_lot.Calculer(request=request, parametres=parametres)
    if "erreur" in resultat:
        return JsonResponse(resultat, status=401)
    return JsonResponse(resultat)


def Impression_pdf(request):
    # Récupération des données du formulaire
    liste_conso = json.loads(request.POST.get("consommations"))
    dict_prestations = json.loads(request.POST.get("prestations"))
    idfamille = int(request.POST.get("idfamille"))

    # Importation des données de la DB
    liste_dates = []
    dict_prepa = {"individus": [], "activites": [], "unites": []}
    for conso in liste_conso:
        if conso["individu"] not in dict_prepa["individus"]: dict_prepa["individus"].append(conso["individu"])
        if conso["activite"] not in dict_prepa["activites"]: dict_prepa["activites"].append(conso["activite"])
        if conso["unite"] not in dict_prepa["unites"]: dict_prepa["unites"].append(conso["unite"])
        liste_dates.append(utils_dates.ConvertDateENGtoDate(conso["date"]))
    dict_individus = {individu.pk: individu for individu in Individu.objects.filter(pk__in=dict_prepa["individus"])}
    dict_activites = {activite.pk: activite for activite in Activite.objects.filter(pk__in=dict_prepa["activites"])}
    dict_unites = {unite.pk: unite for unite in Unite.objects.filter(pk__in=dict_prepa["unites"])}
    if liste_dates:
        date_min = min(liste_dates)

    # Préparation des données pour le pdf
    dict_donnees = {"reservations": {}, "evenements": []}
    for conso in liste_conso:
        individu = dict_individus[conso["individu"]]
        activite = dict_activites[conso["activite"]]
        unite = dict_unites[conso["unite"]]

        if str(conso["prestation"]) in dict_prestations:
            prestation = dict_prestations[str(conso["prestation"])]
        else:
            prestation = None

        dict_donnees["reservations"].setdefault(conso["individu"], {"nom": individu.nom, "prenom": individu.prenom, "date_naiss": individu.date_naiss, "sexe": individu.Get_sexe(), "activites": {}})
        dict_donnees["reservations"][conso["individu"]]["activites"].setdefault(conso["activite"], {"nom": activite.nom, "agrement": activite.Get_agrement(date=date_min), "dates": {}})
        dict_donnees["reservations"][conso["individu"]]["activites"][conso["activite"]]["dates"].setdefault(conso["date"], {})
        dict_donnees["reservations"][conso["individu"]]["activites"][conso["activite"]]["dates"][conso["date"]].setdefault(conso["unite"],
            {"conso": conso, "nomUnite": unite.nom, "etat": conso["etat"], "type": unite.type, "heure_debut": conso["heure_debut"], "heure_fin": conso["heure_fin"], "IDprestation": str(conso["prestation"]), "prestation": prestation}
        )
        if conso["evenement"] and conso["evenement"] not in dict_donnees["evenements"]:
            dict_donnees["evenements"].append(conso["evenement"])

    # Création du PDF
    from consommations.utils import utils_impression_reservations
    impression = utils_impression_reservations.Impression(titre="Réservations", dict_donnees=dict_donnees)
    nom_fichier = impression.Get_nom_fichier()
    champs = {
        "{SOLDE}": impression.dict_donnees["{SOLDE}"],
    }

    # Récupération des valeurs de fusion
    return JsonResponse({"nom_fichier": nom_fichier, "categorie": "reservations", "label_fichier": "Réservations", "champs": champs, "idfamille": idfamille})


