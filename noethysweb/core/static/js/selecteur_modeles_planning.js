//  Copyright (c) 2019-2021 Ivan LUCAS.
//  Noethysweb, application de gestion multi-activités.
//  Distribué sous licence GNU GPL.

// Sélecteur compact de modèles de planning : recherche, liste défilante, pastilles des modèles choisis,
// modèles récents en tête, nombre de collaborateurs concernés et avertissements pour les modèles non proposés.
//
// var selecteur = SelecteurModelesPlanning({conteneur: "#id", url: "...", csrf: "...",
//     parametres: function() { return {collaborateurs: [1, 2], date: "2026-11-16"}; }, change: function(ids) {}});
// selecteur.maj(); selecteur.selection(); selecteur.forcer(); selecteur.reinitialiser([ids]);

(function() {
    var STYLE = "" +
        ".smp-pastilles {display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px;}" +
        ".smp-pastille {display: inline-flex; align-items: center; gap: 6px; background: #e6f1fb; color: #0c447c; border-radius: 4px; padding: 2px 4px 2px 8px; font-size: 0.82rem;}" +
        ".smp-pastille.smp-hors {background: #fff3cd; color: #856404;}" +
        ".smp-pastille button {border: 0; background: none; color: inherit; padding: 0 4px; line-height: 1; font-size: 1rem; cursor: pointer;}" +
        ".smp-barre {display: flex; gap: 6px;}" +
        ".smp-barre input[type=search] {flex: 1;}" +
        ".smp-filtre .btn.active {background: #3c8dbc; color: #fff; border-color: #3c8dbc;}" +
        ".smp-liste {border: 1px solid #ced4da; border-radius: 4px; max-height: 232px; overflow-y: auto; margin-top: 6px; background: #fff;}" +
        ".smp-groupe {font-size: 0.72rem; color: #6c757d; text-transform: uppercase; letter-spacing: .03em; padding: 5px 10px 2px; background: #f4f6f9; position: sticky; top: 0; z-index: 1;}" +
        ".smp-item {display: grid; grid-template-columns: 18px minmax(0, 1fr) auto auto; gap: 8px; align-items: center; padding: 5px 10px; border-top: 1px solid #f1f1f1; margin: 0; cursor: pointer; font-weight: normal;}" +
        ".smp-item:hover, .smp-item.smp-focus {background: #f0f6fb;}" +
        ".smp-item.smp-non-propose .smp-nom {color: #6c757d;}" +
        ".smp-sous {display: block; font-size: 0.75rem; color: #6c757d;}" +
        ".smp-cycle {font-size: 0.72rem; background: #eeedfe; color: #3c3489; border-radius: 4px; padding: 1px 6px; white-space: nowrap;}" +
        ".smp-elig {font-size: 0.75rem; white-space: nowrap; color: #495057; min-width: 46px; text-align: right;}" +
        ".smp-elig.smp-partiel {color: #b26a00;} .smp-elig.smp-aucun {color: #b02a37;}" +
        ".smp-vide {padding: 10px; color: #6c757d; font-size: 0.85rem;}" +
        ".smp-alerte {background: #fff3cd; color: #856404; border-radius: 4px; padding: 6px 10px; margin-top: 6px; font-size: 0.82rem;}" +
        ".smp-alerte ul {margin: 2px 0 0; padding-left: 18px;}";

    function Injecter_style() {
        if (document.getElementById("smp_style")) { return; }
        var style = document.createElement("style");
        style.id = "smp_style";
        style.textContent = STYLE;
        document.head.appendChild(style);
    }

    function Echapper(texte) {
        return $("<div>").text(texte === null || texte === undefined ? "" : String(texte)).html();
    }

    function Normaliser(texte) {
        return String(texte || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }

    function Heures(valeur) {
        if (!valeur) { return ""; }
        var minutes = Math.round(valeur * 60);
        return Math.floor(minutes / 60) + " h" + (minutes % 60 ? " " + ("0" + (minutes % 60)).slice(-2) : "");
    }

    var compteur = 0;

    window.SelecteurModelesPlanning = function(options) {
        Injecter_style();
        var uid = "smp" + (++compteur);
        var $conteneur = $(options.conteneur);
        var etat = {modeles: [], nbre_collaborateurs: 0, selection: (options.selection || []).map(Number), filtre: "proposes", recherche: "", forcer: false, charge: false};
        var requete = null, minuteur = null;

        $conteneur.html(
            "<div class='smp'>" +
            "<div class='smp-pastilles' id='" + uid + "_pastilles' aria-live='polite'></div>" +
            "<div class='smp-barre'>" +
            "<input type='search' class='form-control form-control-sm' id='" + uid + "_recherche' placeholder='Rechercher un modèle' aria-label='Rechercher un modèle de planning' autocomplete='off'>" +
            "<div class='btn-group btn-group-sm smp-filtre' role='group' aria-label='Modèles affichés'>" +
            "<button type='button' class='btn btn-default active' data-filtre='proposes' aria-pressed='true'>Proposés</button>" +
            "<button type='button' class='btn btn-default' data-filtre='tous' aria-pressed='false'>Tous</button></div></div>" +
            "<div class='smp-liste' id='" + uid + "_liste' role='group' aria-label='Modèles de planning'><div class='smp-vide'>Chargement…</div></div>" +
            "<div id='" + uid + "_alertes'></div>" +
            "</div>");
        var $liste = $("#" + uid + "_liste"), $pastilles = $("#" + uid + "_pastilles"), $alertes = $("#" + uid + "_alertes"), $recherche = $("#" + uid + "_recherche");

        function Modele(id) { return etat.modeles.find(function(m) { return m.id === id; }); }

        function Est_propose(modele) {
            return etat.nbre_collaborateurs === 0 || modele.eligibles === null || modele.eligibles > 0;
        }

        function Ligne(modele) {
            var coche = etat.selection.indexOf(modele.id) >= 0;
            var propose = Est_propose(modele);
            var sous = [];
            if (modele.heures) { sous.push(Heures(modele.heures) + " / sem."); }
            if (modele.restreint) { sous.push((propose ? "Proposé à : " : "Réservé à : ") + modele.restriction); }
            var elig = "";
            if (etat.nbre_collaborateurs > 1 && modele.eligibles !== null) {
                var classe = modele.eligibles === 0 ? " smp-aucun" : (modele.eligibles < etat.nbre_collaborateurs ? " smp-partiel" : "");
                elig = "<span class='smp-elig" + classe + "' title='Collaborateurs à qui ce modèle est proposé'><i class='fa fa-users' aria-hidden='true'></i> "
                    + modele.eligibles + " / " + etat.nbre_collaborateurs + "<span class='sr-only'> collaborateurs concernés</span></span>";
            } else if (!propose) {
                elig = "<span class='smp-elig smp-aucun'>Non proposé</span>";
            } else {
                elig = "<span class='smp-elig'></span>";
            }
            return "<label class='smp-item" + (propose ? "" : " smp-non-propose") + "' data-id='" + modele.id + "'>" +
                "<input type='checkbox' value='" + modele.id + "'" + (coche ? " checked" : "") + ">" +
                "<span><span class='smp-nom'>" + Echapper(modele.nom) + "</span>" + (sous.length ? "<span class='smp-sous'>" + Echapper(sous.join(" · ")) + "</span>" : "") + "</span>" +
                "<span class='smp-cycle'>" + Echapper(modele.nb_semaines > 1 ? modele.nb_semaines + " sem." : "1 sem.") + "</span>" + elig + "</label>";
        }

        function Afficher_liste() {
            var recherche = Normaliser(etat.recherche);
            var visibles = etat.modeles.filter(function(m) {
                if (recherche && Normaliser(m.nom + " " + (m.restriction || "")).indexOf(recherche) < 0) { return false; }
                return etat.filtre === "tous" || Est_propose(m) || etat.selection.indexOf(m.id) >= 0;
            });
            var recents = visibles.filter(function(m) { return m.recent !== null && Est_propose(m); }).sort(function(a, b) { return a.recent - b.recent; });
            var autres = visibles.filter(function(m) { return m.recent === null && Est_propose(m); });
            var non_proposes = visibles.filter(function(m) { return !Est_propose(m); });
            var html = "";
            if (recents.length && !recherche) {
                html += "<div class='smp-groupe'>Utilisés récemment</div>" + recents.map(Ligne).join("");
                html += autres.length ? "<div class='smp-groupe'>Autres modèles proposés</div>" + autres.map(Ligne).join("") : "";
            } else {
                var proposes = recents.concat(autres).sort(function(a, b) { return a.nom.localeCompare(b.nom); });
                html += proposes.length ? "<div class='smp-groupe'>" + (etat.nbre_collaborateurs ? "Modèles proposés" : "Modèles") + "</div>" + proposes.map(Ligne).join("") : "";
            }
            if (non_proposes.length) {
                html += "<div class='smp-groupe'>Non proposés pour " + (etat.nbre_collaborateurs > 1 ? "ces collaborateurs" : "ce collaborateur") + "</div>" + non_proposes.map(Ligne).join("");
            }
            if (!html) {
                html = "<div class='smp-vide'>" + (recherche ? "Aucun modèle ne correspond à « " + Echapper(etat.recherche) + " »." : "Aucun modèle proposé. Cliquez sur « Tous » pour afficher les autres modèles.") + "</div>";
            }
            $liste.html(html);
            var nbre_proposes = etat.modeles.filter(Est_propose).length;
            $conteneur.find("[data-filtre='proposes']").text("Proposés · " + nbre_proposes);
            $conteneur.find("[data-filtre='tous']").text("Tous · " + etat.modeles.length);
        }

        function Afficher_selection() {
            $pastilles.html(etat.selection.map(function(id) {
                var modele = Modele(id);
                if (!modele) { return ""; }
                var hors = !Est_propose(modele) || (etat.nbre_collaborateurs > 1 && modele.eligibles !== null && modele.eligibles < etat.nbre_collaborateurs);
                return "<span class='smp-pastille" + (hors ? " smp-hors" : "") + "'>" + Echapper(modele.nom) +
                    "<button type='button' data-retirer='" + id + "' aria-label='Retirer " + Echapper(modele.nom) + "'>&times;</button></span>";
            }).join(""));

            // Avertissements
            var partiels = [], exceptions = [];
            etat.selection.forEach(function(id) {
                var modele = Modele(id);
                if (!modele || modele.eligibles === null || !etat.nbre_collaborateurs) { return; }
                if (modele.eligibles === 0) { exceptions.push(modele); }
                else if (modele.eligibles < etat.nbre_collaborateurs) { partiels.push(modele); }
            });
            var html = "";
            if (exceptions.length || partiels.length) {
                html += "<div class='smp-alerte' role='status'><i class='fa fa-exclamation-triangle margin-r-5' aria-hidden='true'></i><ul>";
                exceptions.forEach(function(m) {
                    html += "<li><strong>" + Echapper(m.nom) + "</strong> n'est pas proposé " + (etat.nbre_collaborateurs > 1 ? "à ces collaborateurs" : "à ce collaborateur")
                        + " (réservé à : " + Echapper(m.restriction) + "). Il sera appliqué à titre exceptionnel.</li>";
                });
                partiels.forEach(function(m) {
                    html += etat.forcer
                        ? "<li><strong>" + Echapper(m.nom) + "</strong> sera appliqué aux " + etat.nbre_collaborateurs + " collaborateurs, y compris ceux à qui il n'est pas proposé.</li>"
                        : "<li><strong>" + Echapper(m.nom) + "</strong> ne sera appliqué " + (m.eligibles > 1 ? "qu'aux " + m.eligibles + " collaborateurs" : "qu'à 1 collaborateur")
                          + " sur " + etat.nbre_collaborateurs + " à qui il est proposé.</li>";
                });
                html += "</ul>";
                if (partiels.length) {
                    html += "<label class='mb-0 mt-1' style='font-weight: normal;'><input type='checkbox' class='smp-forcer'" + (etat.forcer ? " checked" : "") + "> Appliquer aussi aux collaborateurs à qui ces modèles ne sont pas proposés</label>";
                }
                html += "</div>";
            }
            $alertes.html(html);
        }

        function Notifier() {
            Afficher_selection();
            if (options.change) { options.change(etat.selection.slice(), etat.forcer); }
        }

        function Charger() {
            var parametres = options.parametres ? options.parametres() : {};
            if (requete) { requete.abort(); }
            requete = $.ajax({url: options.url, type: "POST", dataType: "json", data: {
                csrfmiddlewaretoken: options.csrf, collaborateurs: JSON.stringify(parametres.collaborateurs || []), date: parametres.date || ""
            }}).done(function(data) {
                etat.modeles = data.modeles;
                etat.nbre_collaborateurs = data.nbre_collaborateurs;
                etat.selection = etat.selection.filter(function(id) { return Modele(id); });
                etat.charge = true;
                Afficher_liste();
                Notifier();
            }).fail(function(xhr) {
                if (xhr.statusText === "abort") { return; }
                $liste.html("<div class='smp-vide'>Impossible de charger la liste des modèles.</div>");
            });
        }

        // Evénements
        $liste.on("change", "input[type=checkbox]", function() {
            var id = Number(this.value);
            if (this.checked) { if (etat.selection.indexOf(id) < 0) { etat.selection.push(id); } }
            else { etat.selection = etat.selection.filter(function(x) { return x !== id; }); }
            Notifier();
        });
        $pastilles.on("click", "[data-retirer]", function() {
            var id = Number($(this).data("retirer"));
            etat.selection = etat.selection.filter(function(x) { return x !== id; });
            $liste.find("input[value='" + id + "']").prop("checked", false);
            Notifier();
            $recherche.focus();
        });
        $alertes.on("change", ".smp-forcer", function() { etat.forcer = this.checked; Notifier(); });
        $conteneur.on("click", "[data-filtre]", function() {
            etat.filtre = $(this).data("filtre");
            $conteneur.find("[data-filtre]").each(function() { var actif = $(this).data("filtre") === etat.filtre; $(this).toggleClass("active", actif).attr("aria-pressed", actif); });
            Afficher_liste();
        });
        $recherche.on("input", function() { etat.recherche = this.value; Afficher_liste(); });
        $recherche.on("keydown", function(e) {
            if (e.key === "Enter") {
                e.preventDefault();
                var premier = $liste.find("input[type=checkbox]:not(:checked)").first();
                if (premier.length) { premier.prop("checked", true).trigger("change"); }
            }
            if (e.key === "ArrowDown") { e.preventDefault(); $liste.find("input[type=checkbox]").first().focus(); }
        });
        $liste.on("keydown", "input[type=checkbox]", function(e) {
            var cases = $liste.find("input[type=checkbox]"), index = cases.index(this);
            if (e.key === "ArrowDown" && index < cases.length - 1) { e.preventDefault(); cases.eq(index + 1).focus(); }
            if (e.key === "ArrowUp") { e.preventDefault(); index > 0 ? cases.eq(index - 1).focus() : $recherche.focus(); }
            if (e.key === "Enter") { e.preventDefault(); $(this).prop("checked", !this.checked).trigger("change"); }
        });
        $liste.on("focus", "input[type=checkbox]", function() { $(this).closest(".smp-item").addClass("smp-focus"); });
        $liste.on("blur", "input[type=checkbox]", function() { $(this).closest(".smp-item").removeClass("smp-focus"); });

        return {
            maj: function() { clearTimeout(minuteur); minuteur = setTimeout(Charger, 200); },
            selection: function() { return etat.selection.slice(); },
            forcer: function() { return etat.forcer; },
            reinitialiser: function(selection) {
                etat.selection = (selection || []).map(Number); etat.forcer = false; etat.recherche = ""; $recherche.val("");
                etat.filtre = "proposes";
                $conteneur.find("[data-filtre]").each(function() { var actif = $(this).data("filtre") === "proposes"; $(this).toggleClass("active", actif).attr("aria-pressed", actif); });
                Charger();
            }
        };
    };
})();
