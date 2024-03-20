# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import decimal
from django.urls import reverse
from django.db.models import Q, Sum
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Cotisation, Ventilation
from core.utils import utils_dates, utils_texte


class Page(crud.Page):
    model = Cotisation
    url_liste = "cotisations_liste"
    description_liste = "Voici ci-dessous la liste des adhésions."
    description_saisie = "Saisissez toutes les informations concernant l'adhésion à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une adhésion"
    objet_pluriel = "des adhésions"
    url_supprimer_plusieurs = "cotisations_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = Cotisation

    def get_queryset(self):
        condition = (Q(type_cotisation__structure__in=self.request.user.structures.all()) | Q(type_cotisation__structure__isnull=True))
        return Cotisation.objects.select_related('famille', 'individu', 'type_cotisation', 'type_cotisation__structure', 'unite_cotisation', 'depot_cotisation').filter(self.Get_filtres("Q"), condition)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", "fgenerique:famille", "idcotisation", "date_saisie", "date_creation_carte", "numero", "date_debut", "date_fin",
                   "observations", "type_cotisation__nom", "unite_cotisation__nom", "depot_cotisation__date"]
        check = columns.CheckBoxSelectColumn(label="")
        individu = columns.CompoundColumn("Individu", sources=['individu__nom', 'individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        nom_cotisation = columns.TextColumn("Nom", sources=['type_cotisation__nom', 'unite_cotisation__nom'], processor='Get_nom_cotisation')
        depot = columns.TextColumn("Dépôt", sources=['depot_cotisation__date'], processor='Get_date_depot')
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville", processor='Get_ville_resid')
        solde = columns.TextColumn("Solde", sources=[], processor="Get_solde")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idcotisation', 'date_debut', 'date_fin', 'famille', 'individu', 'nom_cotisation', 'numero', 'depot', "rue_resid", "cp_resid", "ville_resid", "solde"]
            hidden_columns = ["rue_resid", "cp_resid", "ville_resid", "solde"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            labels = {
                "date_debut": "Début",
                "date_fin": "Fin",
            }
            ordering = ["date_debut"]

        def Get_nom_cotisation(self, instance, *args, **kwargs):
            if instance.prestation:
                return instance.prestation.label
            else:
                return "%s - %s" % (instance.type_cotisation.nom, instance.unite_cotisation.nom)

        def Get_solde(self, instance, *args, **kwargs):
            # Calcul du solde de la prestation de la cotisation
            if not hasattr(self, "dict_soldes"):
                dict_ventilations = {temp["prestation_id"]: temp["total"] for temp in Ventilation.objects.values("prestation_id").filter(prestation__cotisation__isnull=False).annotate(total=Sum("montant"))}
                self.dict_soldes = {}
                for prestation in Cotisation.objects.select_related("prestation").values("prestation__pk", "prestation__montant").filter():
                    if prestation["prestation__pk"]:
                        self.dict_soldes.setdefault(prestation["prestation__pk"], decimal.Decimal(0))
                        self.dict_soldes[prestation["prestation__pk"]] += dict_ventilations.get(prestation["prestation__pk"], decimal.Decimal(0)) - prestation["prestation__montant"]
                del dict_ventilations
            if instance.prestation_id not in self.dict_soldes:
                return ""
            solde = self.dict_soldes.get(instance.prestation_id, decimal.Decimal(0))
            if solde == decimal.Decimal(0):
                couleur = "success"
            elif solde > decimal.Decimal(0):
                couleur = "info"
            else:
                couleur = "danger"
            return """<span class='badge badge-%s'>%s</span>""" % (couleur, utils_texte.Formate_montant(solde))

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_cotisation", kwargs={"idfamille": instance.famille_id, "idcotisation": instance.pk}), title="Imprimer ou envoyer par email l'adhésion"),
                self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users"),
            ]
            return self.Create_boutons_actions(html)

        def Get_date_depot(self, instance, *args, **kwargs):
            if instance.depot_cotisation:
                return utils_dates.ConvertDateToFR(instance.depot_cotisation.date)
            return ""

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.famille.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.famille.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.famille.ville_resid


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
