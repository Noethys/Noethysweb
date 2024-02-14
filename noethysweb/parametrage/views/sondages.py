# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.views.generic import TemplateView
from django.db.models import Count
from crispy_forms.utils import render_crispy_form
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import Sondage, SondagePage, SondageQuestion
from parametrage.forms.sondages import Formulaire_sondage, Formulaire_page, Formulaire_question


def Get_form_page(request):
    # Récupération des données
    idsondage = int(request.POST.get("idsondage", 0))
    idpage = int(request.POST.get("idpage", 0))
    page = SondagePage.objects.get(pk=idpage) if idpage else None

    # Création et rendu html du formulaire
    form = Formulaire_page(request=request, idsondage=idsondage, instance=page)
    return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})


def Valid_form_page(request):
    # Importation de la page si c'est une modification
    page = SondagePage.objects.get(pk=int(request.POST["idpage"])) if request.POST.get("idpage", None) != "None" else None

    # Vérification du form
    form = Formulaire_page(request.POST, request=request, idsondage=int(request.POST["sondage"]), instance=page)
    if not form.is_valid():
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in form.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)

    instance = form.save()
    return JsonResponse({"succes": True, "id_page": instance.pk, "titre_page": instance.titre, "nouvelle_page": page == None})


def Supprimer_page(request):
    page = SondagePage.objects.get(pk=int(request.POST.get("idpage", 0)))
    page.delete()
    return JsonResponse({"success": True})


def Get_form_question(request):
    # Récupération des données
    idpage = int(request.POST.get("idpage", 0))
    idquestion = int(request.POST.get("idquestion", 0))
    question = SondageQuestion.objects.get(pk=idquestion) if idquestion else None

    # Création et rendu html du formulaire
    form = Formulaire_question(request=request, idpage=idpage, instance=question)
    return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})


def Valid_form_question(request):
    # Importation de la question si c'est une modification
    question = SondageQuestion.objects.get(pk=int(request.POST["idquestion"])) if request.POST.get("idquestion", None) != "None" else None

    # Vérification du form
    form = Formulaire_question(request.POST, request=request, idpage=int(request.POST["page"]), instance=question)
    if not form.is_valid():
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in form.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)

    instance = form.save()
    return JsonResponse({"succes": True, "id_page": instance.page_id, "id_question": instance.pk, "titre_question": instance.label, "nouvelle_question": question == None})


def Supprimer_question(request):
    question = SondageQuestion.objects.get(pk=int(request.POST.get("idquestion", 0)))
    question.delete()
    return JsonResponse({"success": True})


def Reorganiser(request):
    donnee = request.POST.get("donnee")
    nouvel_ordre = json.loads(request.POST.get("nouvel_ordre"))
    idsondage = int(request.POST.get("idsondage"))

    if donnee == "page":
        dict_pages = {page.pk:page for page in SondagePage.objects.filter(sondage_id=idsondage)}
        for index_page, id_page in enumerate(nouvel_ordre, start=1):
            page = dict_pages[int(id_page.replace("page_", ""))]
            if page.ordre != index_page:
                page.ordre = index_page
                page.save()

    if donnee == "question":
        dict_questions = {question.pk:question for question in SondageQuestion.objects.filter(page__sondage_id=idsondage)}
        for id_page, liste_questions in nouvel_ordre:
            for index_question, id_question in enumerate(liste_questions, start=1):
                question = dict_questions[int(id_question.replace("question_", ""))]
                if question.ordre != index_question or question.page_id != id_page:
                    question.page_id = id_page
                    question.ordre = index_question
                    question.save()

    return JsonResponse({"success": True})


class Page(crud.Page):
    model = Sondage
    url_liste = "sondages_liste"
    url_ajouter = "sondages_ajouter"
    url_modifier = "sondages_modifier"
    url_supprimer = "sondages_supprimer"
    url_consulter = "sondages_consulter"
    description_liste = "Voici ci-dessous la liste des formulaires. Vous pouvez créer ici des sondages, enquêtes ou questionnaires qui apparaîtront sur le portail. Une fois le formulaire créé, vous devrez paramétrer un article (Menu Paramétrage > Portail > Articles) auquel vous associerez le formulaire afin de le faire apparaître sur le portail."
    description_saisie = "Saisissez toutes les informations concernant le formulaire à créer et cliquez sur le bouton Enregistrer."
    objet_singulier = "un formulaire"
    objet_pluriel = "des formulaires"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
        {"label": "Consulter les réponses", "classe": "btn btn-default", "href": reverse_lazy("sondages_reponses_resume"), "icone": "fa fa-pie-chart"},
    ]


class Liste(Page, crud.Liste):
    model = Sondage

    def get_queryset(self):
        return Sondage.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure()).annotate(nbre_repondants=Count("sondagerepondant"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idsondage", "titre", "public"]
        public = columns.TextColumn("Public", sources="public", processor="Get_public")
        nbre_repondants = columns.TextColumn("Réponses", sources=["nbre_repondants"])
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idsondage", "titre", "public", "nbre_repondants", "actions"]

        def Get_public(self, instance, **kwargs):
            return instance.get_public_display()

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_consulter, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire_sondage

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.object.idsondage})


class Modifier(Page, crud.Modifier):
    form_class = Formulaire_sondage

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['pk']})


class Supprimer(Page, crud.Supprimer):
    pass


class Consulter(Page, TemplateView):
    template_name = "parametrage/sondages.html"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Consulter un formulaire"
        context['box_introduction'] = "Vous pouvez ici ajouter des questions au formulaire ou modifier les paramètres du formulaire. Pour ajouter une page, cliquez sur + Ajouter une page, puis dans le cadre de la page, cliquez sur + pour ajouter une question."
        context['onglet_actif'] = "sondages_liste"

        # Importation du sondage
        context['sondage'] = Sondage.objects.get(pk=self.kwargs["pk"])

        # Importation des questions et des pages
        pages = {page: [] for page in SondagePage.objects.filter(sondage_id=self.kwargs["pk"]).order_by("ordre")}
        for question in SondageQuestion.objects.select_related("page").filter(page__sondage_id=self.kwargs["pk"]).order_by("page__ordre", "ordre"):
            pages[question.page].append({"id_question": question.pk, "label_question": question.label})
        context["donnees"] = json.dumps([{"id_page": page.pk, "titre_page": page.titre, "questions": pages[page]} for page in sorted(list(pages.keys()), key=lambda x: x.ordre)])
        return context
