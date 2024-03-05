# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.contrib import messages
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille


def Generer_tiers_solidaires(request):
    # Génération automatique des tiers solidaires de toutes les familles
    for famille in Famille.objects.all():
        if not famille.tiers_solidaire:
            famille.Maj_infos(maj_adresse=False, maj_mail=False, maj_mobile=False, maj_titulaire_helios=False, maj_tiers_solidaire=True, maj_code_compta=False)

    # Réactualisation de la page
    messages.add_message(request, messages.SUCCESS, "Opération terminée")
    return JsonResponse({"url": reverse_lazy("liste_titulaires_helios")})


class Page(crud.Page):
    model = Famille
    description_liste = "Voici ci-dessous la liste des titulaires Hélios et des tiers solidaires. Cliquez sur le bouton ci-dessous pour générer les tiers solidaires manquants si besoin."
    menu_code = "liste_titulaires_helios"


class Liste(Page, crud.Liste):
    template_name = "individus/liste_titulaires_helios.html"
    model = Famille

    def get_queryset(self):
        try:
            return Famille.objects.select_related("titulaire_helios", "tiers_solidaire").filter(self.Get_filtres("Q"))
        except:
            return Famille.objects.select_related("titulaire_helios", "tiers_solidaire")

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['page_titre'] = "Titulaires Hélios et tiers solidaires"
        context['box_titre'] = "Liste des titulaires Hélios et des tiers solidaires"
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "idfamille", "titulaire_helios__nom", "tiers_solidaire__nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        titulaire_helios = columns.TextColumn("Titulaire Hélios", sources=['titulaire_helios__nom', 'titulaire_helios__prenom'])
        tiers_solidaire = columns.TextColumn("Tiers solidaire", sources=['tiers_solidaire__nom', 'tiers_solidaire__prenom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idfamille", "nom", "titulaire_helios", "tiers_solidaire"]
            ordering = ["nom"]
            labels = {"nom": "Famille"}

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("famille_divers", kwargs={"idfamille": instance.idfamille})),
            ]
            return self.Create_boutons_actions(html)
