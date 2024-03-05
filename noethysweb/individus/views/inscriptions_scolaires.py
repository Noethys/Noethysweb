# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Classe, Scolarite
from individus.forms.inscriptions_scolaires import Formulaire, Formulaire_ajouter_plusieurs
from fiche_individu.forms.individu_scolarite import Formulaire as Formulaire_scolarite
from django.contrib import messages
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Template, RequestContext
from core.views.mydatatableview import MyDatatable, columns, helpers



def Get_periodes(request):
    idecole = request.POST.get('idecole')
    resultat = ""
    if idecole:
        periodes = Classe.objects.values("date_debut", "date_fin").filter(ecole_id=idecole).annotate(nbre_classes=Count("pk")).order_by("date_debut")
        if periodes:
            html = """
            <option value="">---------</option>
            {% for periode in periodes %}
                <option value="{{ periode.date_debut|date:'Y-m-d' }}_{{ periode.date_fin|date:'Y-m-d' }}">Du {{ periode.date_debut|date:'d/m/Y' }} au {{ periode.date_fin|date:'d/m/Y' }} ({{ periode.nbre_classes }} classes)</option>
            {% endfor %}
            """
            context = {'periodes': periodes}
            resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)



def Get_classes(request):
    idecole = request.POST.get('idecole')
    periode = request.POST.get('periode')
    resultat = ""
    if idecole and periode:
        date_debut, date_fin = periode.split("_")
        classes = Classe.objects.filter(ecole_id=idecole, date_debut=date_debut, date_fin=date_fin).order_by("nom")
        if classes:
            html = """
            <option value="">---------</option>
            {% for classe in classes %}
                <option value="{{ classe.pk }}">{{ classe.nom }}</option>
            {% endfor %}
            """
            context = {'classes': classes}
            resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)



def Get_inscrits(request):
    idclasse = request.POST.get('idclasse')
    resultat = ""
    if idclasse:
        scolarites = Scolarite.objects.select_related('individu', 'niveau').filter(classe_id=idclasse).order_by("individu__nom", "individu__prenom")
        if scolarites:
            html = """
            {% for scolarite in scolarites %}
            <tr><td><div class="form-inline">
                <input name="inscrits" type="checkbox" class="check_item" value="{{ scolarite.pk }}">
                <span style="margin-left: 4px;margin-right:20px;">{{ scolarite.individu.Get_nom }} ({{ scolarite.niveau.abrege }})</span>
            </div></td></tr>
            {% endfor %}
            """
            context = {'scolarites': scolarites}
            resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)


class Page(crud.Page):
    model = Scolarite
    url_liste = "inscriptions_scolaires_liste"
    url_ajouter = "inscriptions_scolaires_ajouter"
    url_ajouter_plusieurs = "inscriptions_scolaires_ajouter_plusieurs"
    url_modifier = "inscriptions_scolaires_modifier"
    url_supprimer = "inscriptions_scolaires_supprimer"
    url_supprimer_plusieurs = "inscriptions_scolaires_plusieurs"
    description_liste = "Saisissez ici les étapes de scolarité de l'individu."
    description_saisie = "Saisissez toutes les informations concernant l'étape de scolarité et cliquez sur le bouton Enregistrer."
    objet_singulier = "une étape de scolarité"
    objet_pluriel = "des inscriptions scolaires"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Scolarité"
        context['onglet_actif'] = "scolarite"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(idclasse=self.Get_idclasse(), request=self.request)
        return context

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        return reverse_lazy(self.url_liste, kwargs={'idclasse': self.Get_idclasse()})

    def Get_idclasse(self):
        return self.kwargs.get("idclasse", 0)

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idclasse"] = self.Get_idclasse()
        return form_kwargs



