# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Prestation, Ventilation
from fiche_famille.forms.famille_remboursement import Formulaire
from fiche_famille.views.famille import Onglet
from facturation.utils import utils_factures
from reglements.utils import utils_ventilation


class Ajouter(Onglet, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Ajouter, self).get_context_data(**kwargs)
        context['box_titre'] = "Créer un remboursement"
        context['box_introduction'] = "Vous pouvez créer ici un remboursement si le compte de la famille est créditeur. Deux prestations et un règlement fictif seront générés automatiquement afin de régulariser le compte."
        context['onglet_actif'] = "reglements"
        return context

    def get_success_url(self):
        return reverse_lazy("famille_reglements_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Ajouter, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def form_valid(self, form):
        # Enregistrement du règlement
        reglement = form.save(commit=True)

        # Création de la ventilation positive
        prestation_positive = Prestation.objects.create(date=reglement.date, categorie="autre", label="Remboursement", famille=reglement.famille,
                                                        montant_initial=-reglement.montant, montant=-reglement.montant)

        # Ventilation de la ventilation positive
        utils_ventilation.Ventilation_auto(IDfamille=reglement.famille_id)

        # Création de la prestation négative
        prestation_negative = Prestation.objects.create(date=reglement.date, categorie="autre", label="Remboursement", famille=reglement.famille,
                                               montant_initial=reglement.montant, montant=reglement.montant)

        # Ventilation de la prestation négative
        Ventilation.objects.create(famille=reglement.famille, reglement=reglement, prestation=prestation_negative, montant=reglement.montant)

        # Recalcule le solde des factures de la famille
        utils_factures.Maj_solde_actuel_factures(IDfamille=reglement.famille_id)

        return super().form_valid(form)
