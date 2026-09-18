# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from django.urls import reverse
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import Rattachement, Cotisation, UniteCotisation
from cotisations.views.liste_adherents import Page


class Liste(Page, crud.Liste):
    model = Rattachement

    def get_queryset(self):
        idunite_cotisation = self.kwargs.get("idunite_cotisation")

        # Familles ayant une adhésion familiale pour cette unité : tous les membres du foyer sont adhérents
        idfamilles_cotisation_familiale = list(Cotisation.objects.filter(
            unite_cotisation_id=idunite_cotisation, individu__isnull=True).values_list("famille_id", flat=True))

        # Individus ayant directement une adhésion individuelle pour cette unité
        idindividus_cotisation_individuelle = list(Cotisation.objects.filter(
            unite_cotisation_id=idunite_cotisation, individu__isnull=False).values_list("individu_id", flat=True))

        condition = Q(famille_id__in=idfamilles_cotisation_familiale, categorie__in=(1, 2)) | Q(individu_id__in=idindividus_cotisation_individuelle)
        return Rattachement.objects.select_related("individu", "famille").filter(condition).filter(self.Get_filtres("Q")).distinct()

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        idunite_cotisation = self.kwargs.get("idunite_cotisation")
        unite_cotisation = UniteCotisation.objects.select_related("type_cotisation").get(pk=idunite_cotisation)
        context["page_titre"] = "Liste des adhérents"
        context["box_titre"] = "Individus adhérents - %s (%s)" % (unite_cotisation.nom, unite_cotisation.type_cotisation.nom)
        context["box_introduction"] = ("Voici la liste des individus adhérents à cette unité d'adhésion. Pour une adhésion "
            "familiale, tous les membres du foyer sont listés individuellement. "
            "<br><a class='btn btn-default mt-3' href='%s'><i class='fa fa-users margin-r-5'></i>Voir la liste des familles adhérentes</a>"
            % reverse("liste_adherents_familles", kwargs={"idunite_cotisation": idunite_cotisation}))
        context["impression_introduction"] = ""
        context["impression_conclusion"] = ""
        context["onglet_actif"] = "liste_adherents"
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille"]
        nom = columns.TextColumn("Nom", sources=['individu__nom'])
        prenom = columns.TextColumn("Prénom", sources=['individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        age = columns.IntegerColumn("Age", sources=[], processor="Get_age")
        rue_resid = columns.TextColumn("Adresse", sources=[], processor="Get_rue_resid")
        cp_resid = columns.TextColumn("CP", sources=[], processor="Get_cp_resid")
        ville_resid = columns.TextColumn("Ville", sources=[], processor="Get_ville_resid")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idrattachement", "nom", "prenom", "age", "famille", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom", "prenom"]

        def Get_age(self, instance, *args, **kwargs):
            return instance.individu.Get_age()

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.individu.Get_adresse()["rue"]

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.individu.Get_adresse()["cp"]

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.individu.Get_adresse()["ville"]
