import datetime, json
from decimal import Decimal
from django.db.models import Q, Sum
from django.urls import reverse
from core.views import crud
from core.models import Inscription, Activite, Prestation, Ventilation
from individus.utils.utils_pieces_manquantes import Get_pieces_manquantes_par_inscriptions
from individus.utils import utils_vaccinations
from portail.utils.utils_renseignements_manquants import Get_renseignements_manquants_par_inscriptions
from portail.utils.utils_questionnaires_manquants import Get_questions_par_inscriptions
from portail.utils.utils_sondages_manquants import Get_sondages_manquants_par_inscriptions
from core.views.customdatatable import CustomDatatable, Colonne
from core.utils.utils_tooltip import Get_html_with_tooltip


class Page(crud.Page):
    model = Inscription
    url_liste = "suivi_administratif_liste"
    url_modifier = "suivi_administratif_modifier"
    url_supprimer = "suivi_administratif_supprimer"
    objet_singulier = "une vérification"
    objet_pluriel = "des vérifications"

class Liste(Page, crud.CustomListe):
    template_name = "individus/suivi_administratif.html"

    colonnes = [
        Colonne("individu", "Individu"),
        Colonne("renseignements_manquants", "Renseignements"),
        Colonne("pieces_manquantes", "Pièces manquantes"),
        Colonne("vaccins_manquants", "Vaccinations"),
        Colonne("questions_manquantes", "Questionnaires"),
        Colonne("sondages_manquants", "Sondages"),
        Colonne("besoin_certification", "Vérification en attente"),
        Colonne("solde_a_payer", "Solde à payer"),
    ]

    def Get_activite(self):
        activite = self.kwargs.get("activite")
        if activite:
            return activite.replace("A", "")
        # Sélectionner la première activité disponible par défaut
        condition = Q(visible=True)
        premiere_activite = Activite.objects.filter(self.Get_condition_structure(), condition).order_by("-date_fin", "nom").first()
        if premiere_activite:
            return str(premiere_activite.pk)
        return None

    def get_queryset(self):
        """Inscriptions visibles pour les structures de l'utilisateur et l'activité sélectionnée."""
        
        condition = Q(activite__structure__in=self.request.user.structures.all()) & Q(activite__visible=True)
        activite = self.Get_activite()
        if activite:
            condition &= Q(activite=activite)
            result = Inscription.objects.select_related("famille", "individu", "activite").prefetch_related(
                "activite__pieces",
                "activite__pieces__type_piece_document"
            ).filter(self.Get_filtres("Q"), condition)
        else:
            # Aucune activité disponible
            result = Inscription.objects.none()
        
        return result
    

    def Get_solde_par_individu(self, individus, activites):
        
        prestations_qs = Prestation.objects.filter(activite__in=activites, individu__in=individus)
        dict_prestations = {
            temp["individu"]: temp["total"]
            for temp in prestations_qs.values("individu").annotate(total=Sum("montant"))
        }

        dict_reglements = {
            temp["prestation__individu"]: temp["total"]
            for temp in Ventilation.objects.filter(prestation__in=prestations_qs)
            .values("prestation__individu")
            .annotate(total=Sum("montant"))
        }

        dict_solde = {}
        for ind in individus:
            total_prest = dict_prestations.get(ind.pk, Decimal(0))
            total_regl = dict_reglements.get(ind.pk, Decimal(0))
            solde = total_regl - total_prest
            dict_solde[ind.pk] = {
                "solde": float(solde),
                "prestations": float(total_prest),
                "reglements": float(total_regl),
            }
        
        return dict_solde

    def Get_customdatatable(self):
        
        inscriptions = self.get_queryset()
        individus = [ins.individu for ins in inscriptions]
        activites = [ins.activite.pk for ins in inscriptions]

        dict_solde = self.Get_solde_par_individu(individus, activites)

        # Préchargement optimisé de TOUTES les données manquantes en 3 appels batch
        dict_pieces_manquantes = Get_pieces_manquantes_par_inscriptions(inscriptions)
        
        dict_questions_manquantes = Get_questions_par_inscriptions(inscriptions)
        
        dict_renseignements_manquants = Get_renseignements_manquants_par_inscriptions(inscriptions)
        
        dict_sondages_manquants = Get_sondages_manquants_par_inscriptions(inscriptions)

        lignes = []
        
        for ins in inscriptions:
            individu = ins.individu
            famille = ins.famille
            solde_info = dict_solde.get(individu.pk, {"solde": 0})

            individu_url = reverse('individu_resume', kwargs={'idfamille': famille.pk, 'idindividu': individu.pk})
            individu_html = f"<a href='{individu_url}'>{individu.nom} {individu.prenom}</a>"

            # Pièces manquantes - lookup dans dict pré-calculé
            missing_pieces = dict_pieces_manquantes.get(individu.pk, [])
            nb_pieces = len(missing_pieces)
            if nb_pieces == 0: 
                pieces_html = "0"
            else: 
                tooltip_text = "&#10;".join([piece['label'] for piece in missing_pieces]) if missing_pieces else None
                pieces_html = Get_html_with_tooltip(nb_pieces, tooltip_text)

            # Vaccins (à optimiser aussi si nécessaire plus tard)
            nb_vaccins = len(utils_vaccinations.Get_vaccins_obligatoires_by_inscriptions([ins]).get(individu, []) or [])
            
            # Questions - lookup dans dict pré-calculé
            nb_questions = len(dict_questions_manquantes.get(individu.pk, []))
            
            # Renseignements - lookup dans dict pré-calculé
            renseignement = dict_renseignements_manquants.get(individu.pk, {'nbre': 0})
            nb_renseignements = renseignement.get("nbre", 0)
            
            # Sondages - lookup dans dict pré-calculé
            nb_sondages = len(dict_sondages_manquants.get(individu.pk, []))

            lignes.append((
                individu_html,
                nb_renseignements,
                pieces_html,
                nb_vaccins,
                nb_questions,
                nb_sondages,
                "Oui" if ins.besoin_certification else "Non",
                f"{solde_info['solde']:.2f} €"
            ))
                       
        return CustomDatatable(colonnes=self.colonnes, lignes=lignes, filtres=self.Get_filtres())

    def get_context_data(self, **kwargs):
        
        context = super().get_context_data(**kwargs)

        # Conserver l'activité sélectionnée pour le template
        activite = self.Get_activite()
        context['activite'] = int(activite) if activite else None

        # Construction de la liste d'activités pour le select
        condition = Q(visible=True)
        liste_activites = []
        for act in Activite.objects.filter(self.Get_condition_structure(), condition).order_by("-date_fin", "nom"):
            if act.date_fin.year == 2999:
                liste_activites.append((act.pk, f"{act.nom} - Activité illimitée"))
            elif act.date_fin:
                liste_activites.append((act.pk,
                                        f"{act.nom} - Du {act.date_debut.strftime('%d/%m/%Y')} au {act.date_fin.strftime('%d/%m/%Y')}"))
            else:
                liste_activites.append((act.pk, f"{act.nom} - A partir du {act.date_debut.strftime('%d/%m/%Y')}"))

        context['liste_activites'] = liste_activites

        context['page_titre'] = "Suivi administratif des individus"
        context['box_titre'] = "Suivi administratif"
        context['box_introduction'] = "Cette liste permet de suivre les éléments <strong> MANQUANTS </strong> et les soldes par individu."
        
        context['datatable'] = self.Get_customdatatable()
        
        return context
