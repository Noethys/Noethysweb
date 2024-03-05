# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import AttestationFiscale
from core.utils import utils_texte


class Page(crud.Page):
    model = AttestationFiscale
    url_liste = "liste_attestations_fiscales"
    url_supprimer = "attestations_fiscales_supprimer"
    menu_code = "liste_attestations_fiscales"
    description_liste = "Voici ci-dessous la liste des attestations fiscales générées."
    objet_singulier = "une attestation fiscale"
    objet_pluriel = "des attestations fiscales"
    url_supprimer_plusieurs = "attestations_fiscales_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    model = AttestationFiscale

    def get_queryset(self):
        return AttestationFiscale.objects.select_related('famille', 'lot').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idattestation", "date_edition", "famille", "numero", "date_debut", "date_fin", "total", "lot__nom"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        total = columns.TextColumn("Total", sources=['total'], processor='Get_total')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idattestation", "date_edition", "famille", "numero", "date_debut", "date_fin", "total", "lot"]
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]

        def Get_total(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.total)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_attestation_fiscale", kwargs={"idfamille": instance.famille_id, "idattestation": instance.pk}), title="Imprimer ou envoyer par email l'attestation fiscale'"),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Supprimer(Page, crud.Supprimer):
    pass


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass