# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Min, Max
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Quotient, Prestation
from fiche_famille.forms.famille_quotients import Formulaire
from fiche_famille.views.famille import Onglet


class Page(Onglet):
    model = Quotient
    url_liste = "famille_quotients_liste"
    url_ajouter = "famille_quotients_ajouter"
    url_modifier = "famille_quotients_modifier"
    url_supprimer = "famille_quotients_supprimer"
    description_liste = "Consultez et saisissez ici les quotients familiaux de la famille."
    description_saisie = "Saisissez toutes les informations concernant le quotient et cliquez sur le bouton Enregistrer."
    objet_singulier = "un quotient familial"
    objet_pluriel = "des quotients familiaux"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Quotients familiaux"
        context['onglet_actif'] = "quotients"
        if self.request.user.has_perm("core.famille_quotients_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
            ]
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.famille_quotients_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def validation_form(self, form):
        # Vérifie que ce quotient n'est pas en conflit avec un autre quotient existant
        conditions = Q(famille_id=self.Get_idfamille(), type_quotient=form.cleaned_data["type_quotient"], date_debut__lte=form.cleaned_data["date_fin"], date_fin__gte=form.cleaned_data["date_debut"])
        quotients = Quotient.objects.filter(conditions).exclude(pk=self.object.pk if self.object else None)
        if quotients:
            form.add_error(None, "Il existe déjà %d quotient(s) de même type sur la même période !" % len(quotients))
            return False, form

        # Vérifie si un recalcul des prestations est nécessaire
        if "date_debut" in form.changed_data or "date_fin" in form.changed_data or "quotient" in form.changed_data or "revenu" in form.changed_data:

            # Période à recalculer
            date_min = min(form.cleaned_data["date_debut"], form.initial["date_debut"]) if "date_debut" in form.initial else form.cleaned_data["date_debut"]
            date_max = max(form.cleaned_data["date_fin"], form.initial["date_fin"]) if "date_fin" in form.initial else form.cleaned_data["date_fin"]

            # Recherche s'il y a des prestations facturées sur cette période
            prestations_facturees = Prestation.objects.filter(famille=form.cleaned_data["famille"], date__range=(date_min, date_max), facture__isnull=False).aggregate(Min("date"), Max("date"))
            if prestations_facturees["date__min"]:
                # Si le montant du QF a été modifié
                if "quotient" in form.changed_data:
                    form.add_error(None, "Vous ne pouvez pas modifier le montant du quotient car des prestations sont déjà facturées sur la période du %s au %s. Créez plutôt un nouveau QF." % (prestations_facturees["date__min"].strftime("%d/%m/%Y"), prestations_facturees["date__max"].strftime("%d/%m/%Y")))
                    return False, form
                # Si ce sont seulement les dates du QF qui ont été modifiées
                if (form.cleaned_data["date_debut"] > prestations_facturees["date__min"]) or (form.cleaned_data["date_fin"] < prestations_facturees["date__max"]):
                    form.add_error(None, "Ces nouvelles dates sont erronées car des prestations sont déjà facturées sur la période du %s au %s. Créez plutôt un nouveau QF." % (prestations_facturees["date__min"].strftime("%d/%m/%Y"), prestations_facturees["date__max"].strftime("%d/%m/%Y")))
                    return False, form

            # Enregistrement du quotient
            if self.verbe_action == "Modifier":
                self.object.save()
            if self.verbe_action == "Ajouter":
                self.object = form.save()

            # Recalcul des prestations
            self.Recalculer_prestations(date_min=date_min, date_max=date_max)

        return True, form

    def Recalculer_prestations(self, date_min=None, date_max=None):
        # Recherche s'il y a des prestations à modifier sur la période
        prestations = Prestation.objects.filter(famille_id=self.Get_idfamille(), date__range=(date_min, date_max), facture__isnull=True, activite__isnull=False)
        keys_prestations = list({(prestation.individu_id, prestation.activite_id): True for prestation in prestations}.keys())

        # Recalcule les prestations
        if keys_prestations:
            logger.debug("Recalcul des prestations après changement de QF...")
            from consommations.utils.utils_grille_virtuelle import Grille_virtuelle
            for idindividu, idactivite in keys_prestations:
                grille = Grille_virtuelle(request=self.request, idfamille=self.Get_idfamille(), idindividu=idindividu, idactivite=idactivite, date_min=date_min, date_max=date_max)
                grille.Recalculer_tout()
                grille.Enregistrer()


class Liste(Page, crud.Liste):
    model = Quotient
    template_name = "fiche_famille/famille_liste.html"

    def get_queryset(self):
        return Quotient.objects.filter(Q(famille__pk=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idquotient', 'date_debut', 'date_fin', 'type_quotient__nom', 'quotient', 'revenu']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        type_quotient = columns.TextColumn("Type de quotient", sources=["type_quotient__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idquotient', 'date_debut', 'date_fin', 'type_quotient', 'quotient', 'revenu']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            if not view.request.user.has_perm("core.famille_quotients_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"

    def form_valid(self, form):
        resultat, form = self.validation_form(form)
        if not resultat:
            return self.render_to_response(self.get_context_data(form=form))
        return super(Ajouter, self).form_valid(form)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"

    def form_valid(self, form):
        resultat, form = self.validation_form(form)
        if not resultat:
            return self.render_to_response(self.get_context_data(form=form))
        return super(Modifier, self).form_valid(form)


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"

    def Check_protections(self, objet=None):
        protections = []
        prestations_facturees = Prestation.objects.filter(famille=objet.famille, date__range=(objet.date_debut, objet.date_fin), facture__isnull=False).aggregate(Min("date"), Max("date"))
        if prestations_facturees["date__min"]:
            protections.append("Vous ne pouvez pas supprimer ce quotient car des prestations sont déjà facturées sur la période du %s au %s. Créez plutôt un nouveau QF." % (prestations_facturees["date__min"].strftime("%d/%m/%Y"), prestations_facturees["date__max"].strftime("%d/%m/%Y")))
        return protections

    def Apres_suppression(self, objet=None):
        self.Recalculer_prestations(date_min=objet.date_debut, date_max=objet.date_fin)
