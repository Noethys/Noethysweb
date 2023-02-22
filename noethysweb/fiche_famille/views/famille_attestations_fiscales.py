# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse, reverse_lazy
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import AttestationFiscale
from core.utils import utils_texte
from fiche_famille.views.famille import Onglet


class Page(Onglet):
    model = AttestationFiscale
    url_liste = "famille_attestations_fiscales_liste"
    url_supprimer = "famille_attestations_fiscales_supprimer"
    description_liste = "Voici ci-dessous la liste des attestations fiscales générées pour cette famille."
    objet_singulier = "une attestation fiscale"
    objet_pluriel = "des attestations fiscales"

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})


class Liste(Page, crud.Liste):
    model = AttestationFiscale
    template_name = "fiche_famille/famille_pieces.html"

    def get_queryset(self):
        return AttestationFiscale.objects.select_related("lot").filter(Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Attestations fiscales"
        context['onglet_actif'] = "outils"
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idattestation", "date_edition", "numero", "date_debut", "date_fin", "total", "lot__nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        total = columns.TextColumn("Total", sources=['total'], processor='Get_total')
        lot = columns.TextColumn("Lot", sources=['lot__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idattestation", "date_edition", "numero", "date_debut", "date_fin", "total", "lot"]
            processors = {
                "date_edition": helpers.format_date('%d/%m/%Y'),
                "date_debut": helpers.format_date('%d/%m/%Y'),
                "date_fin": helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]

        def Get_total(self, instance, **kwargs):
            return utils_texte.Formate_montant(instance.total)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_imprimer(url=reverse("famille_voir_attestation_fiscale", kwargs={"idfamille": instance.famille_id, "idattestation": instance.pk}), title="Imprimer ou envoyer par email l'attestation fiscale"),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, kwargs={"idfamille": instance.famille_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"
