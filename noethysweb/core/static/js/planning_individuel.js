/*  Copyright (c) 2019-2026 Ivan LUCAS.
    Noethysweb, application de gestion multi-activités.
    Distribué sous licence GNU GPL.
    Planning individuel annuel d'un collaborateur (vues calendrier, colonnes par mois et mois x jours) */

(function($) {
    "use strict";

    var CFG = window.PLANNING_INDIVIDUEL;
    var JOURS_COURTS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
    var JOURS_LETTRES = ["L", "M", "M", "J", "V", "S", "D"];
    var JOURS_LONGS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
    var MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
    var MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
    var VUES = {calendrier: "Calendrier", colonnes: "Colonnes", mois: "Mois × jours"};

    // ------------------------------------------------------------------ Outils
    function Echapper(texte) {
        return String(texte === null || texte === undefined ? "" : texte).replace(/[&<>"']/g, function(c) {
            return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
        });
    }
    function Pad(n) { return (n < 10 ? "0" : "") + n; }
    // Dates en minutes depuis l'epoch (heure locale "naïve" traitée comme UTC), jours en nombre de jours depuis l'epoch
    function Parse_min(texte) {
        if (!texte) { return null; }
        var p = texte.split(/[- :T]/);
        return Date.UTC(+p[0], +p[1] - 1, +p[2], +(p[3] || 0), +(p[4] || 0)) / 60000;
    }
    function Format_min(m) {
        var d = new Date(m * 60000);
        return d.getUTCFullYear() + "-" + Pad(d.getUTCMonth() + 1) + "-" + Pad(d.getUTCDate()) + " " + Pad(d.getUTCHours()) + ":" + Pad(d.getUTCMinutes());
    }
    function Jour_de(m) { return Math.floor(m / 1440); }
    function Parse_jour(texte) { return Math.floor(Date.UTC(+texte.substr(0, 4), +texte.substr(5, 2) - 1, +texte.substr(8, 2)) / 86400000); }
    function Iso_jour(j) { var d = new Date(j * 86400000); return d.getUTCFullYear() + "-" + Pad(d.getUTCMonth() + 1) + "-" + Pad(d.getUTCDate()); }
    function Jour_semaine(j) { return (new Date(j * 86400000).getUTCDay() + 6) % 7; }
    function Infos_jour(j) { var d = new Date(j * 86400000); return {a: d.getUTCFullYear(), m: d.getUTCMonth(), j: d.getUTCDate()}; }
    function Jour_depuis(a, m, j) { return Math.floor(Date.UTC(a, m, j) / 86400000); }
    function Nbre_jours_mois(a, m) { return new Date(Date.UTC(a, m + 1, 0)).getUTCDate(); }
    function Texte_jour_long(j) { var i = Infos_jour(j); return JOURS_LONGS[Jour_semaine(j)] + " " + i.j + " " + MOIS[i.m] + " " + i.a; }
    function Texte_jour_court(j) { var i = Infos_jour(j); return JOURS_COURTS[Jour_semaine(j)].toLowerCase() + ". " + i.j + " " + MOIS_COURTS[i.m]; }
    function Texte_jour_fr(j) { var i = Infos_jour(j); return Pad(i.j) + "/" + Pad(i.m + 1) + "/" + i.a; }
    function Heure(m) { m = ((m % 1440) + 1440) % 1440; return Pad(Math.floor(m / 60)) + ":" + Pad(m % 60); }
    function Heure_courte(m) { m = ((m % 1440) + 1440) % 1440; return Pad(Math.floor(m / 60)) + "h" + Pad(m % 60); }
    function Minutes_heure(texte) { if (!texte) { return null; } var p = texte.split(":"); return +p[0] * 60 + +p[1]; }
    function Duree(minutes) {
        var signe = minutes < 0 ? "-" : "";
        minutes = Math.round(Math.abs(minutes));
        var h = Math.floor(minutes / 60), m = minutes % 60;
        return signe + h + "h" + (m ? Pad(m) : "");
    }
    function Valeur(v, unite) {
        if ((unite || S.objectif.unite) === "jours") {
            var r = Math.round(v * 10) / 10;
            return String(r).replace(".", ",") + " j";
        }
        return Duree(v * 60);
    }
    function Debounce(fonction, delai) {
        var minuteur = null;
        return function() { var args = arguments, ctx = this; clearTimeout(minuteur); minuteur = setTimeout(function() { fonction.apply(ctx, args); }, delai); };
    }
    function Ajax(url, donnees) {
        donnees = donnees || {};
        donnees.csrfmiddlewaretoken = CFG.csrf;
        return $.ajax({url: url, type: "POST", data: donnees, dataType: "json"});
    }
    function Message_erreur(xhr, defaut) { return (xhr && xhr.responseJSON && xhr.responseJSON.erreur) || defaut || "Une erreur est survenue"; }
    function Focus_corps() {
        // Donne le focus clavier au planning sans faire défiler la page
        var el = document.getElementById("pi_corps");
        if (el && document.activeElement !== el) { try { el.focus({preventScroll: true}); } catch (e) { el.focus(); } }
    }
    function Pluriel(n, mot, pluriel) { return n + " " + (n > 1 ? (pluriel || mot + "s") : mot); }
    function Aujourdhui() { return Parse_jour(S.aujourdhui || new Date().toISOString().substr(0, 10)); }

    // ------------------------------------------------------------------ Etat
    var S = {
        collab: null, contrats: [], cats: new Map(), catOrdre: [], affs: new Map(), affOrdre: [], modeles: [],
        evts: new Map(), index: new Map(), feries: new Map(), vacances: [],
        periode: null, objectif: {}, parametres: {}, peut_regler_tous: false, periode_suivante: "", prefs: {},
        aujourdhui: null, prochain_tmp: -1, charge: false
    };
    var V = {vue: "calendrier", selection: new Set(), ancre: null, curseur: null, masquees: new Set(), drag: null, pop_jour: null};
    var Pile = {annuler: [], retablir: []};
    var Alias = new Map(), Versions = new Map();
    var File_envoi = [], envoi_en_cours = false, derniere_sauvegarde = null;
    var Presse_papier = null;
    var requete_donnees = null;

    function Id_actuel(id) { var vus = 0; while (Alias.has(id) && vus < 50) { id = Alias.get(id); vus++; } return id; }
    function Modifiable() { return !!(S.collab && S.collab.modifiable); }
    function Debut_periode() { return Parse_jour(S.periode.debut); }
    function Fin_periode() { return Parse_jour(S.periode.fin); }
    function Dans_periode(j) { return j >= Debut_periode() && j <= Fin_periode(); }

    // ------------------------------------------------------------------ Données
    function Evt_depuis_serveur(e) {
        return {id: e.id, c: e.c, cat: e.cat, aff: e.aff, t: e.t || "", s: Parse_min(e.d), e: Parse_min(e.f), rs: Parse_min(e.rd), re: Parse_min(e.rf), v: e.v};
    }
    function Evt_vers_serveur(evt) {
        return {c: S.collab.id, cat: evt.cat, aff: evt.aff || null, t: evt.t || "", d: Format_min(evt.s), f: Format_min(evt.e),
                rd: evt.rs !== null && evt.rs !== undefined ? Format_min(evt.rs) : null, rf: evt.re !== null && evt.re !== undefined ? Format_min(evt.re) : null};
    }
    function Copie_evt(evt) { return $.extend({}, evt); }

    function Reindexer() {
        S.index.clear();
        S.evts.forEach(function(evt) {
            for (var j = Jour_de(evt.s); j <= Jour_de(evt.e - 1); j++) {
                if (!S.index.has(j)) { S.index.set(j, []); }
                S.index.get(j).push(evt.id);
            }
        });
        S.index.forEach(function(liste) { liste.sort(function(a, b) { return S.evts.get(a).s - S.evts.get(b).s; }); });
    }
    function Evts_du_jour(j, tous) {
        return (S.index.get(j) || []).map(function(id) { return S.evts.get(id); }).filter(function(evt) { return evt && (tous || !V.masquees.has(evt.cat)); });
    }
    function Minutes_dans_jour(evt, j) { return Math.max(0, Math.min(evt.e, (j + 1) * 1440) - Math.max(evt.s, j * 1440)); }
    function Peut_chevaucher(a, b) { var ca = S.cats.get(a.cat), cb = S.cats.get(b.cat); return (ca && ca.chevauchement) || (cb && cb.chevauchement); }
    function Conflits(candidat, ignorer) {
        ignorer = ignorer || new Set();
        var resultat = [];
        for (var j = Jour_de(candidat.s); j <= Jour_de(candidat.e - 1); j++) {
            Evts_du_jour(j, true).forEach(function(autre) {
                if (autre.id === candidat.id || ignorer.has(autre.id) || resultat.indexOf(autre) >= 0) { return; }
                if (candidat.s < autre.e && candidat.e > autre.s && !Peut_chevaucher(candidat, autre)) { resultat.push(autre); }
            });
        }
        return resultat;
    }
    function Contrat_actif(j) {
        for (var i = 0; i < S.contrats.length; i++) {
            var c = S.contrats[i];
            if (c.d <= j && (c.f === null || j <= c.f)) { return c; }
        }
        return null;
    }
    function Vacances_de(j) {
        for (var i = 0; i < S.vacances.length; i++) { if (S.vacances[i].d <= j && j <= S.vacances[i].f) { return S.vacances[i]; } }
        return null;
    }
    function Chemin_aff(id) {
        var noms = [], a = S.affs.get(id), garde = 0;
        while (a && garde < 50) { noms.unshift(a.nom); a = S.affs.get(a.parent); garde++; }
        return noms.join(" › ");
    }
    function Options_affectations(valeur) {
        var html = "<option value=''>Aucune affectation</option>";
        S.affOrdre.forEach(function(id) {
            var a = S.affs.get(id);
            if (!a.actif && id !== valeur) { return; }
            html += "<option value='" + id + "' data-niveau='" + a.niveau + "' title='" + Echapper(Chemin_aff(id)) + "'" + (id === valeur ? " selected" : "") + ">" + Echapper(a.nom) + (a.actif ? "" : " (inactive)") + "</option>";
        });
        return html;
    }
    function Options_categories(valeur) {
        return S.catOrdre.map(function(id) { var c = S.cats.get(id); return "<option value='" + id + "' data-couleur='" + Echapper(c.couleur) + "'" + (id === valeur ? " selected" : "") + ">" + Echapper(c.nom) + "</option>"; }).join("");
    }

    // ------------------------------------------------------------------ Listes déroulantes avec recherche (select2)
    function Format_categorie(option) {
        if (!option.id || !option.element) { return option.text; }
        var couleur = option.element.getAttribute("data-couleur") || "#888";
        return $("<span class='pi-s2-cat'>").append($("<span class='pl-pastille'>").css("background", couleur)).append($("<span>").text(option.text));
    }
    function Format_affectation(option) {
        if (!option.id || !option.element) { return option.text; }
        return $("<span>").css("padding-left", (+(option.element.getAttribute("data-niveau") || 0) * 14) + "px").text(option.text);
    }
    function Normaliser(texte) { return String(texte || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
    function Recherche_affectation(params, option) {
        // Recherche sur le chemin complet (affectations parentes comprises), sans tenir compte des accents
        if (!params.term || !params.term.trim()) { return option; }
        var chemin = option.element ? (option.element.getAttribute("title") || option.text) : option.text;
        return Normaliser(chemin).indexOf(Normaliser(params.term.trim())) >= 0 ? option : null;
    }
    function Select2($select, options) {
        if (!$.fn.select2 || !$select.length) { return; }
        if ($select.data("select2")) { $select.select2("destroy"); }
        $select.select2($.extend({language: "fr", width: "100%", theme: "bootstrap4"}, options || {}));
    }
    function Select2_categorie($select, $modal) {
        Select2($select, {dropdownParent: $modal, templateResult: Format_categorie, templateSelection: Format_categorie});
    }
    function Select2_affectation($select, $modal) {
        Select2($select, {dropdownParent: $modal, templateResult: Format_affectation, matcher: Recherche_affectation});
    }
    function Proteger_echap(id) {
        // Échap sur une liste select2 ouverte ferme seulement la liste, pas la fenêtre
        var modale = document.getElementById(id);
        if (!modale) { return; }
        modale.addEventListener("keydown", function(e) {
            if (e.key === "Escape" && modale.querySelector(".select2-container--open")) { e.pi_liste_ouverte = true; }
        }, true);
        $(modale).on("keydown", function(e) { if (e.originalEvent && e.originalEvent.pi_liste_ouverte) { e.stopImmediatePropagation(); } });
    }
    function Initialiser_select2() {
        Proteger_echap("pi_modal_evt");
        Proteger_echap("pi_modal_periode");
        Select2($("#pi_collab_select"), {placeholder: "Rechercher un collaborateur…"});
    }

    // ------------------------------------------------------------------ Règles de calcul (identiques au serveur : utils_objectif.py)
    function Regle(cat) {
        var c = S.cats.get(cat);
        if (!c) { return 0; }
        if (c.objectif === "DUREE") { return 1; }
        if (c.objectif === "FORFAIT") { return "F"; }
        return c.type === "ADDITION" ? 1 : (c.type === "SOUSTRACTION" ? -1 : 0);
    }
    function Valeur_jour(j) {
        // Valeur comptée dans l'objectif (heures ou jours selon l'unité), tous évènements confondus (les filtres d'affichage n'ont pas d'effet)
        var minutes = 0, forfait = 0, positifs = 0;
        Evts_du_jour(j, true).forEach(function(evt) {
            var r = Regle(evt.cat);
            if (!r) { return; }
            var m = Minutes_dans_jour(evt, j);
            if (r === "F") { forfait += m; } else { minutes += r * m; if (r > 0) { positifs += m; } }
        });
        var seuil = S.objectif.seuil_demi_journee || 240;
        if (S.objectif.unite === "jours") {
            var t = positifs + forfait;
            return t > 0 ? (t >= seuil ? 1 : 0.5) : 0;
        }
        var valeur = minutes / 60;
        if (forfait > 0) { valeur += forfait >= seuil ? S.objectif.forfait_journalier : S.objectif.forfait_journalier / 2; }
        return valeur;
    }
    function Totaux_planifies() {
        var total = 0, a_date = 0, auj = Aujourdhui(), par_mois = {};
        for (var j = Debut_periode(); j <= Fin_periode(); j++) {
            var v = Valeur_jour(j);
            if (!v) { continue; }
            total += v;
            if (j <= auj) { a_date += v; }
            var i = Infos_jour(j), cle = i.a * 12 + i.m;
            par_mois[cle] = (par_mois[cle] || 0) + v;
        }
        return {total: total, a_date: a_date, par_mois: par_mois};
    }

    // ------------------------------------------------------------------ Chargement
    function Charger(annee, type_periode, garder_selection) {
        if (envoi_en_cours || File_envoi.length) {
            toastr.info("Enregistrement en cours, réessayez dans un instant");
            return $.Deferred().reject().promise();
        }
        if (requete_donnees) { requete_donnees.abort(); }
        S.charge = false;
        Statut("<i class='fa fa-refresh fa-spin' aria-hidden='true'></i>Chargement…");
        var donnees = {idcollaborateur: CFG.idcollaborateur};
        if (annee) { donnees.annee = annee; }
        if (type_periode) { donnees.type_periode = type_periode; }
        requete_donnees = Ajax(CFG.urls.donnees, donnees).done(function(data) {
            requete_donnees = null;
            Charger_donnees(data);
            if (!garder_selection) { V.selection.clear(); V.ancre = null; V.curseur = null; }
            Pile.annuler = []; Pile.retablir = [];
            Rafraichir_tout();
            Statut();
        }).fail(function(xhr, statut) {
            requete_donnees = null;
            if (statut === "abort") { return; }
            $("#pi_corps").html("<div class='pi-chargement'>" + Echapper(Message_erreur(xhr, "Impossible de charger le planning")) + "</div>");
            Statut("");
        });
        return requete_donnees;
    }

    function Charger_donnees(data) {
        S.collab = data.collaborateur;
        S.contrats = data.collaborateur.contrats.map(function(c) { return {d: Parse_jour(c.d), f: c.f ? Parse_jour(c.f) : null, h: c.h, poste: c.poste, mode: c.mode, d_txt: c.d, f_txt: c.f}; });
        S.cats.clear(); S.catOrdre = [];
        data.categories.forEach(function(c) { S.cats.set(c.id, c); S.catOrdre.push(c.id); });
        S.affs.clear(); S.affOrdre = [];
        data.affectations.forEach(function(a) { S.affs.set(a.id, a); S.affOrdre.push(a.id); });
        S.modeles = data.modeles;
        S.evts.clear(); Alias.clear(); Versions.clear();
        data.evenements.forEach(function(e) { S.evts.set(e.id, Evt_depuis_serveur(e)); });
        Reindexer();
        S.feries.clear();
        data.feries.forEach(function(f) { S.feries.set(Parse_jour(f.date), f.nom); });
        S.vacances = data.vacances.map(function(v) { return {d: Parse_jour(v.debut), f: Parse_jour(v.fin), nom: v.nom}; });
        S.objectif = data.objectif;
        S.periode = data.objectif.periode;
        S.periode_suivante = data.periode_suivante;
        S.parametres = data.parametres;
        S.peut_regler_tous = data.peut_regler_tous;
        S.prefs = data.preferences;
        S.aujourdhui = data.aujourdhui;
        if (!S.charge_une_fois) { V.vue = S.prefs.vue || "calendrier"; S.charge_une_fois = true; }
        S.charge = true;
    }

    function Recharger_objectif() {
        return Ajax(CFG.urls.objectif, {idcollaborateur: CFG.idcollaborateur, annee: S.periode.annee, type_periode: S.periode.type}).done(function(data) {
            S.objectif = data.objectif;
            Rafraichir_tout();
        });
    }

    var Memoriser_preferences = Debounce(function(preferences) {
        Ajax(CFG.urls.preferences, {preferences: JSON.stringify(preferences)}).done(function(data) { S.prefs = data.preferences; });
    }, 600);

    // ------------------------------------------------------------------ Modifications, annulation et enregistrement
    function Ids_en_attente() {
        var ids = new Set();
        File_envoi.forEach(function(lot) { lot.changements.forEach(function(ch) { ids.add(Id_actuel(ch.id)); }); });
        return ids;
    }
    function Appliquer_localement(changements) {
        changements.forEach(function(ch) {
            if (ch.type === "create") { S.evts.set(ch.apres.id, Copie_evt(ch.apres)); }
            if (ch.type === "update") {
                var actuel = S.evts.get(Id_actuel(ch.id));
                if (actuel) { var v = actuel.v; S.evts.set(actuel.id, $.extend(Copie_evt(ch.apres), {id: actuel.id, v: v})); }
            }
            if (ch.type === "delete") { S.evts.delete(Id_actuel(ch.id)); }
        });
        Reindexer();
    }
    function Valider(libelle, changements) {
        if (!changements.length) { return; }
        Appliquer_localement(changements);
        Envoyer(changements);
        Pile.annuler.push({libelle: libelle, changements: changements});
        if (Pile.annuler.length > 100) { Pile.annuler.shift(); }
        Pile.retablir = [];
        Rafraichir_tout();
    }
    function Inverser(changements) {
        return changements.slice().reverse().map(function(ch) {
            var id = Id_actuel(ch.id);
            if (ch.type === "create") {
                var actuel = S.evts.get(id);
                return {type: "delete", id: id, avant: actuel ? Copie_evt(actuel) : ch.apres};
            }
            if (ch.type === "delete") {
                var nouveau = Copie_evt(ch.avant);
                nouveau.id = S.prochain_tmp--;
                Alias.set(id, nouveau.id);
                return {type: "create", id: nouveau.id, apres: nouveau};
            }
            return {type: "update", id: id, avant: Copie_evt(ch.apres), apres: $.extend(Copie_evt(ch.avant), {id: id})};
        });
    }
    function Changements_valides(changements) {
        var supprimes = new Set(), i, ch;
        for (i = 0; i < changements.length; i++) {
            ch = changements[i];
            if ((ch.type === "update" || ch.type === "delete") && !S.evts.has(Id_actuel(ch.id))) { return false; }
            if (ch.type === "delete") { supprimes.add(Id_actuel(ch.id)); }
        }
        for (i = 0; i < changements.length; i++) {
            ch = changements[i];
            if ((ch.type === "create" || ch.type === "update") && Conflits($.extend({}, ch.apres, {id: Id_actuel(ch.id)}), supprimes).length) { return false; }
        }
        return true;
    }
    function Annuler_retablir(source, cible, verbe) {
        if (envoi_en_cours || File_envoi.length) { toastr.info("Enregistrement en cours, réessayez dans un instant"); return; }
        var action = source.pop();
        if (!action) { return; }
        var inverse = Inverser(action.changements);
        if (!Changements_valides(inverse)) {
            toastr.warning("Impossible " + (verbe === "Annulé" ? "d'annuler" : "de rétablir") + " « " + action.libelle + " » : le planning a été modifié depuis.");
            Rafraichir_tout();
            return;
        }
        Appliquer_localement(inverse);
        Envoyer(inverse);
        cible.push({libelle: action.libelle, changements: inverse});
        toastr.info(verbe + " : " + action.libelle);
        Rafraichir_tout();
    }
    function Annuler() { Annuler_retablir(Pile.annuler, Pile.retablir, "Annulé"); }
    function Retablir() { Annuler_retablir(Pile.retablir, Pile.annuler, "Rétabli"); }

    function Envoyer(changements) { File_envoi.push({changements: changements}); Traiter_file(); }
    function Traiter_file() {
        if (envoi_en_cours || !File_envoi.length) { return; }
        envoi_en_cours = true;
        Statut();
        var lot = File_envoi[0], temporaires = {};
        var operations = lot.changements.map(function(ch) {
            var id = Id_actuel(ch.id);
            if (ch.type === "create") {
                temporaires[String(id)] = id;
                return {op: "create", tmp: String(id), data: Evt_vers_serveur(S.evts.get(id) || ch.apres)};
            }
            var actuel = S.evts.get(id);
            var version = actuel ? actuel.v : (ch.avant ? (Versions.has(id) ? Versions.get(id) : ch.avant.v) : 1);
            if (ch.type === "update") { return {op: "update", id: id, v: version, data: Evt_vers_serveur(actuel || ch.apres)}; }
            return {op: "delete", id: id, v: version};
        });
        Ajax(CFG.urls.enregistrer, {idcollaborateur: CFG.idcollaborateur, operations: JSON.stringify(operations)}).done(function(data) {
            File_envoi.shift();
            Object.keys(data.crees || {}).forEach(function(tmp) {
                var ancien = temporaires[tmp], nouveau = data.crees[tmp], evt = S.evts.get(ancien);
                Alias.set(ancien, nouveau.id);
                if (evt) { S.evts.delete(ancien); evt.id = nouveau.id; evt.v = nouveau.v; S.evts.set(nouveau.id, evt); }
                Versions.set(nouveau.id, nouveau.v);
            });
            Object.keys(data.maj || {}).forEach(function(id) {
                var evt = S.evts.get(+id);
                if (evt) { evt.v = data.maj[id]; }
                Versions.set(+id, data.maj[id]);
            });
            Reindexer();
            envoi_en_cours = false;
            derniere_sauvegarde = new Date();
            Statut();
            Traiter_file();
        }).fail(function(xhr) {
            envoi_en_cours = false;
            File_envoi = [];
            bootbox.alert({title: "Modification non enregistrée", message: Echapper(Message_erreur(xhr, "La modification n'a pas pu être enregistrée."))});
            Charger(S.periode.annee, S.periode.type, true);
        });
    }

    // ------------------------------------------------------------------ Rendu d'un jour
    function Infos_cellule(j) {
        var evts = Evts_du_jour(j), ferie = S.feries.get(j), vac = Vacances_de(j), js = Jour_semaine(j);
        var classes = ["pi-j"];
        if (js >= 5) { classes.push("we"); }
        if (ferie) { classes.push("ferie"); }
        if (vac) { classes.push("vac"); }
        if (j === Aujourdhui()) { classes.push("auj"); }
        if (V.selection.has(j)) { classes.push("sel"); }
        if (V.curseur === j) { classes.push("curseur"); }
        if (S.contrats.length && !Contrat_actif(j)) { classes.push("hors"); }
        // Répartition par catégorie (toutes catégories visibles)
        var par_cat = new Map(), total = 0;
        evts.forEach(function(evt) { var m = Minutes_dans_jour(evt, j); par_cat.set(evt.cat, (par_cat.get(evt.cat) || 0) + m); total += m; });
        var dominante = null;
        par_cat.forEach(function(m, cat) { if (dominante === null || m > par_cat.get(dominante)) { dominante = cat; } });
        var cat = dominante !== null ? S.cats.get(dominante) : null;
        var pile = "";
        if (total > 0) {
            par_cat.forEach(function(m, id) { var c = S.cats.get(id); pile += "<i style='width:" + (m / total * 100).toFixed(1) + "%;background:" + Echapper(c ? c.couleur : "#888") + "'></i>"; });
            pile = "<span class='pi-pile' aria-hidden='true'>" + pile + "</span>";
        }
        var valeur = Valeur_jour(j);
        var texte = "";
        if (cat) {
            var regle = Regle(cat.id);
            texte = (regle === 1 || regle === -1) && S.objectif.unite !== "jours" ? Duree(total) : cat.nom;
            if (regle === 1 && S.objectif.unite === "jours") { texte = Duree(total); }
        }
        var titre = Texte_jour_long(j) + (ferie ? " · " + ferie : "") + (vac ? " · " + vac.nom : "");
        evts.forEach(function(evt) { var c = S.cats.get(evt.cat); titre += "\n" + Heure_courte(evt.s) + "–" + Heure_courte(evt.e) + " " + (c ? c.nom : "") + (evt.t ? " (" + evt.t + ")" : ""); });
        if (valeur) { titre += "\nTotal compté : " + Valeur(valeur); }
        return {classes: classes, cat: cat, total: total, nb_cats: par_cat.size, pile: pile, texte: texte, titre: titre, ferie: ferie, valeur: valeur, js: js,
                fond: cat ? Teinte(cat.couleur) : ""};
    }
    var cache_teintes = {};
    function Teinte(couleur) {
        if (cache_teintes[couleur]) { return cache_teintes[couleur]; }
        var r = 128, g = 128, b = 128, m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(couleur || "");
        if (m) { r = parseInt(m[1], 16); g = parseInt(m[2], 16); b = parseInt(m[3], 16); }
        cache_teintes[couleur] = "rgba(" + r + "," + g + "," + b + ",0.2)";
        return cache_teintes[couleur];
    }
    function Mois_de_la_periode() {
        var liste = [], i = Infos_jour(Debut_periode());
        for (var n = 0; n < 12; n++) {
            var a = i.a + Math.floor((i.m + n) / 12), m = (i.m + n) % 12;
            liste.push({a: a, m: m, cle: a * 12 + m, debut: Jour_depuis(a, m, 1), nbre: Nbre_jours_mois(a, m)});
        }
        return liste;
    }

    // ------------------------------------------------------------------ Vues
    function Rendu_vue() {
        if (!S.charge) { return; }
        var html = V.vue === "colonnes" ? Rendu_colonnes() : (V.vue === "mois" ? Rendu_mois_jours() : Rendu_calendrier());
        var $corps = $("#pi_corps");
        var $box = $corps.find(".pi-tableau-box"), haut = $box.length ? $box.scrollTop() : 0, gauche = $box.length ? $box.scrollLeft() : 0;
        $corps.attr("data-vue-affichee", V.vue).html(html);
        $box = $corps.find(".pi-tableau-box");
        if ($box.length) { $box.scrollTop(haut).scrollLeft(gauche); }
    }

    function Rendu_calendrier() {
        var totaux = Totaux_planifies(), auj = Infos_jour(Aujourdhui());
        var html = "<div class='pi-cal-grille' role='presentation'>";
        Mois_de_la_periode().forEach(function(mo) {
            var courant = mo.a === auj.a && mo.m === auj.m;
            html += "<section class='pi-cal-mois" + (courant ? " courant" : "") + "' aria-label='" + MOIS[mo.m] + " " + mo.a + "'>" +
                "<div class='pi-cal-tete'><h3>" + MOIS[mo.m] + " " + mo.a + "</h3><span>" + Valeur(totaux.par_mois[mo.cle] || 0) + "</span></div>" +
                "<div class='pi-cal-jours' role='grid'>" + JOURS_LETTRES.map(function(l, index) { return "<span class='pi-cal-jl' aria-hidden='true' title='" + JOURS_LONGS[index] + "'>" + l + "</span>"; }).join("");
            for (var k = 0; k < Jour_semaine(mo.debut); k++) { html += "<span class='pi-cal-c vide' aria-hidden='true'></span>"; }
            for (var d = 0; d < mo.nbre; d++) {
                var j = mo.debut + d, c = Infos_cellule(j);
                html += "<div class='" + c.classes.join(" ") + " pi-cal-c' data-j='" + j + "' role='gridcell' aria-selected='" + V.selection.has(j) + "' title='" + Echapper(c.titre) + "'" +
                        (c.fond && !c.ferie ? " style='background-color:" + c.fond + "'" : "") + ">" + (d + 1) + c.pile + "</div>";
            }
            html += "</div></section>";
        });
        return html + "</div>";
    }

    function Html_pastille_jour(c) {
        if (c.ferie && !c.cat) { return "<span class='pi-pastille-jour ferie'>Férié</span>"; }
        if (!c.cat) { return ""; }
        return "<span class='pi-pastille-jour" + (c.nb_cats > 1 ? " multi" : "") + "' style='background:" + Echapper(c.cat.couleur) + "'>" + Echapper(c.texte) + "</span>";
    }

    function Rendu_colonnes() {
        var mois = Mois_de_la_periode(), totaux = Totaux_planifies(), auj = Infos_jour(Aujourdhui());
        var html = "<div class='pi-tableau-box'><table class='pi-co' role='grid' aria-label='Planning annuel, une colonne par mois'><thead><tr>";
        mois.forEach(function(mo) {
            html += "<th scope='col' class='" + (mo.a === auj.a && mo.m === auj.m ? "courant" : "") + "'>" + MOIS[mo.m] + (mo.m === 0 || mo === mois[0] ? " " + mo.a : "") +
                    "<small>" + Valeur(totaux.par_mois[mo.cle] || 0) + "</small></th>";
        });
        html += "</tr></thead><tbody>";
        for (var d = 0; d < 31; d++) {
            html += "<tr>";
            mois.forEach(function(mo) {
                if (d >= mo.nbre) { html += "<td class='nx' aria-hidden='true'></td>"; return; }
                var j = mo.debut + d, c = Infos_cellule(j);
                if (c.js === 0 && d > 0) { c.classes.push("lundi"); }
                html += "<td class='" + c.classes.join(" ") + "' data-j='" + j + "' role='gridcell' aria-selected='" + V.selection.has(j) + "' title='" + Echapper(c.titre) + "'>" +
                        "<div class='pi-co-c'><span class='pi-co-jl'>" + JOURS_LETTRES[c.js] + "</span><span class='pi-co-n'>" + Pad(d + 1) + "</span>" + Html_pastille_jour(c) + "</div></td>";
            });
            html += "</tr>";
        }
        html += "</tbody><tfoot><tr>";
        var cumul = 0;
        mois.forEach(function(mo) { cumul += totaux.par_mois[mo.cle] || 0; html += "<td>" + Valeur(totaux.par_mois[mo.cle] || 0) + "<small>cumul " + Valeur(cumul) + "</small></td>"; });
        return html + "</tr></tfoot></table></div>";
    }

    function Rendu_mois_jours() {
        var mois = Mois_de_la_periode(), totaux = Totaux_planifies(), auj = Infos_jour(Aujourdhui());
        var html = "<div class='pi-tableau-box'><table class='pi-mj' role='grid' aria-label='Planning annuel par mois et par jour'><thead><tr><th class='pi-mj-nom' scope='col'>Mois</th>";
        for (var d = 1; d <= 31; d++) { html += "<th scope='col'>" + d + "</th>"; }
        html += "<th class='pi-mj-total' scope='col'>Total</th></tr></thead><tbody>";
        var cumul = 0;
        mois.forEach(function(mo) {
            var courant = mo.a === auj.a && mo.m === auj.m;
            html += "<tr class='" + (courant ? "courant" : "") + "'><th class='pi-mj-nom' scope='row'>" + MOIS[mo.m] + (mo.m === 0 || mo === mois[0] ? " " + mo.a : "") + "</th>";
            for (var d = 0; d < 31; d++) {
                if (d >= mo.nbre) { html += "<td class='nx' aria-hidden='true'></td>"; continue; }
                var j = mo.debut + d, c = Infos_cellule(j);
                if (c.js === 0) { c.classes.push("lundi"); }
                var texte = c.ferie && !c.cat ? "Férié" : (c.cat ? (Regle(c.cat.id) === 0 || Regle(c.cat.id) === "F" ? Abrege(c.cat.nom) : Duree(c.total)) : "");
                html += "<td class='" + c.classes.join(" ") + "' data-j='" + j + "' role='gridcell' aria-selected='" + V.selection.has(j) + "' title='" + Echapper(c.titre) + "'" +
                        (c.fond && !c.ferie ? " style='background-color:" + c.fond + "'" : "") + "><span class='pi-mj-jl'>" + JOURS_LETTRES[c.js] + "</span><span class='pi-mj-v'>" + Echapper(texte) + "</span>" + c.pile + "</td>";
            }
            cumul += totaux.par_mois[mo.cle] || 0;
            html += "<td class='pi-mj-total'>" + Valeur(totaux.par_mois[mo.cle] || 0) + "<small>cumul " + Valeur(cumul) + "</small></td></tr>";
        });
        html += "</tbody><tfoot><tr><td class='pi-mj-nom'>Total</td><td colspan='31' style='text-align:left;padding-left:12px;font-weight:600'>" + Echapper(Texte_resume_objectif(totaux)) + "</td>" +
                "<td class='pi-mj-total'>" + Valeur(totaux.total) + "</td></tr></tfoot></table></div>";
        return html;
    }
    function Abrege(nom) { return nom.length > 5 ? nom.substr(0, 4) + "." : nom; }

    // ------------------------------------------------------------------ Objectif
    function Texte_resume_objectif(totaux) {
        var o = S.objectif;
        if (!o.a_objectif) { return "Aucun objectif sur cette période"; }
        var solde = totaux.total - o.objectif;
        return "Objectif " + Valeur(o.objectif) + " · " + (solde >= 0 ? "excédent " + Valeur(solde) : "reste " + Valeur(-solde));
    }

    function Html_objectif_detail() {
        var o = S.objectif, totaux = Totaux_planifies();
        if (!o.a_objectif) {
            return "<p class='pl-muted pl-petit mb-1'>Aucun objectif sur cette période : pas de contrat ou contrat en mode « Aucun ».</p>" + Html_avertissements(o) + Html_ajustements(o);
        }
        var solde = totaux.total - o.objectif, ecart = totaux.a_date - o.objectif_a_date;
        var pct = o.objectif > 0 ? Math.min(100, totaux.total / o.objectif * 100) : 100;
        var pct_date = o.objectif > 0 ? Math.min(100, o.objectif_a_date / o.objectif * 100) : 0;
        var periode_en_cours = Aujourdhui() >= Debut_periode() && Aujourdhui() <= Fin_periode();
        var html = "<div class='pi-obj-chiffres'><strong>" + Valeur(totaux.total) + "</strong><span>sur " + Valeur(o.objectif) + "</span></div>" +
            "<div class='pi-jauge' role='img' aria-label='Planifié " + Valeur(totaux.total) + " sur un objectif de " + Valeur(o.objectif) + "'><i class='" + (solde > 0 ? "depasse" : "") + "' style='width:" + pct.toFixed(1) + "%'></i>" +
            (periode_en_cours ? "<b style='left:" + pct_date.toFixed(1) + "%' title='Objectif à date'></b>" : "") + "</div>" +
            "<div class='pi-jauge-txt'><span>" + Math.round(o.objectif > 0 ? totaux.total / o.objectif * 100 : 0) + " % planifié</span><span>" + (solde >= 0 ? "Excédent " + Valeur(solde) : "Reste " + Valeur(-solde)) + "</span></div>";
        if (periode_en_cours) {
            html += "<div class='pi-obj-ligne'><span>À date (" + Texte_jour_fr(Aujourdhui()) + ")</span><strong>" + Valeur(totaux.a_date) + " / " + Valeur(o.objectif_a_date) + "</strong></div>" +
                    "<div class='pi-obj-ligne'><span>Écart à date</span><span class='pl-badge " + (ecart >= 0 ? "pl-badge-ecart-plus" : "pl-badge-ecart-moins") + "'>" + (ecart >= 0 ? "+" : "") + Valeur(ecart) + "</span></div>";
        }
        html += "<details class='pi-detail'><summary>Détail du calcul</summary><ul>";
        o.detail.forEach(function(ligne) { html += "<li>" + Echapper(ligne.texte) + (ligne.valeur ? " = <strong>" + Echapper(ligne.valeur) + "</strong>" : "") + "</li>"; });
        if (o.total_ajustements) { html += "<li>Ajustements et reports : <strong>" + (o.total_ajustements > 0 ? "+" : "") + Valeur(o.total_ajustements) + "</strong></li>"; }
        if (o.forfait_journalier) { html += "<li>Durée forfaitaire journalière : " + Valeur(o.forfait_journalier) + "</li>"; }
        html += "</ul></details>";
        return html + Html_avertissements(o) + Html_ajustements(o);
    }
    function Html_avertissements(o) {
        return (o.avertissements || []).map(function(texte) { return "<div class='pi-avert'><i class='fa fa-exclamation-triangle' aria-hidden='true'></i> " + Echapper(texte) + "</div>"; }).join("");
    }
    function Html_ajustements(o) {
        var html = "<span class='pl-label pi-ajust-titre'>Ajustements et reports</span>";
        if (!o.ajustements.length) { html += "<p class='pl-muted pl-petit mb-1'>Aucun ajustement sur cette période.</p>"; }
        o.ajustements.forEach(function(a) {
            var report = a.type === "REPORT";
            html += "<div class='pi-ajust'><span class='pi-ajust-txt'><span>" + Texte_jour_fr(Parse_jour(a.date)) + (report ? " <span class='pl-badge pl-badge-contrat'>Report</span>" : "") + "</span>" +
                    "<small title='" + Echapper(a.motif) + "'>" + Echapper(a.motif || "Sans motif") + "</small></span><span class='pi-ajust-val'>" + (a.valeur > 0 ? "+" : "") + Valeur(a.valeur) + "</span>" +
                    (Modifiable() ? "<button type='button' class='pl-mini-btn' data-ajust-modifier='" + a.id + "' aria-label='Modifier l’ajustement du " + Texte_jour_fr(Parse_jour(a.date)) + "' title='Modifier'><i class='fa fa-pencil' aria-hidden='true'></i></button>" +
                    "<button type='button' class='pl-mini-btn' data-ajust-supprimer='" + a.id + "' aria-label='Supprimer l’ajustement du " + Texte_jour_fr(Parse_jour(a.date)) + "' title='Supprimer'><i class='fa fa-trash' aria-hidden='true'></i></button>" : "") + "</div>";
        });
        if (Modifiable()) {
            html += "<div class='pi-obj-actions'><button type='button' class='pl-lien' data-action='ajust-ajouter'><i class='fa fa-plus' aria-hidden='true'></i> Ajouter un ajustement</button>" +
                    (o.a_objectif ? "<button type='button' class='pl-lien' data-action='reporter'><i class='fa fa-share' aria-hidden='true'></i> Reporter le solde sur " + Echapper(S.periode_suivante) + "</button>" : "") + "</div>";
        }
        return html;
    }

    function Rendu_objectif() {
        var o = S.objectif, totaux = Totaux_planifies();
        $("#pi_objectif").html(Html_objectif_detail());
        $("#pi_modal_objectif_corps").html(Html_objectif_detail());
        var resume = o.a_objectif ? Valeur(totaux.total) + " / " + Valeur(o.objectif) : "Aucun objectif";
        $("#pi_acc_resume_objectif").text(resume);

        // Bandeau (mode fiche)
        if (CFG.mode === "fiche") {
            var html = "";
            if (o.a_objectif) {
                var solde = totaux.total - o.objectif, ecart = totaux.a_date - o.objectif_a_date, pct = o.objectif > 0 ? Math.min(100, totaux.total / o.objectif * 100) : 100;
                var en_cours = Aujourdhui() >= Debut_periode() && Aujourdhui() <= Fin_periode();
                html += "<div class='pi-bandeau-carte'><small>Planifié " + Echapper(S.periode.libelle) + "</small><strong>" + Valeur(totaux.total) + "</strong><span>sur un objectif de " + Valeur(o.objectif) + "</span>" +
                        "<div class='pi-jauge' aria-hidden='true'><i class='" + (solde > 0 ? "depasse" : "") + "' style='width:" + pct.toFixed(1) + "%'></i></div></div>" +
                        "<div class='pi-bandeau-carte'><small>Solde de la période</small><strong>" + (solde >= 0 ? "+" : "") + Valeur(solde) + "</strong><span>" + (solde >= 0 ? "excédent" : "reste à planifier") + "</span></div>";
                if (en_cours) {
                    html += "<div class='pi-bandeau-carte'><small>À date</small><strong>" + (ecart >= 0 ? "+" : "") + Valeur(ecart) + "</strong><span>" + Valeur(totaux.a_date) + " planifiées / " + Valeur(o.objectif_a_date) + " attendues</span></div>";
                }
            } else {
                html += "<div class='pi-bandeau-carte'><small>Objectif</small><strong>—</strong><span>Aucun objectif sur cette période</span></div>";
            }
            $("#pi_bandeau").html(html);
            Rendu_entete_objectif();
        }
    }

    function Resume_contrats() {
        // Contrats couvrant la période : "Annualisé · 28 h/sem. + Volume fixe"
        return S.contrats.filter(function(c) { return c.d <= Fin_periode() && (c.f === null || c.f >= Debut_periode()); }).map(function(c) {
            return c.mode + (c.h ? " · " + String(c.h).replace(".", ",") + " h/sem." : "");
        }).join(" + ");
    }
    function Rendu_entete_objectif() {
        // Ligne de titre de l'objectif (fiche collaborateur) : rappel du contrat et accès directs
        var o = S.objectif, nb = o.ajustements.length, contrats = Resume_contrats();
        var html = "<h3 class='pi-entete-titre'>Objectif " + Echapper(S.periode.libelle) + "</h3>" +
            (contrats ? "<span class='pi-entete-sep' aria-hidden='true'></span><span class='pi-entete-contrat' title='" + Echapper(contrats) + "'>" + Echapper(contrats) + "</span>" : "") +
            "<span class='pl-espace'></span><span class='pi-entete-liens'>" +
            "<button type='button' class='pl-lien' data-action='objectif-detail'><i class='fa fa-bullseye' aria-hidden='true'></i>Détail du calcul</button>" +
            "<button type='button' class='pl-lien' data-action='objectif-ajustements'>Ajustements <span class='pi-badge-nb' aria-label='" + Pluriel(nb, "ajustement") + "'>" + nb + "</span></button>";
        if (Modifiable()) {
            html += "<button type='button' class='pl-lien' data-action='ajust-ajouter'><i class='fa fa-plus' aria-hidden='true'></i>Ajouter</button>" +
                    (o.a_objectif ? "<button type='button' class='pl-lien' data-action='reporter' title='Reporter le solde sur " + Echapper(S.periode_suivante) + "'><i class='fa fa-share' aria-hidden='true'></i>Reporter le solde</button>" : "");
        }
        $("#pi_entete_objectif").html(html + "</span>");
    }

    // ------------------------------------------------------------------ Légende, collaborateur, barre d'outils
    function Rendu_legende() {
        var stats = new Map();
        S.evts.forEach(function(evt) {
            var j1 = Math.max(Jour_de(evt.s), Debut_periode()), j2 = Math.min(Jour_de(evt.e - 1), Fin_periode());
            for (var j = j1; j <= j2; j++) {
                var st = stats.get(evt.cat) || {minutes: 0, jours: new Set()};
                st.minutes += Minutes_dans_jour(evt, j); st.jours.add(j);
                stats.set(evt.cat, st);
            }
        });
        var html = "", chips = "";
        S.catOrdre.forEach(function(id) {
            var c = S.cats.get(id), st = stats.get(id);
            if (!st && !V.masquees.has(id)) { return; }
            var regle = Regle(id), note = regle === 0 ? "non comptabilisé" : (regle === -1 ? "soustrait" : (regle === "F" ? "compté au forfait" : ""));
            var visible = !V.masquees.has(id);
            var nb = st ? st.jours.size : 0;
            html += "<button type='button' class='pi-leg' data-cat='" + id + "' aria-pressed='" + visible + "' title='" + (visible ? "Masquer" : "Afficher") + " cette catégorie'>" +
                    "<span class='pl-pastille' style='background:" + Echapper(c.couleur) + "'></span><span class='pl-leg-nom'><span>" + Echapper(c.nom) + "</span><small>" + Pluriel(nb, "jour") + (note ? " · " + note : "") + "</small></span>" +
                    "<span class='pl-leg-val'>" + Duree(st ? st.minutes : 0) + "</span></button>";
            chips += "<button type='button' class='pi-chip' data-cat='" + id + "' aria-pressed='" + visible + "'><span class='pl-pastille' style='background:" + Echapper(c.couleur) + "'></span>" +
                     Echapper(c.nom) + " <b>" + Duree(st ? st.minutes : 0) + "</b></button>";
        });
        if (!html) { html = "<p class='pl-muted pl-petit mb-0'>Aucun évènement sur cette période.</p>"; }
        $("#pi_legende").html(html);
        $("#pi_legende_chips").html(chips);
        $("#pi_acc_resume_legende").text(stats.size ? Pluriel(stats.size, "catégorie") + (V.masquees.size ? " · " + V.masquees.size + " masquée" + (V.masquees.size > 1 ? "s" : "") : "") : "Aucun évènement");
    }

    function Rendu_collaborateur() {
        if (CFG.mode !== "page" || !S.collab) { return; }
        var html = "";
        S.contrats.forEach(function(c) {
            html += "<li><strong>" + Echapper(c.poste) + "</strong> · du " + Texte_jour_fr(c.d) + (c.f !== null ? " au " + Texte_jour_fr(c.f) : " (sans fin)") +
                    (c.h ? " · " + String(c.h).replace(".", ",") + " h/sem." : "") + " · " + Echapper(c.mode) + "</li>";
        });
        $("#pi_contrats").html(html || "<li>Aucun contrat</li>");
        $("#pi_acc_resume_collab").text(S.collab.nom + " " + S.collab.prenom);
        $("#pi_lien_fiche").attr("href", CFG.url_fiche.replace("/0", "/" + S.collab.id));
        $("#pi_lecture").prop("hidden", Modifiable());
    }

    function Rendu_barre() {
        if (!S.periode) { return; }
        $("#pi_periode_titre").text(S.periode.libelle);
        $("#pi_app button[data-type-periode]").each(function() { $(this).attr("aria-pressed", String(this.getAttribute("data-type-periode") === S.periode.type)); });
        $("[data-type-periode='SCOLAIRE']").prop("hidden", S.parametres.mois_debut_scolaire === 1);
        $("#pi_app button[data-vue]").each(function() { $(this).attr("aria-pressed", String(this.getAttribute("data-vue") === V.vue)); });
        $("#pi_annuler").prop("disabled", !Pile.annuler.length).attr("title", Pile.annuler.length ? "Annuler « " + Pile.annuler[Pile.annuler.length - 1].libelle + " » (Ctrl+Z)" : "Annuler (Ctrl+Z)");
        $("#pi_retablir").prop("disabled", !Pile.retablir.length).attr("title", Pile.retablir.length ? "Rétablir « " + Pile.retablir[Pile.retablir.length - 1].libelle + " » (Ctrl+Y)" : "Rétablir (Ctrl+Y)");
        $(".pi-edition").prop("hidden", !Modifiable());
        $("#pi_parametres_btn").prop("hidden", !S.peut_regler_tous);
    }

    function Rendu_actions() {
        var $barre = $("#pi_actions");
        if (!V.selection.size || !Modifiable()) { $barre.prop("hidden", true); return; }
        var jours = Jours_selectionnes(), n = jours.length;
        var texte = n === 1 ? Texte_jour_court(jours[0]) : Pluriel(n, "jour") + " sélectionné" + (n > 1 ? "s" : "") + " (" + Texte_jour_court(jours[0]) + " → " + Texte_jour_court(jours[n - 1]) + ")";
        $("#pi_actions_texte").text(texte);
        $("#pi_act_coller").prop("disabled", !Presse_papier);
        $barre.prop("hidden", false);
        Positionner_actions();
    }

    function Positionner_actions() {
        // Barre flottante en bas de l'écran, centrée sur la partie visible du planning
        var $barre = $("#pi_actions");
        if ($barre.prop("hidden")) { return; }
        var carte = document.querySelector("#pi_app .pl-card-planning");
        if (!carte) { return; }
        var r = carte.getBoundingClientRect(), largeur = $barre.outerWidth();
        var centre = (Math.max(r.left, 0) + Math.min(r.right, window.innerWidth)) / 2;
        var gauche = Math.max(8, Math.min(centre - largeur / 2, window.innerWidth - largeur - 8));
        var bas = Math.max(12, window.innerHeight - r.bottom + 12);
        $barre.css({left: gauche + "px", bottom: Math.min(bas, window.innerHeight - 60) + "px"});
    }

    function Statut(texte) {
        var $s = $("#pi_statut");
        if (texte !== undefined) { $s.html(texte); return; }
        if (envoi_en_cours || File_envoi.length) { $s.html("<i class='fa fa-refresh fa-spin' aria-hidden='true'></i> Enregistrement…"); return; }
        if (derniere_sauvegarde) { $s.html("<i class='fa fa-check' aria-hidden='true'></i> Enregistré à " + Pad(derniere_sauvegarde.getHours()) + ":" + Pad(derniere_sauvegarde.getMinutes())); return; }
        $s.text(Modifiable() ? "" : "Consultation seule");
    }

    function Rafraichir_tout() {
        if (!S.charge) { return; }
        Rendu_barre();
        Rendu_collaborateur();
        Rendu_vue();
        Rendu_legende();
        Rendu_objectif();
        Rendu_actions();
        if (V.pop_jour !== null) { Ouvrir_jour(V.pop_jour, null, true); }
    }

    // ------------------------------------------------------------------ Sélection
    function Jours_selectionnes() { return Array.from(V.selection).sort(function(a, b) { return a - b; }); }
    function Plage(a, b) { var liste = [], min = Math.min(a, b), max = Math.max(a, b); for (var j = min; j <= max; j++) { if (Dans_periode(j)) { liste.push(j); } } return liste; }
    function Selectionner(jours, ajouter) {
        if (!ajouter) { V.selection.clear(); }
        jours.forEach(function(j) { V.selection.add(j); });
        Maj_selection();
    }
    function Maj_selection() {
        $("#pi_corps [data-j]").each(function() {
            var j = +this.getAttribute("data-j");
            this.classList.toggle("sel", V.selection.has(j));
            this.classList.toggle("curseur", V.curseur === j);
            this.setAttribute("aria-selected", V.selection.has(j) ? "true" : "false");
        });
        Rendu_actions();
    }
    function Vider_selection() { V.selection.clear(); V.ancre = null; Maj_selection(); }

    // ------------------------------------------------------------------ Actions sur les jours
    function Nouvel_evt(j, debut, fin, cat, aff, titre) {
        return {id: S.prochain_tmp--, c: S.collab.id, cat: cat, aff: aff || null, t: titre || "", s: j * 1440 + debut, e: j * 1440 + fin, rs: null, re: null, v: 1};
    }
    function Est_non_ouvre(j) { return Jour_semaine(j) >= 5 || S.feries.has(j); }

    function Creer_periode(options) {
        // options : {jours, cat, plages: [[debut, fin]], aff, titre, ignorer_non_ouvres, conflit: "ignorer"|"remplacer"}
        var changements = [], supprimes = new Set(), ignores = 0, remplaces = 0, crees = 0, nouveaux = [];
        options.jours.forEach(function(j) {
            if (options.ignorer_non_ouvres && Est_non_ouvre(j)) { return; }
            if (options.conflit === "remplacer") {
                Evts_du_jour(j, true).forEach(function(evt) {
                    if (supprimes.has(evt.id) || Jour_de(evt.s) !== j) { return; }
                    supprimes.add(evt.id); remplaces++;
                    changements.push({type: "delete", id: evt.id, avant: Copie_evt(evt)});
                });
            }
            options.plages.forEach(function(plage) {
                var evt = Nouvel_evt(j, plage[0], plage[1], options.cat, options.aff, options.titre);
                var conflits = Conflits(evt, supprimes).concat(nouveaux.filter(function(autre) { return evt.s < autre.e && evt.e > autre.s && !Peut_chevaucher(evt, autre); }));
                if (conflits.length) { ignores++; return; }
                nouveaux.push(evt); crees++;
                changements.push({type: "create", id: evt.id, apres: evt});
            });
        });
        var cat = S.cats.get(options.cat);
        if (!crees && !remplaces) { toastr.warning(ignores ? "Aucun évènement créé : les jours sélectionnés sont déjà occupés." : "Aucun jour ouvré dans la sélection."); return 0; }
        Valider((options.libelle || "Créer une période") + " (" + (cat ? cat.nom : "") + ")", changements);
        var message = Pluriel(crees, "évènement créé", "évènements créés");
        if (remplaces) { message += ", " + Pluriel(remplaces, "évènement remplacé", "évènements remplacés"); }
        if (ignores) { message += ", " + Pluriel(ignores, "plage ignorée", "plages ignorées") + " (déjà occupée" + (ignores > 1 ? "s" : "") + ")"; }
        toastr.success(message + ". Ctrl+Z pour annuler.");
        return crees;
    }

    function Plages_mode(mode, prefs) {
        prefs = prefs || S.prefs;
        if (mode === "matin") { return [[Minutes_heure(prefs.matin_debut), Minutes_heure(prefs.matin_fin)]]; }
        if (mode === "am") { return [[Minutes_heure(prefs.am_debut), Minutes_heure(prefs.am_fin)]]; }
        return [[Minutes_heure(prefs.journee_debut), Minutes_heure(prefs.journee_fin)]];
    }

    function Poser_rapidement(cat, mode) {
        var jours = Jours_selectionnes();
        if (!jours.length) { return; }
        Creer_periode({jours: jours, cat: cat, plages: Plages_mode(mode), ignorer_non_ouvres: jours.length > 1 && S.prefs.ignorer_non_ouvres !== false, conflit: "remplacer",
                       libelle: "Poser " + {journee: "la journée", matin: "le matin", am: "l'après-midi"}[mode]});
    }

    function Effacer_selection() {
        var changements = [], vus = new Set();
        Jours_selectionnes().forEach(function(j) {
            Evts_du_jour(j).forEach(function(evt) {
                if (vus.has(evt.id)) { return; }
                vus.add(evt.id);
                changements.push({type: "delete", id: evt.id, avant: Copie_evt(evt)});
            });
        });
        if (!changements.length) { toastr.info("Aucun évènement à effacer sur la sélection"); return; }
        Valider("Effacer " + Pluriel(changements.length, "évènement"), changements);
        toastr.success(Pluriel(changements.length, "évènement supprimé", "évènements supprimés") + ". Ctrl+Z pour annuler.");
    }

    function Copier_selection() {
        var jours = Jours_selectionnes();
        if (!jours.length) { return; }
        var base = jours[0], items = [], vus = new Set();
        jours.forEach(function(j) {
            Evts_du_jour(j).forEach(function(evt) {
                if (vus.has(evt.id) || Jour_de(evt.s) !== j) { return; }
                vus.add(evt.id);
                items.push({decalage: evt.s - base * 1440, duree: evt.e - evt.s, cat: evt.cat, aff: evt.aff, t: evt.t});
            });
        });
        Presse_papier = {base: base, nbre_jours: jours[jours.length - 1] - base + 1, items: items};
        Rendu_actions();
        toastr.info(items.length ? Pluriel(items.length, "évènement copié", "évènements copiés") + " (" + Pluriel(Presse_papier.nbre_jours, "jour") + ")" : "Aucun évènement à copier");
    }

    function Coller() {
        if (!Presse_papier || !Presse_papier.items.length) { toastr.info("Rien à coller : copiez d'abord des jours (Ctrl+C)"); return; }
        var cibles = Jours_selectionnes();
        if (!cibles.length) { return; }
        var changements = [], ignores = 0, nouveaux = [];
        // Si la sélection est plus grande que la copie, la copie est répétée sur toute la sélection
        var departs = [cibles[0]];
        if (cibles.length > Presse_papier.nbre_jours) {
            for (var d = cibles[0] + Presse_papier.nbre_jours; d <= cibles[cibles.length - 1]; d += Presse_papier.nbre_jours) { departs.push(d); }
        }
        departs.forEach(function(depart) {
            Presse_papier.items.forEach(function(item) {
                var s = depart * 1440 + item.decalage;
                if (!Dans_periode(Jour_de(s))) { return; }
                var evt = {id: S.prochain_tmp--, c: S.collab.id, cat: item.cat, aff: item.aff, t: item.t, s: s, e: s + item.duree, rs: null, re: null, v: 1};
                if (Conflits(evt).length || nouveaux.some(function(autre) { return evt.s < autre.e && evt.e > autre.s && !Peut_chevaucher(evt, autre); })) { ignores++; return; }
                nouveaux.push(evt);
                changements.push({type: "create", id: evt.id, apres: evt});
            });
        });
        if (!changements.length) { toastr.warning("Aucun évènement collé : les jours ciblés sont déjà occupés."); return; }
        Valider("Coller " + Pluriel(changements.length, "évènement"), changements);
        toastr.success(Pluriel(changements.length, "évènement collé", "évènements collés") + (ignores ? ", " + Pluriel(ignores, "ignoré") + " (chevauchement)" : "") + ".");
    }

    // ------------------------------------------------------------------ Popover du jour
    function Ouvrir_jour(j, ancre, rafraichir) {
        var $pop = $("#pi_pop");
        var evts = Evts_du_jour(j, true), ferie = S.feries.get(j), vac = Vacances_de(j), valeur = Valeur_jour(j);
        var html = "<button type='button' class='pl-mini-btn pi-pop-fermer' data-action='pop-fermer' aria-label='Fermer'><i class='fa fa-times' aria-hidden='true'></i></button>" +
            "<h3 id='pi_pop_titre'>" + Texte_jour_long(j) + "</h3><div class='pi-pop-sous'>" +
            (ferie ? "<span class='pl-badge pl-badge-ferie'>" + Echapper(ferie) + "</span>" : "") +
            (vac ? "<span class='pl-badge pl-badge-vacances'>" + Echapper(vac.nom) + "</span>" : "") +
            (S.contrats.length && !Contrat_actif(j) ? "<span class='pl-badge pl-badge-contrat'>Hors contrat</span>" : "") + "</div>";
        if (!evts.length) { html += "<p class='pl-muted pl-petit mb-0'>Aucun évènement.</p>"; }
        evts.forEach(function(evt) {
            var c = S.cats.get(evt.cat), multi = Jour_de(evt.e - 1) !== Jour_de(evt.s);
            var horaires = multi ? Texte_jour_court(Jour_de(evt.s)) + " " + Heure_courte(evt.s) + " → " + Texte_jour_court(Jour_de(evt.e - 1)) + " " + Heure_courte(evt.e) : Heure_courte(evt.s) + " – " + Heure_courte(evt.e);
            var details = [c ? c.nom : "", evt.t, evt.aff ? Chemin_aff(evt.aff) : ""].filter(Boolean).join(" · ");
            html += "<div class='pi-evt'><span class='pl-pastille' style='background:" + Echapper(c ? c.couleur : "#888") + "'></span><span class='pi-evt-txt'><b>" + horaires + "</b><small title='" + Echapper(details) + "'>" + Echapper(details) + "</small></span>" +
                    (Modifiable() ? "<button type='button' class='pl-mini-btn' data-evt-modifier='" + evt.id + "' aria-label='Modifier l’évènement de " + horaires + "' title='Modifier'><i class='fa fa-pencil' aria-hidden='true'></i></button>" +
                    "<button type='button' class='pl-mini-btn' data-evt-supprimer='" + evt.id + "' aria-label='Supprimer l’évènement de " + horaires + "' title='Supprimer'><i class='fa fa-trash' aria-hidden='true'></i></button>" : "") + "</div>";
        });
        html += "<div class='pi-pop-actions'><span class='pl-muted pl-petit'>" + (valeur ? "Compté : <strong>" + Valeur(valeur) + "</strong>" : "") + "</span><span class='pl-espace'></span>" +
                (Modifiable() ? "<button type='button' class='pl-btn pl-btn-sm pl-btn-primaire' data-action='evt-ajouter' data-jour='" + j + "'><i class='fa fa-plus' aria-hidden='true'></i>Ajouter</button>" : "") + "</div>";
        $pop.html(html).prop("hidden", false).attr("data-jour", j);
        V.pop_jour = j;
        if (!rafraichir) {
            Positionner($pop, ancre || $("#pi_corps [data-j='" + j + "']")[0]);
            setTimeout(function() { var $b = $pop.find("[data-evt-modifier], [data-action='evt-ajouter']").first(); ($b.length ? $b : $pop.find("[data-action='pop-fermer']")).trigger("focus"); }, 0);
        }
    }
    function Fermer_jour(rendre_focus) {
        var j = V.pop_jour;
        $("#pi_pop").prop("hidden", true);
        V.pop_jour = null;
        if (rendre_focus && j !== null) { Focus_corps(); }
    }
    function Positionner($el, ancre, x, y) {
        var largeur = $el.outerWidth(), hauteur = $el.outerHeight(), gauche, haut;
        if (ancre && ancre.getBoundingClientRect) {
            var r = ancre.getBoundingClientRect();
            gauche = r.right + 8; haut = r.top - 8;
            if (gauche + largeur > window.innerWidth - 8) { gauche = r.left - largeur - 8; }
        } else { gauche = x; haut = y; }
        gauche = Math.max(8, Math.min(gauche, window.innerWidth - largeur - 8));
        haut = Math.max(8, Math.min(haut, window.innerHeight - hauteur - 8));
        $el.css({left: gauche + "px", top: haut + "px"});
    }

    // ------------------------------------------------------------------ Menu contextuel
    function Ouvrir_menu(x, y) {
        var jours = Jours_selectionnes();
        if (!jours.length) { return; }
        var titre = jours.length === 1 ? Texte_jour_long(jours[0]) : Pluriel(jours.length, "jour") + " sélectionnés";
        var html = "<div class='pl-menu-titre'>" + Echapper(titre) + "</div>";
        html += "<button type='button' role='menuitem' data-menu='jour'" + (jours.length > 1 ? " disabled" : "") + "><i class='fa fa-list' aria-hidden='true'></i>Voir et modifier la journée…<span class='pl-kbd'>Entrée</span></button>";
        if (Modifiable()) {
            html += "<button type='button' role='menuitem' data-menu='ajouter'><i class='fa fa-plus' aria-hidden='true'></i>Ajouter un évènement…</button>" +
                    "<button type='button' role='menuitem' data-menu='periode'><i class='fa fa-calendar-plus-o' aria-hidden='true'></i>Créer une période…</button>" +
                    "<div class='pl-menu-sep'></div><div class='pi-menu-titre'>Poser rapidement</div>";
            S.catOrdre.forEach(function(id) {
                var c = S.cats.get(id);
                html += "<div class='pi-menu-pose'><span class='pl-pastille' style='background:" + Echapper(c.couleur) + "'></span><span class='nom'>" + Echapper(c.nom) + "</span>" +
                        "<button type='button' role='menuitem' data-poser='" + id + "' data-mode='journee' aria-label='Poser " + Echapper(c.nom) + " : journée'>Journée</button>" +
                        "<button type='button' role='menuitem' data-poser='" + id + "' data-mode='matin' aria-label='Poser " + Echapper(c.nom) + " : matin'>Matin</button>" +
                        "<button type='button' role='menuitem' data-poser='" + id + "' data-mode='am' aria-label='Poser " + Echapper(c.nom) + " : après-midi'>A-midi</button></div>";
            });
            html += "<div class='pl-menu-sep'></div>" +
                    (S.modeles.length ? "<button type='button' role='menuitem' data-menu='modele'><i class='fa fa-th-list' aria-hidden='true'></i>Appliquer un modèle…</button>" : "") +
                    "<button type='button' role='menuitem' data-menu='copier'><i class='fa fa-copy' aria-hidden='true'></i>Copier<span class='pl-kbd'>Ctrl+C</span></button>" +
                    "<button type='button' role='menuitem' data-menu='coller'" + (Presse_papier ? "" : " disabled") + "><i class='fa fa-paste' aria-hidden='true'></i>Coller<span class='pl-kbd'>Ctrl+V</span></button>" +
                    "<button type='button' role='menuitem' class='danger' data-menu='effacer'><i class='fa fa-trash' aria-hidden='true'></i>Effacer les évènements<span class='pl-kbd'>Suppr</span></button>";
        }
        var $menu = $("#pi_menu").html(html).prop("hidden", false);
        Positionner($menu, null, x, y);
        $menu.find("button:not(:disabled)").first().trigger("focus");
    }
    function Fermer_menu() { $("#pi_menu").prop("hidden", true); }

    // ------------------------------------------------------------------ Modale évènement
    var Edition = null;
    function Ouvrir_evt(evt, jour) {
        if (!Modifiable()) { return; }
        Fermer_menu();
        // La fenêtre du jour est masquée pendant l'édition puis réaffichée à la fermeture
        V.pop_retour = V.pop_jour;
        if (V.pop_jour !== null) { Fermer_jour(); }
        var nouveau = !evt;
        if (nouveau) {
            var plage = Plages_mode("journee")[0];
            var cat = S.dernier_cat && S.cats.has(S.dernier_cat) ? S.dernier_cat : S.catOrdre[0];
            evt = Nouvel_evt(jour, plage[0], plage[1], cat, null, "");
        }
        Edition = {id: nouveau ? null : evt.id, avant: nouveau ? null : Copie_evt(evt)};
        var j1 = Jour_de(evt.s), j2 = Jour_de(evt.e - 1);
        $("#pi_modal_evt_titre").text(nouveau ? "Nouvel évènement" : "Modifier l'évènement");
        Select2_categorie($("#pi_evt_cat").html(Options_categories(evt.cat)), $("#pi_modal_evt"));
        $("#pi_evt_date").val(Iso_jour(j1));
        $("#pi_evt_debut").val(Heure(evt.s));
        $("#pi_evt_fin").val(Heure(evt.e));
        $("#pi_evt_multi").prop("checked", j2 !== j1);
        $("#pi_evt_date_fin").val(Iso_jour(Jour_de(evt.e))).closest(".form-group").prop("hidden", j2 === j1);
        $("#pi_evt_titre").val(evt.t || "");
        Select2_affectation($("#pi_evt_aff").html(Options_affectations(evt.aff)), $("#pi_modal_evt"));
        $("#pi_evt_rdebut").val(evt.rs !== null && evt.rs !== undefined ? Heure(evt.rs) : "");
        $("#pi_evt_rfin").val(evt.re !== null && evt.re !== undefined ? Heure(evt.re) : "");
        $("#pi_evt_info").text("").removeClass("erreur");
        $("#pi_evt_supprimer").prop("hidden", nouveau);
        $("#pi_modal_evt").modal("show");
    }
    function Valider_evt() {
        var date = $("#pi_evt_date").val(), debut = Minutes_heure($("#pi_evt_debut").val()), fin = Minutes_heure($("#pi_evt_fin").val());
        var $info = $("#pi_evt_info");
        if (!date || debut === null || fin === null) { $info.text("Saisissez la date et les heures de début et de fin.").addClass("erreur"); return; }
        var j = Parse_jour(date), s = j * 1440 + debut, e;
        if ($("#pi_evt_multi").prop("checked")) {
            var date_fin = $("#pi_evt_date_fin").val();
            if (!date_fin) { $info.text("Saisissez la date de fin.").addClass("erreur"); return; }
            e = Parse_jour(date_fin) * 1440 + fin;
        } else {
            e = j * 1440 + fin;
            if (fin <= debut) { e += 1440; }      // évènement de nuit
        }
        if (e <= s) { $info.text("La fin doit être postérieure au début.").addClass("erreur"); return; }
        if (e - s > 31 * 1440) { $info.text("Un évènement ne peut pas dépasser 31 jours.").addClass("erreur"); return; }
        if (!Dans_periode(j)) { $info.text("La date doit être comprise dans la période affichée (" + S.periode.libelle + ").").addClass("erreur"); return; }
        var rd = Minutes_heure($("#pi_evt_rdebut").val()), rf = Minutes_heure($("#pi_evt_rfin").val());
        if ((rd === null) !== (rf === null)) { $info.text("Saisissez à la fois le début et la fin du réalisé.").addClass("erreur"); return; }
        var rs = rd !== null ? j * 1440 + rd : null, re = rf !== null ? j * 1440 + rf : null;
        if (re !== null && re <= rs) { re += 1440; }
        var cat = +$("#pi_evt_cat").val(), aff = $("#pi_evt_aff").val() ? +$("#pi_evt_aff").val() : null;
        var apres = {id: Edition.id !== null ? Id_actuel(Edition.id) : S.prochain_tmp--, c: S.collab.id, cat: cat, aff: aff, t: $("#pi_evt_titre").val().trim(), s: s, e: e, rs: rs, re: re, v: 1};
        var conflits = Conflits(apres);
        if (conflits.length) {
            var c = S.cats.get(conflits[0].cat);
            $info.text("Chevauchement avec « " + (c ? c.nom : "") + " » de " + Heure_courte(conflits[0].s) + " à " + Heure_courte(conflits[0].e) + " le " + Texte_jour_fr(Jour_de(conflits[0].s)) + ".").addClass("erreur");
            return;
        }
        S.dernier_cat = cat;
        if (Edition.id === null) {
            Valider("Ajouter un évènement", [{type: "create", id: apres.id, apres: apres}]);
        } else {
            var actuel = S.evts.get(Id_actuel(Edition.id));
            if (!actuel) { $info.text("Cet évènement n'existe plus.").addClass("erreur"); return; }
            apres.v = actuel.v;
            Valider("Modifier un évènement", [{type: "update", id: actuel.id, avant: Copie_evt(actuel), apres: apres}]);
        }
        $("#pi_modal_evt").modal("hide");
    }
    function Supprimer_evt(id) {
        var evt = S.evts.get(Id_actuel(id));
        if (!evt) { return; }
        Valider("Supprimer un évènement", [{type: "delete", id: evt.id, avant: Copie_evt(evt)}]);
        toastr.success("Évènement supprimé. Ctrl+Z pour annuler.");
    }

    // ------------------------------------------------------------------ Modale "Créer une période"
    function Ouvrir_periode(cat) {
        if (!Modifiable()) { return; }
        Fermer_menu();
        var jours = Jours_selectionnes();
        if (!jours.length) { return; }
        var p = S.prefs;
        $("#pi_per_intro").text(jours.length === 1 ? Texte_jour_long(jours[0]) : "Du " + Texte_jour_court(jours[0]) + " au " + Texte_jour_court(jours[jours.length - 1]) + " · " + Pluriel(jours.length, "jour"));
        Select2_categorie($("#pi_per_cat").html(Options_categories(cat || S.dernier_cat || S.catOrdre[0])), $("#pi_modal_periode"));
        Select2_affectation($("#pi_per_aff").html(Options_affectations(null)), $("#pi_modal_periode"));
        $("#pi_per_titre").val("");
        $("input[name='pi_per_mode'][value='journee']").prop("checked", true);
        $("#pi_per_journee_debut").val(p.journee_debut); $("#pi_per_journee_fin").val(p.journee_fin);
        $("#pi_per_matin_debut").val(p.matin_debut); $("#pi_per_matin_fin").val(p.matin_fin);
        $("#pi_per_am_debut").val(p.am_debut); $("#pi_per_am_fin").val(p.am_fin);
        $("#pi_per_perso_debut").val(p.journee_debut); $("#pi_per_perso_fin").val(p.journee_fin);
        $("#pi_per_non_ouvres").prop("checked", p.ignorer_non_ouvres !== false);
        $("input[name='pi_per_conflit'][value='ignorer']").prop("checked", true);
        $("#pi_per_memoriser").prop("checked", false);
        Maj_apercu_periode();
        $("#pi_modal_periode").modal("show");
    }
    function Options_periode() {
        var mode = $("input[name='pi_per_mode']:checked").val(), plages;
        var lire = function(a, b) { var d = Minutes_heure($(a).val()), f = Minutes_heure($(b).val()); return d !== null && f !== null && f > d ? [d, f] : null; };
        if (mode === "matin") { plages = [lire("#pi_per_matin_debut", "#pi_per_matin_fin")]; }
        else if (mode === "am") { plages = [lire("#pi_per_am_debut", "#pi_per_am_fin")]; }
        else if (mode === "journee_coupee") { plages = [lire("#pi_per_matin_debut", "#pi_per_matin_fin"), lire("#pi_per_am_debut", "#pi_per_am_fin")]; }
        else if (mode === "perso") { plages = [lire("#pi_per_perso_debut", "#pi_per_perso_fin")]; }
        else { plages = [lire("#pi_per_journee_debut", "#pi_per_journee_fin")]; }
        return {jours: Jours_selectionnes(), cat: +$("#pi_per_cat").val(), plages: plages, aff: $("#pi_per_aff").val() ? +$("#pi_per_aff").val() : null,
                titre: $("#pi_per_titre").val().trim(), ignorer_non_ouvres: $("#pi_per_non_ouvres").prop("checked"), conflit: $("input[name='pi_per_conflit']:checked").val(), mode: mode};
    }
    function Maj_apercu_periode() {
        var o = Options_periode(), $ap = $("#pi_per_apercu");
        if (o.plages.some(function(p) { return !p; })) { $ap.html("<span class='text-danger'>Vérifiez les horaires : l'heure de fin doit être postérieure à l'heure de début.</span>"); return; }
        var jours = o.jours.filter(function(j) { return !(o.ignorer_non_ouvres && Est_non_ouvre(j)); });
        var occupes = jours.filter(function(j) { return Evts_du_jour(j, true).length; }).length;
        var duree = o.plages.reduce(function(t, p) { return t + p[1] - p[0]; }, 0);
        var texte = Pluriel(jours.length * o.plages.length, "évènement") + " de " + Duree(duree / o.plages.length) + " sur " + Pluriel(jours.length, "jour");
        if (occupes) { texte += " · " + Pluriel(occupes, "jour") + " déjà occupé" + (occupes > 1 ? "s" : "") + (o.conflit === "remplacer" ? " : leurs évènements seront remplacés" : " : les plages en chevauchement seront ignorées"); }
        $ap.text(texte);
    }
    function Valider_periode() {
        var o = Options_periode();
        if (o.plages.some(function(p) { return !p; })) { Maj_apercu_periode(); return; }
        if ($("#pi_per_memoriser").prop("checked")) {
            var prefs = {journee_debut: $("#pi_per_journee_debut").val(), journee_fin: $("#pi_per_journee_fin").val(), matin_debut: $("#pi_per_matin_debut").val(),
                         matin_fin: $("#pi_per_matin_fin").val(), am_debut: $("#pi_per_am_debut").val(), am_fin: $("#pi_per_am_fin").val(), ignorer_non_ouvres: o.ignorer_non_ouvres};
            $.extend(S.prefs, prefs);
            Memoriser_preferences(prefs);
        }
        S.dernier_cat = o.cat;
        if (Creer_periode(o)) { $("#pi_modal_periode").modal("hide"); }
    }

    // ------------------------------------------------------------------ Modale "Appliquer un modèle"
    function Ouvrir_modele() {
        if (!Modifiable()) { return; }
        Fermer_menu();
        var jours = Jours_selectionnes();
        var portee = jours.length ? (jours.length === 1 ? Texte_jour_long(jours[0]) : "Du " + Texte_jour_court(jours[0]) + " au " + Texte_jour_court(jours[jours.length - 1]) + " (" + Pluriel(jours.length, "jour") + ")")
                                  : "Toute la période " + S.periode.libelle;
        $("#pi_mod_intro").text(portee);
        Frise_modele().reinitialiser();
        Selecteur_modele().reinitialiser();
        $("input[name='pi_mod_conflit'][value='ignorer']").prop("checked", true);
        $("#pi_mod_apercu").prop("hidden", true).text("");
        $("#pi_modal_modele").modal("show");
    }
    var selecteur_modele = null;
    function Selecteur_modele() {
        if (!selecteur_modele) {
            selecteur_modele = SelecteurModelesPlanning({conteneur: "#pi_mod_modeles", url: CFG.urls.liste_modeles, csrf: CFG.csrf, parametres: function() {
                return {collaborateurs: [CFG.idcollaborateur || (S.collab && S.collab.id)].filter(Boolean), date: Iso_jour(Jours_modele()[0])};
            }, change: function() { Frise_modele().maj(); $("#pi_mod_apercu").prop("hidden", true); }});
        }
        return selecteur_modele;
    }
    var frise_modele = null;
    function Jours_modele() {
        var jours = Jours_selectionnes();
        if (!jours.length) { for (var j = Debut_periode(); j <= Fin_periode(); j++) { jours.push(j); } }
        return jours;
    }
    function Frise_modele() {
        if (!frise_modele) {
            frise_modele = FriseModelesPlanning({conteneur: "#pi_mod_frise", url: CFG.urls.frise, csrf: CFG.csrf, parametres: function() {
                return {modeles: Selecteur_modele().selection(), dates: Jours_modele().map(Iso_jour)};
            }, change: function() { $("#pi_mod_apercu").prop("hidden", true); }});
        }
        return frise_modele;
    }
    function Envoyer_modele(apercu) {
        var modeles = Selecteur_modele().selection();
        if (!modeles.length) { $("#pi_mod_apercu").prop("hidden", false).text("Cochez au moins un modèle."); return; }
        var jours = Jours_modele();
        if (!apercu && (envoi_en_cours || File_envoi.length)) { toastr.info("Enregistrement en cours, réessayez dans un instant"); return; }
        Ajax(CFG.urls.modele, {idcollaborateur: CFG.idcollaborateur, modeles: JSON.stringify(modeles), dates: JSON.stringify(jours.map(Iso_jour)),
                               conflit: $("input[name='pi_mod_conflit']:checked").val(), apercu: apercu ? "true" : "false",
                               departs: JSON.stringify(Frise_modele().departs()), forcer: Selecteur_modele().forcer() ? "true" : "false"}).done(function(data) {
            var texte = Pluriel(data.nbre_crees, "évènement") + (apercu ? " sera créé" + (data.nbre_crees > 1 ? "s" : "") : " créé" + (data.nbre_crees > 1 ? "s" : "")) +
                        (data.nbre_supprimes ? ", " + Pluriel(data.nbre_supprimes, "évènement") + " supprimé" + (data.nbre_supprimes > 1 ? "s" : "") : "") +
                        (data.nbre_ignores ? ", " + Pluriel(data.nbre_ignores, "ignoré") + " (chevauchement)" : "") +
                        (data.nbre_hors_contrat ? ", " + data.nbre_hors_contrat + " hors contrat" : "") + ".";
            (data.messages_restriction || []).forEach(function(message) { texte += " " + message + "."; });
            if (apercu) { $("#pi_mod_apercu").prop("hidden", false).text(texte); return; }
            $("#pi_modal_modele").modal("hide");
            toastr.success(texte);
            Charger(S.periode.annee, S.periode.type, true);
        }).fail(function(xhr) { $("#pi_mod_apercu").prop("hidden", false).text(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Ajustements, reports et paramètres
    function Ouvrir_ajustement(id) {
        var a = id ? S.objectif.ajustements.filter(function(x) { return x.id === id; })[0] : null;
        $("#pi_aju_id").val(a ? a.id : "");
        $("#pi_modal_ajust_titre").text(a ? (a.type === "REPORT" ? "Modifier le report de solde" : "Modifier l'ajustement") : "Nouvel ajustement");
        var defaut = Dans_periode(Aujourdhui()) ? Aujourdhui() : Debut_periode();
        $("#pi_aju_date").val(a ? a.date : Iso_jour(defaut)).attr("min", S.periode.debut).attr("max", S.periode.fin);
        $("#pi_aju_valeur").val(a ? String(a.valeur).replace(".", ",") : "");
        $("#pi_aju_unite").text(S.objectif.unite === "jours" ? "jours" : "heures (décimales : 1,5 = 1h30)");
        $("#pi_aju_motif").val(a ? a.motif : "");
        $("#pi_aju_info").text("").removeClass("erreur");
        $("#pi_modal_objectif").modal("hide");
        $("#pi_modal_ajust").modal("show");
    }
    function Donnees_periode(donnees) { return $.extend({idcollaborateur: CFG.idcollaborateur, annee: S.periode.annee, type_periode: S.periode.type}, donnees || {}); }
    function Valider_ajustement() {
        Ajax(CFG.urls.ajustement, Donnees_periode({idajustement: $("#pi_aju_id").val(), date: $("#pi_aju_date").val(), valeur: $("#pi_aju_valeur").val(), motif: $("#pi_aju_motif").val()})).done(function(data) {
            S.objectif = data.objectif;
            $("#pi_modal_ajust").modal("hide");
            toastr.success("Ajustement enregistré");
            Rafraichir_tout();
        }).fail(function(xhr) { $("#pi_aju_info").text(Message_erreur(xhr)).addClass("erreur"); });
    }
    function Supprimer_ajustement(id) {
        bootbox.confirm({title: "Supprimer l'ajustement", message: "Voulez-vous vraiment supprimer cet ajustement ?", buttons: {confirm: {label: "Supprimer", className: "btn-danger"}, cancel: {label: "Annuler"}},
            callback: function(ok) {
                if (!ok) { return; }
                Ajax(CFG.urls.supprimer_ajustement, Donnees_periode({idajustement: id})).done(function(data) {
                    S.objectif = data.objectif; Rafraichir_tout(); toastr.success("Ajustement supprimé");
                }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
            }});
    }
    function Reporter_solde() {
        if (envoi_en_cours || File_envoi.length) { toastr.info("Enregistrement en cours, réessayez dans un instant"); return; }
        var totaux = Totaux_planifies(), solde = totaux.total - S.objectif.objectif;
        var texte = solde > 0 ? "L'excédent de <strong>" + Valeur(solde) + "</strong> réduira l'objectif " + Echapper(S.periode_suivante) + "."
                  : (solde < 0 ? "Le déficit de <strong>" + Valeur(-solde) + "</strong> augmentera l'objectif " + Echapper(S.periode_suivante) + "." : "Le solde est nul.");
        var en_cours = Aujourdhui() <= Fin_periode();
        bootbox.confirm({title: "Reporter le solde " + Echapper(S.periode.libelle), message: texte + "<br><br>Le report est enregistré comme un ajustement au " + Texte_jour_fr(Fin_periode() + 1) +
                         ". Un report déjà effectué pour cette période est remplacé." + (en_cours ? "<br><br><strong>Attention : la période n'est pas terminée</strong>, le solde peut encore évoluer. Vous pourrez refaire le report plus tard." : ""),
            buttons: {confirm: {label: "Reporter"}, cancel: {label: "Annuler"}},
            callback: function(ok) {
                if (!ok) { return; }
                Ajax(CFG.urls.reporter, Donnees_periode()).done(function(data) { toastr.success(data.message); }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
            }});
    }
    function Ouvrir_parametres() {
        var p = S.parametres;
        $("#pi_par_volume").val(String(p.volume_annuel).replace(".", ","));
        $("#pi_par_temps_plein").val(String(p.temps_plein).replace(".", ","));
        $("#pi_par_forfait").val(String(p.forfait_jours).replace(".", ","));
        $("#pi_par_periode").val(p.periode);
        $("#pi_par_mois").val(p.mois_debut_scolaire);
        $("#pi_modal_parametres").modal("show");
    }
    function Valider_parametres() {
        var parametres = {volume_annuel: $("#pi_par_volume").val(), temps_plein: $("#pi_par_temps_plein").val(), forfait_jours: $("#pi_par_forfait").val(),
                          periode: $("#pi_par_periode").val(), mois_debut_scolaire: $("#pi_par_mois").val()};
        Ajax(CFG.urls.parametres, {parametres: JSON.stringify(parametres)}).done(function() {
            $("#pi_modal_parametres").modal("hide");
            toastr.success("Paramètres enregistrés");
            Charger(S.periode.annee, S.periode.type, true);
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Impression, email, Excel et agenda
    var Diff_action = null;
    var DIFF_OPTIONS = {annuel: [], bilan: [], calendrier: ["notes"], individuel: ["affs", "realise"], recapitulatif: []};
    var DIFF_TITRES = {imprimer: "Imprimer le planning", email: "Envoyer le planning par email", excel: "Exporter vers Excel"};
    function Fermer_menu_diffusion() { $("#pi_diffusion_menu").prop("hidden", true); $("#pi_diffusion_btn").attr("aria-expanded", "false"); }
    function Ouvrir_diffusion(action) {
        if (!S.charge) { return; }
        if (action === "ecran") { window.print(); return; }
        if (action === "ical") { Ouvrir_ical(); return; }
        Diff_action = action;
        Fermer_jour(); Fermer_menu();
        $("#pi_diff_titre").text(DIFF_TITRES[action] + " · " + S.collab.nom + " " + S.collab.prenom);
        $("#pi_diff_types_bloc").prop("hidden", action === "excel");
        $("#pi_diff_excel_bloc").prop("hidden", action !== "excel");
        // Période : toute la période, plage de mois ou jours sélectionnés
        $("#pi_diff_portee_periode").text("Toute la période " + S.periode.libelle);
        $("#pi_diff_portee_periode_info").text("du " + Texte_jour_fr(Debut_periode()) + " au " + Texte_jour_fr(Fin_periode()));
        var options = Mois_de_la_periode().map(function(mo) { return "<option value='" + mo.a + "-" + Pad(mo.m + 1) + "'>" + MOIS[mo.m].charAt(0).toUpperCase() + MOIS[mo.m].substr(1) + " " + mo.a + "</option>"; }).join("");
        var auj = Infos_jour(Dans_periode(Aujourdhui()) ? Aujourdhui() : Debut_periode()), courant = auj.a + "-" + Pad(auj.m + 1);
        $("#pi_diff_mois_debut").html(options).val(courant);
        $("#pi_diff_mois_fin").html(options).val(courant);
        var jours = Jours_selectionnes();
        $("#pi_diff_selection_info").text(jours.length ? (jours.length === 1 ? Texte_jour_long(jours[0]) : Pluriel(jours.length, "jour") + " (" + Texte_jour_court(jours[0]) + " → " + Texte_jour_court(jours[jours.length - 1]) + ")") : "Aucun jour sélectionné");
        $("input[name='pi_diff_portee'][value='selection']").prop("disabled", !jours.length);
        $("input[name='pi_diff_portee'][value='" + (jours.length > 1 ? "selection" : "periode") + "']").prop("checked", true);
        // Destinataire
        var $dest = $("#pi_diff_dest").removeClass("erreur");
        if (S.collab.mail) { $dest.html("<i class='fa fa-envelope-o' aria-hidden='true'></i> " + Echapper(S.collab.mail) + " <span class='pl-muted' style='margin-left:auto'>" + (S.collab.mail_pro ? "adresse professionnelle" : "adresse personnelle") + "</span>"); }
        else { $dest.addClass("erreur").text("Aucune adresse email : renseignez-la dans la fiche collaborateur (Coordonnées)."); }
        $("#pi_diff_email_bloc").prop("hidden", action !== "email");
        $("#pi_diff_realise").prop("checked", false);
        Maj_diffusion();
        $("#pi_modal_diffusion").modal("show");
    }
    function Type_diffusion() { return $("input[name='pi_diff_type']:checked").val() || "annuel"; }
    function Maj_diffusion() {
        var excel = Diff_action === "excel", type = Type_diffusion(), export_paie = $("input[name='pi_diff_export']:checked").val() === "paie";
        var portee_fixe = excel ? !export_paie : (type === "annuel" || type === "bilan");
        $("#pi_diff_portee_bloc .pl-radio-carte").prop("hidden", portee_fixe);
        $("#pi_diff_portee_fixe").prop("hidden", !portee_fixe).text(excel ? "Le bilan annuel porte toujours sur toute la période " + S.periode.libelle + "." : "Ce document porte toujours sur toute la période " + S.periode.libelle + ".");
        var options = excel ? [] : DIFF_OPTIONS[type];
        $("#pi_diff_options [data-option]").each(function() { this.hidden = options.indexOf(this.getAttribute("data-option")) < 0; });
        $("#pi_diff_options").prop("hidden", excel);
        $("#pi_diff_sans_option").prop("hidden", options.length > 0);
        // Avertissement sur le volume de pages
        var avert = "", portee = $("input[name='pi_diff_portee']:checked").val();
        if (!portee_fixe && (type === "calendrier" || type === "recapitulatif") && !excel) {
            var nb = portee === "periode" ? 12 : (portee === "mois" ? Math.abs(Nb_mois($("#pi_diff_mois_debut").val(), $("#pi_diff_mois_fin").val())) + 1 : 0);
            if (nb > 3) { avert = "Ce document comporte une page par mois : " + nb + " pages seront générées."; }
        }
        if (Diff_action === "email" && !S.collab.mail) { avert = "Impossible d'envoyer : ce collaborateur n'a pas d'adresse email."; }
        $("#pi_diff_avert").text(avert).prop("hidden", !avert);
        $("#pi_diff_valider").prop("disabled", Diff_action === "email" && !S.collab.mail);
    }
    function Nb_mois(a, b) { if (!a || !b) { return 0; } return (+b.substr(0, 4) - +a.substr(0, 4)) * 12 + (+b.substr(5, 2) - +a.substr(5, 2)); }
    function Valider_diffusion() {
        var coche = function(id) { return $(id).is(":checked") ? "true" : "false"; };
        var donnees = Donnees_periode({type: Type_diffusion(), portee: $("input[name='pi_diff_portee']:checked").val(), mois_debut: $("#pi_diff_mois_debut").val(), mois_fin: $("#pi_diff_mois_fin").val(),
                                       dates: JSON.stringify(Jours_selectionnes().map(Iso_jour)), afficher_realise: coche("#pi_diff_realise"),
                                       afficher_affectations: coche("#pi_diff_affs"), afficher_notes: coche("#pi_diff_notes"), export: $("input[name='pi_diff_export']:checked").val()});
        var url = {imprimer: CFG.urls.imprimer, email: CFG.urls.email, excel: CFG.urls.excel}[Diff_action];
        var $bouton = $("#pi_diff_valider").prop("disabled", true).html("<i class='fa fa-spinner fa-spin margin-r-5'></i>Génération…");
        Ajax(url, donnees).done(function(data) {
            $("#pi_modal_diffusion").modal("hide");
            if (Diff_action === "imprimer") { $("#pi_modal_diffusion").one("hidden.bs.modal", function() { charge_pdf(data); }); }
            if (Diff_action === "excel" || Diff_action === "email") { window.location = data.url; }
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); })
          .always(function() { $bouton.prop("disabled", false).html("<i class='fa fa-check margin-r-5'></i>Valider"); });
    }
    function Ouvrir_ical() {
        $("#pi_ical_intro").text("Abonnez l'agenda de " + S.collab.nom + " " + S.collab.prenom + " (Google Agenda, Outlook, téléphone…) avec ce lien. Les évènements s'y mettent à jour automatiquement.");
        Action_ical("obtenir", true);
    }
    function Action_ical(action, ouvrir) {
        Ajax(CFG.urls.ical, {idcollaborateur: CFG.idcollaborateur, action: action}).done(function(data) {
            if (!data.url) { $("#pi_modal_ical").modal("hide"); toastr.success("Le lien d'agenda a été désactivé"); return; }
            $("#pi_ical_url").val(data.url);
            if (ouvrir) { $("#pi_modal_ical").modal("show"); }
            if (action === "regenerer") { toastr.success("Nouveau lien généré : l'ancien ne fonctionne plus"); }
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Navigation
    function Changer_periode(annee, type) {
        Fermer_jour(); Fermer_menu();
        Charger(annee, type);
    }
    function Changer_vue(vue) {
        if (!VUES[vue] || vue === V.vue) { return; }
        V.vue = vue;
        Rafraichir_tout();
        Memoriser_preferences({vue: vue});
    }
    function Changer_collaborateur(id) {
        if (!id || id === CFG.idcollaborateur) { return; }
        if (envoi_en_cours || File_envoi.length) { toastr.info("Enregistrement en cours, réessayez dans un instant"); $("#pi_collab_select").val(CFG.idcollaborateur).trigger("change.select2"); return; }
        CFG.idcollaborateur = id;
        $("#pi_collab_select").val(id).trigger("change.select2");
        Fermer_jour(); Fermer_menu();
        V.masquees.clear();
        if (window.history && history.replaceState) { history.replaceState(null, "", "?idcollaborateur=" + id); }
        Charger(S.periode ? S.periode.annee : null, null);
    }
    function Deplacer_curseur(delta, etendre) {
        var depart = V.curseur !== null ? V.curseur : (V.selection.size ? Jours_selectionnes()[0] : (Dans_periode(Aujourdhui()) ? Aujourdhui() : Debut_periode()));
        var j = Math.max(Debut_periode(), Math.min(Fin_periode(), depart + delta));
        V.curseur = j;
        if (etendre && V.ancre !== null) { Selectionner(Plage(V.ancre, j)); }
        else { V.ancre = j; Selectionner([j]); }
        var el = $("#pi_corps [data-j='" + j + "']")[0];
        if (el && el.scrollIntoView) { el.scrollIntoView({block: "nearest", inline: "nearest"}); }
    }
    function Delta_vertical(sens) {
        // Haut/bas : semaine (calendrier), jour (colonnes), mois (mois x jours)
        if (V.vue === "colonnes") { return sens; }
        if (V.vue === "mois") {
            var j = V.curseur !== null ? V.curseur : Debut_periode(), i = Infos_jour(j);
            var a = i.a + Math.floor((i.m + sens + 12) / 12) - 1, m = (i.m + sens + 12) % 12;
            return Jour_depuis(a, m, Math.min(i.j, Nbre_jours_mois(a, m))) - j;
        }
        return 7 * sens;
    }
    function Delta_horizontal(sens) {
        if (V.vue !== "colonnes") { return sens; }
        var j = V.curseur !== null ? V.curseur : Debut_periode(), i = Infos_jour(j);
        var a = i.a + Math.floor((i.m + sens + 12) / 12) - 1, m = (i.m + sens + 12) % 12;
        return Jour_depuis(a, m, Math.min(i.j, Nbre_jours_mois(a, m))) - j;
    }

    // ------------------------------------------------------------------ Evènements de l'interface
    function Initialiser() {
        var $corps = $("#pi_corps");

        // Sélection à la souris (cliquer-glisser)
        $corps.on("mousedown", "[data-j]", function(e) {
            if (e.button !== 0) { return; }
            var j = +this.getAttribute("data-j");
            Fermer_menu();
            if (V.pop_jour !== null && V.pop_jour !== j) { Fermer_jour(); }
            if (e.shiftKey && V.ancre !== null) { Selectionner(Plage(V.ancre, j)); }
            else if (e.ctrlKey || e.metaKey) {
                if (V.selection.has(j)) { V.selection.delete(j); } else { V.selection.add(j); }
                V.ancre = j; Maj_selection();
            } else {
                V.ancre = j;
                V.drag = {depart: j};
                Selectionner([j]);
            }
            V.curseur = j;
            Focus_corps();
            e.preventDefault();
        });
        $corps.on("mouseover", "[data-j]", function() {
            if (!V.drag) { return; }
            Selectionner(Plage(V.drag.depart, +this.getAttribute("data-j")));
        });
        $(document).on("mouseup.pi", function() { V.drag = null; });
        $corps.on("dblclick", "[data-j]", function() { Ouvrir_jour(+this.getAttribute("data-j"), this); });
        $corps.on("contextmenu", "[data-j]", function(e) {
            var j = +this.getAttribute("data-j");
            if (!V.selection.has(j)) { V.ancre = j; Selectionner([j]); }
            V.curseur = j;
            Fermer_jour();
            Ouvrir_menu(e.clientX, e.clientY);
            e.preventDefault();
        });

        // Clavier
        $corps.on("keydown", function(e) {
            if (!S.charge) { return; }
            var touche = e.key;
            if (touche === "ArrowLeft") { Deplacer_curseur(Delta_horizontal(-1), e.shiftKey); e.preventDefault(); }
            else if (touche === "ArrowRight") { Deplacer_curseur(Delta_horizontal(1), e.shiftKey); e.preventDefault(); }
            else if (touche === "ArrowUp") { Deplacer_curseur(Delta_vertical(-1), e.shiftKey); e.preventDefault(); }
            else if (touche === "ArrowDown") { Deplacer_curseur(Delta_vertical(1), e.shiftKey); e.preventDefault(); }
            else if (touche === "Enter" && V.curseur !== null) { Ouvrir_jour(V.curseur); e.preventDefault(); }
            else if ((touche === "ContextMenu" || (touche === "F10" && e.shiftKey)) && V.selection.size) {
                var el = $corps.find("[data-j='" + Jours_selectionnes()[0] + "']")[0], r = el ? el.getBoundingClientRect() : {left: 100, bottom: 100};
                Ouvrir_menu(r.left, r.bottom); e.preventDefault();
            }
        });
        $(document).on("keydown.pi", function(e) {
            var cible = e.target, saisie = cible && (/^(INPUT|TEXTAREA|SELECT)$/.test(cible.tagName) || cible.isContentEditable);
            if (saisie || $(".modal.show").length) { return; }
            if (!$(cible).closest("#pi_app").length && cible !== document.body) { return; }
            var ctrl = e.ctrlKey || e.metaKey, touche = (e.key || "").toLowerCase();
            if (touche === "escape") {
                if (!$("#pi_menu").prop("hidden")) { Fermer_menu(); Focus_corps(); }
                else if (V.pop_jour !== null) { Fermer_jour(true); }
                else { Vider_selection(); }
                return;
            }
            if (ctrl && touche === "z" && !e.shiftKey) { e.preventDefault(); if (Modifiable()) { Annuler(); } return; }
            if (ctrl && (touche === "y" || (touche === "z" && e.shiftKey))) { e.preventDefault(); if (Modifiable()) { Retablir(); } return; }
            if (!V.selection.size || !Modifiable()) { return; }
            if (ctrl && touche === "c") { e.preventDefault(); Copier_selection(); }
            else if (ctrl && touche === "v") { e.preventDefault(); Coller(); }
            else if ((touche === "delete" || touche === "backspace") && $(cible).closest("#pi_corps, body").length) { e.preventDefault(); Effacer_selection(); }
        });

        // Fermeture des popovers au clic extérieur
        $(document).on("mousedown.pi", function(e) {
            if (!$(e.target).closest("#pi_menu").length) { Fermer_menu(); }
            if (V.pop_jour !== null && !$(e.target).closest("#pi_pop, [data-j], .modal, .bootbox").length) { Fermer_jour(); }
        });
        $(window).on("resize.pi scroll.pi", Debounce(function() { Fermer_menu(); }, 50));
        $(window).on("resize.pi scroll.pi", Positionner_actions);
        document.addEventListener("fullscreenchange", Positionner_actions);

        // Barre d'outils
        $("#pi_app").on("click", "button[data-vue]", function() { Changer_vue(this.getAttribute("data-vue")); });
        $("#pi_app").on("click", "button[data-type-periode]", function() {
            var type = this.getAttribute("data-type-periode");
            if (type === S.periode.type) { return; }
            // Conserve la période qui contient le milieu de la période actuelle
            var milieu = Infos_jour(Math.floor((Debut_periode() + Fin_periode()) / 2));
            var annee = type === "SCOLAIRE" && milieu.m + 1 < S.parametres.mois_debut_scolaire ? milieu.a - 1 : milieu.a;
            Changer_periode(annee, type);
        });
        $("#pi_prec").on("click", function() { Changer_periode(S.periode.annee - 1, S.periode.type); });
        $("#pi_suiv").on("click", function() { Changer_periode(S.periode.annee + 1, S.periode.type); });
        $("#pi_aujourdhui").on("click", function() {
            var auj = Infos_jour(Aujourdhui()), annee = S.periode.type === "SCOLAIRE" && auj.m + 1 < S.parametres.mois_debut_scolaire ? auj.a - 1 : auj.a;
            var aller = function() { V.curseur = Aujourdhui(); V.ancre = V.curseur; Selectionner([V.curseur]); var el = $corps.find("[data-j='" + V.curseur + "']")[0]; if (el) { el.scrollIntoView({block: "center", inline: "center"}); } };
            if (annee !== S.periode.annee) { Changer_periode(annee, S.periode.type); var d = requete_donnees; if (d) { d.done(function() { setTimeout(aller, 0); }); } } else { aller(); }
        });
        $("#pi_annuler").on("click", Annuler);
        $("#pi_retablir").on("click", Retablir);
        $("#pi_ajouter").on("click", function() {
            var jours = Jours_selectionnes();
            Ouvrir_evt(null, jours.length ? jours[0] : (Dans_periode(Aujourdhui()) ? Aujourdhui() : Debut_periode()));
        });
        $("#pi_actualiser").on("click", function() { Charger(S.periode.annee, S.periode.type, true); });
        $("#pi_plein_ecran").on("click", function() {
            var el = document.getElementById("pi_app");
            if (document.fullscreenElement) { document.exitFullscreen(); } else if (el.requestFullscreen) { el.requestFullscreen(); }
        });
        // Impression et diffusion
        $("#pi_diffusion_btn").on("click", function(e) {
            e.stopPropagation();
            var $menu = $("#pi_diffusion_menu"), ouvrir = $menu.prop("hidden");
            $menu.prop("hidden", !ouvrir);
            $(this).attr("aria-expanded", String(ouvrir));
            if (ouvrir) {
                // Ouverture vers la gauche, sauf si le menu sortirait de l'écran
                $menu.addClass("pl-pop-droite");
                if ($menu[0].getBoundingClientRect().left < 8) { $menu.removeClass("pl-pop-droite"); }
            }
            if (ouvrir) { $menu.find("button:visible").first().trigger("focus"); }
        });
        $("#pi_diffusion_menu").on("click", "[data-diffusion]", function() { Fermer_menu_diffusion(); Ouvrir_diffusion(this.getAttribute("data-diffusion")); });
        $("#pi_diffusion_menu").on("keydown", function(e) {
            var $items = $(this).find("button:visible"), index = $items.index(document.activeElement);
            if (e.key === "ArrowDown") { $items.eq((index + 1) % $items.length).trigger("focus"); e.preventDefault(); }
            if (e.key === "ArrowUp") { $items.eq((index - 1 + $items.length) % $items.length).trigger("focus"); e.preventDefault(); }
            if (e.key === "Escape" || e.key === "Tab") { Fermer_menu_diffusion(); $("#pi_diffusion_btn").trigger("focus"); e.preventDefault(); e.stopPropagation(); }
        });
        $(document).on("mousedown.pi", function(e) { if (!$(e.target).closest("#pi_diffusion_menu, #pi_diffusion_btn").length) { Fermer_menu_diffusion(); } });
        $("#pi_modal_diffusion").on("change", "input[name='pi_diff_type'], input[name='pi_diff_export'], input[name='pi_diff_portee'], select", Maj_diffusion);
        $("#pi_modal_diffusion").on("focus", ".pl-inline-champs select", function() { $("input[name='pi_diff_portee'][value='mois']").prop("checked", true); Maj_diffusion(); });
        $("#pi_modal_diffusion").on("dblclick", ".pl-type-doc", Valider_diffusion);
        $("#pi_diff_valider").on("click", Valider_diffusion);
        $("#pi_ical_copier").on("click", function() {
            var champ = document.getElementById("pi_ical_url");
            champ.select();
            if (navigator.clipboard) { navigator.clipboard.writeText(champ.value).then(function() { toastr.success("Lien copié"); }); } else { document.execCommand("copy"); toastr.success("Lien copié"); }
        });
        $("#pi_ical_regenerer").on("click", function() { Action_ical("regenerer"); });
        $("#pi_ical_revoquer").on("click", function() { Action_ical("revoquer"); });
        $("#pi_parametres_btn").on("click", Ouvrir_parametres);

        // Barre d'actions de la sélection
        $("#pi_act_periode").on("click", function() { Ouvrir_periode(); });
        $("#pi_act_modele").on("click", Ouvrir_modele);
        $("#pi_act_copier").on("click", Copier_selection);
        $("#pi_act_coller").on("click", Coller);
        $("#pi_act_effacer").on("click", Effacer_selection);
        $("#pi_act_fermer").on("click", Vider_selection);

        // Menu contextuel
        $("#pi_menu").on("click", "[data-menu]", function() {
            var action = $(this).data("menu"), jours = Jours_selectionnes();
            Fermer_menu();
            if (action === "jour") { Ouvrir_jour(jours[0]); }
            if (action === "ajouter") { Ouvrir_evt(null, jours[0]); }
            if (action === "periode") { Ouvrir_periode(); }
            if (action === "modele") { Ouvrir_modele(); }
            if (action === "copier") { Copier_selection(); }
            if (action === "coller") { Coller(); }
            if (action === "effacer") { Effacer_selection(); }
        });
        $("#pi_menu").on("click", "[data-poser]", function() { Fermer_menu(); Poser_rapidement(+$(this).data("poser"), $(this).data("mode")); });
        $("#pi_menu").on("keydown", function(e) {
            var $items = $(this).find("button:not(:disabled)"), index = $items.index(document.activeElement);
            if (e.key === "ArrowDown") { $items.eq((index + 1) % $items.length).trigger("focus"); e.preventDefault(); }
            if (e.key === "ArrowUp") { $items.eq((index - 1 + $items.length) % $items.length).trigger("focus"); e.preventDefault(); }
            if (e.key === "Tab") { Fermer_menu(); Focus_corps(); e.preventDefault(); }
        });

        // Popover du jour
        $("#pi_pop").on("click", "[data-action='pop-fermer']", function() { Fermer_jour(true); });
        $("#pi_pop").on("click", "[data-action='evt-ajouter']", function() { Ouvrir_evt(null, +$(this).data("jour")); });
        $("#pi_pop").on("click", "[data-evt-modifier]", function() { var evt = S.evts.get(Id_actuel(+$(this).data("evt-modifier"))); if (evt) { Ouvrir_evt(evt); } });
        $("#pi_pop").on("click", "[data-evt-supprimer]", function() { Supprimer_evt(+$(this).data("evt-supprimer")); });
        $("#pi_pop").on("keydown", function(e) { if (e.key === "Escape") { Fermer_jour(true); e.stopPropagation(); } });

        // Modale évènement
        $("#pi_evt_valider").on("click", Valider_evt);
        // Barre d'actions masquée tant qu'une fenêtre est ouverte
        $(document).on("show.bs.modal.pi", ".pi-modal, #modal_pdf", function() { $("#pi_actions").addClass("pi-masque"); });
        $(document).on("hidden.bs.modal.pi", ".pi-modal, #modal_pdf", function() { if (!$(".pi-modal.show, #modal_pdf.show").length) { $("#pi_actions").removeClass("pi-masque"); } });
        $("#pi_modal_evt").on("hidden.bs.modal", function() {
            if (V.pop_retour !== null && V.pop_retour !== undefined) { var j = V.pop_retour; V.pop_retour = null; Ouvrir_jour(j); }
        });
        $("#pi_evt_supprimer").on("click", function() { if (Edition && Edition.id !== null) { Supprimer_evt(Edition.id); $("#pi_modal_evt").modal("hide"); } });
        $("#pi_evt_multi").on("change", function() { $("#pi_evt_date_fin").closest(".form-group").prop("hidden", !this.checked); });
        $("#pi_evt_realise_copier").on("click", function() { $("#pi_evt_rdebut").val($("#pi_evt_debut").val()); $("#pi_evt_rfin").val($("#pi_evt_fin").val()); });
        $("#pi_modal_evt").on("keydown", "input", function(e) { if (e.key === "Enter") { Valider_evt(); e.preventDefault(); } });

        // Modale période
        $("#pi_modal_periode").on("change input", "input, select", Maj_apercu_periode);
        $("#pi_modal_periode").on("focus", ".pl-inline-champs input", function() { $(this).closest(".pl-radio-carte").find("input[type=radio]").prop("checked", true); Maj_apercu_periode(); });
        $("#pi_per_valider").on("click", Valider_periode);

        // Modale modèle
        $("#pi_mod_btn_apercu").on("click", function() { Envoyer_modele(true); });

        $("#pi_mod_valider").on("click", function() { Envoyer_modele(false); });

        // Objectif et ajustements
        $(document).on("click.pi", "[data-action='ajust-ajouter']", function() { Ouvrir_ajustement(null); });
        $(document).on("click.pi", "[data-ajust-modifier]", function() { Ouvrir_ajustement(+$(this).data("ajust-modifier")); });
        $(document).on("click.pi", "[data-ajust-supprimer]", function() { Supprimer_ajustement(+$(this).data("ajust-supprimer")); });
        $(document).on("click.pi", "[data-action='reporter']", function() { $("#pi_modal_objectif").modal("hide"); Reporter_solde(); });
        $(document).on("click.pi", "[data-action='objectif-detail']", function() {
            $("#pi_modal_objectif").one("shown.bs.modal", function() { $(this).find(".pi-detail").prop("open", true); }).modal("show");
        });
        $(document).on("click.pi", "[data-action='objectif-ajustements']", function() {
            $("#pi_modal_objectif").one("shown.bs.modal", function() { var t = $(this).find(".pi-ajust-titre")[0]; if (t) { t.scrollIntoView({block: "start"}); } }).modal("show");
        });
        $("#pi_aju_valider").on("click", Valider_ajustement);
        $("#pi_par_valider").on("click", Valider_parametres);

        // Légende : masquer / afficher une catégorie
        $("#pi_app").on("click", "button[data-cat]", function() {
            var id = +this.getAttribute("data-cat");
            if (V.masquees.has(id)) { V.masquees.delete(id); } else { V.masquees.add(id); }
            Rafraichir_tout();
        });

        // Panneau latéral (accordéon : plusieurs sections peuvent être ouvertes)
        $("#pi_app").on("click", ".pl-acc-tete", function() {
            var ouvert = $(this).attr("aria-expanded") === "true";
            $(this).attr("aria-expanded", String(!ouvert));
            $("#" + $(this).attr("aria-controls")).prop("hidden", ouvert);
        });

        // Collaborateur
        Initialiser_select2();
        $("#pi_collab_select").on("change", function() { Changer_collaborateur(+this.value); });

        // Avertissement avant de quitter avec des modifications non enregistrées
        $(window).on("beforeunload.pi", function() { if (envoi_en_cours || File_envoi.length) { return "Des modifications sont en cours d'enregistrement."; } });
    }

    $(function() {
        if (!CFG || !CFG.idcollaborateur) { return; }
        Initialiser();
        Charger(null, null);
    });

})(jQuery);
