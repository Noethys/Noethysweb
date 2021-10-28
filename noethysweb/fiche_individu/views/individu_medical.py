# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Individu, Vaccin, Information, Medecin, TypeMaladie, Vaccin
from fiche_individu.forms.individu_info_medicale import Formulaire as Formulaire_info_medicale
from fiche_individu.forms.individu_vaccin import Formulaire as Formulaire_vaccin
from fiche_individu.forms.individu_medecin import Formulaire as Formulaire_medecin
from fiche_individu.views.individu import Onglet
from datatableview.views import MultipleDatatableView
from django.http import JsonResponse
from core.utils import utils_dates
import datetime


def Select_medecin(request):
    # Récupération des données du formulaire
    idindividu = int(request.POST.get("idindividu"))
    idmedecin = request.POST.get("medecin")

    # Enregistrement du médecin
    if idmedecin == "":
        medecin = None
    else:
        medecin = Medecin.objects.get(pk=idmedecin)

    individu = Individu.objects.get(pk=idindividu)
    individu.medecin = medecin
    individu.save()

    return JsonResponse({"success": True})

def Deselect_medecin(request):
    # Récupération des données du formulaire
    idindividu = int(request.POST.get("idindividu"))

    # Suppression du médecin
    individu = Individu.objects.get(pk=idindividu)
    individu.medecin = None
    individu.save()

    return JsonResponse({"success": True})

def RechercherVaccinsObligatoires(individu=None, nonvalides_only=False):
    liste_resultats = []
    vaccins = Vaccin.objects.select_related("type_vaccin").prefetch_related("type_vaccin__types_maladies").filter(individu=individu)
    for maladie in TypeMaladie.objects.filter(vaccin_obligatoire=True).order_by("nom"):
        if not individu.date_naiss or not maladie.vaccin_date_naiss_min or (maladie.vaccin_date_naiss_min and individu.date_naiss >= maladie.vaccin_date_naiss_min):
            valide = False
            for vaccin in vaccins:
                if maladie in vaccin.type_vaccin.types_maladies.all():
                    if vaccin.type_vaccin.duree_validite:
                        date_fin_validite = vaccin.date + utils_dates.ConvertDureeStrToDuree(vaccin.type_vaccin.duree_validite)
                        if date_fin_validite >= datetime.date.today():
                            valide = True
                    else:
                        valide = True
            if not nonvalides_only or (nonvalides_only and not valide):
                liste_resultats.append({"label": maladie.nom, "valide": valide})
    return liste_resultats


class Page(Onglet):
    url_liste = "individu_medical_liste"
    description_saisie = "Saisissez toutes les informations et cliquez sur le bouton Enregistrer."
    objet_singulier = ""
    objet_pluriel = ""

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Médical"
        context['onglet_actif'] = "medical"
        context['boutons_liste_informations'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy("individu_infosmedicales_ajouter", kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.Get_idfamille()}), "icone": "fa fa-plus"},
        ]
        context['boutons_liste_vaccinations'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy("individu_vaccins_ajouter", kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.Get_idfamille()}), "icone": "fa fa-plus"},
        ]
        context['form_selection_medecin'] = Formulaire_medecin(idindividu=self.Get_idindividu())
        context['vaccins_obligatoires'] = RechercherVaccinsObligatoires(individu=context["individu"])
        context['pieces_manquantes'] = [{"label": "Fiche sanitaire", "valide": True}, {"label": "Fiche famille", "valide": False}]
        return context

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idindividu"] = self.Get_idindividu()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST and self.request.POST.get("page") == "info_medicale":
            url = "individu_infosmedicales_ajouter"
        if "SaveAndNew" in self.request.POST and self.request.POST.get("page") == "vaccin":
            url = "individu_vaccins_ajouter"
        return reverse_lazy(url, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)})



class Liste(Page, MultipleDatatableView):
    template_name = "fiche_individu/individu_medical.html"


    class informations_datatable_class(MyDatatable):
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            model = Information
            structure_template = MyDatatable.structure_template
            columns = ['intitule']
            ordering = ['intitule']
            footer = False

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            # Récupération idindividu et idfamille
            kwargs = kwargs["view"].kwargs
            # Ajoute l'id de la ligne
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse("individu_infosmedicales_modifier", kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse("individu_infosmedicales_supprimer", kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)


    class vaccins_datatable_class(MyDatatable):
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            model = Vaccin
            structure_template = MyDatatable.structure_template
            columns = ['date', 'type_vaccin']
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date']
            footer = False

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            # Récupération idindividu et idfamille
            kwargs = kwargs["view"].kwargs
            # Ajoute l'id de la ligne
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse("individu_vaccins_modifier", kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse("individu_vaccins_supprimer", kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)

    datatable_classes = {
        'informations': informations_datatable_class,
        'vaccins': vaccins_datatable_class,
    }

    def get_informations_datatable_queryset(self):
        return Information.objects.filter(individu=self.Get_idindividu())

    def get_vaccins_datatable_queryset(self):
        return Vaccin.objects.filter(individu=self.Get_idindividu())

    def get_datatables(self, only=None):
        datatables = super(Liste, self).get_datatables(only)
        return datatables





class Ajouter_infomedicale(Page, crud.Ajouter):
    form_class = Formulaire_info_medicale
    model = Information
    template_name = "fiche_individu/individu_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Informations personnelles"
        context['onglet_actif'] = "medical"
        return context


class Modifier_infomedicale(Page, crud.Modifier):
    form_class = Formulaire_info_medicale
    model = Information
    template_name = "fiche_individu/individu_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Informations personnelles"
        context['onglet_actif'] = "medical"
        return context


class Supprimer_infomedicale(Page, crud.Supprimer):
    form_class = Formulaire_info_medicale
    model = Information
    template_name = "fiche_individu/individu_delete.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Informations personnelles"
        context['onglet_actif'] = "medical"
        return context


class Ajouter_vaccin(Page, crud.Ajouter):
    form_class = Formulaire_vaccin
    model = Vaccin
    template_name = "fiche_individu/individu_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Vaccinations"
        context['onglet_actif'] = "medical"
        return context


class Modifier_vaccin(Page, crud.Modifier):
    form_class = Formulaire_vaccin
    model = Vaccin
    template_name = "fiche_individu/individu_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Vaccinations"
        context['onglet_actif'] = "medical"
        return context


class Supprimer_vaccin(Page, crud.Supprimer):
    form_class = Formulaire_vaccin
    model = Vaccin
    template_name = "fiche_individu/individu_delete.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Vaccinations"
        context['onglet_actif'] = "medical"
        return context
