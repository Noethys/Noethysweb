# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse, reverse_lazy
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Consommation
from fiche_famille.views.famille import Onglet
from consommations.forms.liste_consommations import Formulaire


class Page(Onglet):
    model = Consommation
    url_liste = "famille_liste_consommations"
    url_modifier = "famille_liste_consommations_modifier"
    url_supprimer = "famille_liste_consommations_supprimer"
    url_supprimer_plusieurs = "famille_liste_consommations_supprimer_plusieurs"
    description_liste = "Voici ci-dessous la liste détaillée des consommations de cette famille. Cliquez sur <i class='fa fa-eye-slash'></i> pour afficher les colonnes masquées disponibles."
    description_saisie = "Saisissez toutes les informations concernant la consommation à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une consommation"
    objet_pluriel = "des consommations"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        # Ajout l'idfamille à l'URL de suppression groupée
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'idfamille': self.kwargs.get('idfamille', None), "listepk": "xxx"})
        return context

    def get_success_url(self):
        return reverse_lazy(self.url_liste, kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Liste(Page, crud.Liste):
    model = Consommation
    template_name = "fiche_famille/famille_pieces.html"

    def get_queryset(self):
        return Consommation.objects.select_related("activite", "inscription", "individu", "unite", "groupe", "categorie_tarif", "prestation", "evenement").filter(Q(inscription__famille_id=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Liste détaillée des consommations"
        context['onglet_actif'] = "outils"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        context['boutons_coches'] = json.dumps([
            {"id": "bouton_dissocier_prestation", "action": """action_bouton_coche("%s")""" % reverse("ajax_consommations_dissocier_prestation"), "title": "Dissocier la prestation", "label": "Dissocier la prestation"},
        ])
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "idconso", "date_saisie", "date", "unite__nom", "groupe__nom", "etat", "activite__nom",
                   "heure_debut", "heure_fin", "quantite", "prestation__idprestation", "categorie_tarif__nom", "prestation__label", "prestation__montant"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        unite = columns.TextColumn("Unité", sources=['unite__nom'])
        groupe = columns.TextColumn("Groupe", sources=['groupe__nom'])
        categorie_tarif = columns.TextColumn("Catégorie", sources=['categorie_tarif__nom'])
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        etat = columns.TextColumn("Etat", sources=['etat'], processor='Get_etat')
        prestation = columns.TextColumn("ID Prestation", sources=['prestation__idprestation'])
        label_prestation = columns.TextColumn("Label prestation", sources=["prestation__label"])
        montant_prestation = columns.TextColumn("Montant prestation", sources=["prestation__montant"])
        ville_resid = columns.TextColumn("Ville", sources=None, processor="Get_ville_resid")
        nom_evenement = columns.TextColumn("Evénement", sources=["evenement__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check","idconso", "date_saisie", "individu", "date", "unite", "nom_evenement", "groupe", "activite", "etat", "heure_debut", "heure_fin",
                       "quantite", "categorie_tarif", "prestation", "label_prestation", "montant_prestation", "ville_resid", "actions"]
            processors = {
                "date": helpers.format_date('%d/%m/%Y'),
                "date_saisie": helpers.format_date('%d/%m/%Y %H:%M'),
                "heure_debut": helpers.format_date('%H:%M'),
                "heure_fin": helpers.format_date('%H:%M'),
                "montant_prestation": "Formate_montant_standard",
            }
            hidden_columns = ["date_saisie", "prestation", "label_prestation", "montant_prestation", "ville_resid", "quantite", "categorie_tarif", "nom_evenement"]
            ordering = ["date_saisie"]

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.individu.ville_resid

        def Get_etat(self, instance, **kwargs):
            return instance.get_etat_display()

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, kwargs={"idfamille": instance.inscription.famille_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, kwargs={"idfamille": instance.inscription.famille_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)


class Modifier(Page, crud.Modifier):
    template_name = "fiche_famille/famille_edit.html"
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"

    def Check_protections(self, objet=None):
        protections = []
        if objet.etat in ("present", "absenti", "absentj"):
            protections.append("La consommation est pointée")
        if objet.prestation:
            protections.append("Une prestation est associée")
        return protections


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "fiche_famille/famille_delete.html"

    def Check_protections(self, objets=[]):
        protections = []
        for conso in objets:
            if conso.etat in ("present", "absenti", "absentj"):
                protections.append("La consommation ID%d est pointée %s" % (conso.pk, conso.etat))
            if conso.prestation:
                protections.append("La consommation ID%d est associée à une prestation" % conso.pk)
        return protections
