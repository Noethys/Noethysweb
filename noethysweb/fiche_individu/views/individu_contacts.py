# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ContactUrgence
from fiche_individu.forms.individu_contacts import Formulaire
from fiche_individu.forms.individu_contacts_importer import Formulaire as Formulaire_importer
from fiche_individu.views.individu import Onglet
from django.db.models import Q


class Page(Onglet):
    model = ContactUrgence
    url_liste = "individu_contacts_liste"
    url_ajouter = "individu_contacts_ajouter"
    url_modifier = "individu_contacts_modifier"
    url_supprimer = "individu_contacts_supprimer"
    description_liste = "Consultez et saisissez ici les contacts d'urgence et de sortie de l'individu."
    description_saisie = "Saisissez toutes les informations concernant le contact et cliquez sur le bouton Enregistrer."
    objet_singulier = "un contact d'urgence et de sortie"
    objet_pluriel = "des contacts d'urgence et de sortie"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Contacts d'urgence et de sortie"
        context['onglet_actif'] = "contacts"
        if self.request.user.has_perm("core.individu_contacts_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
                {"label": "Importer depuis une autre fiche", "classe": "btn btn-default", "href": reverse_lazy("individu_contacts_importer", kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-download"},
            ]
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.individu_contacts_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idindividu"] = self.Get_idindividu()
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)})



class Liste(Page, crud.Liste):
    model = ContactUrgence
    template_name = "fiche_individu/individu_liste.html"

    def get_queryset(self):
        return ContactUrgence.objects.filter(Q(individu=self.Get_idindividu()) & Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcontact", "nom", "prenom", "rue_resid", "tel_domicile", "tel_mobile", "tel_travail", "autorisation_sortie", "autorisation_appel"]
        tel_domicile = columns.TextColumn("Tél domicile", processor="Get_tel_domicile")
        tel_mobile = columns.TextColumn("Tél portable", processor="Get_tel_mobile")
        tel_travail = columns.TextColumn("Tél pro.", processor="Get_tel_travail")
        lien = columns.TextColumn("Lien", processor="Get_lien")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        autorisations = columns.TextColumn("Autorisations", sources=["autorisation_sortie", "autorisation_appel"], processor='Get_autorisations')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcontact", "nom", "prenom", "tel_domicile", "tel_mobile", "tel_travail", "lien", "autorisations", "actions"]
            ordering = ['nom', 'prenom']
            labels = {
                "lien": "Lien",
            }

        def Get_tel_domicile(self, instance, *args, **kwargs):
            return instance.tel_domicile

        def Get_tel_mobile(self, instance, *args, **kwargs):
            return instance.tel_mobile

        def Get_tel_travail(self, instance, *args, **kwargs):
            return instance.tel_travail

        def Get_lien(self, instance, *args, **kwargs):
            return instance.lien

        def Get_autorisations(self, instance, *args, **kwargs):
            return instance.Get_autorisations()

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            if not view.request.user.has_perm("core.individu_scolarite_modifier"):
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
    template_name = "fiche_individu/individu_edit.html"
    mode = "fiche_individu"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"
    mode = "fiche_individu"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_individu/individu_delete.html"


class Importer(Page, TemplateView):
    form_class = Formulaire_importer
    template_name = "fiche_individu/individu_edit.html"
    mode = "fiche_individu"

    def get_context_data(self, **kwargs):
        context = super(Importer, self).get_context_data(**kwargs)
        context['box_introduction'] = "Cochez le ou les contacts à importer et cliquez sur le bouton Importer."
        context['form'] = Formulaire_importer(idfamille=self.kwargs['idfamille'], idindividu=self.kwargs['idindividu'], request=self.request)
        return context

    def post(self, request, **kwargs):
        # Validation du form
        form = Formulaire_importer(request.POST, idfamille=self.kwargs['idfamille'], idindividu=self.kwargs['idindividu'], request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Importation des contacts
        liste_txt = form.cleaned_data.get("contacts", "")
        if liste_txt:
            liste_idcontact = liste_txt.split(";")
            for contact in ContactUrgence.objects.filter(pk__in=[int(idcontact) for idcontact in liste_idcontact]):
                contact.pk = None
                contact.individu_id = self.kwargs['idindividu']
                contact.save()

        return HttpResponseRedirect(reverse_lazy("individu_contacts_liste", args=(self.kwargs['idfamille'], self.kwargs['idindividu'])))
