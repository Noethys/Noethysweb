# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Depot, Reglement
from reglements.forms.depots_reglements import Formulaire
from core.utils import utils_texte, utils_preferences
from django.shortcuts import render
from django.db.models import Q, Sum, Count
import json, datetime
from decimal import Decimal
from django.http import JsonResponse, HttpResponseRedirect




def Get_stats(request):
    liste_reglements = request.POST.get("liste_reglements")
    if len(liste_reglements) == 0:
        texte = "Aucun règlement inclus"
    else:
        liste_reglements = [int(id) for id in liste_reglements.split(";")]
        total = Decimal(0)
        liste_details = []
        for stat in Reglement.objects.select_related('mode').values("mode__label").filter(pk__in=liste_reglements).annotate(total=Sum("montant"), nbre=Count("pk")):
            liste_details.append("%d %s (%s)" % (stat["nbre"], stat["mode__label"], utils_texte.Formate_montant(stat["total"])))
            total += stat["total"]
        texte = "%d règlements (%s) : %s." % (len(liste_reglements), utils_texte.Formate_montant(total), utils_texte.Convert_liste_to_texte_virgules(liste_details))
    return JsonResponse({"texte": texte})



def Modifier_reglements(request):
    """ Renvoie le contenu de la table """
    liste_reglements = request.POST.get("liste_reglements")
    only_inclus = True if request.POST.get("only_inclus") == "true" else False

    if len(liste_reglements) == 0:
        liste_reglements = []
    else:
        liste_reglements = [int(id) for id in liste_reglements.split(";")]
    if only_inclus:
        condition = Q(pk__in=liste_reglements)
    else:
        condition = (Q(pk__in=liste_reglements) | Q(depot__isnull=True))

    lignes = []
    for reglement in Reglement.objects.select_related("mode", "emetteur", "payeur", "compte", "famille").filter(condition):
        lignes.append({
            "pk": reglement.pk,
            "date": str(reglement.date) if reglement.date else None,
            "mode": reglement.mode.label,
            "emetteur": reglement.emetteur.nom if reglement.emetteur else None,
            "numero_piece": reglement.numero_piece,
            "payeur": reglement.payeur.nom,
            "montant": float(reglement.montant),
            "famille": reglement.famille.nom,
            "avis_depot": str(reglement.avis_depot) if reglement.avis_depot else None,
            "compte": reglement.compte.nom,
            "date_differe": str(reglement.date_differe) if reglement.date_differe else None,
            "observations": reglement.observations if reglement.observations else None,
            "encaissement_autorise": True if not reglement.date_differe or (reglement.date_differe and reglement.date_differe <= datetime.date.today()) else False,
        })

    context = {
        "resultats": json.dumps(lignes),
        "selections": json.dumps(liste_reglements),
        "only_inclus": only_inclus,
    }
    return render(request, "reglements/selection_reglements_depot.html", context)


class Page(crud.Page):
    model = Depot
    url_liste = "depots_reglements_liste"
    url_ajouter = "depots_reglements_ajouter"
    url_modifier = "depots_reglements_modifier"
    url_supprimer = "depots_reglements_supprimer"
    description_liste = "Voici ci-dessous la liste des dépôts de règlements."
    description_saisie = "Saisissez toutes les informations concernant le dépôt à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un dépôt de règlements"
    objet_pluriel = "des dépôts de règlements"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]

    def form_valid(self, form):
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Recherche les règlements existants pour ce dépôt
        if self.object:
            reglements_existants = Reglement.objects.filter(depot=self.object)
        else:
            reglements_existants = []

        # Recherche les règlements associés
        if len(form.cleaned_data["reglements"]) == 0:
            liste_idreglement = []
        else:
            liste_idreglement = [int(id) for id in form.cleaned_data["reglements"].split(";")]
        liste_modifications = []
        liste_reglements = Reglement.objects.filter(pk__in=liste_idreglement)
        montant_total = Decimal(0)
        for reglement in liste_reglements:
            montant_total += reglement.montant

        # Enregistrement du dépôt
        if not self.object:
            self.object = form.save()
        self.object.montant = montant_total
        self.object.save()

        # Modification des règlements associés
        for reglement in liste_reglements:
            reglement.depot = self.object
            liste_modifications.append(reglement)

        # Détache du dépôt les règlements qui ne sont plus associés
        for reglement in reglements_existants:
            if reglement not in liste_reglements:
                reglement.depot = None
                liste_modifications.append(reglement)

        # Enregistrement des modifications dans la db
        Reglement.objects.bulk_update(liste_modifications, ["depot"], batch_size=50)

        return HttpResponseRedirect(self.get_success_url())


class Liste(Page, crud.Liste):
    model = Depot

    def get_queryset(self):
        return Depot.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['iddepot', 'date', 'nom', 'montant', 'verrouillage', 'compte__nom', 'observations', 'code_compta']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        compte = columns.TextColumn("Compte", sources=["compte__nom"])
        montant = columns.TextColumn("Montant", sources=["montant"], processor='Get_montant')
        verrouillage = columns.TextColumn("Verrouillage", sources=["montant"], processor='Get_verrouillage')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['iddepot', 'verrouillage', 'date', 'nom', 'montant', 'compte', 'observations']
            #hidden_columns = = ["iddepot"]
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date']

        def Get_montant(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.montant)

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

