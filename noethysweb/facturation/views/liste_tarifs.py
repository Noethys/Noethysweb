# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views.base import CustomView
from django.views.generic import TemplateView
from facturation.forms.liste_tarifs import Formulaire
from core.models import Tarif, TarifLigne, CategorieTarif, LISTE_METHODES_TARIFS, DICT_COLONNES_TARIFS
from core.utils import utils_dates, utils_texte


class View(CustomView, TemplateView):
    menu_code = "liste_tarifs"
    template_name = "facturation/liste_tarifs.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des tarifs"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))

        resultats = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "resultats": resultats,
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        activite = parametres["activite"]
        tarifs = Tarif.objects.select_related('nom_tarif').prefetch_related('categories_tarifs').filter(activite=activite).order_by("-date_debut")
        tarifs_lignes = TarifLigne.objects.filter(activite=activite).order_by("num_ligne")

        source = []
        source.append(u"<FONT SIZE=+1><B><center>Tarifs de l'activité %s</center></B></FONT><BR>" % activite.nom)

        if len(tarifs) == 0:
            source.append(u"<P>Aucun tarif</P>")

        for tarif in tarifs:
            texte_categories = utils_texte.Convert_liste_to_texte_virgules([categorie.nom for categorie in tarif.categories_tarifs.all()])

            # Création des champs
            index = 0
            for dictMethode in LISTE_METHODES_TARIFS:
                if dictMethode["code"] == tarif.methode:
                    champs = dictMethode["champs"]
                index += 1

            tableau = []
            ligne = []
            dict_remplissage_colonnes = {}
            numColonne = 0
            for code in champs:
                dict_colonne = DICT_COLONNES_TARIFS[code]
                ligne.append(dict_colonne["label"])
                dict_remplissage_colonnes[numColonne] = 0
                numColonne += 1
            tableau.append(ligne)

            numLigne = 0
            for tarif_ligne in tarifs_lignes:
                ligne = []
                if tarif.pk == tarif_ligne.tarif_id:
                    numColonne = 0
                    for codeChamp in champs:
                        valeur = getattr(tarif_ligne, codeChamp)
                        if type(valeur) == int or type(valeur) == float:
                            if codeChamp in ("montant_unique", "montant_min", "montant_max", "ajustement", "revenu_min", "revenu_max"):
                                valeur = utils_texte.Formate_montant(valeur)
                            else:
                                valeur = str(valeur)
                        if valeur == "None": valeur = ""
                        if codeChamp == "date" and valeur != None :
                            valeur = utils_dates.ConvertDateToFR(valeur)
                        if valeur == None: valeur = ""
                        ligne.append(valeur)

                        if valeur != "":
                            dict_remplissage_colonnes[numColonne] += 1

                        numColonne += 1

                    tableau.append(ligne)

                    numLigne += 1

            # Enlève des colonnes vides
            tableau2 = []
            for ligne in tableau:
                ligne2 = []
                numColonne = 0
                for valeur in ligne:
                    if dict_remplissage_colonnes[numColonne] > 0:
                        ligne2.append(valeur)
                    numColonne += 1
                tableau2.append(ligne2)

            source.append(u"<p><b>%s</b><br><FONT SIZE=-1>%s - Tarif à partir du %s</FONT></p>" % (tarif.nom_tarif.nom, texte_categories, utils_dates.ConvertDateToFR(tarif.date_debut)))

            source.append(u"<p><table class='table table-bordered'>")
            for ligne in tableau2:
                source.append("<tr align=center>")
                for valeur in ligne:
                    source.append("<td>%s</td>" % valeur)
                source.append("</tr>")
            source.append("</table></p>")

        return "".join(source)
