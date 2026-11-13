# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div, HTML
from crispy_forms.bootstrap import Field, InlineRadios
from core.widgets import DatePickerWidget
from core.forms.select2 import Select2MultipleWidget
from core.models import Collaborateur, GroupeCollaborateurs, TypePosteCollaborateur
from core.utils.utils_commandes import Commandes
from core.models import ModelePlanningCollaborateur, TypeEvenementCollaborateur, LigneModelePlanningCollaborateur, AffectationCollaborateur, JOURS_COMPLETS_SEMAINE
from collaborateurs.utils.utils_affectations import Arbre
from parametrage.widgets import Ligne_modele_planning


class Formulaire(FormulaireBase, ModelForm):
    disponibilite = forms.ChoiceField(label="Proposer ce modèle", widget=forms.RadioSelect(), required=True, initial="TOUS",
                                      choices=[("TOUS", "À tous les collaborateurs"), ("RESTREINT", "Seulement pour…")],
                                      help_text="Lors de l'application, seuls les modèles proposés aux collaborateurs concernés sont présentés en priorité. Un modèle non proposé reste utilisable à titre exceptionnel, avec un avertissement.")
    lignes = forms.CharField(label="Evènements", required=True, widget=Ligne_modele_planning(attrs={}), help_text="Ajoutez ici les événements (horaires et types d'événements) qui composent ce modèle de planning.")

    class Meta:
        model = ModelePlanningCollaborateur
        fields = ["nom", "observations", "inclure_feries", "nb_semaines", "reperage", "date_reference", "vacances_cycle", "groupes", "postes", "collaborateurs"]
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
            "nb_semaines": forms.RadioSelect(),
            "reperage": forms.RadioSelect(),
            "vacances_cycle": forms.RadioSelect(),
            "date_reference": DatePickerWidget(),
            "groupes": Select2MultipleWidget({"data-minimum-input-length": 0}),
            "postes": Select2MultipleWidget({"data-minimum-input-length": 0}),
            "collaborateurs": Select2MultipleWidget({"data-minimum-input-length": 0}),
        }
        help_texts = {
            "nom": "Saisissez le nom du modèle de planning. Exemple : Semaine type animateur.",
            "observations": "Vous pouvez saisir ici des informations complémentaires sur ce modèle.",
            "inclure_feries": "Cochez cette case pour que les événements du modèle soient également créés sur les jours fériés.",
            "nb_semaines": "Un modèle peut décrire une seule semaine type ou un roulement de 2 ou 3 semaines.",
            "reperage": "Indiquez comment déterminer la semaine du cycle qui s'applique à une date donnée. Avec les semaines impaires / paires, la semaine 1 correspond aux numéros de semaine impairs du calendrier.",
            "date_reference": "La semaine qui contient cette date sera la semaine 1 du cycle. Le cycle se poursuit ensuite indéfiniment, y compris d'une année sur l'autre.",
            "groupes": "Le modèle est proposé aux membres de ces groupes de collaborateurs.",
            "postes": "Le modèle est proposé aux collaborateurs dont le contrat porte sur l'un de ces postes. Le poste est celui du contrat en cours au début de la période d'application.",
            "collaborateurs": "Le modèle est également proposé à ces collaborateurs.",
            "vacances_cycle": "Une semaine compte comme semaine de vacances si tous ses jours du lundi au vendredi sont en vacances. Pendant une semaine de vacances non numérotée, seuls les évènements définis pour toutes les semaines du cycle sont appliqués.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_plannings_collaborateurs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Cycle
        self.fields["nb_semaines"].label = "Durée du cycle"
        self.fields["reperage"].label = "Repérage du cycle"
        self.fields["vacances_cycle"].label = "Pendant les vacances"
        if not self.instance.pk:
            self.fields["vacances_cycle"].initial = "PAUSE"

        # Disponibilité
        self.fields["groupes"].queryset = GroupeCollaborateurs.objects.all().order_by("nom")
        self.fields["postes"].queryset = TypePosteCollaborateur.objects.all().order_by("nom")
        self.fields["collaborateurs"].queryset = Collaborateur.objects.all().order_by("nom", "prenom")
        if self.instance.pk and (self.instance.groupes.exists() or self.instance.postes.exists() or self.instance.collaborateurs.exists()):
            self.fields["disponibilite"].initial = "RESTREINT"
        from collaborateurs.utils.utils_modeles_planning import Get_groupes, Get_postes
        import datetime
        ids_collaborateurs = list(Collaborateur.objects.values_list("pk", flat=True))
        groupes, postes = Get_groupes(ids_collaborateurs), Get_postes(ids_collaborateurs, datetime.date.today())
        self.donnees_collaborateurs = json.dumps({idcollaborateur: {"g": sorted(groupes.get(idcollaborateur, [])), "p": postes.get(idcollaborateur)} for idcollaborateur in ids_collaborateurs})

        # Lignes
        arbre_affectations = Arbre()
        self.fields["lignes"].widget.request = self.request
        self.fields["lignes"].widget.attrs.update({
            "types_evenements": json.dumps({type_evenement.pk: type_evenement.nom for type_evenement in TypeEvenementCollaborateur.objects.all()}),
            "jours_semaine": json.dumps({num_jour: nom_jour for num_jour, nom_jour in JOURS_COMPLETS_SEMAINE}),
            "affectations": json.dumps({idaffectation: arbre_affectations.Get_chemin(idaffectation) for idaffectation in arbre_affectations.affectations}),
            "couleurs": json.dumps({type_evenement.pk: type_evenement.couleur for type_evenement in TypeEvenementCollaborateur.objects.all()}),
            "types_temps": json.dumps({type_evenement.pk: type_evenement.type for type_evenement in TypeEvenementCollaborateur.objects.all()}),
        })
        lignes = LigneModelePlanningCollaborateur.objects.select_related("type_evenement").filter(modele_id=self.instance.pk if self.instance else 0)
        self.fields["lignes"].initial = json.dumps([{
            "idligne": ligne.pk, "semaine": ligne.semaine, "jour": ligne.jour, "periode": ligne.periode, "heure_debut": str(ligne.heure_debut),
            "heure_fin": str(ligne.heure_fin), "type_evenement": ligne.type_evenement_id, "titre": ligne.titre, "affectation": ligne.affectation_id}
            for ligne in lignes])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modeles_plannings_collaborateurs_liste' %}"),
            Fieldset("Généralités",
                Field("nom"),
                Field("observations"),
                Field("inclure_feries"),
            ),
            Fieldset("Cycle",
                InlineRadios("nb_semaines"),
                Div(
                    Field("reperage"),
                    Div(Field("date_reference"), id="div_date_reference"),
                    Div(Field("vacances_cycle"), id="div_vacances_cycle"),
                    id="div_options_cycle"),
            ),
            Fieldset("Disponibilité",
                Field("disponibilite"),
                Div(
                    Field("groupes"),
                    Field("postes"),
                    Field("collaborateurs"),
                    HTML("<div class='form-group row'><div class='col-md-2'></div><div class='col-md-10'><div id='resume_disponibilite' class='text-muted' aria-live='polite' "
                         "style='background:#f4f6f9;border-radius:4px;padding:6px 10px;'></div></div></div>"),
                    id="div_restrictions"),
            ),
            Fieldset("Evènements",
                Field("lignes"),
            ),
            HTML("<script>var donnees_collaborateurs = %s;</script>" % self.donnees_collaborateurs),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        if self.cleaned_data.get("disponibilite") == "RESTREINT":
            if not (self.cleaned_data.get("groupes") or self.cleaned_data.get("postes") or self.cleaned_data.get("collaborateurs")):
                self.add_error("disponibilite", "Sélectionnez au moins un groupe, un poste ou un collaborateur")
        else:
            for nom in ("groupes", "postes", "collaborateurs"):
                self.cleaned_data[nom] = self.fields[nom].queryset.none()
        nb_semaines = int(self.cleaned_data.get("nb_semaines") or 1)
        if self.cleaned_data.get("reperage") == "PARITE" and nb_semaines != 2:
            self.add_error("reperage", "Le repérage par semaines impaires / paires n'est possible qu'avec un cycle de 2 semaines")
        if nb_semaines > 1 and self.cleaned_data.get("reperage") == "REFERENCE" and not self.cleaned_data.get("date_reference"):
            self.add_error("date_reference", "Saisissez une date de référence")
        try:
            lignes = json.loads(self.cleaned_data.get("lignes") or "[]")
        except ValueError:
            lignes = []
        if any(int(ligne.get("semaine") or 0) > nb_semaines for ligne in lignes):
            self.add_error("lignes", "Certains évènements sont placés sur une semaine qui n'existe plus dans le cycle. Supprimez-les ou déplacez-les avant de réduire la durée du cycle.")
        return self.cleaned_data


EXTRA_SCRIPT = """
<script>
    function Maj_options_cycle() {
        var nb = parseInt($("input[name='nb_semaines']:checked").val() || 1);
        var reperage = $("input[name='reperage']:checked").val();
        $("input[name='reperage'][value='PARITE']").closest(".custom-control, .form-check").toggle(nb === 2);
        if (nb !== 2 && reperage === "PARITE") {
            $("input[name='reperage'][value='APPLICATION']").prop("checked", true);
            reperage = "APPLICATION";
        }
        $("#div_options_cycle").toggle(nb > 1);
        $("#div_date_reference").toggle(nb > 1 && reperage === "REFERENCE");
        $("#div_vacances_cycle").toggle(nb > 1 && reperage !== "PARITE");
        if (typeof Maj_cycle_grille === "function") {
            Maj_cycle_grille(nb, nb === 2 && reperage === "PARITE");
        }
    }
    function Maj_disponibilite() {
        var restreint = $("input[name='disponibilite']:checked").val() === "RESTREINT";
        $("#div_restrictions").toggle(restreint);
        if (!restreint) { return; }
        var groupes = ($("#id_groupes").val() || []).map(Number), postes = ($("#id_postes").val() || []).map(Number), collaborateurs = ($("#id_collaborateurs").val() || []).map(Number);
        var nb = {total: 0, groupe: 0, poste: 0, nom: 0};
        $.each(donnees_collaborateurs, function(id, infos) {
            id = Number(id);
            var par_nom = collaborateurs.indexOf(id) >= 0, par_groupe = infos.g.some(function(g) { return groupes.indexOf(g) >= 0; }), par_poste = postes.indexOf(infos.p) >= 0;
            if (!(par_nom || par_groupe || par_poste)) { return; }
            nb.total++;
            if (par_groupe) { nb.groupe++; } else if (par_poste) { nb.poste++; } else { nb.nom++; }
        });
        var details = [];
        if (nb.groupe) { details.push(nb.groupe + " par groupe"); }
        if (nb.poste) { details.push(nb.poste + " par poste"); }
        if (nb.nom) { details.push(nb.nom + " nommément"); }
        $("#resume_disponibilite").html("<i class='fa fa-users margin-r-5'></i>Proposé actuellement à <strong>" + nb.total + " collaborateur" + (nb.total > 1 ? "s" : "") + "</strong>"
            + (details.length ? " : " + details.join(", ") + "." : "."));
    }
    $(document).ready(function() {
        $("input[name='nb_semaines'], input[name='reperage']").on("change", Maj_options_cycle);
        Maj_options_cycle();
        $("input[name='disponibilite']").on("change", Maj_disponibilite);
        $("#id_groupes, #id_postes, #id_collaborateurs").on("change", Maj_disponibilite);
        Maj_disponibilite();
    });
</script>
"""
