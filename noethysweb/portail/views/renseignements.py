# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.http import HttpResponseRedirect, Http404
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils.translation import gettext as _
from core.views import crud
from core.models import Consentement, Rattachement, Inscription
from individus.utils import utils_vaccinations, utils_assurances
from portail.views.base import CustomView
from portail.forms.approbations import Formulaire


class View(CustomView, crud.Modifier):
    menu_code = "portail_renseignements"
    form_class = Formulaire
    template_name = "portail/renseignements.html"
    mode = "CONSULTATION"
    titre_historique = "Valider les approbations"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_titre'] = _("Renseignements")

        familles = self.get_famille_object()
        context['familles'] = familles
        # Initialiser un dictionnaire pour contenir les attachements et les inscriptions de toutes les familles
        context['rattachements'] = []
        renseignements_manquants = {}

        for famille in familles:
            # Récupérer les rattachements (individus) pour chaque famille
            rattachements = Rattachement.objects.prefetch_related('famille','individu').filter(
                famille=famille,
                individu__deces=False
            ).order_by("individu__nom", "individu__prenom")

            context['rattachements'].extend(rattachements)  # Ajoutez les rattachements de cette famille au contexte

            # Récupérer les inscriptions pour la famille
            if hasattr(self.request.user, 'individu') and self.request.user.individu is not None:
                inscriptions = Inscription.objects.select_related("activite", "individu").filter(
                    individu=self.request.user.individu,
                    date_fin__isnull=True
                )
            else:
                conditions = Q(famille=famille) & (
                        Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
                inscriptions = Inscription.objects.select_related("activite", "individu").filter(conditions)

            # Récupérer les vaccins et assurances manquants pour chaque famille
            for individu, liste_vaccinations in utils_vaccinations.Get_vaccins_obligatoires_by_inscriptions(
                    inscriptions=inscriptions).items():
                renseignements_manquants.setdefault(individu, [])
                renseignements_manquants[individu].append(
                    "%d vaccination%s manquante%s" % (
                        len(liste_vaccinations), "s" if len(liste_vaccinations) else "",
                        "s" if len(liste_vaccinations) else ""
                    )
                )

            # Récupérer les assurances manquantes pour chaque famille
            for individu in utils_assurances.Get_assurances_manquantes_by_inscriptions(
                    famille=famille, inscriptions=inscriptions):
                renseignements_manquants.setdefault(individu, [])
                renseignements_manquants[individu].append("Assurance manquante")

        context["renseignements_manquants"] = renseignements_manquants

        return context

    def get_object(self):
        if hasattr(self.request.user, 'individu') and self.request.user.individu is not None:
            return self.request.user.individu  # Renvoyer l'individu si l'utilisateur est un individu
        return self.request.user.famille  # Renvoyer la famille si l'utilisateur fait partie d'une famille

    def get_famille_object(self):
        if hasattr(self.request.user, 'famille'):
            return [self.request.user.famille]  # Renvoyer sous forme de liste même s'il s'agit d'une seule famille
        elif hasattr(self.request.user, 'individu'):
            # Récupérer toutes les familles auxquelles l'individu est rattaché
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            return [rattachement.famille for rattachement in rattachements if rattachement.famille and rattachement.titulaire == 1]
        return []

    def get_success_url(self):
        return reverse_lazy("portail_renseignements")

    def form_valid(self, form):
        """ Enregistrement des approbations """
        familles = self.get_famille_object()
        if not familles:
            messages.add_message(self.request, messages.ERROR, _("Utilisateur non reconnu."))
            return self.form_invalid(form)

        # Enregistrement des approbations cochées
        nbre_coches = 0
        for code, coche in form.cleaned_data.items():
            if coche:
                if "unite" in code:
                    idunite = int(code.replace("unite_", ""))
                    for famille in familles:
                        Consentement.objects.create(famille=famille, unite_consentement_id=idunite)
                    nbre_coches += 1
                elif "rattachement" in code:
                    # Extraction de l'id du rattachement en se basant sur le format "rattachement_<id>_famille_<id>"
                    try:
                        parts = code.split('_')
                        if len(parts) >= 2 and parts[0] == "rattachement":
                            idrattachement = int(parts[1])  # Le deuxième élément est l'ID du rattachement
                            Rattachement.objects.filter(pk=idrattachement).update(
                                certification_date=datetime.datetime.now())
                            nbre_coches += 1
                        else:
                            messages.add_message(self.request, messages.ERROR,
                                                 _("Format de rattachement invalide: %s") % code)
                            return self.form_invalid(form)
                    except (ValueError, IndexError):
                        messages.add_message(self.request, messages.ERROR,
                                             _("Erreur de traitement du rattachement: %s") % code)
                        return self.form_invalid(form)
                elif "famille" in code:
                    for famille in familles:
                        famille.certification_date = datetime.datetime.now()
                        famille.save()
                    nbre_coches += 1

        # Confirmation message
        if nbre_coches == 0:
            messages.add_message(self.request, messages.ERROR, _("Aucune approbation n'a été cochée"))
        elif nbre_coches == 1:
            messages.add_message(self.request, messages.SUCCESS, _("L'approbation cochée a bien été enregistrée"))
        else:
            messages.add_message(self.request, messages.SUCCESS,
                                 _("Les %d approbations cochées ont bien été enregistrées") % nbre_coches)


        if self.object:
            print("instance=self.object",self.object)
            self.save_historique(instance=self.object, form=form)
        return HttpResponseRedirect(self.get_success_url())
