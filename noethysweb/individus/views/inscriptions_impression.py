# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Inscription
from django.db.models import Q
from individus.forms.inscriptions_choix_modele import Formulaire as Form_modele
from django.http import JsonResponse
import json


def Impression_pdf(request):
    # Récupération des inscriptions cochées
    inscriptions_cochees = json.loads(request.POST.get("inscriptions_cochees"))
    if not inscriptions_cochees:
        return JsonResponse({"erreur": "Veuillez cocher au moins une inscription dans la liste"}, status=401)

    # Récupération du modèle de document
    valeurs_form_modele = json.loads(request.POST.get("form_modele"))
    form_modele = Form_modele(valeurs_form_modele)
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)

    dict_options = form_modele.cleaned_data

    # Création du PDF
    from fiche_individu.utils import utils_inscriptions
    inscription = utils_inscriptions.Inscriptions()
    resultat = inscription.Impression(liste_inscriptions=inscriptions_cochees, dict_options=dict_options)
    if not resultat:
        return JsonResponse({"success": False}, status=401)
    return JsonResponse({"nom_fichier": resultat["nom_fichier"]})



class Page(crud.Page):
    model = Inscription
    url_liste = "inscriptions_impression"
    menu_code = "inscriptions_impression"


class Liste(Page, crud.Liste):
    template_name = "individus/inscriptions_impression.html"
    model = Inscription

    def get_queryset(self):
        condition = Q(activite__structure__in=self.request.user.structures.all())
        return Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif", "activite").filter(self.Get_filtres("Q"), condition)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des inscriptions"
        context['box_titre'] = "Imprimer des inscriptions"
        context['box_introduction'] = "Cochez des inscriptions, sélectionnez si besoin un modèle de document puis cliquez sur le bouton Aperçu."
        context['onglet_actif'] = "inscriptions_impression"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        context['form_modele'] = Form_modele()
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", 'idinscription', 'date_debut', 'date_fin', 'activite__nom', 'groupe__nom', 'statut', 'categorie_tarif__nom']
        check = columns.CheckBoxSelectColumn(label="")
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        groupe = columns.TextColumn("Groupe", sources=['groupe__nom'])
        categorie_tarif = columns.TextColumn("Catégorie de tarif", sources=['categorie_tarif__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idinscription", 'date_debut', 'date_fin', 'individu', 'famille', 'activite', 'groupe', 'categorie_tarif', 'statut']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
                'statut': 'Formate_statut',
            }
            ordering = ['date_debut']

        def Formate_statut(self, instance, *args, **kwargs):
            if instance.statut == "attente":
                return "<i class='fa fa-hourglass-2 text-yellow'></i> Attente"
            elif instance.statut == "refus":
                return "<i class='fa fa-times-circle text-red'></i> Refus"
            else:
                return "<i class='fa fa-check-circle-o text-green'></i> Valide"
