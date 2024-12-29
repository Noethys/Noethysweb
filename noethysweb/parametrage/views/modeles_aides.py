# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Aide
from parametrage.forms.modeles_aides import Formulaire, Formulaire_creation
from fiche_famille.forms.famille_aides import FORMSET_COMBI


class Page(crud.Page):
    model = Aide
    url_liste = "modeles_aides_liste"
    url_ajouter = "modeles_aides_creer"
    url_modifier = "modeles_aides_modifier"
    url_supprimer = "modeles_aides_supprimer"
    description_liste = "Voici ci-dessous la liste des modèles d'aides."
    description_saisie = "Saisissez toutes les informations concernant le modèle à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle d'aide"
    objet_pluriel = "des modèles d'aides"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]

    def get_context_data(self, *args, **kwargs):
        context_data = super(Page, self).get_context_data(**kwargs)

        # Traitement du Combi aides
        if getattr(self, "form_class", None) == Formulaire:
            if "activite" in self.kwargs:
                activite = self.kwargs["activite"]
            else:
                activite = self.object.activite.idactivite
            if self.request.POST:
                context_data['formset_combi'] = FORMSET_COMBI(self.request.POST, instance=self.object, form_kwargs={'activite': activite})
            else:
                context_data['formset_combi'] = FORMSET_COMBI(instance=self.object, form_kwargs={'activite': activite})

        return context_data

    def form_valid(self, form):
        if getattr(self, "verbe_action", None) == "Supprimer":
            return super().form_valid(form)

        if "activite" in self.kwargs:
            activite = self.kwargs["activite"]
        else:
            activite = self.object.activite.idactivite
        formset_combi = FORMSET_COMBI(self.request.POST, instance=self.object, form_kwargs={'activite': activite})
        if formset_combi.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde de l'aide
        self.object = form.save()

        # Sauvegarde des combi
        if formset_combi.is_valid():
            for formline in formset_combi.forms:
                if formline.cleaned_data.get('DELETE') and form.instance.pk:
                    formline.instance.delete()
                if formline.cleaned_data.get('DELETE') == False:
                    instance = formline.save(commit=False)
                    instance.aide = self.object
                    instance.save()
                    formline.save_m2m()

        return super().form_valid(form)


class Liste(Page, crud.Liste):
    model = Aide

    def get_queryset(self):
        return Aide.objects.select_related("activite").filter(self.Get_filtres("Q"), famille__isnull=True)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idaide", "nom", "activite__nom", "date_debut", "date_fin"]
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idaide", "nom", "activite", "date_debut", "date_fin", "actions"]
            ordering = ["nom"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }


class Creer(Page, crud.Ajouter):
    form_class = Formulaire_creation
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Creer, self).get_context_data(**kwargs)
        context['box_introduction'] = "Vous devez sélectionner une activité."
        return context

    def post(self, request, **kwargs):
        return HttpResponseRedirect(reverse_lazy("modeles_aides_ajouter", kwargs={"activite": request.POST.get("activite")}))


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["activite"] = self.kwargs.get("activite", None)
        return form_kwargs


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
