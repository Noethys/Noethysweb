# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import DepotCotisations, Cotisation
from cotisations.forms.depots_cotisations import Formulaire
from core.utils import utils_texte, utils_preferences
from django.shortcuts import render
from django.db.models import Q, Count
import json, datetime
from decimal import Decimal
from django.http import JsonResponse, HttpResponseRedirect




def Get_stats(request):
    liste_cotisations = request.POST.get("liste_cotisations")
    if len(liste_cotisations) == 0:
        texte = "Aucune adhésion incluse"
    else:
        liste_cotisations = [int(id) for id in liste_cotisations.split(";")]
        liste_details = []
        cotisations = Cotisation.objects.select_related('type_cotisation', 'unite_cotisation').values("type_cotisation__nom", "unite_cotisation__nom").filter(pk__in=liste_cotisations).annotate(nbre=Count("pk"))
        for stat in cotisations:
            liste_details.append("%d %s %s" % (stat["nbre"], stat["type_cotisation__nom"], stat["unite_cotisation__nom"]))
        texte = "%d adhésions : %s." % (len(liste_cotisations), utils_texte.Convert_liste_to_texte_virgules(liste_details))
    return JsonResponse({"texte": texte})



def Modifier_cotisations(request):
    """ Renvoie le contenu de la table """
    liste_cotisations = request.POST.get("liste_cotisations")
    only_inclus = True if request.POST.get("only_inclus") == "true" else False

    if len(liste_cotisations) == 0:
        liste_cotisations = []
    else:
        liste_cotisations = [int(id) for id in liste_cotisations.split(";")]
    if only_inclus:
        condition = Q(pk__in=liste_cotisations)
    else:
        condition = (Q(pk__in=liste_cotisations) | Q(depot_cotisation__isnull=True))

    # Sélectionne uniquement les structures accessibles par l'utilisateur
    condition &= (Q(type_cotisation__structure__in=request.user.structures.all()) | Q(type_cotisation__structure__isnull=True))

    lignes = []
    for cotisation in Cotisation.objects.select_related("type_cotisation", "type_cotisation__structure", "unite_cotisation", "famille", "individu").filter(condition):
        lignes.append({
            "pk": cotisation.pk,
            "date_debut": str(cotisation.date_debut) if cotisation.date_debut else None,
            "date_fin": str(cotisation.date_fin) if cotisation.date_fin else None,
            "type_cotisation": cotisation.type_cotisation.nom,
            "unite_cotisation": cotisation.unite_cotisation.nom,
            "famille": cotisation.famille.nom,
            "individu": cotisation.individu.Get_nom() if cotisation.individu else None,
            "date_creation_carte": str(cotisation.date_creation_carte) if cotisation.date_creation_carte else None,
            "observations": cotisation.observations if cotisation.observations else None,
        })

    context = {
        "resultats": json.dumps(lignes),
        "selections": json.dumps(liste_cotisations),
        "only_inclus": only_inclus,
    }
    return render(request, "cotisations/selection_cotisations_depot.html", context)


class Page(crud.Page):
    model = DepotCotisations
    url_liste = "depots_cotisations_liste"
    url_ajouter = "depots_cotisations_ajouter"
    url_modifier = "depots_cotisations_modifier"
    url_supprimer = "depots_cotisations_supprimer"
    description_liste = "Voici ci-dessous la liste des dépôts d'adhésions."
    description_saisie = "Saisissez toutes les informations concernant le dépôt à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un dépôt d'adhésions"
    objet_pluriel = "des dépôts d'adhésions"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]

    def form_valid(self, form):
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Recherche les cotisations existantes pour ce dépôt
        if self.object:
            cotisations_existantes = Cotisation.objects.filter(depot_cotisation=self.object)
        else:
            cotisations_existantes = []

        # Recherche les cotisations associées
        if len(form.cleaned_data["cotisations"]) == 0:
            liste_idcotisation = []
        else:
            liste_idcotisation = [int(id) for id in form.cleaned_data["cotisations"].split(";")]
        liste_modifications = []
        liste_cotisations = Cotisation.objects.filter(pk__in=liste_idcotisation)

        # Enregistrement du dépôt
        if not self.object:
            self.object = form.save()

        self.object.quantite = len(liste_cotisations)
        self.object.save()

        # Modification des règlements associés
        for cotisation in liste_cotisations:
            cotisation.depot_cotisation = self.object
            liste_modifications.append(cotisation)

        # Détache du dépôt les règlements qui ne sont plus associés
        for cotisation in cotisations_existantes:
            if cotisation not in liste_cotisations:
                cotisation.depot_cotisation = None
                liste_modifications.append(cotisation)

        # Enregistrement des modifications dans la db
        Cotisation.objects.bulk_update(liste_modifications, ["depot_cotisation"], batch_size=50)

        return HttpResponseRedirect(self.get_success_url())


class Liste(Page, crud.Liste):
    model = DepotCotisations

    def get_queryset(self):
        return DepotCotisations.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['iddepot', 'date', 'nom', 'quantite', 'verrouillage', 'observations']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        verrouillage = columns.TextColumn("Verrouillage", sources=["montant"], processor='Get_verrouillage')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['iddepot', 'verrouillage', 'date', 'nom', 'quantite', 'observations']
            #hidden_columns = = ["iddepot"]
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date']

        def Get_verrouillage(self, instance, **kwargs):
            if instance.verrouillage:
                return "<span class='text-green'><i class='fa fa-lock margin-r-5'></i> Verrouillé</span>"
            else:
                return "<span class='text-red'><i class='fa fa-unlock margin-r-5'></i> Non verrouillé</span>"


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

