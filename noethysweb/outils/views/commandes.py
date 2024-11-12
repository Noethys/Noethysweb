# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic import TemplateView
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Commande, CommandeVersion, CommandeModeleColonne, Ouverture, Consommation, Information
from outils.forms.commandes import Formulaire


def Generer_pdf(request):
    donnees = json.loads(request.POST["donnees"])
    idcommande = int(request.POST["idcommande"])

    # Récupération du mail du restaurateur
    mail_restaurateur = None
    if request.POST["email"] == "true":
        commande = Commande.objects.select_related("modele", "modele__restaurateur").get(pk=idcommande)
        if commande.modele.restaurateur and commande.modele.restaurateur.mail:
            mail_restaurateur = commande.modele.restaurateur.mail
        if not mail_restaurateur:
            return JsonResponse({"erreur": "Aucun restaurateur n'a été associé à cette commande ou aucune adresse mail n'a été saisie pour le restaurateur associé"}, status=401)

    dict_donnees = {
        "cases": donnees,
        "idcommande": idcommande,
        "orientation": "paysage",
    }

    # Création du PDF
    from outils.utils import utils_impression_commande
    impression = utils_impression_commande.Impression(titre="Commande des repas", dict_donnees=dict_donnees)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier, "label_fichier": "Commande de repas", "categorie": "commande_repas", "adresse": mail_restaurateur, "champs": impression.Get_champs_fusion_pour_email("commande_repas", "champs")})


class Page(crud.Page):
    model = Commande
    url_liste = "commandes_liste"
    url_ajouter = "commandes_ajouter"
    url_modifier = "commandes_modifier"
    url_supprimer = "commandes_supprimer"
    url_consulter = "commandes_consulter"
    description_liste = "Voici ci-dessous la liste des commandes de repas."
    description_saisie = "Saisissez toutes les informations concernant la commande à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une commande"
    objet_pluriel = "des commandes"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Commande

    def get_queryset(self):
        return Commande.objects.select_related("modele").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcommande", "date_debut", "date_fin", "nom"]
        nom_modele = columns.TextColumn("Modèle", sources="modele__nom")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcommande", "date_debut", "date_fin", "nom", "nom_modele", "actions"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["date_debut"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_consulter, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_context_data(self, **kwargs):
        context = super(Ajouter, self).get_context_data(**kwargs)
        return context

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.object.idcommande if self.object else 0})


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['pk']})


class Supprimer(Page, crud.Supprimer):
    pass


