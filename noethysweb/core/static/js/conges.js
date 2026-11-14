/*  Copyright (c) 2019-2026 Ivan LUCAS.
    Noethysweb, application de gestion multi-activités.
    Distribué sous licence GNU GPL.
    Congés et absences des collaborateurs : demandes, traitement, compteurs (page des demandes, page des compteurs et onglet de la fiche) */

(function($) {
    "use strict";

    var C = window.CONGES;
    var Etat = {filtre: "ATTENTE", demandes: [], edition: null, traitement: null, annee_fiche: null};

    // ------------------------------------------------------------------ Outils
    function Echapper(texte) {
        return String(texte === null || texte === undefined ? "" : texte).replace(/[&<>"']/g, function(c) {
            return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
        });
    }
    function Ajax(url, donnees) {
        donnees = $.extend({csrfmiddlewaretoken: C.csrf}, donnees || {});
        return $.ajax({url: url, type: "POST", data: donnees, dataType: "json"});
    }
    function Message_erreur(xhr, defaut) { return (xhr && xhr.responseJSON && xhr.responseJSON.erreur) || defaut || "Une erreur est survenue"; }
    function Debounce(fonction, delai) {
        var minuteur = null;
        return function() { var args = arguments; clearTimeout(minuteur); minuteur = setTimeout(function() { fonction.apply(null, args); }, delai); };
    }
    function Type(id) { return C.types.find(function(t) { return t.id === +id; }); }
    function Collab(id) { return C.collaborateurs.find(function(c) { return c.id === +id; }); }
    function Libelle_annee(type, annee) { return !type || type.mois_debut === 1 ? String(annee) : annee + "-" + (annee + 1); }
    function Options_annees(type, selection) {
        var courante = type ? type.annee : +C.aujourdhui.substr(0, 4), html = "";
        for (var annee = courante - 3; annee <= courante + 1; annee++) {
            html += "<option value='" + annee + "'" + (annee === (selection || courante) ? " selected" : "") + ">" + Libelle_annee(type, annee) + (annee === courante ? " (en cours)" : "") + "</option>";
        }
        return html;
    }
    function Options_types(selection, actifs_seulement) {
        return C.types.filter(function(t) { return !actifs_seulement || t.actif || t.id === selection; }).map(function(t) {
            return "<option value='" + t.id + "'" + (t.id === selection ? " selected" : "") + ">" + Echapper(t.nom) + (t.unite === "HEURES" ? " (heures)" : "") + "</option>";
        }).join("");
    }
    function Rafraichir() {
        if ($("#cg_demandes").length) { Charger_demandes(); }
        if ($("#cg_compteurs").length) { Charger_compteurs(); }
        if ($("#cg_fiche_compteurs").length) { Charger_fiche(); }
    }

    // ------------------------------------------------------------------ Liste des demandes
    var ETATS = {ATTENTE: ["warning", "En attente"], VALIDEE: ["success", "Validée"], REFUSEE: ["danger", "Refusée"], ANNULEE: ["secondary", "Annulée"]};

    function Charger_demandes() {
        Ajax(C.urls.demandes, {etat: Etat.filtre, idcollaborateur: C.idcollaborateur || 0}).done(function(data) {
            Etat.demandes = data.demandes;
            $("#cg_nb_attente").text(data.nb_attente || "");
            Rendu_demandes();
        }).fail(function(xhr) { $("#cg_demandes").html("<tr><td colspan='7' class='text-danger'>" + Echapper(Message_erreur(xhr)) + "</td></tr>"); });
    }

    function Rendu_demandes() {
        var fiche = C.mode === "fiche";
        $(".cg-col-collab").prop("hidden", fiche);
        if (!Etat.demandes.length) {
            $("#cg_demandes").html("<tr><td colspan='7' class='text-muted'>" + (Etat.filtre === "ATTENTE" ? "Aucune demande en attente." : "Aucune demande.") + "</td></tr>");
            return;
        }
        $("#cg_demandes").html(Etat.demandes.map(function(d) {
            var etat = ETATS[d.etat], actions = "";
            if (d.etat === "ATTENTE" && d.traitable) { actions += "<button type='button' class='btn btn-primary btn-xs' data-action='traiter' data-id='" + d.id + "'><i class='fa fa-gavel margin-r-5'></i>Traiter</button>"; }
            if (d.etat === "ATTENTE") { actions += "<button type='button' class='btn btn-default btn-xs' data-action='modifier' data-id='" + d.id + "' title='Modifier la demande' aria-label='Modifier la demande'><i class='fa fa-pencil'></i></button>"; }
            if ((d.etat === "ATTENTE" || d.etat === "VALIDEE") && d.traitable) { actions += "<button type='button' class='btn btn-default btn-xs' data-action='annuler' data-id='" + d.id + "' title='Annuler la demande' aria-label='Annuler la demande'><i class='fa fa-times'></i></button>"; }
            var details = [d.motif ? "Motif : " + d.motif : "", d.commentaire ? "Décision : " + d.commentaire : ""].filter(Boolean);
            var saisie = d.date_demande + (d.auteur ? " par " + d.auteur : "") + (d.decideur ? "<br><small class='text-muted'>" + Echapper((d.etat === "REFUSEE" ? "Refusée" : (d.etat === "ANNULEE" ? "Traitée" : "Validée")) + " le " + d.date_decision + " par " + d.decideur) + "</small>" : "");
            return "<tr>" +
                (fiche ? "" : "<td><a href='" + C.urls.fiche.replace(/0$/, d.c) + "'>" + Echapper(d.collaborateur) + "</a></td>") +
                "<td><span class='cg-pastille' style='background:" + Echapper(d.couleur) + "' aria-hidden='true'></span>" + Echapper(d.type_nom) + "</td>" +
                "<td>" + Echapper(d.periode_txt) + (details.length ? "<br><small class='text-muted'>" + Echapper(details.join(" · ")) + "</small>" : "") + "</td>" +
                "<td class='text-right text-nowrap'>" + Echapper(d.quantite_txt) + "</td>" +
                "<td><span class='badge badge-" + etat[0] + "'>" + etat[1] + "</span></td>" +
                "<td class='cg-saisie'>" + saisie + "</td>" +
                "<td class='text-right text-nowrap cg-actions'>" + actions + "</td></tr>";
        }).join(""));
    }

    // ------------------------------------------------------------------ Saisie d'une demande
    function Ouvrir_demande(d) {
        Etat.edition = d || null;
        $("#cg_modal_demande_titre strong").text(d ? "Modifier la demande d'absence" : "Nouvelle demande d'absence");
        var $collab = $("#cg_dem_collab");
        $("#cg_dem_collab_bloc").prop("hidden", C.mode === "fiche");
        $collab.html("<option></option>" + C.collaborateurs.map(function(c) { return "<option value='" + c.id + "'>" + Echapper(c.nom) + "</option>"; }).join(""));
        $collab.val(d ? d.c : (C.idcollaborateur || "")).trigger("change.select2");
        var types_actifs = C.types.filter(function(t) { return t.actif; });
        $("#cg_dem_type").html(Options_types(d ? d.type : (types_actifs.length ? types_actifs[0].id : null), true));
        $("#cg_dem_debut").val(d ? d.date_debut : C.aujourdhui);
        $("#cg_dem_fin").val(d ? d.date_fin : C.aujourdhui);
        $("#cg_dem_debut_am").prop("checked", d ? d.debut_apres_midi : false);
        $("#cg_dem_fin_matin").prop("checked", d ? d.fin_matin : false);
        $("#cg_dem_heure_debut").val(d ? d.heure_debut : "");
        $("#cg_dem_heure_fin").val(d ? d.heure_fin : "");
        $("#cg_dem_motif").val(d ? d.motif : "");
        $("#cg_dem_calcul").attr("class", "cg-calcul").empty();
        Maj_formulaire_demande();
        $("#cg_modal_demande").modal("show");
        if (!C.types.length) { $("#cg_dem_calcul").attr("class", "cg-calcul alert alert-warning").text("Aucun type de congé n'est paramétré (Paramétrage > Collaborateurs > Types de congés)."); }
    }

    function Donnees_demande() {
        var heures = !$("#cg_dem_heures_bloc").prop("hidden");
        return {
            iddemande: Etat.edition ? Etat.edition.id : 0, idcollaborateur: C.mode === "fiche" ? C.idcollaborateur : ($("#cg_dem_collab").val() || 0),
            idtype: $("#cg_dem_type").val() || 0, date_debut: $("#cg_dem_debut").val(), date_fin: $("#cg_dem_fin").val() || $("#cg_dem_debut").val(),
            debut_apres_midi: $("#cg_dem_debut_am").prop("checked"), fin_matin: $("#cg_dem_fin_matin").prop("checked"),
            heure_debut: heures ? $("#cg_dem_heure_debut").val() : "", heure_fin: heures ? $("#cg_dem_heure_fin").val() : "", motif: $("#cg_dem_motif").val()
        };
    }

    function Maj_formulaire_demande() {
        var type = Type($("#cg_dem_type").val()), meme_jour = $("#cg_dem_debut").val() && $("#cg_dem_debut").val() === $("#cg_dem_fin").val();
        $("#cg_dem_heures_bloc").prop("hidden", !(type && type.unite === "HEURES" && meme_jour));
        var avec_heures = !$("#cg_dem_heures_bloc").prop("hidden") && ($("#cg_dem_heure_debut").val() || $("#cg_dem_heure_fin").val());
        $("#cg_dem_debut_am, #cg_dem_fin_matin").prop("disabled", !!avec_heures);
        var collab = Collab(C.mode === "fiche" ? C.idcollaborateur : $("#cg_dem_collab").val());
        $("#cg_dem_traiter").prop("hidden", !(collab && collab.modifiable));
        Calculer_demande();
    }

    var Calculer_demande = Debounce(function() {
        var donnees = Donnees_demande(), $calcul = $("#cg_dem_calcul");
        if (!donnees.idcollaborateur || !donnees.idtype || !donnees.date_debut) { $calcul.attr("class", "cg-calcul").empty(); return; }
        var signature = JSON.stringify(donnees);
        $calcul.data("signature", signature);
        Ajax(C.urls.calculer, donnees).done(function(data) {
            if ($calcul.data("signature") !== signature) { return; }
            if (data.erreur) { $calcul.attr("class", "cg-calcul alert alert-warning").text(data.erreur); return; }
            var texte = "<strong>Durée décomptée : " + Echapper(data.quantite_txt) + "</strong> · Solde " + Echapper(data.periode) + " : " + Echapper(data.solde_txt) +
                (data.attente_txt ? " (dont " + Echapper(data.attente_txt) + " déjà demandés en attente)" : "") + " → <strong>" + Echapper(data.apres_txt) + "</strong> après cette demande.";
            if (data.bloquant) { texte += "<br><i class='fa fa-exclamation-triangle'></i> Ce type de congé n'autorise pas de solde négatif : la demande ne pourra pas être validée en l'état."; }
            $calcul.attr("class", "cg-calcul alert " + (data.negatif ? "alert-warning" : "alert-info")).html(texte);
        });
    }, 250);

    function Enregistrer_demande(traiter) {
        var $boutons = $("#cg_dem_enregistrer, #cg_dem_traiter").prop("disabled", true);
        Ajax(C.urls.enregistrer, Donnees_demande()).done(function(data) {
            $("#cg_modal_demande").modal("hide");
            toastr.success(Etat.edition ? "Demande modifiée" : "Demande enregistrée");
            Rafraichir();
            if (traiter) { $("#cg_modal_demande").one("hidden.bs.modal", function() { Ouvrir_traitement(data.demande.id); }); }
        }).fail(function(xhr) {
            $("#cg_dem_calcul").attr("class", "cg-calcul alert alert-danger").text(Message_erreur(xhr));
        }).always(function() { $boutons.prop("disabled", false); });
    }

    // ------------------------------------------------------------------ Traitement d'une demande
    function Ouvrir_traitement(id) {
        $("#cg_tr_contenu").html("<p class='text-muted'><i class='fa fa-spinner fa-spin margin-r-5'></i>Analyse de la demande…</p>");
        $("#cg_tr_commentaire").val("");
        $("#cg_tr_valider, #cg_tr_refuser").prop("disabled", true);
        $("#cg_modal_traiter").modal("show");
        Ajax(C.urls.apercu, {iddemande: id}).done(function(data) {
            Etat.traitement = data.demande;
            Rendu_traitement(data.demande, data.apercu);
        }).fail(function(xhr) { $("#cg_tr_contenu").html("<div class='alert alert-danger'>" + Echapper(Message_erreur(xhr)) + "</div>"); });
    }

    function Ligne(icone, html, classe) {
        return "<div class='cg-ligne" + (classe ? " " + classe : "") + "'><i class='fa fa-" + icone + "' aria-hidden='true'></i><div>" + html + "</div></div>";
    }
    function Liste_repliable(titre, elements) {
        if (elements.length <= 3) { return Echapper(titre) + " : " + elements.map(Echapper).join(", "); }
        return "<details><summary>" + Echapper(titre) + "</summary>" + elements.map(Echapper).join("<br>") + "</details>";
    }

    function Rendu_traitement(d, a) {
        var html = "<h6 class='cg-titre-demande'><span class='cg-pastille' style='background:" + Echapper(d.couleur) + "' aria-hidden='true'></span>" +
            Echapper(d.collaborateur) + " · " + Echapper(d.type_nom) + " · " + Echapper(d.periode_txt) + "</h6>";
        if (d.motif) { html += Ligne("comment-o", "Motif : " + Echapper(d.motif)); }
        if (!a) { $("#cg_tr_contenu").html(html + "<div class='alert alert-info mb-0'>Cette demande a déjà été traitée.</div>"); return; }
        if (a.erreurs && a.erreurs.length) { html += "<div class='alert alert-danger'>" + a.erreurs.map(Echapper).join("<br>") + "</div>"; }
        if (a.quantite_txt) {
            html += Ligne("balance-scale", "Durée décomptée : <strong>" + Echapper(a.quantite_txt) + "</strong> · Solde " + Echapper(a.periode) + " : " + Echapper(a.solde_txt) + " → <strong" +
                (a.solde_apres < 0 ? " class='text-danger'" : "") + ">" + Echapper(a.solde_apres_txt) + "</strong>" + (a.attente_autres_txt ? " (" + Echapper(a.attente_autres_txt) + " d'autres demandes en attente)" : ""));
            html += Ligne("calendar-plus-o", Liste_repliable(a.creneaux.length + " évènement" + (a.creneaux.length > 1 ? "s" : "") + " « " + a.categorie + " » créé" + (a.creneaux.length > 1 ? "s" : ""), a.creneaux));
            html += a.travail.length ? Ligne("calendar-minus-o", Liste_repliable(a.travail.length + " évènement" + (a.travail.length > 1 ? "s" : "") + " de travail retiré" + (a.travail.length > 1 ? "s" : "") +
                " (restaurables en cas d'annulation)", a.travail), "attention") : Ligne("calendar-check-o", "Aucun évènement de travail à retirer.");
            html += a.equipe.length ? Ligne("users", "Absents dans ses groupes : " + a.equipe.map(function(e) { return "<strong>" + Echapper(e.nom) + "</strong> (" + Echapper(e.texte) + ")"; }).join(" · "), "attention")
                                    : Ligne("users", "Aucun autre membre de ses groupes n'est absent sur la période.");
        }
        $("#cg_tr_contenu").html(html);
        $("#cg_tr_refuser").prop("disabled", false);
        $("#cg_tr_valider").prop("disabled", !!(a.erreurs && a.erreurs.length));
    }

    function Decider(decision) {
        if (!Etat.traitement) { return; }
        var $boutons = $("#cg_tr_valider, #cg_tr_refuser").prop("disabled", true);
        Ajax(C.urls.decider, {iddemande: Etat.traitement.id, decision: decision, commentaire: $("#cg_tr_commentaire").val()}).done(function(data) {
            $("#cg_modal_traiter").modal("hide");
            toastr.success(data.message);
            Rafraichir();
        }).fail(function(xhr) {
            toastr.error(Message_erreur(xhr));
            $boutons.prop("disabled", false);
        });
    }

    function Annuler_demande(d) {
        var message = "<p>Annuler la demande de <strong>" + Echapper(d.collaborateur) + "</strong> (" + Echapper(d.type_nom) + ", " + Echapper(d.periode_txt) + ") ?</p>";
        if (d.etat === "VALIDEE") {
            message += "<p>Les absences créées dans le planning seront supprimées.</p>";
            if (d.retires) { message += "<div class='custom-control custom-checkbox'><input type='checkbox' class='custom-control-input' id='cg_an_restaurer' checked><label class='custom-control-label' for='cg_an_restaurer'>Restaurer les évènements de travail retirés lors de la validation</label></div>"; }
        }
        bootbox.confirm({title: "Annuler une demande", message: message, buttons: {confirm: {label: "Annuler la demande", className: "btn-danger"}, cancel: {label: "Fermer", className: "btn-default"}},
            callback: function(ok) {
                if (!ok) { return; }
                Ajax(C.urls.annuler, {iddemande: d.id, restaurer: $("#cg_an_restaurer").length ? $("#cg_an_restaurer").prop("checked") : false}).done(function(data) {
                    toastr.success(data.message);
                    Rafraichir();
                }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
            }});
    }

    // ------------------------------------------------------------------ Compteurs (page)
    function Init_compteurs() {
        $("#cg_cp_type").html(Options_types(C.types.length ? C.types[0].id : null, false));
        $("#cg_cp_groupe").append(C.groupes.map(function(g) { return "<option value='" + g.id + "'>" + Echapper(g.nom) + "</option>"; }).join(""));
        Maj_annees_compteurs();
        $("#cg_cp_type").on("change", function() { Maj_annees_compteurs(); Charger_compteurs(); });
        $("#cg_cp_annee, #cg_cp_groupe").on("change", Charger_compteurs);
        Charger_compteurs();
    }
    function Maj_annees_compteurs() { $("#cg_cp_annee").html(Options_annees(Type($("#cg_cp_type").val()))); }

    function Charger_compteurs() {
        if (!C.types.length) { $("#cg_compteurs").html("<tr><td colspan='6' class='text-muted'>Aucun type de congé n'est paramétré (Paramétrage > Collaborateurs > Types de congés).</td></tr>"); return; }
        Ajax(C.urls.compteurs, {idtype: $("#cg_cp_type").val(), annee: $("#cg_cp_annee").val(), idgroupe: $("#cg_cp_groupe").val() || 0}).done(function(data) {
            if (!data.lignes.length) { $("#cg_compteurs").html("<tr><td colspan='6' class='text-muted'>Aucun collaborateur.</td></tr>"); return; }
            $("#cg_compteurs").html(data.lignes.map(function(l) {
                return "<tr><td><a href='" + C.urls.fiche.replace(/0$/, l.c) + "'>" + Echapper(l.collaborateur) + "</a></td>" +
                    "<td class='text-right'>" + Echapper(l.droits_txt) + "</td><td class='text-right'>" + Echapper(l.poses_txt) + "</td>" +
                    "<td class='text-right" + (l.solde < 0 ? " text-danger" : "") + "'><strong>" + Echapper(l.solde_txt) + "</strong></td>" +
                    "<td class='text-right'>" + (l.attente ? Echapper(l.attente_txt) : "<span class='text-muted'>-</span>") + "</td>" +
                    "<td class='text-right" + (l.previsionnel < 0 ? " text-danger" : "") + "'>" + Echapper(l.previsionnel_txt) + "</td></tr>";
            }).join(""));
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Compteurs (fiche du collaborateur)
    function Charger_fiche() {
        Ajax(C.urls.compteurs, {idcollaborateur: C.idcollaborateur, annee: Etat.annee_fiche || 0}).done(function(data) {
            $("#cg_attribuer").prop("hidden", !data.modifiable || !C.types.length);
            $("#cg_transferer").prop("hidden", !data.modifiable || C.types.length < 2);
            Etat.lignes_fiche = data.lignes;
            if (!data.lignes.length) {
                $("#cg_fiche_compteurs").html("<p class='text-muted mb-0'>" + (C.types.length ? "Aucun compteur actif." : "Aucun type de congé n'est paramétré (Paramétrage > Collaborateurs > Types de congés).") + "</p>");
                return;
            }
            $("#cg_fiche_compteurs").html(Html_liste_compteurs(data.lignes, data.modifiable));
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    function Html_liste_compteurs(lignes, modifiable) {
        // Liste compacte : une ligne par type de congé, avec une jauge (posés en plein, en attente en hachuré) et le détail des droits dépliable
        var html = "<div class='cg-liste-tete' aria-hidden='true'><span>Type</span><span>Utilisation</span><span class='text-right'>Solde</span><span></span></div>";
        lignes.forEach(function(l) {
            var couleur = Echapper(l.couleur || "#3c8dbc");
            var base = Math.max(l.droits, l.poses + l.attente);
            var negatif = l.solde < 0;
            // Solde dépassé : la partie posée au-delà des droits est affichée en rouge
            var pct_poses = base > 0 ? Math.min(100, (negatif ? l.droits : l.poses) / base * 100) : 0;
            var pct_depasse = base > 0 && negatif ? Math.min(100 - pct_poses, (l.poses - l.droits) / base * 100) : 0;
            var pct_attente = base > 0 ? Math.min(100 - pct_poses - pct_depasse, l.attente / base * 100) : 0;
            var vide = !l.droits && !l.poses && !l.attente;
            var details = [];
            if (l.poses) { details.push(Echapper(l.poses_txt) + (l.unite === "HEURES" ? " posées" : " posés")); }
            if (l.attente) { details.push(Echapper(l.attente_txt) + " en attente"); }
            details.push(l.droits ? "droits " + Echapper(l.droits_txt) : "aucun droit attribué");
            var jauge = vide ? "<span class='cg-jauge-vide'>Aucun droit attribué sur cette période" +
                    (modifiable ? " · <button type='button' class='cg-lien' data-action='attribuer' data-type='" + l.type + "'>Attribuer des droits</button>" : "") + "</span>" :
                "<div class='cg-jauge" + (negatif ? " negatif" : "") + "' role='img' aria-label='" + Echapper(l.poses_txt + " posés sur " + l.droits_txt + (l.attente ? ", " + l.attente_txt + " en attente" : "")) + "'>" +
                    "<span style='width:" + pct_poses.toFixed(1) + "%;background:" + couleur + "'></span>" +
                    (pct_depasse ? "<span class='cg-jauge-depasse' style='width:" + pct_depasse.toFixed(1) + "%'></span>" : "") +
                    (pct_attente ? "<span class='cg-jauge-attente' style='width:" + pct_attente.toFixed(1) + "%;background-color:" + couleur + "'></span>" : "") + "</div>" +
                "<small class='text-muted'>" + details.join(" · ") + "</small>";
            var impact = l.attente ? "<span class='cg-impact" + (l.previsionnel < 0 ? " negatif" : "") + "' title='Solde après validation des demandes en attente : " + Echapper(l.previsionnel_txt) + "'>−" + Echapper(l.attente_txt) + "</span>" : "";
            var droits = l.droits_detail.map(function(d) {
                return "<tr><td>" + Echapper(d.nature) + "</td><td class='text-right'><strong>" + Echapper(d.valeur_txt) + "</strong></td><td>" + Echapper(d.motif || "") + "</td><td class='text-muted'>" + d.date + "</td>" +
                    (modifiable ? "<td class='text-right'><button type='button' class='cg-lien text-danger' data-action='supprimer-droit' data-id='" + d.id + "' aria-label='Supprimer ce droit' title='Supprimer'><i class='fa fa-trash'></i></button></td>" : "") + "</tr>";
            }).join("");
            html += "<details class='cg-liste-ligne'><summary>" +
                "<span class='cg-liste-type'><i class='fa fa-chevron-right cg-chevron' aria-hidden='true'></i><span class='cg-pastille' style='background:" + couleur + "'></span>" +
                    "<span><strong>" + Echapper(l.nom) + "</strong><small class='text-muted d-block'>" + Echapper(l.periode) + "</small></span></span>" +
                "<span class='cg-liste-jauge'>" + jauge + "</span>" +
                "<span class='cg-liste-solde" + (negatif ? " text-danger" : "") + "'>" + Echapper(l.solde_txt) + "</span>" +
                "<span>" + impact + "</span></summary>" +
                "<div class='cg-liste-detail'>" + (droits ?
                    "<table class='table table-sm mb-0 cg-table-droits'><thead><tr><th>Origine</th><th class='text-right'>Valeur</th><th>Motif</th><th>Saisi le</th>" + (modifiable ? "<th><span class='sr-only'>Actions</span></th>" : "") + "</tr></thead><tbody>" + droits + "</tbody></table>" :
                    "<p class='text-muted small mb-0'>Aucun droit attribué sur cette période.</p>") +
                    (l.attente ? "<p class='small mb-0 mt-1'>Solde après validation des demandes en attente : <strong class='" + (l.previsionnel < 0 ? "text-danger" : "") + "'>" + Echapper(l.previsionnel_txt) + "</strong></p>" : "") +
                "</div></details>";
        });
        return "<div class='cg-liste'>" + html + "</div>";
    }

    // ------------------------------------------------------------------ Attribution de droits
    function Ouvrir_droits(idtype_force) {
        var idtype = typeof idtype_force === "number" ? idtype_force : (C.mode === "compteurs" ? +$("#cg_cp_type").val() : (C.types.length ? C.types[0].id : null));
        $("#cg_dr_type").html(Options_types(idtype, true));
        Maj_droits_type(C.mode === "compteurs" ? +$("#cg_cp_annee").val() : Etat.annee_fiche);
        $("#cg_dr_nature").val("DROIT");
        $("#cg_dr_valeur, #cg_dr_motif").val("");
        $("#cg_dr_collabs_bloc").prop("hidden", C.mode === "fiche");
        if (C.mode !== "fiche") {
            var groupes = C.groupes.map(function(g) { return {id: "g" + g.id, text: g.nom + " (groupe)"}; });
            var collabs = C.collaborateurs.filter(function(c) { return c.modifiable; }).map(function(c) { return {id: "c" + c.id, text: c.nom}; });
            var $select = $("#cg_dr_collabs");
            if ($select.data("select2")) { $select.select2("destroy"); }
            $select.empty().select2({data: [{id: "tous", text: "Tous les collaborateurs"}, {text: "Groupes", children: groupes}, {text: "Collaborateurs", children: collabs}],
                                     placeholder: "Sélectionnez des collaborateurs ou des groupes", language: "fr", width: "100%", theme: "bootstrap4", dropdownParent: $("#cg_modal_droits")});
            if (+$("#cg_cp_groupe").val()) { $select.val(["g" + $("#cg_cp_groupe").val()]).trigger("change"); }
        }
        $("#cg_modal_droits").modal("show");
    }
    function Maj_droits_type(annee) {
        var type = Type($("#cg_dr_type").val());
        $("#cg_dr_annee").html(Options_annees(type, annee));
        $("#cg_dr_unite").text(type ? (type.unite === "HEURES" ? "(heures)" : "(jours)") : "");
    }
    function Enregistrer_droits() {
        var ids = [];
        if (C.mode === "fiche") { ids = [C.idcollaborateur]; }
        else {
            ($("#cg_dr_collabs").val() || []).forEach(function(valeur) {
                if (valeur === "tous") { C.collaborateurs.forEach(function(c) { if (c.modifiable) { ids.push(c.id); } }); }
                else if (valeur.charAt(0) === "g") { var g = C.groupes.find(function(g) { return g.id === +valeur.substr(1); }); if (g) { ids = ids.concat(g.collaborateurs); } }
                else { ids.push(+valeur.substr(1)); }
            });
        }
        Ajax(C.urls.droits, {idtype: $("#cg_dr_type").val(), annee: $("#cg_dr_annee").val(), nature: $("#cg_dr_nature").val(), valeur: $("#cg_dr_valeur").val(),
                             motif: $("#cg_dr_motif").val(), collaborateurs: JSON.stringify(Array.from(new Set(ids)))}).done(function(data) {
            $("#cg_modal_droits").modal("hide");
            toastr.success(data.message);
            Rafraichir();
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Transfert entre compteurs (fiche)
    function Ouvrir_transfert() {
        var lignes = Etat.lignes_fiche || [];
        // Origine par défaut : premier compteur avec un solde positif ; destination : un compte épargne-temps s'il existe
        var source = (lignes.find(function(l) { return l.solde > 0; }) || lignes[0] || {}).type || (C.types[0] || {}).id;
        var cet = C.types.find(function(t) { return t.id !== source && /pargne|CET/i.test(t.nom); });
        var destination = cet ? cet.id : (C.types.find(function(t) { return t.id !== source; }) || {}).id;
        $("#cg_tr_source").html(Options_types(source, false));
        $("#cg_tr_destination").html(Options_types(destination, true));
        $("#cg_tr_valeur, #cg_tr_motif").val("");
        Maj_transfert(true);
        $("#cg_modal_transfert").modal("show");
    }
    function Maj_transfert(periodes) {
        var source = Type($("#cg_tr_source").val()), destination = Type($("#cg_tr_destination").val());
        if (periodes) {
            $("#cg_tr_annee_source").html(Options_annees(source, Etat.annee_fiche));
            $("#cg_tr_annee_destination").html(Options_annees(destination, destination ? destination.annee : null));
        }
        $("#cg_tr_unite").text(source && source.unite === "HEURES" ? "(heures)" : "(jours)");
        var $info = $("#cg_tr_info").removeClass("text-danger");
        if (source && destination && source.unite !== destination.unite) { $info.addClass("text-danger").text("Les deux compteurs doivent avoir la même unité."); return; }
        if (source && destination && source.id === destination.id) { $info.addClass("text-danger").text("Choisissez deux compteurs différents."); return; }
        var ligne = (Etat.lignes_fiche || []).find(function(l) { return source && l.type === source.id && l.annee === +$("#cg_tr_annee_source").val(); });
        $info.html(ligne ? "Solde disponible sur " + Echapper(ligne.nom) + " " + Echapper(ligne.periode) + " : <strong>" + Echapper(ligne.previsionnel_txt) + "</strong>" + (ligne.attente ? " (demandes en attente déduites)" : "") : "");
    }
    function Valider_transfert() {
        Ajax(C.urls.transferer, {idcollaborateur: C.idcollaborateur, idsource: $("#cg_tr_source").val(), iddestination: $("#cg_tr_destination").val(),
                                 annee_source: $("#cg_tr_annee_source").val(), annee_destination: $("#cg_tr_annee_destination").val(),
                                 valeur: $("#cg_tr_valeur").val(), motif: $("#cg_tr_motif").val()}).done(function(data) {
            $("#cg_modal_transfert").modal("hide");
            toastr.success(data.message);
            Rafraichir();
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Report des soldes (page des compteurs)
    function Ids_selection(valeurs) {
        var ids = [];
        (valeurs || []).forEach(function(valeur) {
            if (valeur === "tous") { C.collaborateurs.forEach(function(c) { if (c.modifiable) { ids.push(c.id); } }); }
            else if (valeur.charAt(0) === "g") { var g = C.groupes.find(function(g) { return g.id === +valeur.substr(1); }); if (g) { ids = ids.concat(g.collaborateurs); } }
            else { ids.push(+valeur.substr(1)); }
        });
        return Array.from(new Set(ids));
    }
    function Ouvrir_report() {
        var idtype = +$("#cg_cp_type").val();
        $("#cg_rp_type").html(Options_types(idtype, false));
        Maj_report_periodes(+$("#cg_cp_annee").val());
        $("#cg_rp_plafond").val("");
        $("#cg_rp_negatifs").prop("checked", false);
        var groupes = C.groupes.map(function(g) { return {id: "g" + g.id, text: g.nom + " (groupe)"}; });
        var collabs = C.collaborateurs.filter(function(c) { return c.modifiable; }).map(function(c) { return {id: "c" + c.id, text: c.nom}; });
        var $select = $("#cg_rp_collabs");
        if ($select.data("select2")) { $select.select2("destroy"); }
        $select.empty().select2({data: [{id: "tous", text: "Tous les collaborateurs"}, {text: "Groupes", children: groupes}, {text: "Collaborateurs", children: collabs}],
                                 placeholder: "Sélectionnez des collaborateurs ou des groupes", language: "fr", width: "100%", theme: "bootstrap4", dropdownParent: $("#cg_modal_report")});
        $select.val([+$("#cg_cp_groupe").val() ? "g" + $("#cg_cp_groupe").val() : "tous"]).trigger("change.select2");
        $("#cg_modal_report").modal("show");
        Apercu_report();
    }
    function Maj_report_periodes(selection) {
        var type = Type($("#cg_rp_type").val());
        // Par défaut, la période précédant la période en cours
        $("#cg_rp_annee").html(Options_annees(type, selection || (type ? type.annee - 1 : null)));
    }
    function Parametres_report() {
        return {idtype: $("#cg_rp_type").val(), annee: $("#cg_rp_annee").val(), plafond: $("#cg_rp_plafond").val(), negatifs: $("#cg_rp_negatifs").prop("checked") ? 1 : 0,
                collaborateurs: JSON.stringify(Ids_selection($("#cg_rp_collabs").val()))};
    }
    var Apercu_report = Debounce(function() {
        var $apercu = $("#cg_rp_apercu"), parametres = Parametres_report();
        $("#cg_rp_valider").prop("disabled", true);
        if (parametres.collaborateurs === "[]") { $apercu.html("<p class='text-muted small mb-0'>Sélectionnez des collaborateurs.</p>"); return; }
        Ajax(C.urls.reporter, $.extend({apercu: 1}, parametres)).done(function(data) {
            var type = Type(parametres.idtype), ignores = [];
            if (data.ignores.deja) { ignores.push(data.ignores.deja + " déjà reporté" + (data.ignores.deja > 1 ? "s" : "")); }
            if (data.ignores.nul) { ignores.push(data.ignores.nul + " solde" + (data.ignores.nul > 1 ? "s" : "") + " nul" + (data.ignores.nul > 1 ? "s" : "")); }
            if (data.ignores.negatif) { ignores.push(data.ignores.negatif + " solde" + (data.ignores.negatif > 1 ? "s" : "") + " négatif" + (data.ignores.negatif > 1 ? "s" : "")); }
            var html = "<div class='cg-rp-resume'><strong>" + data.lignes.length + " report" + (data.lignes.length > 1 ? "s" : "") + "</strong> de " + Echapper(data.periode_source) +
                " vers " + Echapper(data.periode_suivante) + (data.lignes.length ? " · total " + Echapper(data.total_txt) : "") +
                (ignores.length ? "<span class='text-muted'> · ignorés : " + ignores.join(", ") + "</span>" : "") + "</div>";
            if (data.lignes.length) {
                html += "<div class='cg-rp-liste'><table class='table table-sm mb-0'><thead><tr><th>Collaborateur</th><th class='text-right'>Solde " + Echapper(data.periode_source) + "</th><th class='text-right'>Reporté</th></tr></thead><tbody>" +
                    data.lignes.map(function(l) {
                        return "<tr><td>" + Echapper(l.collaborateur) + "</td><td class='text-right'>" + Echapper(l.solde_txt) + "</td><td class='text-right'><strong>" + Echapper(l.valeur_txt) + "</strong>" +
                            (l.plafonne ? " <span class='badge badge-warning' title='Valeur limitée par le plafond'>plafonné</span>" : "") + "</td></tr>";
                    }).join("") + "</tbody></table></div>";
            }
            $apercu.html(html);
            $("#cg_rp_valider").prop("disabled", !data.lignes.length);
        }).fail(function(xhr) { $apercu.html("<p class='text-danger small mb-0'>" + Echapper(Message_erreur(xhr)) + "</p>"); });
    }, 300);
    function Valider_report() {
        var $bouton = $("#cg_rp_valider").prop("disabled", true);
        Ajax(C.urls.reporter, Parametres_report()).done(function(data) {
            $("#cg_modal_report").modal("hide");
            toastr.success(data.message);
            Rafraichir();
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); $bouton.prop("disabled", false); });
    }

    // ------------------------------------------------------------------ Initialisation
    $(function() {
        if ($("#cg_demandes").length) {
            $(".cg-filtres [data-etat]").on("click", function() {
                Etat.filtre = this.getAttribute("data-etat");
                $(".cg-filtres [data-etat]").each(function() { var actif = this.getAttribute("data-etat") === Etat.filtre; $(this).toggleClass("active", actif).attr("aria-pressed", String(actif)); });
                Charger_demandes();
            });
            $("#cg_nouvelle").on("click", function() { Ouvrir_demande(null); });
            $("#cg_demandes").on("click", "[data-action]", function() {
                var d = Etat.demandes.find(function(x) { return x.id === +this.getAttribute("data-id"); }, this);
                if (!d) { return; }
                var action = this.getAttribute("data-action");
                if (action === "traiter") { Ouvrir_traitement(d.id); }
                if (action === "modifier") { Ouvrir_demande(d); }
                if (action === "annuler") { Annuler_demande(d); }
            });
            Charger_demandes();
        }

        // Fenêtre de saisie d'une demande
        $("#cg_dem_collab").select2({placeholder: "Sélectionnez un collaborateur", language: "fr", width: "100%", theme: "bootstrap4", dropdownParent: $("#cg_modal_demande")});
        $("#cg_modal_demande").on("change input", "input, select, textarea", Maj_formulaire_demande);
        $("#cg_dem_debut").on("change", function() { if (!$("#cg_dem_fin").val() || $("#cg_dem_fin").val() < this.value) { $("#cg_dem_fin").val(this.value); Maj_formulaire_demande(); } });
        $("#cg_dem_enregistrer").on("click", function() { Enregistrer_demande(false); });
        $("#cg_dem_traiter").on("click", function() { Enregistrer_demande(true); });

        // Fenêtre de traitement
        $("#cg_tr_valider").on("click", function() { Decider("valider"); });
        $("#cg_tr_refuser").on("click", function() { Decider("refuser"); });

        // Droits
        $("#cg_attribuer").on("click", Ouvrir_droits);
        $("#cg_dr_type").on("change", function() { Maj_droits_type(+$("#cg_dr_annee").val()); });
        $("#cg_dr_enregistrer").on("click", Enregistrer_droits);
        $("#cg_transferer").on("click", Ouvrir_transfert);
        $("#cg_tr_source, #cg_tr_destination").on("change", function() { Maj_transfert(true); });
        $("#cg_tr_annee_source").on("change", function() { Maj_transfert(false); });
        $("#cg_tr_valider").on("click", Valider_transfert);
        $("#cg_reporter").on("click", Ouvrir_report);
        $("#cg_rp_type").on("change", function() { Maj_report_periodes(); Apercu_report(); });
        $("#cg_rp_annee, #cg_rp_collabs, #cg_rp_negatifs").on("change", Apercu_report);
        $("#cg_rp_plafond").on("input", Apercu_report);
        $("#cg_rp_valider").on("click", Valider_report);

        if ($("#cg_compteurs").length) { Init_compteurs(); }
        if ($("#cg_fiche_compteurs").length) {
            var courante = C.types.length ? C.types[0].annee : +C.aujourdhui.substr(0, 4);
            Etat.annee_fiche = courante;
            $("#cg_fi_annee").html(Options_annees(C.types.length && C.types.every(function(t) { return t.mois_debut === C.types[0].mois_debut; }) ? C.types[0] : null, courante))
                .on("change", function() { Etat.annee_fiche = +this.value; Charger_fiche(); });
            $("#cg_fiche_compteurs").on("click", "[data-action='attribuer']", function(e) { e.preventDefault(); Ouvrir_droits(+this.getAttribute("data-type")); });
            $("#cg_fiche_compteurs").on("click", "[data-action='supprimer-droit']", function() {
                var id = this.getAttribute("data-id");
                bootbox.confirm({title: "Supprimer un droit", message: "Supprimer ce droit ?", buttons: {confirm: {label: "Supprimer", className: "btn-danger"}, cancel: {label: "Annuler"}}, callback: function(ok) {
                    if (ok) { Ajax(C.urls.supprimer_droit, {iddroit: id}).done(Rafraichir).fail(function(xhr) { toastr.error(Message_erreur(xhr)); }); }
                }});
            });
            Charger_fiche();
        }
    });
})(jQuery);
