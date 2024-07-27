# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, copy
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Classe
from parametrage.forms.classes import Formulaire, Formulaire_dupliquer


def Dupliquer(request):
    """ Dupliquer des classes """
    # Validation du formulaire
    form = Formulaire_dupliquer(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["%s : %s" % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": messages_erreurs}, status=401)

    # Duplication des classes cochées
    for classe in Classe.objects.filter(pk__in=json.loads(request.POST["liste_classes"])):
        nouvelle_classe = copy.deepcopy(classe)
        nouvelle_classe.pk = None
        nouvelle_classe.date_debut = form.cleaned_data["date_debut"]
        nouvelle_classe.date_fin = form.cleaned_data["date_fin"]
        if form.cleaned_data["nom_ancien_texte"]:
            nouvelle_classe.nom = classe.nom.replace(form.cleaned_data["nom_ancien_texte"], form.cleaned_data["nom_nouveau_texte"])
        nouvelle_classe.save()
        nouvelle_classe.niveaux.set(classe.niveaux.all())

    return JsonResponse({"resultat": "ok"})


class Page(crud.Page):
    model = Classe
    url_liste = "classes_liste"
    url_ajouter = "classes_ajouter"
    url_modifier = "classes_modifier"
    url_supprimer = "classes_supprimer"
    url_supprimer_plusieurs = "classes_supprimer_plusieurs"
    description_liste = "Voici ci-dessous la liste des classes. Il est possible de dupliquer des classes existantes en les cochant dans la liste puis en cliquant sur le bouton Dupliquer."
    description_saisie = "Saisissez toutes les informations concernant la classe à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une classe"
    objet_pluriel = "des classes"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    template_name = "parametrage/classes.html"
    model = Classe

    def get_queryset(self):
        return Classe.objects.prefetch_related("niveaux").filter(self.Get_filtres("Q")).annotate(nbre_inscrits=Count("scolarite"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        context['active_checkbox'] = True
        context['boutons_coches'] = json.dumps([
            {"id": "bouton_dupliquer", "action": "action_classe(1)", "title": "Dupliquer", "label": "<i class='fa fa-copy margin-r-5'></i>Dupliquer"},
        ])
        context["form_dupliquer"] = Formulaire_dupliquer(request=self.request)
        return context

    class datatable_class(MyDatatable):
        filtres = ["idclasse", "nom", "ecole__nom", "date_debut", "date_fin"]
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        ecole = columns.TextColumn("Ecole", sources=["ecole__nom"])
        nbre_inscrits = columns.TextColumn("Elèves", sources="nbre_inscrits")
        niveaux = columns.TextColumn("Niveaux", sources=None, processor='Get_niveaux')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idclasse", "nom", "ecole", "date_debut", "date_fin", "nbre_inscrits", "niveaux"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_debut"]

        def Get_niveaux(self, instance, *args, **kwargs):
            return ", ".join([niveau.abrege for niveau in instance.niveaux.all()])


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