class Consulter(Page, TemplateView):
    template_name = "outils/commandes.html"
    mode = "CONSULTATION"
    model = Commande
    boutons_liste = []

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context["box_titre"] = "Consulter une commande"
        context["box_introduction"] = "Vous pouvez ici modifier une commande."
        context["onglet_actif"] = "commandes_liste"

        commande = Commande.objects.select_related("modele", "modele__restaurateur").get(pk=self.kwargs["pk"])
        context["commande"] = commande
        colonnes = CommandeModeleColonne.objects.filter(modele=commande.modele).order_by("ordre")
        context["colonnes"] = colonnes

        # Recherche des unités utilisées
        conditions = Q()
        parametres_colonnes_suggestion = {}
        parametres_colonnes_total = {}
        for colonne in colonnes:
            parametres = json.loads(colonne.parametres) if colonne.parametres else {}
            colonne.dict_parametres = parametres

            # Pour les suggestions
            for unite in parametres.get("unites", []):
                idunite, idgroupe = unite.split("_")
                conditions |= Q(unite_id=int(idunite), groupe_id=int(idgroupe))
                parametres_colonnes_suggestion.setdefault(colonne, [])
                parametres_colonnes_suggestion[colonne].append((idunite, idgroupe))

            # Pour les totaux
            for idcol in parametres.get("colonnes", []):
                parametres_colonnes_total.setdefault(colonne.pk, [])
                parametres_colonnes_total[colonne.pk].append(int(idcol))

        # Colonnes total
        context["colonnes_total_json"] = json.dumps(parametres_colonnes_total)

        # Recherche des dates d'ouverture
        liste_dates = list({ouverture.date: True for ouverture in Ouverture.objects.filter(conditions, date__gte=commande.date_debut, date__lte=commande.date_fin).order_by("date")}.keys())
        context["dates"] = liste_dates

        # Recherche des consommations
        consommations = Consommation.objects.select_related("individu").prefetch_related("individu__regimes_alimentaires").filter(conditions, date__gte=commande.date_debut, date__lte=commande.date_fin, etat__in=("reservation", "present"))

        # Recherche les informations personnelles
        dict_infos_temp = {}
        for info in Information.objects.filter(individu_id__in=list({conso.individu_id: True for conso in consommations}.keys())): #, diffusion_listing_repas=True):
            dict_infos_temp.setdefault(info.individu_id, [])
            dict_infos_temp[info.individu_id].append(info)

        # Regroupement des données
        dict_conso = {}
        dict_regimes = {}
        dict_infos_perso = {}

        for conso in consommations:
            # Recherche les suggestions
            key = "%s_%s_%s" % (conso.date, conso.unite_id, conso.groupe_id)
            dict_conso.setdefault(key, 0)
            dict_conso[key] += conso.quantite or 1

            # Recherche les régimes
            if conso.individu.regimes_alimentaires.exists():
                key = "%s_%s" % (conso.date, conso.groupe_id)
                dict_regimes.setdefault(key, [])
                texte_regimes = "%s : %s." % (conso.individu.Get_nom(), ", ".join([regime.nom for regime in conso.individu.regimes_alimentaires.all()]))
                dict_regimes[key].append(texte_regimes)

            # Recherche les infos perso
            if conso.individu_id in dict_infos_temp:
                key = "%s_%s" % (conso.date, conso.groupe_id)
                dict_infos_perso.setdefault(key, {})
                if conso.individu not in dict_infos_perso[key]:
                    dict_infos_perso[key][conso.individu] = dict_infos_temp[conso.individu_id]

        # Recherche les valeurs de la dernière version ou de la version demandée
        if self.kwargs.get("idversion", None):
            version = CommandeVersion.objects.get(pk=self.kwargs["idversion"])
        else:
            version = CommandeVersion.objects.filter(commande=commande).last()
        context["version"] = version
        valeurs_version = json.loads(version.valeurs) if version else {}

        # Recherche la précédente version et la version suivante
        context["version_precedente"] = CommandeVersion.objects.values("idversion", "horodatage").filter(commande=commande, idversion__lt=version.pk if version else 0).order_by("-pk").first()
        context["version_suivante"] = CommandeVersion.objects.values("idversion", "horodatage").filter(commande=commande, idversion__gt=version.pk if version else 0).order_by("pk").first()

        # Création des cases
        valeurs = {}
        is_colonne_suggestion_exists = False
        for colonne in colonnes:
            for date in liste_dates:
                # Récupération de la valeur de la case
                valeur_version = valeurs_version.get("%s_%d" % (date, colonne.pk), {})
                valeur = valeur_version.get("valeur", 0)
                texte = valeur_version.get("texte", "")

                # Récupération de la suggestion de la case
                suggestion = 0
                if "SUGGESTION" in colonne.categorie:
                    is_colonne_suggestion_exists = True
                    for idunite, idgroupe in parametres_colonnes_suggestion.get(colonne, []):
                        suggestion += dict_conso.get("%s_%s_%s" % (date, idunite, idgroupe), 0)

                # Récupération des conso réelles
                if "CONSO" in colonne.categorie:
                    for idunite, idgroupe in parametres_colonnes_suggestion.get(colonne, []):
                        valeur += dict_conso.get("%s_%s_%s" % (date, idunite, idgroupe), 0)

                # Récupération des infos automatiques
                if "INFOS" in colonne.categorie:
                    texte = []

                    # Régimes
                    if colonne.dict_parametres["type_infos"] == "REGIMES":
                        for idgroupe in colonne.dict_parametres["groupes"]:
                            texte.extend(dict_regimes.get("%s_%s" % (date, idgroupe), []))

                    # Infos
                    if colonne.dict_parametres["type_infos"] == "INFOS":
                        for idgroupe in colonne.dict_parametres["groupes"]:
                            for individu, liste_infos in dict_infos_perso.get("%s_%s" % (date, idgroupe), {}).items():
                                liste_temp = []
                                # Filtrage des infos selon les paramètres de la colonne
                                for info in liste_infos:
                                    if (not colonne.dict_parametres.get("categories_informations", []) or str(info.categorie.pk) in colonne.dict_parametres.get("categories_informations", [])) and \
                                            (not colonne.dict_parametres.get("coche_afficher_commande", None) or info.diffusion_listing_repas):
                                        liste_temp.append(info)
                                # Ajout de l'individu et de ses infos
                                if liste_temp:
                                    texte_infos = "%s : %s." % (individu.Get_nom(), ", ".join([info.intitule for info in liste_temp]))
                                    texte.append(texte_infos)

                    texte = "<br/>".join(texte)

                valeurs["%s_%d" % (date, colonne.pk)] = {
                    "valeur": valeur,
                    "texte": texte,
                    "suggestion": suggestion,
                }

        context["valeurs_json"] = json.dumps(valeurs)
        context["is_colonne_suggestion_exists"] = is_colonne_suggestion_exists

        return context

    def post(self, request, *args, **kwargs):
        donnees = json.loads(self.request.POST.get("donnees"))

        # Préparation des données
        donnees_save = {}
        for key, variables in donnees.items():
            if variables["categorie"] in ("numerique_suggestion", "numerique_libre"):
                donnees_save[key] = {"valeur": variables["valeur"]}
            if variables["categorie"] in ("texte_libre"):
                donnees_save[key] = {"texte": variables["texte"]}
        donnees_save_json = json.dumps(donnees_save)

        # Création d'une nouvelle version de la commande si besoin
        derniere_version = CommandeVersion.objects.filter(commande_id=self.kwargs["pk"]).last()
        if not derniere_version or derniere_version.valeurs != donnees_save_json:
            CommandeVersion.objects.create(commande_id=self.kwargs["pk"], valeurs=donnees_save_json)

        return HttpResponseRedirect(reverse_lazy("commandes_liste"))
