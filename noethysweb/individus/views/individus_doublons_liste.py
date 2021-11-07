# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Count, F, CharField, Value
from django.db.models.functions import Concat
from core.views import crud
from core.models import Individu
from core.views.customdatatable import CustomDatatable, Colonne


class Page(crud.Page):
    model = Individu
    url_liste = "individus_doublons_liste"


class Liste(Page, crud.CustomListe):
    filtres = ["individu", "nbre_occurences"]
    colonnes = [
        Colonne(code="individu", label="Individu", classe="CharField", label_filtre="Nom"),
        Colonne(code="nbre_occurences", label="Nbre occurences", classe="IntegerField"),
    ]

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des individus en doublon"
        context['box_titre'] = "Liste des individus en doublon"
        context['box_introduction'] = "Voici ci-dessous la liste des individus en doublon (recherche selon le nom et le prénom). Cette liste vous permet d'identifier des individus qui auraient été saisis en double."
        context["datatable"] = self.Get_customdatatable()
        context["hauteur_table"] = "400px"
        return context

    def Get_customdatatable(self):
        # Recherche des doublons
        qs = Individu.objects.annotate(nom_complet=Concat(F('nom'), Value(' '), F('prenom'), output_field=CharField()))
        resultats = qs.values('nom_complet').annotate(nbre_occurences=Count('nom_complet')).filter(nbre_occurences__gt=1)

        # Formatage des résultats
        lignes = []
        for resultat in resultats:
            lignes.append((resultat["nom_complet"], resultat["nbre_occurences"]))
        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())
