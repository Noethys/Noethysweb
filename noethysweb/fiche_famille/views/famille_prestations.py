# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from decimal import Decimal
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum
from django.template import Template, RequestContext
from django.http import HttpResponse, JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Prestation, Tarif, Inscription, Consommation
from fiche_famille.forms.famille_prestations import Formulaire, FORMSET_DEDUCTIONS
from fiche_famille.views.famille import Onglet
from core.utils import utils_texte


def Supprimer_consommation(request):
    """ Supprime les ou une consommation associée à la prestation """
    idconso = int(request.POST.get("idconso"))
    idprestation = int(request.POST.get("idprestation"))
    if idconso == 0:
        # Suppression de toutes les consommations associées à la prestation
        for conso in Consommation.objects.filter(prestation_id=idprestation).order_by("date"):
            if conso.etat in ("present", "absenti", "absentj"):
                return JsonResponse({"erreur": "Vous ne pouvez pas supprimer la consommation ID%d car elle est déjà pointée" % conso.pk}, status=401)
            conso.delete()
    else:
        # Suppression de la consommation sélectionnée
        conso = Consommation.objects.get(pk=idconso)
        if conso.etat in ("present", "absenti", "absentj"):
            return JsonResponse({"erreur": "Vous ne pouvez pas supprimer une consommation déjà pointée"}, status=401)
        conso.delete()
    return JsonResponse({"resultat": True})


def Get_activites(request):
    """ Renvoie la liste des activités pour un individu donné """
    idindividu = request.POST.get('idindividu')
    idfamille = request.POST.get('idfamille')
    if not idindividu or not idfamille:
        resultat = ""
    else:
        activites = list({inscription.activite: True for inscription in Inscription.objects.select_related("activite").filter(individu_id=idindividu, famille_id=idfamille).order_by("date_debut")}.keys())
        html = """
        <option value="">---------</option>
        {% for activite in activites %}
            <option value="{{ activite.pk }}">{{ activite.nom }}</option>
        {% endfor %}
        """
        context = {'activites': activites}
        resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)


def Get_tarifs(request):
    """ Renvoie la liste des tarifs pour une activité donnée """
    idactivite = request.POST.get('idactivite')
    idcategorie_tarif = request.POST.get('idcategorie_tarif')
    masquer_evenements = request.POST.get('masquer_evenements') == "oui"
    if not idactivite or not idcategorie_tarif:
        resultat = ""
    else:
        conditions = Q(activite_id=idactivite, categories_tarifs=idcategorie_tarif)
        if masquer_evenements:
            conditions &= Q(evenement__isnull=True)
        tarifs = Tarif.objects.select_related('nom_tarif').filter(conditions).order_by("date_debut")
        html = """
        <option value="">---------</option>
        {% for tarif in tarifs %}
            <option value="{{ tarif.pk }}">{{ tarif }} - {{ tarif.nom_tarif.nom }} - à partir du {{ tarif.date_debut|date:'d/m/Y' }}</option>
        {% endfor %}
        """
        context = {'tarifs': tarifs}
        resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)


class Page(Onglet):
    model = Prestation
    url_liste = "famille_prestations_liste"
    url_ajouter = "famille_prestations_ajouter"
    url_modifier = "famille_prestations_modifier"
    url_supprimer = "famille_prestations_supprimer"
    url_supprimer_plusieurs = "famille_prestations_supprimer_plusieurs"
    description_liste = "Vous pouvez consulter ici les prestations de la famille. Il s'agit généralement de prestations générées automatiquement mais vous pouvez également cliquer sur le bouton Ajouter pour créer une prestation manuelle."
    description_saisie = "Saisissez toutes les informations concernant la prestation et cliquez sur le bouton Enregistrer."
    objet_singulier = "une prestation"
    objet_pluriel = "des prestations"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Prestations"
        context['onglet_actif'] = "prestations"
        if self.request.user.has_perm("core.famille_prestations_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
                {"label": "Ajouter depuis un modèle", "classe": "btn btn-default", "href": reverse_lazy("famille_prestations_selection_modele", kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
            ]
        context['bouton_supprimer'] = self.request.user.has_perm("core.famille_prestations_modifier")
        # Ajout l'idfamille à l'URL de suppression groupée
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'idfamille': self.kwargs.get('idfamille', None), "listepk": "xxx"})
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.famille_prestations_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idindividu au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})



class Liste(Page, crud.Liste):
    model = Prestation
    template_name = "fiche_famille/famille_liste.html"

    def get_queryset(self):
        return Prestation.objects.select_related("individu", "activite", "activite__structure", "facture").annotate(ventile=Sum("ventilation__montant")).filter(Q(famille__pk=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idprestation', 'date', 'individu__nom', 'activite__nom', 'label', 'montant']
        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        facture = columns.TextColumn("Facture", sources=["facture__numero"])
        activite = columns.TextColumn("Activité", sources=['activite__nom'])
        label = columns.TextColumn("Label", sources=['label'])
        individu = columns.TextColumn("Individu", sources=["individu__nom", "individu__prenom"], processor="Formate_individu")
        montant = columns.TextColumn("Montant", sources=["montant"], processor='Formate_montant')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idprestation', 'date', 'individu', 'activite', 'label', 'quantite', 'montant', 'facture']
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
                'montant': "Formate_montant_standard",
            }
            ordering = ['date']
            hidden_columns = ['quantite']

        def Formate_montant(self, instance, **kwargs):
            ventile = Decimal(instance.ventile or 0.0)
            if ventile == Decimal(0):
                classe = "text-red"
                title = "Prestation impayée"
            elif ventile == instance.montant:
                classe = "text-green"
                title = "Prestation totalement payée"
            else:
                classe = "text-orange"
                title = "Prestation partiellement payée (%s)" % utils_texte.Formate_montant(ventile)
            return "<span title='%s' class='%s'>%s</span>" % (title, classe, utils_texte.Formate_montant(instance.montant))

        def Formate_individu(self, instance, **kwargs):
            return instance.individu.Get_nom() if instance.individu else ""

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            if not view.request.user.has_perm("core.famille_prestations_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            if not instance.activite or instance.activite.structure in view.request.user.structures.all():
                # Affiche les boutons d'action si l'utilisateur est associé à la prestation
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
    template_name = "parametrage/famille_edit.html"

    def get_context_data(self, *args, **kwargs):
        context_data = super(ClasseCommune, self).get_context_data(**kwargs)

        # Traitement du Combi aides
        if self.request.POST:
            context_data['formset_combi'] = FORMSET_DEDUCTIONS(self.request.POST, instance=self.object)
        else:
            context_data['formset_combi'] = FORMSET_DEDUCTIONS(instance=self.object)

        return context_data

    def form_valid(self, form):
        formset_combi = FORMSET_DEDUCTIONS(self.request.POST, instance=self.object)
        if formset_combi.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde de l'aide
        self.object = form.save()

        # Sauvegarde des combi
        if formset_combi.is_valid():
            for formline in formset_combi.forms:
                if formline.cleaned_data.get('DELETE') and form.instance.pk and formline.instance.pk :
                    formline.instance.delete()
                if formline.cleaned_data.get('DELETE') == False:
                    instance = formline.save(commit=False)
                    instance.prestation = self.object
                    instance.famille = self.object.famille
                    instance.date = self.object.date
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


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "fiche_famille/famille_delete.html"
