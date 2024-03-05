# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse
from django.http import JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Information
from fiche_individu.forms.individu_information import Formulaire


def Modifier_diffusion(request):
    idinformation = int(request.POST["idinformation"])
    type_diffusion = request.POST["type_diffusion"]

    # Importation de l'information à modifier
    info = Information.objects.get(pk=idinformation)

    if type_diffusion == "L":
        info.diffusion_listing_enfants = not info.diffusion_listing_enfants
    if type_diffusion == "C":
        info.diffusion_listing_conso = not info.diffusion_listing_conso
    if type_diffusion == "R":
        info.diffusion_listing_repas = not info.diffusion_listing_repas
    info.save()

    return JsonResponse({"succes": True})


class Page(crud.Page):
    model = Information
    url_liste = "informations_liste"
    url_modifier = "informations_modifier"
    url_supprimer = "informations_supprimer"
    description_liste = "Voici ci-dessous la liste des informations personnelles des individus. La colonne Diffusion indique si l'information est diffusée sur le listing des informations (L), la liste des consommations (C) et la commande des repas (R). Vous pouvez cliquer directement sur L, C ou R pour activer ou désactiver la diffusion."
    description_saisie = "Saisissez toutes les informations souhaitées et cliquez sur le bouton Enregistrer."
    objet_singulier = "une information personnelle"
    objet_pluriel = "des informations personnelles"


class Liste(Page, crud.Liste):
    model = Information
    template_name = "individus/liste_informations.html"

    def get_queryset(self):
        return Information.objects.select_related("individu", "categorie").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['page_titre'] = "Informations personnelles"
        context['box_titre'] = "Liste des informations personnelles"
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "idinformation", "categorie__nom", "intitule", "description"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        categorie = columns.CompoundColumn("Catégorie", sources=['categorie__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        diffusion = columns.TextColumn("Diffusion", sources=[], processor='Get_diffusion')
        intitule = columns.TextColumn("Intitulé", processor="Get_intitule")
        description = columns.TextColumn("Description", processor="Get_description")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idinformation", "individu", "categorie", "intitule", "description", "diffusion"]
            ordering = ["individu"]

        def Get_intitule(self, instance, *args, **kwargs):
            return instance.intitule

        def Get_description(self, instance, *args, **kwargs):
            return instance.description

        def Get_diffusion(self, instance, *args, **kwargs):
            html = []
            html.append("""<small style="cursor: pointer;" onclick="modifier_diffusion('L', %d)" title="Diffusion sur le listing des informations : Cliquez pour modifier." class="badge badge-%s">L</small>""" % (instance.pk, "success" if instance.diffusion_listing_enfants else "danger"))
            html.append("""<small style="cursor: pointer;" onclick="modifier_diffusion('C', %d)" title="Diffusion sur la liste des consommations : Cliquez pour modifier." class="badge badge-%s">C</small>""" % (instance.pk, "success" if instance.diffusion_listing_conso else "danger"))
            html.append("""<small style="cursor: pointer;" onclick="modifier_diffusion('R', %d)" title="Diffusion sur la commande des repas : Cliquez pour modifier." class="badge badge-%s">R</small>""" % (instance.pk, "success" if instance.diffusion_listing_repas else "danger"))
            return " ".join(html)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
