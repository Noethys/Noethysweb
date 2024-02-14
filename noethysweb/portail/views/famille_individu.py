from django import forms
from core.models import Individu, Famille, Rattachement
from django.shortcuts import render
from core.utils import utils_questionnaires
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
import logging
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from django.utils.translation import gettext as _

class View(CustomView, TemplateView):
    menu_code = "portail_renseignements"
    template_name = "portail/famille_individu.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Ajouter un enfant")
        context['famille'] = Famille.objects.prefetch_related('nom').filter(nom=self.request.user.famille,)
        return context

class IndividuForm(forms.ModelForm):
    class Meta:
        model = Individu
        fields = ['prenom', 'nom']

    def save_individu(self, famille):
        # Sauvegarde de l'objet Individu en base de données
        individu = super().save(commit=False)
        individu.save()

        categorie = "2"
        titulaire = True
        # Création des questionnaires de type individu
        utils_questionnaires.Creation_reponses(categorie="individu", liste_instances=[individu])

        # Recherche d'une adresse à rattacher
        rattachements = Rattachement.objects.prefetch_related('individu').filter(famille=famille)
        for rattachement in rattachements:
                if rattachement.individu.adresse_auto is None:
                    individu.adresse_auto = rattachement.individu.pk
                    individu.save()
                    # Sauvegarde du rattachement
                    rattachement = Rattachement(famille=famille, individu=individu, categorie=categorie, titulaire=titulaire)
                    rattachement.save()
                    individu.Maj_infos()
                    break
        return individu

def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['famille'] = Famille.objects.prefetch_related('nom').filter(nom=self.request.user.famille,)
        return context

def contact(request):
    if request.method == 'POST':
        form = IndividuForm(request.POST)
        print("Données soumises:", request.POST)
        if form.is_valid():
            famille_id_dict = Famille.objects.filter(nom=request.user.famille).values('idfamille').first()
            famille_id = famille_id_dict.get('idfamille') if famille_id_dict else None
            print("ID de la famille:", famille_id)

            #Ajouter le rattachement
            if famille_id:
                famille = Famille.objects.get(pk=famille_id)
                print("Famille:", famille)
                individu = form.save_individu(famille)
                print("Individu enregistré:", individu)

                url_success = ""
                print("URL de redirection:", url_success)
                return HttpResponseRedirect(reverse('portail_renseignements'))
    else:
        form = IndividuForm()
    return render(request, 'portail/famille_individu.html', {'form': form})