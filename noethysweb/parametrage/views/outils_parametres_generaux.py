#  Copyright (c) 2024 GIP RECIA.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.core.cache import cache
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from core.views.base import CustomView
from parametrage.forms.outils_parametres_generaux import Formulaire
import django.contrib.messages
from core.models import PortailParametre


class Modifier(CustomView, TemplateView):
    template_name = "core/crud/edit.html"
    compatible_demo = False

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['page_titre'] = "Paramètres Généraux"
        context['box_titre'] = "Paramètres Envoi Emails en LOT"
        context['box_introduction'] = "Ajustez les paramètres de l'envoi d'emails en lot et cliquez sur le bouton Enregistrer."

        # # Récupérer ou initialiser les valeurs de session à partir de la base de données
        if 'emails_activites_active' not in self.request.session :
            # Tentative de récupération des paramètres de la base de données
            emails_activites = PortailParametre.objects.filter(code="emails_activites").first()

            # Initialisez les valeurs de session en fonction des valeurs de la base de données ou par défaut sur False si elles ne sont pas trouvées
            self.request.session['emails_activites_active'] = bool(emails_activites and emails_activites.valeur == 'True')

            # Si les paramètres n'existent pas dans la base de données, définissez-les sur False uniquement dans la session (sans créer de nouvelles entrées)
            if not emails_activites:
                self.request.session['emails_activites_active'] = False

        # Transmettre les valeurs de session au formulaire
        initial_data = {
            "emails_activites": self.request.session.get('emails_activites_active', True),
        }
        context['form'] = Formulaire(initial=initial_data)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Enregistrement :Récupérer les paramètres existants dans la base de données
        dict_parametres = {parametre.code: parametre for parametre in PortailParametre.objects.all()}
        liste_modifications = []
        for code, valeur in form.cleaned_data.items():
            if code in dict_parametres:
                dict_parametres[code].valeur = str(valeur)
                liste_modifications.append(dict_parametres[code])
            else:
                PortailParametre.objects.create(code=code, valeur=str(valeur))
        if liste_modifications:
            PortailParametre.objects.bulk_update(liste_modifications, ["valeur"])

        # Stocker les états des cases à cocher dans la session
        request.session['emails_activites_active'] = form.cleaned_data.get("emails_activites", False)
        cache.delete("parametres_portail")

        django.contrib.messages.success(request, 'Paramètres enregistrés')
        return HttpResponseRedirect(reverse_lazy("outils_parametres_generaux"))