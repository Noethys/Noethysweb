# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, time, os
from copy import deepcopy
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.core import serializers
from django.conf import settings
from core.views.base import CustomView
from core.models import Activite, ResponsableActivite, Agrement, Groupe, Evenement, CategorieTarif, \
                        NomTarif, Unite, UniteRemplissage, Tarif, TarifLigne, CombiTarif, Ouverture, Remplissage, PortailPeriode
from core.utils import utils_fichiers
from parametrage.forms.activites_import_export import Formulaire


class View(CustomView, TemplateView):
    menu_code = "activites_import_export"
    template_name = "parametrage/activites_import_export.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des activités"
        context['box_titre'] = "Importer/Exporter des activités"
        context['box_introduction'] = "Exportez dans un fichier NWA le paramétrage d'une ou plusieurs activités (groupes, unités, tarifs...), par exemple pour le transférer vers une autre base de données, ou importez un paramétrage d'activité à partir d'un fichier NWA. Seul le paramétrage est concerné : aucune donnée sur les familles, inscriptions ou consommations n'est exportée. Renseignez les paramètres et cliquez sur le bouton Exécuter."
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context


def Executer(request):
    # Récupération des options
    time.sleep(1)
    form = Formulaire(request.POST, request.FILES, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    parametres = form.cleaned_data

    if parametres["action"] == "EXPORTER":
        resultats = Exporter(parametres)
        return JsonResponse(resultats)
    else:
        resultats = Importer(parametres)
        return JsonResponse(resultats)


def Exporter(parametres):
    activites = Activite.objects.prefetch_related("groupes_activites", "pieces", "cotisations", "types_consentements").filter(pk__in=parametres["selection_activites_exportables"])

    liste_objets = []
    for activite in activites:
        liste_objets.append(activite)
        liste_objets.extend(activite.groupes_activites.all())
        liste_objets.extend(activite.pieces.all())
        liste_objets.extend(activite.cotisations.all())
        liste_objets.extend(activite.types_consentements.all())

        # Duplications simples
        tables = [ResponsableActivite, Agrement, Groupe, Unite, Evenement, CategorieTarif, NomTarif,
                  UniteRemplissage, Tarif, TarifLigne, Ouverture, Remplissage, PortailPeriode]
        for classe in tables:
            for objet in classe.objects.filter(activite=activite):
                liste_objets.append(objet)

        # Combi de tarifs
        for objet in CombiTarif.objects.filter(tarif__activite=activite):
            liste_objets.append(objet)

    # Création du fichier
    nom_fichier = "export_activites.nwa"
    rep_temp = utils_fichiers.GetTempRep()
    with open(os.path.join(rep_temp, nom_fichier), "w", encoding="utf-8") as fichier:
        fichier.write(serializers.serialize("json", liste_objets, indent=4))

    # Renvoie l'URL du fichier
    url_fichier = os.path.join(settings.MEDIA_URL, "temp", nom_fichier)
    return {"resultat": "ok", "action": "EXPORTER", "url_fichier": url_fichier}


def Importer(parametres):
    # Récupération de la liste des activités importables
    selection_activites_importables = json.loads(parametres["selection_activites_importables"] or "[]")
    if not selection_activites_importables:
        json_data = json.loads(parametres["fichier"].read())
        liste_activites = [{"value": objet["pk"], "text": objet["fields"]["nom"]} for objet in json_data if objet["model"] == "core.activite"]
        return {"resultat": "ok", "action": "SELECTION_ACTIVITES", "liste_activites": json.dumps(liste_activites)}

    # Désérialisation
    dict_objets = {}
    for objet in serializers.deserialize("json", parametres["fichier"].read(), ignorenonexistent=True):
        nom_classe = objet.object._meta.object_name
        dict_objets.setdefault(nom_classe, [])
        dict_objets[nom_classe].append(objet)

    dict_nouveaux_objets = {}

    def Get_objet(nom_classe="", pk=None, remplacements={}):
        key = "%s_%d" % (nom_classe, pk)

        # Renvoi le nouvel objet s'il a été créé
        if key in dict_nouveaux_objets:
            return dict_nouveaux_objets[key]

        # Recherche l'objet dans le json
        for objet in dict_objets.get(nom_classe, []):
            if objet.object.pk == pk:

                # Création de l'objet
                objet.object.pk = None
                for champ, valeur in remplacements.items():
                    setattr(objet.object, champ, valeur)
                objet.object.save()

                # Mémorisation des correspondances
                dict_nouveaux_objets[key] = objet.object
                return objet.object
        return None

    for objet_activite in dict_objets.get("Activite", []):
        if str(objet_activite.object.pk) in selection_activites_importables:
            # Activité
            activite = deepcopy(objet_activite.object)
            activite.pk = None
            activite.nom = activite.nom
            activite.structure = parametres["selection_structure"]
            activite.regie = None
            activite.reattribution_auto = False
            activite.reattribution_adresse_exp = None
            activite.reattribution_modele_email = None
            activite.save()

            # Données annexes
            def Ajouter_manytomany(nom_champ=None, nom_classe=None):
                for pk in objet_activite.m2m_data[nom_champ]:
                    instance = Get_objet(nom_classe=nom_classe, pk=pk, remplacements={"structure": parametres["selection_structure"]})
                    getattr(activite, nom_champ).add(instance)

            # Groupes d'activités
            if "groupes_activites" in parametres["donnees"]: Ajouter_manytomany(nom_champ="groupes_activites", nom_classe="TypeGroupeActivite")
            if "pieces" in parametres["donnees"]: Ajouter_manytomany(nom_champ="pieces", nom_classe="TypePiece")
            if "cotisations" in parametres["donnees"]: Ajouter_manytomany(nom_champ="cotisations", nom_classe="TypeCotisation")
            if "types_consentements" in parametres["donnees"]: Ajouter_manytomany(nom_champ="types_consentements", nom_classe="TypeConsentement")

            # Duplications simples
            correspondances = {}

            def Get_correspondances(correspondances={}, objet=None):
                return {
                    "activite_id": activite.pk,
                    "unite_id": correspondances["Unite"][objet.unite_id] if getattr(objet, "unite_id", None) and "Unite" in correspondances else None,
                    "groupe_id": correspondances["Groupe"][objet.groupe_id] if getattr(objet, "groupe_id", None) and "Groupe" in correspondances else None,
                    "unite_remplissage_id": correspondances["UniteRemplissage"][objet.unite_remplissage_id] if getattr(objet, "unite_remplissage_id", None) and "UniteRemplissage" in correspondances else None,
                    "tarif_id": correspondances["Tarif"][objet.tarif_id] if getattr(objet, "tarif_id", None) and "Tarif" in correspondances else None,
                    "nom_tarif_id": correspondances["NomTarif"][objet.nom_tarif_id] if getattr(objet, "nom_tarif_id", None) and "NomTarif" in correspondances else None,
                    "evenement_id": correspondances["Evenement"][objet.evenement_id] if getattr(objet, "evenement_id", None) and "Evenement" in correspondances else None,
                    "structure_id": parametres["selection_structure"].pk,
                    "restaurateur_id": None,
                }

            def Copie_classe(classe=None, bulk=False):
                liste_ajouts = []
                for instance in dict_objets.get(classe._meta.object_name, []):
                    objet_instance = instance.object
                    if objet_instance.activite_id == objet_activite.object.pk:
                        nouvel_objet = deepcopy(objet_instance)
                        nouvel_objet.pk = None

                        # Traitement des ForeignKey
                        for key, valeur in Get_correspondances(correspondances, objet_instance).items():
                            setattr(nouvel_objet, key, valeur)

                        if bulk:
                            # Enregistrement groupé
                            liste_ajouts.append(nouvel_objet)
                        else:
                            # Enregistrement à l'unité et mémorisation des correspondances
                            nouvel_objet.save()

                            # Mémorisation des correspondances
                            correspondances.setdefault(objet_instance._meta.object_name, {})
                            correspondances[objet_instance._meta.object_name][objet_instance.pk] = nouvel_objet.pk

                            # Mémorisation pour la duplication ultérieure des champs manytomany
                            liste_manytomany.append((classe, nouvel_objet, instance.m2m_data))
                if liste_ajouts:
                    classe.objects.bulk_create(liste_ajouts)

            # Duplications avec enregistrement à l'unité
            liste_manytomany = []
            tables = [ResponsableActivite, Agrement, Groupe, Unite, Evenement, CategorieTarif, NomTarif, UniteRemplissage, Tarif, TarifLigne, PortailPeriode]
            for classe in tables:
                Copie_classe(classe=classe)

            # Duplication des champs manytomany à partir des données du fichier (et non de la base de destination)
            noms_classes_dupliquees = [classe._meta.object_name for classe in tables]
            for classe, nouvel_objet, m2m_data in liste_manytomany:
                for field in classe._meta.many_to_many:
                    anciens_pk = m2m_data.get(field.name, [])
                    nom_classe_liee = field.related_model._meta.object_name
                    if nom_classe_liee in noms_classes_dupliquees:
                        # Objet propre à l'activité : on récupère le nouvel ID
                        nouveaux_pk = [correspondances.get(nom_classe_liee, {}).get(pk) for pk in anciens_pk]
                        getattr(nouvel_objet, field.name).set([pk for pk in nouveaux_pk if pk])
                    else:
                        # Objet commun (cotisations, caisses...) : conservé uniquement s'il existe dans la base
                        getattr(nouvel_objet, field.name).set(field.related_model.objects.filter(pk__in=anciens_pk))

            # Duplications avec enregistrement groupé
            for classe in (Ouverture, Remplissage):
                Copie_classe(classe=classe, bulk=True)

            # CombiTarif (lus dans le fichier)
            for instance in dict_objets.get("CombiTarif", []):
                objet_instance = instance.object
                if objet_instance.tarif_id in correspondances.get("Tarif", {}):
                    nouvel_objet = deepcopy(objet_instance)
                    nouvel_objet.pk = None
                    nouvel_objet.tarif_id = correspondances["Tarif"][objet_instance.tarif_id]
                    nouvel_objet.groupe_id = correspondances.get("Groupe", {}).get(objet_instance.groupe_id) if objet_instance.groupe_id else None
                    nouvel_objet.save()
                    nouvel_objet.unites.set([correspondances["Unite"][pk] for pk in instance.m2m_data.get("unites", []) if pk in correspondances.get("Unite", {})])

    return {"resultat": "ok", "action": "IMPORTER"}
