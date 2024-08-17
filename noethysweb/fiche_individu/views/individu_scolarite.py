# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Scolarite, Individu, Classe, NiveauScolaire
from fiche_individu.forms.individu_scolarite import Formulaire
from fiche_individu.views.individu import Onglet
from django.http import HttpResponse
from django.template import Template, RequestContext
from core.utils import utils_dates
from django.db.models import Q



def Get_classes(request):
    idecole = request.POST.get('idecole')
    date_debut = request.POST.get("date_debut")
    date_fin = request.POST.get("date_fin")

    # Formatage des dates
    date_debut = utils_dates.ConvertDateFRtoDate(date_debut)
    date_fin = utils_dates.ConvertDateFRtoDate(date_fin)

    if idecole != "":
        classes = Classe.objects.filter(ecole_id=idecole, date_debut__lte=date_fin, date_fin__gte=date_debut).order_by('nom')
    else:
        classes = []
    if len(classes) == 0:
        resultat = ""
    else:
        html = """
        <option value="">---------</option>
        {% for classe in classes %}
            <option value="{{ classe.pk }}">{{ classe.nom }} (Du {{ classe.date_debut }} au {{ classe.date_fin }})</option>
        {% endfor %}
        """
        context = {'classes': classes}
        resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)


def Get_niveaux(request):
    idclasse = request.POST.get('idclasse')
    if idclasse != "":
        niveaux = Classe.objects.get(pk=idclasse).niveaux.order_by('ordre')
    else:
        niveaux = []
    if len(niveaux) == 0:
        resultat = ""
    elif len(niveaux) == 1:
        html = """<option value="{{ niveau.pk }}">{{ niveau.nom }}</option>"""
        context = {'niveau': niveaux[0]}
        resultat = Template(html).render(RequestContext(request, context))
    else:
        html = """
        <option value="">---------</option>
        {% for niveau in niveaux %}
            <option value="{{ niveau.pk }}">{{ niveau.nom }}</option>
        {% endfor %}
        """
        context = {'niveaux': niveaux}
        resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)



class Page(Onglet):
    model = Scolarite
    url_liste = "individu_scolarite_liste"
    url_ajouter = "individu_scolarite_ajouter"
    url_modifier = "individu_scolarite_modifier"
    url_supprimer = "individu_scolarite_supprimer"
    description_liste = "Consultez et saisissez ici les étapes de scolarité de l'individu."
    description_saisie = "Saisissez toutes les informations concernant l'étape de scolarité et cliquez sur le bouton Enregistrer."
    objet_singulier = "une étape de scolarité"
    objet_pluriel = "des étapes de scolarité"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Scolarité"
        context['onglet_actif'] = "scolarite"
        if self.request.user.has_perm("core.individu_scolarite_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.Get_idfamille()}), "icone": "fa fa-plus"},
            ]
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.individu_scolarite_modifier"):
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
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idindividu': self.Get_idindividu(), 'idfamille': self.kwargs.get('idfamille', None)})



class Liste(Page, crud.Liste):
    model = Scolarite
    template_name = "fiche_individu/individu_liste.html"

    def get_queryset(self):
        return Scolarite.objects.select_related("ecole", "classe").prefetch_related("niveau").filter(Q(individu=self.Get_idindividu()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idscolarite', 'date_debut', 'date_fin', 'ecole__nom', 'classe__nom', 'niveau__abrege']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        ecole = columns.TextColumn("Ecole", sources=["ecole__nom"])
        classe = columns.TextColumn("Classe", sources=["classe__nom"])
        niveau = columns.TextColumn("Niveau", sources=["niveau__abrege"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idscolarite', 'date_debut', 'date_fin', 'ecole', 'classe', 'niveau']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

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


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_individu/individu_delete.html"
