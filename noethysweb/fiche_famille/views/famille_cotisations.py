# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.template import Template, RequestContext
from django.db.models import Max, Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Cotisation, TypeCotisation, UniteCotisation, Prestation, Quotient
from core.utils import utils_dates, utils_texte
from fiche_famille.forms.famille_cotisations import Formulaire
from fiche_famille.views.famille import Onglet
from cotisations.utils import utils_cotisations_manquantes


def On_change_type_cotisation(request):
    idtype_cotisation = request.POST.get('idtype_cotisation')
    if idtype_cotisation == "":
        return HttpResponse("")
    type_cotisation = TypeCotisation.objects.get(pk=idtype_cotisation)
    unites = UniteCotisation.objects.filter(type_cotisation=type_cotisation).order_by('date_debut')
    html = """
    <option value="">---------</option>
    {% for unite in unites %}
        <option value="{{ unite.pk }}" {% if unite.defaut %}selected{% endif %}>{{ unite.nom }}</option>
    {% endfor %}
    """
    context = {'unites': unites}
    resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)


def On_change_unite_cotisation(request):
    idunite_cotisation = request.POST.get('idunite_cotisation')
    idfamille = request.POST.get('idfamille')

    if idunite_cotisation == "":
        return JsonResponse({})

    unite_cotisation = UniteCotisation.objects.get(pk=idunite_cotisation)

    # Validité
    date_debut, date_fin = unite_cotisation.Get_dates_validite()

    # Label
    if unite_cotisation.label_prestation:
        label = unite_cotisation.label_prestation
    else:
        label = "%s - %s" % (unite_cotisation.type_cotisation.nom, unite_cotisation.nom)

    # Date de création
    date_creation_carte = datetime.date.today()

    # Numéro
    derniere_cotisation = Cotisation.objects.last()
    numero = derniere_cotisation.numero if derniere_cotisation and derniere_cotisation.numero else 0
    numero = utils_texte.Incrementer(numero)

    # Tarif
    montant = 0.0
    if unite_cotisation.tarifs:
        qf_famille = Quotient.objects.filter(famille_id=idfamille, date_debut__lte=datetime.date.today(), date_fin__gte=datetime.date.today()).first()
        liste_montants = []
        for ligne in unite_cotisation.tarifs.splitlines():
            tranches, montant_tarif = ligne.split("=")
            qf_min, qf_max = tranches.split("-")
            liste_montants.append(float(montant_tarif))
            if qf_famille and float(qf_min) <= qf_famille.quotient <= float(qf_max):
                montant = float(montant_tarif)
        if not qf_famille:
            montant = max(liste_montants)

    if unite_cotisation.montant:
        montant = unite_cotisation.montant

    # Renvoie les résultats
    dict_resultats = {
        "type": unite_cotisation.type_cotisation.type,
        "carte": unite_cotisation.type_cotisation.carte,
        "date_debut": utils_dates.ConvertDateToFR(date_debut),
        "date_fin": utils_dates.ConvertDateToFR(date_fin),
        "montant": montant,
        "label_prestation": label,
        "date_creation_carte": utils_dates.ConvertDateToFR(date_creation_carte),
        "numero": numero,
    }
    return JsonResponse(dict_resultats)



class Page(Onglet):
    model = Cotisation
    url_liste = "famille_cotisations_liste"
    url_ajouter = "famille_cotisations_ajouter"
    url_modifier = "famille_cotisations_modifier"
    url_supprimer = "famille_cotisations_supprimer"
    url_supprimer_plusieurs = "famille_cotisations_supprimer_plusieurs"
    description_liste = "Consultez et saisissez ici les adhésions de la famille."
    description_saisie = "Saisissez toutes les informations concernant l'adhésion et cliquez sur le bouton Enregistrer."
    objet_singulier = "une adhésion"
    objet_pluriel = "des adhésions"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        if not hasattr(self, "verbe_action"):
            context['box_titre'] = "Adhésions"
        context['onglet_actif'] = "cotisations"
        context['cotisations_manquantes'] = utils_cotisations_manquantes.Get_cotisations_manquantes(famille=context['famille'])
        if self.request.user.has_perm("core.famille_cotisations_modifier"):
            context['boutons_liste'] = [
                {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'idfamille': self.kwargs.get('idfamille', None)}), "icone": "fa fa-plus"},
            ]
        context['bouton_supprimer'] = self.request.user.has_perm("core.famille_cotisations_modifier")
        # Ajout l'idfamille à l'URL de suppression groupée
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={'idfamille': self.kwargs.get('idfamille', None), "listepk": "xxx"})
        return context

    def test_func_page(self):
        if getattr(self, "verbe_action", None) in ("Ajouter", "Modifier", "Supprimer") and not self.request.user.has_perm("core.famille_cotisations_modifier"):
            return False
        return True

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idfmille au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        form_kwargs["idtype_cotisation"] = self.kwargs.get("idtype_cotisation", None)
        form_kwargs["idindividu"] = self.kwargs.get("idindividu", None)
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def form_valid(self, form):
        if getattr(self, "verbe_action", None) == "Supprimer":
            return super().form_valid(form)

        famille = form.cleaned_data["famille"]
        individu = form.cleaned_data["individu"]
        facturer = form.cleaned_data["facturer"]
        date_facturation = form.cleaned_data["date_facturation"]
        label_prestation = form.cleaned_data["label_prestation"]
        montant = form.cleaned_data["montant"]
        prestation = form.cleaned_data["prestation"]
        type_cotisation = form.cleaned_data["type_cotisation"]

        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarde de la cotisation
        self.object = form.save()

        # Sauvegarde de la prestation
        if facturer:
            if prestation == None:
                prestation = Prestation.objects.create(date=date_facturation, categorie="cotisation", label=label_prestation, individu=individu,
                                                       famille=famille, montant_initial=montant, montant=montant, activite=type_cotisation.activite)
            else:
                prestation.date = date_facturation
                prestation.categorie = "cotisation"
                prestation.label = label_prestation
                prestation.famille = famille
                prestation.individu = individu
                prestation.montant_initial = montant
                prestation.montant = montant
                prestation.activite = type_cotisation.activite
                prestation.save()

        if not facturer and prestation:
            prestation.delete()
            prestation = None

        # Associe la prestation à la cotisation
        self.object.prestation = prestation
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())



