# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Aide, CombiAide
from fiche_famille.forms.famille_aides import Formulaire, FORMSET_COMBI, Formulaire_selection_activite
from fiche_famille.views.famille import Onglet


class Page(Onglet):
    model = Aide
    url_liste = "famille_aides_liste"
    url_ajouter = "famille_aides_ajouter"
    url_modifier = "famille_aides_modifier"
    url_supprimer = "famille_aides_supprimer"
    description_liste = "Consultez et saisissez ici les aides de la famille."
    description_saisie = "Saisissez toutes les informations concernant l'aide et cliquez sur le bouton Enregistrer."
    objet_singulier = "une aide"
    objet_pluriel = "des aides"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Aides"
        context['onglet_actif'] = "aides"
        if self.request.user.has_perm("core.famille_aides_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
            ]
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.famille_aides_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idfmille au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        form_kwargs["idactivite"] = self.kwargs.get("idactivite", None)
        form_kwargs["idmodele"] = self.kwargs.get("idmodele", None)
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})



class Liste(Page, crud.Liste):
    model = Aide
    template_name = "fiche_famille/famille_liste.html"

    def get_queryset(self):
        return Aide.objects.select_related("caisse", "activite", "activite__structure").prefetch_related("individus").filter(Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["idaide", "date_debut", "date_fin", "caisse__nom", "activite__nom"]
        beneficiaires = columns.TextColumn("Bénéficiaires", sources=None, processor='Get_beneficiaires')
        caisse = columns.TextColumn("Caisse", sources=["caisse__nom"])
        activite = columns.TextColumn("Activité", sources=["activite__nom"])
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idaide", 'date_debut', 'date_fin', 'beneficiaires', 'caisse', 'activite']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_beneficiaires(self, instance, *args, **kwargs):
            return ", ".join([individu.Get_nom() for individu in instance.individus.all()])

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            if not view.request.user.has_perm("core.famille_aides_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            if instance.activite.structure in view.request.user.structures.all():
                # Affiche les boutons d'action si l'utilisateur est associé à l'aide
                html = [
                    self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                    self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                ]
            else:
                # Afficher que l'accès est interdit
                html = ["<span class='text-red'><i class='fa fa-minus-circle margin-r-5' title='Accès non autorisé'></i>Accès interdit</span>",]
            return self.Create_boutons_actions(html)



class ClasseCommune(Page):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"

    def get_context_data(self, *args, **kwargs):
        context_data = super(ClasseCommune, self).get_context_data(**kwargs)
        context_data["modeles"] = Aide.objects.filter(famille__isnull=True)

        # Traitement du Combi aides
        if "idactivite" in self.kwargs:
            activite = self.kwargs["idactivite"]
        else:
            activite = self.object.activite.idactivite

        if self.request.POST:
            context_data['formset_combi'] = FORMSET_COMBI(self.request.POST, instance=self.object, form_kwargs={'activite': activite})
        else:
            context_data['formset_combi'] = FORMSET_COMBI(instance=self.object, form_kwargs={'activite': activite})

            # Importation du modèle d'aide
            idmodele = self.kwargs.get("idmodele", None)
            if idmodele:
                modele_aide = Aide.objects.get(pk=idmodele)
                combinaisons = CombiAide.objects.filter(aide=modele_aide)
                context_data['formset_combi'].initial = [{"montant": combi.montant, "unites": combi.unites.all()} for combi in combinaisons]
                context_data['formset_combi'].extra = max(combinaisons.count() - 1, 0)

        return context_data

    def form_valid(self, form):
        if "idactivite" in self.kwargs:
            activite = self.kwargs["idactivite"]
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



class Ajouter(ClasseCommune, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Modifier(ClasseCommune, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"


class Selection_activite(Onglet, TemplateView):
    template_name = "fiche_famille/famille_edit.html"

    def get_context_data(self, **kwargs):
        context = super(Selection_activite, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Aides"
        context['box_introduction'] = "Vous devez commencer par sélectionner l'activité associée à l'aide que vous souhaitez créer. Vous pouvez éventuellement sélectionner un modèle d'aide existant à appliquer."
        context['onglet_actif'] = "aides"
        context['form'] = Formulaire_selection_activite(request=self.request)
        return context

    def post(self, request, **kwargs):
        idactivite = int(request.POST.get("activite"))
        idmodele = int(request.POST.get("modele_aide")) if request.POST.get("modele_aide") else 0
        return HttpResponseRedirect(reverse_lazy("famille_aides_configurer", args=(self.Get_idfamille(), idactivite, idmodele)))

    def Get_annuler_url(self):
        return reverse_lazy("famille_aides_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})
