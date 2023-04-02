# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, uuid
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import EvenementCollaborateur, Vacance, Ferie
from core.utils import utils_dates
from collaborateurs.forms.collaborateur_evenements import Formulaire
from collaborateurs.views.collaborateur import Onglet


class Page(Onglet):
    model = EvenementCollaborateur
    url_liste = "collaborateur_evenements_liste"
    url_ajouter = "collaborateur_evenements_ajouter"
    url_modifier = "collaborateur_evenements_modifier"
    url_supprimer = "collaborateur_evenements_supprimer"
    url_supprimer_plusieurs = "collaborateur_evenements_supprimer_plusieurs"
    description_liste = "Saisissez ici les évènements du collaborateur."
    description_saisie = "Saisissez toutes les informations concernant l'évènement et cliquez sur le bouton Enregistrer."
    objet_singulier = "un évènement"
    objet_pluriel = "des évènements"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Evènements"
        context['onglet_actif'] = "evenements"
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)}), "icone": "fa fa-plus"},
            {"label": "Appliquer un modèle de planning", "classe": "btn btn-default", "href": reverse_lazy("collaborateur_appliquer_modele_planning", kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)}), "icone": "fa fa-plus"},
        ]
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None), "listepk": "xxx"})
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idcollaborateur"] = self.Get_idcollaborateur()
        return form_kwargs

    def get_success_url(self):
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idcollaborateur': self.kwargs.get('idcollaborateur', None)})


class Liste(Page, crud.Liste):
    model = EvenementCollaborateur
    template_name = "collaborateurs/collaborateur_liste.html"

    def get_queryset(self):
        return EvenementCollaborateur.objects.select_related("type_evenement").filter(Q(collaborateur_id=self.Get_idcollaborateur()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idevenement", "date_debut", "date_fin", "titre"]
        check = columns.CheckBoxSelectColumn(label="")
        nom_type_evenement = columns.TextColumn("Catégorie", sources=["type_evenement__nom"], processor='Get_nom_type_evenement')
        duree = columns.TextColumn("Durée", sources=None, processor='Get_duree')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idevenement", "date_debut", "date_fin", "duree", "nom_type_evenement", "titre", "actions"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y %H:%M'),
                'date_fin': helpers.format_date('%d/%m/%Y %H:%M'),
            }
            ordering = ['date_debut']

        def Get_nom_type_evenement(self, instance, *args, **kwargs):
            return """<i class="fa fa-circle margin-r-5" style="color: %s"></i> %s""" % (instance.type_evenement.couleur, instance.type_evenement.nom)

        def Get_duree(self, instance, *args, **kwargs):
            return utils_dates.DeltaEnStr(instance.date_fin - instance.date_debut)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"

    def form_valid(self, form):
        resultat = Form_valid_ajouter(form=form, request=self.request, object=self.object)
        if resultat == True:
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=resultat))


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"

    def form_valid(self, form):
        resultat = Form_valid_modifier(form=form, request=self.request, object=self.object)
        if isinstance(resultat, EvenementCollaborateur):
            self.object = resultat
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=resultat))


class Supprimer(Page, crud.Supprimer):
    template_name = "collaborateurs/collaborateur_delete.html"


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "collaborateurs/collaborateur_delete.html"


def Form_valid_ajouter(form=None, request=None, object=None):
    # Vérification du formulaire
    if not form.is_valid():
        return form

    # Sauvegarde de l'évènement
    liste_evenements = []
    if form.cleaned_data["selection_periode"] == "UNIQUE":
        object = form.save()
        liste_evenements.append(object)

    if form.cleaned_data["selection_periode"] == "RECURRENCE":
        occurences = Calcule_occurences(form.cleaned_data)
        serie = str(uuid.uuid4())
        for occurence in occurences:
            evenement = EvenementCollaborateur.objects.create(
                collaborateur=form.cleaned_data["collaborateur"],
                type_evenement=form.cleaned_data["type_evenement"],
                titre=form.cleaned_data["titre"],
                date_debut=occurence["date_debut"],
                date_fin=occurence["date_fin"],
                # serie=serie,
            )
            liste_evenements.append(evenement)

    return True


def Form_valid_modifier(form=None, request=None, object=None):
    # Vérification du formulaire
    if not form.is_valid():
        return form

    # Sauvegarde de l'évènement
    object = form.save()

    return object


def Calcule_occurences(cleaned_data={}):
    """ Calcule les occurences """
    liste_resultats = []

    liste_vacances = Vacance.objects.all()
    liste_feries = Ferie.objects.all()

    cleaned_data["recurrence_jours_vacances"] = [int(x) for x in cleaned_data["recurrence_jours_vacances"]]
    cleaned_data["recurrence_jours_scolaires"] = [int(x) for x in cleaned_data["recurrence_jours_scolaires"]]

    # Liste dates
    listeDates = [cleaned_data["recurrence_date_debut"],]
    tmp = cleaned_data["recurrence_date_debut"]
    while tmp < cleaned_data["recurrence_date_fin"]:
        tmp += datetime.timedelta(days=1)
        listeDates.append(tmp)

    date = cleaned_data["recurrence_date_debut"]
    numSemaine = int(cleaned_data["recurrence_frequence_type"])
    dateTemp = date
    for date in listeDates:

        # Vérifie période et jour
        valide = False
        if utils_dates.EstEnVacances(date=date, liste_vacances=liste_vacances):
            if date.weekday() in cleaned_data["recurrence_jours_vacances"]:
                valide = True
        else:
            if date.weekday() in cleaned_data["recurrence_jours_scolaires"]:
                valide = True

        # Calcul le numéro de semaine
        if len(listeDates) > 0:
            if date.weekday() < dateTemp.weekday():
                numSemaine += 1

        # Fréquence semaines
        if cleaned_data["recurrence_frequence_type"] in (2, 3, 4):
            if numSemaine % cleaned_data["recurrence_frequence_type"] != 0:
                valide = False

        # Semaines paires et impaires
        if valide == True and cleaned_data["recurrence_frequence_type"] in (5, 6):
            numSemaineAnnee = date.isocalendar()[1]
            if numSemaineAnnee % 2 == 0 and cleaned_data["recurrence_frequence_type"] == 6:
                valide = False
            if numSemaineAnnee % 2 != 0 and cleaned_data["recurrence_frequence_type"] == 5:
                valide = False

        # Vérifie si férié
        if cleaned_data["recurrence_feries"] and utils_dates.EstFerie(date, liste_feries):
            valide = False

        # Application
        if valide:
            date_debut_final = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=cleaned_data["recurrence_heure_debut"].hour, minute=cleaned_data["recurrence_heure_debut"].minute)
            date_fin_final = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=cleaned_data["recurrence_heure_fin"].hour, minute=cleaned_data["recurrence_heure_fin"].minute)
            liste_resultats.append({"date_debut": date_debut_final, "date_fin": date_fin_final})

        dateTemp = date
    return liste_resultats