class Liste(Page, crud.Liste):
    model = Cotisation
    template_name = "fiche_famille/famille_cotisations.html"

    def get_queryset(self):
        return Cotisation.objects.select_related("type_cotisation", "type_cotisation__structure").filter(Q(famille=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcotisation", "date_saisie", "date_creation_carte", 'individu__nom', 'individu__prenom', "numero", "date_debut", "date_fin", "observations", "type_cotisation__nom", "unite_cotisation__nom", "depot_cotisation__date"]

        check = columns.CheckBoxSelectColumn(label="")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        beneficiaires = columns.TextColumn("Bénéficiaires", sources=None, processor='Get_beneficiaires')
        nom_cotisation = columns.TextColumn("Nom", sources=['type_cotisation__nom', 'unite_cotisation__nom'], processor='Get_nom_cotisation')
        depot = columns.TextColumn("Dépôt", sources=['depot_cotisation__date'], processor='Get_date_depot')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', 'idcotisation', 'date_debut', 'date_fin', 'beneficiaires', 'nom_cotisation', 'numero', 'depot']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_nom_cotisation(self, instance, *args, **kwargs):
            if instance.prestation:
                return instance.prestation.label
            else:
                return "%s - %s" % (instance.type_cotisation.nom, instance.unite_cotisation.nom)

        def Get_beneficiaires(self, instance, *args, **kwargs):
            if instance.individu == None:
                return instance.famille.nom
            else:
                return instance.individu.Get_nom()

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut l'idindividu dans les boutons d'actions """
            view = kwargs["view"]
            if not view.request.user.has_perm("core.famille_cotisations_modifier"):
                return "<span class='text-red' title='Accès interdit'><i class='fa fa-lock'></i></span>"
            kwargs = view.kwargs
            kwargs["pk"] = instance.pk
            if not instance.type_cotisation.structure or instance.type_cotisation.structure in view.request.user.structures.all():
                # Affiche les boutons d'action si l'utilisateur est associé à ce type de cotisation
                html = [
                    self.Create_bouton_modifier(url=reverse(view.url_modifier, kwargs=kwargs)),
                    self.Create_bouton_supprimer(url=reverse(view.url_supprimer, kwargs=kwargs)),
                    self.Create_bouton_imprimer(url=reverse("famille_voir_cotisation", kwargs={"idfamille": kwargs["idfamille"], "idcotisation": instance.pk}), title="Imprimer ou envoyer par email l'adhésion"),
                ]
            else:
                # Afficher que l'accès est interdit
                html = ["<span class='text-red'><i class='fa fa-minus-circle margin-r-5' title='Accès non autorisé'></i>Accès interdit</span>",]
            return self.Create_boutons_actions(html)

        def Get_date_depot(self, instance, *args, **kwargs):
            if instance.depot_cotisation:
                return utils_dates.ConvertDateToFR(instance.depot_cotisation.date)
            return ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_famille/famille_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "fiche_famille/famille_delete.html"

    # def delete(self, request, *args, **kwargs):
    #     """ Empêche la suppression de cotisation déjà incluse dans dépôt """
    #     if self.get_object().depot_cotisation:
    #         messages.add_message(request, messages.ERROR, "La suppression est impossible car cette adhésion est déjà incluse dans un dépôt")
    #         return HttpResponseRedirect(self.get_success_url(), status=303)
    #     reponse = super(Supprimer, self).delete(request, *args, **kwargs)
    #     return reponse


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    template_name = "fiche_famille/famille_delete.html"

    # def delete(self, request, objet):
    #     """ Empêche la suppression de cotisation déjà incluse dans dépôt """
    #     if objet.depot_cotisation:
    #         messages.add_message(request, messages.ERROR, "La suppression de '%s' est impossible car cette adhésion est déjà incluse dans un dépôt" % objet)
    #         return False
    #     return True