class Liste(Page, crud.Liste):
    model = Scolarite
    template_name = "individus/inscriptions_scolaires.html"

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return HttpResponseRedirect(reverse_lazy(self.url_liste))
        if not form.cleaned_data.get("ecole") or not form.cleaned_data.get("periode") or not form.cleaned_data.get("classe"):
            messages.add_message(request, messages.ERROR, "Veuillez sélectionner une école, une période et une classe")
            return HttpResponseRedirect(reverse_lazy(self.url_liste))

        classe = form.cleaned_data.get("classe")
        return HttpResponseRedirect(reverse_lazy(self.url_liste, kwargs={'idclasse': classe.pk}))

    def get_queryset(self):
        return Scolarite.objects.select_related("individu", "niveau", "ecole", "classe").filter(Q(classe=self.Get_idclasse()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idclasse": self.Get_idclasse(), "listepk": "xxx"})
        context["active_checkbox"] = True
        if self.Get_idclasse():
            context['box_introduction'] = "Vous pouvez ajouter ici un ou plusieurs individus dans la classe sélectionnée."
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idclasse': self.Get_idclasse()}), "icone": "fa fa-plus"},
                {"label": "Ajouter plusieurs individus", "classe": "btn btn-default", "href": reverse_lazy(self.url_ajouter_plusieurs, kwargs={'idclasse': self.Get_idclasse()}), "icone": "fa fa-plus"},
            ]
        else:
            context['box_introduction'] = "Vous devez sélectionner une classe dans le cadre Paramètres pour pouvoir ajouter un ou plusieurs individus."

        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", 'idscolarite', 'date_debut', 'date_fin', 'ecole__nom', 'classe__nom', 'niveau__abrege']
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nom = columns.TextColumn("Nom", sources=["individu__nom"])
        prenom = columns.TextColumn("Prénom", sources=["individu__prenom"])
        date_naiss = columns.TextColumn("Date naiss.", sources=["individu__date_naiss"], processor=helpers.format_date('%d/%m/%Y'))
        niveau = columns.TextColumn("Niveau", sources=["niveau__abrege"])
        ville_resid = columns.TextColumn("Ville de résidence", sources=["individu__ville_resid"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idscolarite", "nom", "prenom", "date_naiss", "date_debut", "date_fin", "niveau", "ville_resid"]
            hidden_columns = ["ville_resid"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["nom", "prenom"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idclasse dans les boutons d'actions """
            view = kwargs["view"]
            # Récupère l'idclasse
            kwargs = view.kwargs
            # Ajoute l'id de la ligne
            kwargs["pk"] = instance.pk
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
            ]
            return self.Create_boutons_actions(html)



class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire_scolarite


class Ajouter_plusieurs(Page, crud.Ajouter):
    form_class = Formulaire_ajouter_plusieurs

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        classe = Classe.objects.get(pk=self.kwargs["idclasse"])
        context['box_titre'] = "Ajouter plusieurs inscriptions scolaires"
        context["idclasse"] = self.kwargs["idclasse"]
        context['box_introduction'] = "Vous pouvez inscrire ici plusieurs individus dans la classe %s. Commencez par sélectionner un niveau puis récupérez la liste des inscrits d'une autre classe en sélectionnant une classe existante. Enfin, cochez les individus à inscrire dans la classe et cliquez sur Enregistrer." % classe.nom
        return context

    def form_valid(self, form):
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        if not form.cleaned_data.get("inscrits"):
            messages.add_message(self.request, messages.ERROR, "Vous devez cocher au moins un individu")
            return self.render_to_response(self.get_context_data(form=form))

        # Récupération des paramètres de l'inscription
        niveau = form.cleaned_data.get("niveau")
        classe = Classe.objects.get(pk=form.cleaned_data.get("idclasse"))
        inscrits = [int(idscolarite) for idscolarite in form.cleaned_data.get("inscrits").split(";")]

        # Enregistrement des scolarités
        nbre_inscriptions_succes = 0
        for idscolarite in inscrits:
            individu = Scolarite.objects.select_related('individu').get(pk=idscolarite).individu
            if Scolarite.objects.filter(individu_id=individu.pk, date_debut__lte=classe.date_fin, date_fin__gte=classe.date_debut).exists():
                messages.add_message(self.request, messages.ERROR, "Inscription impossible : %s est déjà inscrit sur une classe sur cette période." % individu.Get_nom())
            else:
                Scolarite.objects.create(date_debut=classe.date_debut, date_fin=classe.date_fin, classe=classe, ecole=classe.ecole,
                                         individu_id=individu.pk, niveau=niveau)
                nbre_inscriptions_succes += 1

        messages.add_message(self.request, messages.SUCCESS, "%d inscriptions scolaires enregistrées" % nbre_inscriptions_succes)
        return HttpResponseRedirect(self.get_success_url())



class Modifier(Page, crud.Modifier):
    form_class = Formulaire_scolarite

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        scolarite = Scolarite.objects.get(pk=self.kwargs["pk"])
        context['box_introduction'] = "Vous pouvez modifier ici l'étape de scolarité de %s :" % scolarite.individu.Get_nom()
        return context


class Supprimer(Page, crud.Supprimer):
    pass


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    def get_success_url(self):
        return reverse_lazy(self.url_liste, kwargs={"idclasse": self.kwargs["idclasse"]})
