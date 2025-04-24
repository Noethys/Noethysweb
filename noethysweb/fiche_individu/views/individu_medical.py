# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from datatableview.views import MultipleDatatableView
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Individu, Information, Medecin, Vaccin
from fiche_individu.forms.individu_information import Formulaire as Formulaire_information
from fiche_individu.forms.individu_vaccin import Formulaire as Formulaire_vaccin
from fiche_individu.forms.individu_medecin import Formulaire as Formulaire_medecin
from fiche_individu.forms.individu_medecin_ajouter import Formulaire as Formulaire_medecin_ajouter
from fiche_individu.views.individu import Onglet
from individus.utils import utils_vaccinations


def Ajouter_medecin(request):
    """ Ajouter un médecin dans la liste de choix """
    valeurs = json.loads(request.POST.get("valeurs"))

    # Formatage des champs
    valeurs["nom"] = valeurs["nom"].upper()
    valeurs["prenom"] = valeurs["prenom"].title()
    valeurs["rue_resid"] = valeurs["rue_resid"].title()
    valeurs["ville_resid"] = valeurs["ville_resid"].upper()

    # Vérification des données saisies
    form = Formulaire_medecin_ajouter(valeurs)
    if not form.is_valid():
        messages_erreurs = ["%s : %s" % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ", ".join(messages_erreurs)}, status=401)

    # Sauvegarde du médecin
    medecin = form.save()

    # Attribution du médecin à l'individu
    individu = Individu.objects.get(pk=int(valeurs["idindividu"]))
    individu.medecin = medecin
    individu.save()

    return JsonResponse({"id": medecin.pk, "nom": medecin.Get_nom(afficher_ville=True)})


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
        if self.request.user.has_perm("core.individu_medical_modifier"):
            context['boutons_liste_informations'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy("individu_informations_ajouter", kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.Get_idfamille()}), "icone": "fa fa-plus"},
            ]
            context['boutons_liste_vaccinations'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy("individu_vaccinations_ajouter", kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.Get_idfamille()}), "icone": "fa fa-plus"},
            ]
        context['form_selection_medecin'] = Formulaire_medecin(idindividu=self.Get_idindividu())
        context['form_ajout_medecin'] = Formulaire_medecin_ajouter(idindividu=self.Get_idindividu())
        context['vaccins_obligatoires'] = utils_vaccinations.Get_vaccins_obligatoires_individu(individu=context["individu"])
        context['pieces_manquantes'] = [{"label": "Fiche sanitaire", "valide": True}, {"label": "Fiche famille", "valide": False}]
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.individu_medical_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idindividu"] = self.Get_idindividu()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST and self.request.POST.get("page") == "info_medicale":
            url = "individu_informations_ajouter"
        if "SaveAndNew" in self.request.POST and self.request.POST.get("page") == "vaccin":
            url = "individu_vaccinations_ajouter"
        return reverse_lazy(url, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)})



class Liste(Page, MultipleDatatableView):
    template_name = "fiche_individu/individu_medical.html"

    class informations_datatable_class(MyDatatable):
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        intitule = columns.TextColumn("Intitulé", processor="Get_intitule")
        categorie = columns.CompoundColumn("Catégorie", sources=['categorie__nom'])

        class Meta:
            model = Information
            structure_template = MyDatatable.structure_template
            columns = ['categorie', 'intitule']
            ordering = ['categorie', 'intitule']
            footer = False

        def Get_intitule(self, instance, *args, **kwargs):
            return instance.intitule

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            if not kwargs["view"].request.user.has_perm("core.individu_medical_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = kwargs["view"].kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse("individu_informations_modifier", kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse("individu_informations_supprimer", kwargs=kwargs)),
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
            if not kwargs["view"].request.user.has_perm("core.individu_medical_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = kwargs["view"].kwargs
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse("individu_vaccinations_modifier", kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse("individu_vaccinations_supprimer", kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)

    datatable_classes = {
        'informations': informations_datatable_class,
        'vaccins': vaccins_datatable_class,
    }

    def get_informations_datatable_queryset(self):
        return Information.objects.select_related("categorie").filter(individu=self.Get_idindividu())

    def get_vaccins_datatable_queryset(self):
        return Vaccin.objects.select_related("type_vaccin").filter(individu=self.Get_idindividu())

    def get_datatables(self, only=None):
        datatables = super(Liste, self).get_datatables(only)
        return datatables




class Ajouter_information(Page, crud.Ajouter):
    form_class = Formulaire_information
    model = Information
    template_name = "fiche_individu/individu_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Informations personnelles"
        context['onglet_actif'] = "medical"
        return context


class Modifier_information(Page, crud.Modifier):
    form_class = Formulaire_information
    model = Information
    template_name = "fiche_individu/individu_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Informations personnelles"
        context['onglet_actif'] = "medical"
        return context


class Supprimer_information(Page, crud.Supprimer):
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
    model = Vaccin
    template_name = "fiche_individu/individu_delete.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Vaccinations"
        context['onglet_actif'] = "medical"
        return context
