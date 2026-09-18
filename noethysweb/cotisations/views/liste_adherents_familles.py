# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from django.urls import reverse
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import Famille, UniteCotisation
from cotisations.views.liste_adherents import Page


class Liste(Page, crud.Liste):
    model = Famille

    def get_queryset(self):
        idunite_cotisation = self.kwargs.get("idunite_cotisation")
        return Famille.objects.filter(Q(cotisation__unite_cotisation_id=idunite_cotisation), self.Get_filtres("Q")).distinct()

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        idunite_cotisation = self.kwargs.get("idunite_cotisation")
        unite_cotisation = UniteCotisation.objects.select_related("type_cotisation").get(pk=idunite_cotisation)
        context["page_titre"] = "Liste des adhérents"
        context["box_titre"] = "Familles adhérentes - %s (%s)" % (unite_cotisation.nom, unite_cotisation.type_cotisation.nom)
        context["box_introduction"] = ("Voici la liste des familles adhérentes à cette unité d'adhésion. "
            "<br><a class='btn btn-default mt-3' href='%s'><i class='fa fa-user margin-r-5'></i>Voir la liste des individus adhérents</a>"
            % reverse("liste_adherents_individus", kwargs={"idunite_cotisation": idunite_cotisation}))
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["onglet_actif"] = "liste_adherents"
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "idfamille"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        rue_resid = columns.TextColumn("Adresse", sources=['rue_resid'])
        cp_resid = columns.TextColumn("CP", sources=['cp_resid'])
        ville_resid = columns.TextColumn("Ville", sources=['ville_resid'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idfamille", "nom", "rue_resid", "cp_resid", "ville_resid", "actions"]
            ordering = ["nom"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [self.Create_bouton(url=reverse("famille_resume", args=[instance.pk]), title="Ouvrir la fiche famille", icone="fa-users")]
            return self.Create_boutons_actions(html)
