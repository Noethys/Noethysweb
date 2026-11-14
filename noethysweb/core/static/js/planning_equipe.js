/*  Copyright (c) 2019-2026 Ivan LUCAS.
    Noethysweb, application de gestion multi-activités.
    Distribué sous licence GNU GPL.
    Planning des collaborateurs */

(function($) {
    "use strict";

    var CFG = window.PLANNING_CONFIG;
    var JOURS_COURTS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
    var JOURS_LONGS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];
    var MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
    var MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
    var HAUTEURS = {confortable: 48, compact: 26, mini: 16, groupe: 38, sous: 30, replie: 34};
    var COULEURS_AVATAR = ["#1d6fb8", "#0f766e", "#7c3aed", "#b45309", "#be185d", "#0369a1", "#15803d", "#9333ea", "#c2410c", "#475569"];

    // ------------------------------------------------------------------ Outils
    function Echapper(texte) {
        return String(texte === null || texte === undefined ? "" : texte).replace(/[&<>"']/g, function(c) {
            return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
        });
    }
    function Pad(n) { return (n < 10 ? "0" : "") + n; }

    // Les dates sont manipulées en minutes depuis l'epoch (heure locale "naïve" traitée comme UTC : pas de problème de changement d'heure)
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
    function Iso_jour(j) {
        var d = new Date(j * 86400000);
        return d.getUTCFullYear() + "-" + Pad(d.getUTCMonth() + 1) + "-" + Pad(d.getUTCDate());
    }
    function Jour_semaine(j) { return (new Date(j * 86400000).getUTCDay() + 6) % 7; }   // 0 = lundi
    function Infos_jour(j) { var d = new Date(j * 86400000); return {a: d.getUTCFullYear(), m: d.getUTCMonth(), j: d.getUTCDate()}; }
    function Texte_jour_long(j) { var i = Infos_jour(j); return JOURS_LONGS[Jour_semaine(j)] + " " + i.j + " " + MOIS[i.m] + " " + i.a; }
    function Texte_jour_court(j) { var i = Infos_jour(j); return JOURS_COURTS[Jour_semaine(j)] + " " + i.j + " " + MOIS_COURTS[i.m]; }
    function Texte_jour_fr(j) { var i = Infos_jour(j); return Pad(i.j) + "/" + Pad(i.m + 1) + "/" + i.a; }
    function Heure(m) { m = ((m % 1440) + 1440) % 1440; return Pad(Math.floor(m / 60)) + ":" + Pad(m % 60); }
    function Duree(minutes) {
        var signe = minutes < 0 ? "-" : "";
        minutes = Math.round(Math.abs(minutes));
        var h = Math.floor(minutes / 60), m = minutes % 60;
        return signe + h + " h" + (m ? " " + Pad(m) : "");
    }
    function Duree_decimale(minutes) {
        var v = Math.round(minutes / 6) / 10;
        return String(v).replace(".", ",");
    }
    function Aujourdhui() { return Parse_jour(CFG.aujourdhui || new Date().toISOString().substr(0, 10)); }
    function Debounce(fonction, delai) {
        var minuteur = null;
        return function() { var args = arguments, ctx = this; clearTimeout(minuteur); minuteur = setTimeout(function() { fonction.apply(ctx, args); }, delai); };
    }
    function Ajax(url, donnees) {
        donnees = donnees || {};
        donnees.csrfmiddlewaretoken = CFG.csrf;
        return $.ajax({url: url, type: "POST", data: donnees, dataType: "json"});
    }
    function Message_erreur(xhr, defaut) {
        return (xhr && xhr.responseJSON && xhr.responseJSON.erreur) || defaut || "Une erreur est survenue";
    }

    // ------------------------------------------------------------------ Etat
    var S = {
        cats: new Map(), affs: new Map(), affOrdre: [], collabs: new Map(), groupes: [], qualifs: [], modeles: [],
        evts: new Map(),            // id -> évènement {id, c, cat, aff, t, s, e, rs, re, v}
        index: new Map(),           // "c|jour" -> [ids]
        notes: new Map(), remplissages: new Map(), feries: new Map(), vacances: [],
        charges: new Set(),         // jours chargés
        chargement_en_cours: false,
        reglages_defaut: {}, reglages_user: {}, peut_regler_tous: false,
        prochain_tmp: -1
    };
    var V = {
        mode: "date", sous: "aucun", titres: true, affs: true, realise: false, densite: "auto", vue: "frise",
        affiches: [], masques: new Set(), dates: [], pas: 15, cat_defaut: null,
        filtres: {cats: new Set(), aff: null, qualif: null},
        plage: {auto: true, debut: 420, fin: 1140},
        panneau: "dates",          // section ouverte du panneau latéral (accordéon)
        bascules: new Map(),        // groupe -> déplié (true) / replié (false) choisi par l'utilisateur
        selection: new Set(), ligne_courante: null, mois_cal: null, ancre_cal: null, legende: "cat"
    };
    var R = {};                     // réglages effectifs
    var Pile = {annuler: [], retablir: []};
    var Alias = new Map();          // ancien id -> id actuel (après recréation / enregistrement)
    var File_envoi = [], envoi_en_cours = false, derniere_sauvegarde = null;
    var Presse_papier = [];

    function Reglages_effectifs() {
        R = $.extend({}, S.reglages_defaut, S.reglages_user);
    }

    function Id_actuel(id) {
        var vus = 0;
        while (Alias.has(id) && vus < 50) { id = Alias.get(id); vus++; }
        return id;
    }

    // ------------------------------------------------------------------ Données de référence
    function Charger_donnees_reference(data) {
        S.cats.clear();
        data.categories.forEach(function(c) { S.cats.set(c.id, c); });
        S.affs.clear(); S.affOrdre = [];
        data.affectations.forEach(function(a) { S.affs.set(a.id, a); S.affOrdre.push(a.id); });
        S.collabs.clear();
        data.collaborateurs.forEach(function(c, index) {
            c.contrats = c.contrats.map(function(contrat) { return {d: Parse_jour(contrat.d), f: contrat.f ? Parse_jour(contrat.f) : null, h: contrat.h}; });
            c.couleur = COULEURS_AVATAR[index % COULEURS_AVATAR.length];
            c.libelle = c.nom + (c.prenom ? " " + c.prenom : "");
            S.collabs.set(c.id, c);
        });
        S.groupes = data.groupes; S.qualifs = data.qualifications; S.modeles = data.modeles;
        S.reglages_defaut = data.reglages.defaut; S.reglages_user = data.reglages.utilisateur;
        S.peut_regler_tous = data.peut_regler_tous;
        CFG.aujourdhui = data.aujourdhui;
        Reglages_effectifs();
    }

    function Chemin_aff(id, abrege) {
        var noms = [], a = S.affs.get(id), garde = 0;
        while (a && garde < 50) { noms.unshift(abrege ? (a.abrege || a.nom) : a.nom); a = S.affs.get(a.parent); garde++; }
        return noms.join(" › ");
    }
    function Ancetres_aff(id) {
        var liste = [], a = S.affs.get(id), garde = 0;
        while (a && garde < 50) { liste.unshift(a.id); a = S.affs.get(a.parent); garde++; }
        return liste;
    }
    function Dans_sous_arbre(id, racine) {
        return id !== null && id !== undefined && Ancetres_aff(id).indexOf(racine) >= 0;
    }
    function Options_affectations(valeur, actives_seulement, libelle_vide) {
        var html = "<option value=''>" + Echapper(libelle_vide || "Aucune affectation") + "</option>";
        S.affOrdre.forEach(function(id) {
            var a = S.affs.get(id);
            if (actives_seulement && !a.actif && id !== valeur) { return; }
            html += "<option value='" + id + "' data-niveau='" + a.niveau + "'" + (id === valeur ? " selected" : "") + ">" + " ".repeat(a.niveau) + Echapper(a.nom) + (a.actif ? "" : " (inactive)") + "</option>";
        });
        return html;
    }

    function Contrat_actif(c, jour) {
        var collab = S.collabs.get(c);
        if (!collab || !collab.contrats.length) { return null; }
        for (var i = 0; i < collab.contrats.length; i++) {
            var contrat = collab.contrats[i];
            if (contrat.d <= jour && (contrat.f === null || jour <= contrat.f)) { return contrat; }
        }
        return false;
    }
    function Minutes_attendues(c, jours) {
        var total = 0;
        jours.forEach(function(j) {
            if (Jour_semaine(j) >= 5 || S.feries.has(j)) { return; }
            var contrat = Contrat_actif(c, j);
            if (contrat && contrat.h) { total += contrat.h / 5 * 60; }
        });
        return total;
    }

    // ------------------------------------------------------------------ Evènements
    function Evt_depuis_serveur(e) {
        return {id: e.id, c: e.c, cat: e.cat, aff: e.aff, t: e.t || "", s: Parse_min(e.d), e: Parse_min(e.f), rs: Parse_min(e.rd), re: Parse_min(e.rf), v: e.v};
    }
    function Evt_vers_serveur(evt) {
        return {c: evt.c, cat: evt.cat, aff: evt.aff || null, t: evt.t || "", d: Format_min(evt.s), f: Format_min(evt.e),
                rd: evt.rs !== null ? Format_min(evt.rs) : null, rf: evt.re !== null ? Format_min(evt.re) : null};
    }
    function Copie_evt(evt) { return $.extend({}, evt); }

    function Reindexer() {
        S.index.clear();
        S.evts.forEach(function(evt) {
            var j1 = Jour_de(evt.s), j2 = Jour_de(evt.e - 1);
            for (var j = j1; j <= j2; j++) {
                var cle = evt.c + "|" + j;
                if (!S.index.has(cle)) { S.index.set(cle, []); }
                S.index.get(cle).push(evt.id);
            }
        });
        S.index.forEach(function(liste) { liste.sort(function(a, b) { return S.evts.get(a).s - S.evts.get(b).s; }); });
    }
    function Evts_de(c, jour) {
        return (S.index.get(c + "|" + jour) || []).map(function(id) { return S.evts.get(id); });
    }
    function Signe_categorie(cat) {
        var c = S.cats.get(cat);
        if (!c) { return 0; }
        return c.type === "ADDITION" ? 1 : (c.type === "SOUSTRACTION" ? -1 : 0);
    }
    function Minutes_dans_jour(evt, jour, realise) {
        var s = realise ? evt.rs : evt.s, e = realise ? evt.re : evt.e;
        if (s === null || e === null) { return 0; }
        return Math.max(0, Math.min(e, (jour + 1) * 1440) - Math.max(s, jour * 1440));
    }
    function Evt_visible(evt) {
        var f = V.filtres;
        if (f.cats.size && !f.cats.has(evt.cat)) { return false; }
        if (f.aff !== null && !Dans_sous_arbre(evt.aff, f.aff)) { return false; }
        return true;
    }
    function Peut_chevaucher(a, b) {
        var ca = S.cats.get(a.cat), cb = S.cats.get(b.cat);
        return (ca && ca.chevauchement) || (cb && cb.chevauchement);
    }
    function Conflits(candidat, ignorer) {
        // Renvoie les évènements du même collaborateur en chevauchement avec le candidat
        ignorer = ignorer || new Set();
        var resultat = [];
        for (var j = Jour_de(candidat.s); j <= Jour_de(candidat.e - 1); j++) {
            Evts_de(candidat.c, j).forEach(function(autre) {
                if (autre.id === candidat.id || ignorer.has(autre.id) || resultat.indexOf(autre) >= 0) { return; }
                if (candidat.s < autre.e && candidat.e > autre.s && !Peut_chevaucher(candidat, autre)) { resultat.push(autre); }
            });
        }
        return resultat;
    }
    function Est_modifiable(c) { var collab = S.collabs.get(c); return !!(collab && collab.modifiable); }

    // ------------------------------------------------------------------ Chargement
    function Jours_a_charger(jours) {
        return jours.filter(function(j) { return !S.charges.has(j); }).sort(function(a, b) { return a - b; });
    }
    function Tranches(jours) {
        var tranches = [], taille = Math.max(1, R.tranche_jours || 7);
        jours.forEach(function(j) {
            var derniere = tranches[tranches.length - 1];
            if (derniere && j - derniere.debut < taille && j === derniere.fin + 1) { derniere.fin = j; }
            else { tranches.push({debut: j, fin: j}); }
        });
        return tranches;
    }

    function Charger_jours(jours, forcer) {
        var a_charger = forcer ? jours.slice().sort(function(a, b) { return a - b; }) : Jours_a_charger(jours);
        if (!a_charger.length) { return $.Deferred().resolve().promise(); }
        var tranches = Tranches(a_charger);
        var total = tranches.length, faits = 0;
        var deferred = $.Deferred();
        S.chargement_en_cours = true;
        Statut();

        function Suivante() {
            if (!tranches.length) {
                S.chargement_en_cours = false;
                Statut();
                deferred.resolve();
                return;
            }
            var tranche = tranches.shift();
            Ajax(CFG.urls.evenements, {date_debut: Iso_jour(tranche.debut), date_fin: Iso_jour(tranche.fin), collaborateurs: "tous"}).done(function(data) {
                Fusionner_tranche(tranche, data);
                faits++;
                S.progression = Math.round(faits / total * 100);
                Rafraichir_tout();
                Suivante();
            }).fail(function(xhr) {
                S.chargement_en_cours = false;
                toastr.error(Message_erreur(xhr, "Impossible de charger les évènements"));
                Statut();
                deferred.reject();
            });
        }
        Suivante();
        return deferred.promise();
    }

    function Fusionner_tranche(tranche, data) {
        var en_attente = Ids_en_attente();
        // Retire les évènements locaux de la tranche absents du serveur (hors modifications en attente)
        var recus = new Set(data.evenements.map(function(e) { return e.id; }));
        S.evts.forEach(function(evt, id) {
            if (id < 0 || en_attente.has(id)) { return; }
            var j = Jour_de(evt.s);
            if (j >= tranche.debut && j <= tranche.fin && !recus.has(id)) { S.evts.delete(id); }
        });
        data.evenements.forEach(function(e) {
            if (en_attente.has(e.id)) { return; }
            S.evts.set(e.id, Evt_depuis_serveur(e));
        });
        S.notes.forEach(function(texte, cle) {
            var j = +cle.split("|")[0];
            if (j >= tranche.debut && j <= tranche.fin) { S.notes.delete(cle); }
        });
        S.remplissages.forEach(function(liste, cle) {
            var j = +cle.split("|")[0];
            if (j >= tranche.debut && j <= tranche.fin) { S.remplissages.delete(cle); }
        });
        Object.keys(data.remplissages || {}).forEach(function(cle) {
            var p = cle.split("|");
            S.remplissages.set(Cle_note(Parse_jour(p[0]), +p[1]), data.remplissages[cle]);
        });
        for (var j = tranche.debut; j <= tranche.fin; j++) {
            S.charges.add(j);
            S.feries.delete(j);
        }
        data.notes.forEach(function(n) { S.notes.set(Cle_note(Parse_jour(n.date), n.aff), n.texte); });
        data.feries.forEach(function(f) { S.feries.set(Parse_jour(f.date), f.nom); });
        data.vacances.forEach(function(v) {
            var vac = {d: Parse_jour(v.debut), f: Parse_jour(v.fin), nom: v.nom};
            if (!S.vacances.some(function(x) { return x.d === vac.d && x.f === vac.f; })) { S.vacances.push(vac); }
        });
        Reindexer();
    }

    // Notes : clé "jour|affectation" (affectation vide pour la note générale de la journée)
    function Cle_note(jour, aff) { return jour + "|" + (aff || ""); }
    function Note_de(jour, aff) { return S.notes.get(Cle_note(jour, aff)) || ""; }
    function Notes_du_jour(jour) {
        var liste = [];
        S.notes.forEach(function(texte, cle) {
            var p = cle.split("|");
            if (+p[0] === jour) { liste.push({aff: p[1] ? +p[1] : null, texte: texte}); }
        });
        liste.sort(function(a, b) { return (a.aff ? S.affOrdre.indexOf(a.aff) + 1 : 0) - (b.aff ? S.affOrdre.indexOf(b.aff) + 1 : 0); });
        return liste;
    }
    function Texte_notes_du_jour(jour) {
        return Notes_du_jour(jour).map(function(n) { return (n.aff ? Chemin_aff(n.aff, true) + " : " : "") + n.texte; }).join("\n");
    }

    function Vacances_de(jour) {
        for (var i = 0; i < S.vacances.length; i++) { if (S.vacances[i].d <= jour && jour <= S.vacances[i].f) { return S.vacances[i]; } }
        return null;
    }

    function Actualiser() {
        // Les identifiants restent valides : l'historique d'annulation est conservé
        S.charges.clear();
        Charger_jours(V.dates, true);
    }

    // ------------------------------------------------------------------ Modifications, annulation et enregistrement
    function Ids_en_attente() {
        var ids = new Set();
        File_envoi.forEach(function(lot) { lot.changements.forEach(function(ch) { ids.add(Id_actuel(ch.id)); }); });
        return ids;
    }

    // changements : [{type: "create"|"update"|"delete", id, avant, apres}]
    function Appliquer_localement(changements) {
        changements.forEach(function(ch) {
            if (ch.type === "create") { S.evts.set(ch.apres.id, Copie_evt(ch.apres)); }
            if (ch.type === "update") {
                var actuel = S.evts.get(Id_actuel(ch.id));
                if (actuel) { var v = actuel.v; S.evts.set(actuel.id, $.extend(Copie_evt(ch.apres), {id: actuel.id, v: v})); }
            }
            if (ch.type === "delete") { S.evts.delete(Id_actuel(ch.id)); V.selection.delete(Id_actuel(ch.id)); }
        });
        Reindexer();
    }

    function Valider(libelle, changements, deja_enregistre) {
        if (!changements.length) { return; }
        if (!deja_enregistre) {
            Appliquer_localement(changements);
            Envoyer(changements);
        }
        Pile.annuler.push({libelle: libelle, changements: changements});
        if (Pile.annuler.length > 100) { Pile.annuler.shift(); }
        Pile.retablir = [];
        Maj_boutons();
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

    function Annuler() {
        if (envoi_en_cours || File_envoi.length) { toastr.info("Enregistrement en cours, réessayez dans un instant"); return; }
        var action = Pile.annuler.pop();
        if (!action) { return; }
        var inverse = Inverser(action.changements);
        if (!Changements_valides(inverse)) {
            toastr.warning("Impossible d'annuler « " + action.libelle + " » : le planning a été modifié depuis.");
            Maj_boutons();
            return;
        }
        Appliquer_localement(inverse);
        Envoyer(inverse);
        Pile.retablir.push({libelle: action.libelle, changements: inverse});
        toastr.info("Annulé : " + action.libelle);
        Maj_boutons();
        Rafraichir_tout();
    }

    function Retablir() {
        if (envoi_en_cours || File_envoi.length) { toastr.info("Enregistrement en cours, réessayez dans un instant"); return; }
        var action = Pile.retablir.pop();
        if (!action) { return; }
        var inverse = Inverser(action.changements);
        if (!Changements_valides(inverse)) {
            toastr.warning("Impossible de rétablir « " + action.libelle + " » : le planning a été modifié depuis.");
            Maj_boutons();
            return;
        }
        Appliquer_localement(inverse);
        Envoyer(inverse);
        Pile.annuler.push({libelle: action.libelle, changements: inverse});
        toastr.info("Rétabli : " + action.libelle);
        Maj_boutons();
        Rafraichir_tout();
    }

    function Changements_valides(changements) {
        // Vérifie que les évènements à modifier ou supprimer existent encore localement et qu'aucune création ne chevauche
        var supprimes = new Set();
        for (var i = 0; i < changements.length; i++) {
            var ch = changements[i];
            if ((ch.type === "update" || ch.type === "delete") && !S.evts.has(Id_actuel(ch.id))) { return false; }
            if (ch.type === "delete") { supprimes.add(Id_actuel(ch.id)); }
        }
        for (i = 0; i < changements.length; i++) {
            ch = changements[i];
            if ((ch.type === "create" || ch.type === "update") && Conflits($.extend({}, ch.apres, {id: Id_actuel(ch.id)}), supprimes).length) { return false; }
        }
        return true;
    }

    function Envoyer(changements) {
        File_envoi.push({changements: changements});
        Traiter_file();
    }

    function Traiter_file() {
        if (envoi_en_cours || !File_envoi.length) { return; }
        envoi_en_cours = true;
        Statut();
        var lot = File_envoi[0];
        var temporaires = {};
        var operations = lot.changements.map(function(ch) {
            var id = Id_actuel(ch.id);
            if (ch.type === "create") {
                temporaires[String(id)] = id;
                return {op: "create", tmp: String(id), data: Evt_vers_serveur(S.evts.get(id) || ch.apres)};
            }
            var actuel = S.evts.get(id);
            var version = actuel ? actuel.v : (ch.avant ? Version_connue(id, ch.avant.v) : 1);
            if (ch.type === "update") { return {op: "update", id: id, v: version, data: Evt_vers_serveur(actuel || ch.apres)}; }
            return {op: "delete", id: id, v: version};
        });
        Ajax(CFG.urls.enregistrer, {operations: JSON.stringify(operations)}).done(function(data) {
            File_envoi.shift();
            Object.keys(data.crees || {}).forEach(function(tmp) {
                var ancien = temporaires[tmp], nouveau = data.crees[tmp];
                var evt = S.evts.get(ancien);
                Alias.set(ancien, nouveau.id);
                if (evt) {
                    S.evts.delete(ancien);
                    evt.id = nouveau.id; evt.v = nouveau.v;
                    S.evts.set(nouveau.id, evt);
                }
                if (V.selection.has(ancien)) { V.selection.delete(ancien); V.selection.add(nouveau.id); }
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
            Rafraichir_tout();
            Traiter_file();
        }).fail(function(xhr) {
            envoi_en_cours = false;
            File_envoi = [];
            bootbox.alert({title: "Modification non enregistrée", message: Echapper(Message_erreur(xhr, "La modification n'a pas pu être enregistrée."))});
            // On recharge le planning depuis le serveur : l'historique d'annulation n'est plus fiable
            Pile.annuler = []; Pile.retablir = [];
            Maj_boutons();
            S.charges.clear();
            S.evts.forEach(function(evt, id) { if (id < 0) { S.evts.delete(id); } });
            Charger_jours(V.dates, true);
        });
    }
    var Versions = new Map();
    function Version_connue(id, defaut) { return Versions.has(id) ? Versions.get(id) : defaut; }

    // ------------------------------------------------------------------ Préférences d'affichage
    var Memoriser_affichage = Debounce(function() {
        var affichage = {
            mode: V.mode, sous: V.sous, titres: V.titres, affs: V.affs, realise: V.realise, densite: V.densite, vue: V.vue,
            affiches: V.affiches, masques: Array.from(V.masques), pas: V.pas, cat_defaut: V.cat_defaut,
            filtres: {cats: Array.from(V.filtres.cats), aff: V.filtres.aff, qualif: V.filtres.qualif},
            plage: V.plage.auto ? {auto: true} : {auto: false, debut: V.plage.debut, fin: V.plage.fin},
            legende: V.legende, panneau: V.panneau
        };
        Ajax(CFG.urls.affichage, {affichage: JSON.stringify(affichage)});
    }, 1200);

    function Restaurer_affichage(a) {
        a = a || {};
        if (a.mode === "date" || a.mode === "collab") { V.mode = a.mode; }
        if (a.sous === "aucun" || a.sous === "aff") { V.sous = a.sous; }
        ["titres", "affs", "realise"].forEach(function(nom) { if (typeof a[nom] === "boolean") { V[nom] = a[nom]; } });
        if (["auto", "confortable", "compact", "mini"].indexOf(a.densite) >= 0) { V.densite = a.densite; }
        if (a.vue === "frise" || a.vue === "synthese") { V.vue = a.vue; }
        if (Array.isArray(a.affiches)) { V.affiches = a.affiches.filter(function(id) { return S.collabs.has(id); }); }
        if (Array.isArray(a.masques)) { V.masques = new Set(a.masques.filter(function(id) { return S.collabs.has(id); })); }
        V.pas = [5, 10, 15, 30, 60].indexOf(a.pas) >= 0 ? a.pas : (R.pas || 15);
        if (a.cat_defaut && S.cats.has(a.cat_defaut)) { V.cat_defaut = a.cat_defaut; }
        if (a.filtres) {
            V.filtres.cats = new Set((a.filtres.cats || []).filter(function(id) { return S.cats.has(id); }));
            V.filtres.aff = S.affs.has(a.filtres.aff) ? a.filtres.aff : null;
            V.filtres.qualif = S.qualifs.some(function(q) { return q.id === a.filtres.qualif; }) ? a.filtres.qualif : null;
        }
        V.plage = {auto: R.plage_auto !== false, debut: R.plage_debut, fin: R.plage_fin};
        if (a.plage && a.plage.auto === false && a.plage.fin > a.plage.debut) { V.plage = {auto: false, debut: a.plage.debut, fin: a.plage.fin}; }
        if (a.legende === "cat" || a.legende === "aff") { V.legende = a.legende; }
        if (["dates", "collabs", "filtres", "legende", null].indexOf(a.panneau) >= 0 && a.hasOwnProperty("panneau")) { V.panneau = a.panneau; }

        if (!V.affiches.length) {
            // Par défaut : collaborateurs sous contrat aujourd'hui, sinon tous
            var jour = Aujourdhui();
            S.collabs.forEach(function(c) { if (Contrat_actif(c.id, jour)) { V.affiches.push(c.id); } });
            if (!V.affiches.length) { S.collabs.forEach(function(c) { if (V.affiches.length < 40) { V.affiches.push(c.id); } }); }
        }
        if (!V.cat_defaut) {
            var premiere = null;
            S.cats.forEach(function(c) { if (!premiere && c.type === "ADDITION") { premiere = c.id; } });
            V.cat_defaut = premiere || (S.cats.size ? S.cats.keys().next().value : null);
        }
    }

    // ------------------------------------------------------------------ Modèle d'affichage
    var M = {lignes: [], hauteur: 0, groupes: [], plage: {debut: 420, fin: 1140}, densite: "confortable", largeur_piste: 600, rendues: new Map()};
    var $canvas, $scroll, $axe, $sticky, $minimap, $synthese;

    function Collabs_visibles() {
        return V.affiches.filter(function(id) {
            var c = S.collabs.get(id);
            if (!c || V.masques.has(id)) { return false; }
            if (V.filtres.qualif !== null && c.qualifications.indexOf(V.filtres.qualif) < 0) { return false; }
            return true;
        });
    }

    function Evts_visibles(c, jour) {
        return Evts_de(c, jour).filter(Evt_visible);
    }

    function Total_minutes(evts, jour, realise) {
        var total = 0;
        evts.forEach(function(evt) { total += Signe_categorie(evt.cat) * Minutes_dans_jour(evt, jour, realise); });
        return total;
    }

    function Plage_effective(collabs) {
        if (!V.plage.auto) { return {debut: V.plage.debut, fin: V.plage.fin}; }
        // On se base sur le temps de travail (les congés, astreintes de nuit... ne doivent pas élargir la plage), sinon sur tous les évènements
        var mini = null, maxi = null;
        [true, false].forEach(function(travail_seulement) {
            if (mini !== null) { return; }
            collabs.forEach(function(c) {
                V.dates.forEach(function(j) {
                    Evts_visibles(c, j).forEach(function(evt) {
                        if (travail_seulement && Signe_categorie(evt.cat) <= 0) { return; }
                        var s = Math.max(evt.s, j * 1440) - j * 1440, e = Math.min(evt.e, (j + 1) * 1440) - j * 1440;
                        if (mini === null || s < mini) { mini = s; }
                        if (maxi === null || e > maxi) { maxi = e; }
                    });
                });
            });
        });
        if (mini === null) { return {debut: R.plage_debut, fin: R.plage_fin}; }
        var marge = R.plage_marge || 0;
        var debut = Math.max(0, Math.floor((mini - marge) / 60) * 60);
        var fin = Math.min(1440, Math.ceil((maxi + marge) / 60) * 60);
        var plage_min = Math.min(1440, R.plage_min || 480);
        while (fin - debut < plage_min) {
            if (debut > 0) { debut -= 60; }
            if (fin - debut < plage_min && fin < 1440) { fin += 60; }
            if (debut === 0 && fin === 1440) { break; }
        }
        return {debut: debut, fin: fin};
    }

    function Densite_effective(nbre_lignes) {
        if (V.densite !== "auto") { return V.densite; }
        if (R.compact_auto && (V.dates.length > R.compact_jours || nbre_lignes > R.compact_lignes)) { return R.densite_auto || "compact"; }
        return "confortable";
    }

    function Groupe_deplie(cle, index, jour) {
        if (V.bascules.has(cle)) { return V.bascules.get(cle); }
        if (!(R.repli_auto && V.dates.length > R.repli_jours)) { return true; }
        if (R.garder_deplies === "premiere") { return index === 0; }
        if (R.garder_deplies === "aujourdhui_premieres") { return index < 2 || jour === Aujourdhui(); }
        return false;
    }

    // Unités de ligne d'un groupe : [{c, jour}]
    function Construire_sous_affectations(unites, lignes, cle_groupe, niveau_base, ajouter, jour_groupe) {
        // Regroupe les évènements des unités par affectation (arborescence complète)
        var par_aff = new Map();      // aff (ou "sans") -> Map(clé unité -> {unite, evts})
        var utilises = new Set();
        unites.forEach(function(u) {
            Evts_visibles(u.c, u.jour).forEach(function(evt) {
                var cle_aff = evt.aff && S.affs.has(evt.aff) ? evt.aff : "sans";
                if (!par_aff.has(cle_aff)) { par_aff.set(cle_aff, new Map()); }
                var cle_u = u.c + "|" + u.jour;
                if (!par_aff.get(cle_aff).has(cle_u)) { par_aff.get(cle_aff).set(cle_u, {unite: u, evts: []}); }
                par_aff.get(cle_aff).get(cle_u).evts.push(evt);
                if (cle_aff !== "sans") { Ancetres_aff(cle_aff).forEach(function(id) { utilises.add(id); }); }
            });
        });
        function Collabs_sous_arbre(id) {
            // Collaborateurs ayant du temps comptabilisé dans le sous-arbre (pour le taux d'encadrement)
            var collabs = new Set();
            par_aff.forEach(function(unites_aff, cle_aff) {
                if (cle_aff === "sans" || !Dans_sous_arbre(cle_aff, id)) { return; }
                unites_aff.forEach(function(item) { if (Total_minutes(item.evts, item.unite.jour) > 0) { collabs.add(item.unite.c); } });
            });
            return collabs.size;
        }
        function Total_sous_arbre(id) {
            var total = 0;
            par_aff.forEach(function(unites_aff, cle_aff) {
                if (cle_aff === "sans" || !Dans_sous_arbre(cle_aff, id)) { return; }
                unites_aff.forEach(function(item) { total += Total_minutes(item.evts, item.unite.jour); });
            });
            return total;
        }
        S.affOrdre.forEach(function(id) {
            if (!utilises.has(id)) { return; }
            var a = S.affs.get(id);
            ajouter({type: "s", cle: cle_groupe + "|a" + id, aff: id, niveau: niveau_base + a.niveau, libelle: a.nom, couleur: a.couleur, total: Total_sous_arbre(id), jour: jour_groupe, collabs: Collabs_sous_arbre(id)});
            (par_aff.get(id) || new Map()).forEach(function(item) {
                ajouter({type: "l", cle: cle_groupe + "|a" + id + "|" + item.unite.c + "|" + item.unite.jour, c: item.unite.c, jour: item.unite.jour, aff: id, evts: item.evts, niveau: niveau_base + a.niveau + 1});
            });
        });
        if (par_aff.has("sans")) {
            var total = 0;
            par_aff.get("sans").forEach(function(item) { total += Total_minutes(item.evts, item.unite.jour); });
            ajouter({type: "s", cle: cle_groupe + "|sans", aff: null, niveau: niveau_base, libelle: "Sans affectation", total: total, sans: true});
            par_aff.get("sans").forEach(function(item) {
                ajouter({type: "l", cle: cle_groupe + "|sans|" + item.unite.c + "|" + item.unite.jour, c: item.unite.c, jour: item.unite.jour, aff: null, evts: item.evts, niveau: niveau_base + 1});
            });
        }
    }

    function Construire_lignes() {
        var collabs = Collabs_visibles();
        var dates = V.dates;
        var lignes = [], groupes = [];
        var nbre_lignes_estime = collabs.length * dates.length;
        M.densite = Densite_effective(nbre_lignes_estime);
        var h_ligne = HAUTEURS[M.densite] + (M.etroit ? (M.densite === "confortable" ? 18 : 16) : 0);
        var top = 0;
        function Ajouter(ligne) {
            ligne.h = ligne.type === "g" ? HAUTEURS.groupe : (ligne.type === "s" ? HAUTEURS.sous : (ligne.type === "r" ? HAUTEURS.replie : h_ligne));
            ligne.top = top;
            top += ligne.h;
            lignes.push(ligne);
        }

        var groupes_def = V.mode === "date"
            ? dates.map(function(j) { return {cle: "d" + j, jour: j, unites: collabs.map(function(c) { return {c: c, jour: j}; })}; })
            : collabs.map(function(c) { return {cle: "c" + c, c: c, unites: dates.map(function(j) { return {c: c, jour: j}; })}; });

        groupes_def.forEach(function(g, index) {
            var total = 0, attendu = 0, absents = 0;
            g.unites.forEach(function(u) {
                var evts = Evts_visibles(u.c, u.jour);
                total += Total_minutes(evts, u.jour);
                if (evts.some(function(evt) { var cat = S.cats.get(evt.cat); return cat && cat.type !== "ADDITION" && Minutes_dans_jour(evt, u.jour) >= 240; }) &&
                    Total_minutes(evts, u.jour) <= 0) { absents++; }
            });
            if (V.mode === "collab") { attendu = Minutes_attendues(g.c, dates); }
            var deplie = Groupe_deplie(g.cle, index, g.jour);
            var groupe = {type: "g", cle: g.cle, jour: g.jour, c: g.c, total: total, attendu: attendu, absents: absents, deplie: deplie, nbre: g.unites.length};
            groupes.push(groupe);
            if (!deplie) {
                Ajouter({type: "r", cle: g.cle + "|r", groupe: groupe, jour: g.jour, c: g.c, unites: g.unites});
                return;
            }
            Ajouter(groupe);
            if (V.sous === "aff") {
                Construire_sous_affectations(g.unites, lignes, g.cle, 0, Ajouter, V.mode === "date" ? g.jour : undefined);
            } else {
                g.unites.forEach(function(u) {
                    Ajouter({type: "l", cle: g.cle + "|" + u.c + "|" + u.jour, c: u.c, jour: u.jour, aff: undefined, niveau: 0});
                });
            }
        });
        M.lignes = lignes;
        M.groupes = groupes;
        M.hauteur = top;
        M.plage = Plage_effective(collabs);
        M.collabs = collabs;
    }

    function Ligne_evts(ligne) {
        return ligne.evts || Evts_visibles(ligne.c, ligne.jour);
    }

    // ------------------------------------------------------------------ Rendu de la frise
    function Pct(minutes) { return (minutes - M.plage.debut) / (M.plage.fin - M.plage.debut) * 100; }

    function Html_avatar(c, petit) {
        var collab = S.collabs.get(c);
        if (!collab) { return ""; }
        var initiales = ((collab.prenom || "").charAt(0) + (collab.nom || "").charAt(0)).toUpperCase();
        return "<span class='pl-avatar" + (petit ? " petit" : "") + "' style='background:" + collab.couleur + "' aria-hidden='true'>" + Echapper(initiales) + "</span>";
    }

    function Rendu_axe() {
        var html = "<div class='pl-axe-label'>" + (V.mode === "date" ? "Collaborateur" : "Date") + "</div><div class='pl-axe-heures'>";
        var duree = M.plage.fin - M.plage.debut;
        var pas = duree > 16 * 60 ? 120 : 60;
        if (M.largeur_piste < 420 && pas === 60) { pas = 120; }
        for (var m = Math.ceil(M.plage.debut / pas) * pas; m <= M.plage.fin; m += pas) {
            html += "<span style='left:" + Pct(m).toFixed(3) + "%'>" + Pad(Math.floor(m / 60) % 24) + "h</span>";
        }
        html += "</div><div class='pl-axe-total'>Total</div>";
        $axe.html(html);
        // Grille horaire de la piste
        document.getElementById("pl_app").style.setProperty("--pl-pas-grille", (60 / duree * 100).toFixed(4) + "%");
    }

    function Html_barre(evt, ligne) {
        var jour = ligne.jour;
        var debut_jour = jour * 1440;
        var s = evt.s - debut_jour, e = evt.e - debut_jour;
        var gauche = Math.max(s, M.plage.debut), droite = Math.min(e, M.plage.fin);
        var cat = S.cats.get(evt.cat) || {couleur: "#94a3b8", nom: "", type: "NEUTRE"};
        var classes = "pl-barre";
        if (cat.type !== "ADDITION") { classes += " neutre"; }
        if (V.selection.has(evt.id)) { classes += " sel"; }
        if (!Est_modifiable(evt.c)) { classes += " lecture"; }
        if (droite <= gauche) {
            // Evènement entièrement hors de la plage affichée
            var cote = e <= M.plage.debut ? "left:2px" : "right:2px";
            return "<span class='pl-fleche-hors' style='" + cote + "' title='" + Echapper(Heure(evt.s) + "-" + Heure(evt.e) + " (hors plage affichée)") + "'><i class='fa fa-caret-" + (e <= M.plage.debut ? "left" : "right") + "'></i></span>";
        }
        if (s < M.plage.debut) { classes += " hors-gauche"; }
        if (e > M.plage.fin) { classes += " hors-droite"; }
        var largeur_pct = Pct(droite) - Pct(gauche);
        var largeur_px = largeur_pct / 100 * M.largeur_piste;
        var contenu = "";
        if (M.densite !== "mini") {
            var horaires = largeur_px >= R.largeur_horaires ? "<span class='pl-b-h'>" + Heure(evt.s) + (largeur_px >= R.largeur_horaires * 1.7 ? "–" + Heure(evt.e) : "") + "</span>" : "";
            var titre = V.titres && largeur_px >= R.largeur_titre && (evt.t || cat.nom) ? "<span class='pl-b-t'>" + Echapper(evt.t || cat.nom) + "</span>" : "";
            if (V.affs && evt.aff && M.densite === "confortable" && largeur_px >= R.largeur_titre && ligne.aff === undefined) {
                contenu = "<span class='pl-b-col'><span class='pl-b-l1'>" + horaires + titre + "</span><span class='pl-b-aff'>" + Echapper(Chemin_aff(evt.aff, true)) + "</span></span>";
            } else {
                contenu = horaires + titre;
            }
        }
        var html = "<div class='" + classes + "' data-id='" + evt.id + "' style='left:" + Pct(gauche).toFixed(3) + "%;width:calc(" + largeur_pct.toFixed(3) + "% - 1px);background-color:" + Echapper(cat.couleur) + "'>" + contenu + "</div>";
        if (V.realise && evt.rs !== null && evt.re !== null) {
            var rs = Math.max(evt.rs - debut_jour, M.plage.debut), re = Math.min(evt.re - debut_jour, M.plage.fin);
            if (re > rs) { html += "<span class='pl-realise' style='left:" + Pct(rs).toFixed(3) + "%;width:" + (Pct(re) - Pct(rs)).toFixed(3) + "%'></span>"; }
        }
        return html;
    }

    function Html_total(minutes, attendu) {
        if (!minutes && !attendu) { return "<div class='pl-total zero'>0 h</div>"; }
        return "<div class='pl-total'>" + Duree(minutes) + (attendu ? "<small>/ " + Duree(attendu) + "</small>" : "") + "</div>";
    }

    function Html_ligne(ligne) {
        var style = "top:" + ligne.top + "px;height:" + ligne.h + "px";
        if (ligne.type === "g") { return Html_groupe(ligne, style); }
        if (ligne.type === "r") { return Html_replie(ligne, style); }
        if (ligne.type === "s") {
            var indent_sous = 18 + ligne.niveau * 20;
            var icone = ligne.sans ? "<i class='fa fa-info-circle pl-muted' aria-hidden='true'></i>" :
                "<span class='pl-s-icone' aria-hidden='true'" + (ligne.couleur ? " style='background:" + Echapper(ligne.couleur) + ";color:#fff'" : "") + "><i class='fa fa-sitemap'></i></span>";
            return "<div class='pl-l pl-l-sous" + (ligne.sans ? " sans" : "") + "' style='" + style + ";padding-left:" + indent_sous + "px' data-index='" + ligne.index + "'>" + icone +
                "<span class='pl-s-nom'>" + Echapper(ligne.libelle) + "</span><span class='pl-muted'>· " + Duree(ligne.total) + "</span>" + Html_bouton_note_aff(ligne) + Html_remplissage(ligne) + "</div>";
        }
        // Ligne d'évènements
        var evts = Ligne_evts(ligne);
        var collab = S.collabs.get(ligne.c);
        var classes = "pl-l pl-l-ligne";
        var contrat = Contrat_actif(ligne.c, ligne.jour);
        if (contrat === false) { classes += " hors-contrat"; }
        if (S.feries.has(ligne.jour)) { classes += " ferie"; }
        if (V.ligne_courante === ligne.cle) { classes += " courante"; }
        var label, indent = 16 + (ligne.niveau || 0) * 20;
        var verrou = Est_modifiable(ligne.c) ? "" : "<i class='fa fa-lock' title='Lecture seule' aria-label='Lecture seule'></i>";
        if (V.mode === "date") {
            label = Html_avatar(ligne.c, M.densite !== "confortable") + "<span class='pl-lbl-txt'><span class='pl-nom'>" + Echapper(collab.libelle) + "</span>" +
                (M.densite === "confortable" && collab.poste ? "<span class='pl-sous-nom'>" + Echapper(collab.poste) + "</span>" : "") + "</span>" + verrou;
        } else {
            var note = Texte_notes_du_jour(ligne.jour);
            var ferie = S.feries.get(ligne.jour);
            var vac = Vacances_de(ligne.jour);
            label = "<span class='pl-lbl-txt'><span class='pl-nom'>" + Texte_jour_court(ligne.jour) + "</span>" +
                (M.densite === "confortable" ? "<span class='pl-sous-nom'>" + (ferie ? "<span class='pl-texte-ferie'>" + Echapper(ferie) + "</span>" : (vac ? "<span class='pl-texte-vacances'>" + Echapper(vac.nom) + "</span>" : Infos_jour(ligne.jour).a)) + "</span>" : "") + "</span>" +
                (ferie && M.densite !== "confortable" ? "<span class='pl-badge pl-badge-ferie' title='" + Echapper(ferie) + "'>Férié</span>" : "") +
                (note ? "<i class='fa fa-sticky-note pl-icone-note' title='" + Echapper(note) + "' aria-label='Note'></i>" : "") + verrou;
        }
        var html = "<div class='" + classes + "' style='" + style + "' data-index='" + ligne.index + "' role='row'>" +
            "<div class='pl-lbl-ligne' style='padding-left:" + indent + "px' data-action='libelle' role='rowheader'>" + label + "</div>" +
            "<div class='pl-piste' data-index='" + ligne.index + "'>";
        evts.forEach(function(evt) { html += Html_barre(evt, ligne); });
        html += "</div>" + Html_total(Total_minutes(evts, ligne.jour), 0) + "</div>";
        return html;
    }

    function Html_bouton_note_aff(ligne) {
        // Note d'une affectation pour la journée (uniquement en regroupement par date)
        if (ligne.jour === undefined || !ligne.aff) { return ""; }
        var note = Note_de(ligne.jour, ligne.aff);
        return "<button type='button' class='pl-note-btn pl-note-aff" + (note ? " avec" : "") + "' data-action='note' data-jour='" + ligne.jour + "' data-aff='" + ligne.aff + "'" +
            " title='" + Echapper(note || "Ajouter une note pour cette affectation") + "' aria-label='" + Echapper(note ? "Note : " + note : "Ajouter une note pour " + ligne.libelle) + "'>" +
            "<i class='fa fa-sticky-note-o' aria-hidden='true'></i>" + (note ? Echapper(note.split("\n")[0]) : "") + "</button>";
    }

    // Remplissage : consommations prévues de l'activité ou du groupe lié à l'affectation (regroupement par date uniquement)
    function Remplissage_de(jour, aff) { return S.remplissages.get(Cle_note(jour, aff)) || null; }
    function Etat_remplissage(item) {
        if (!item.c) { return ""; }
        if (item.p >= item.c) { return "plein"; }
        return item.c - item.p <= (item.s || 0) ? "alerte" : "ok";
    }
    function Encadrement(ligne, liste) {
        if (!ligne.collabs) { return null; }
        var pic = 0;
        liste.forEach(function(item) { pic = Math.max(pic, item.p); });
        if (!pic) { return null; }
        var seuil = (S.affs.get(ligne.aff) || {}).seuil || null;
        var taux = pic / ligne.collabs;
        return {pic: pic, collabs: ligne.collabs, taux: taux, seuil: seuil, depasse: !!seuil && taux > seuil};
    }
    function Html_remplissage(ligne) {
        if (ligne.jour === undefined || !ligne.aff) { return ""; }
        var liste = Remplissage_de(ligne.jour, ligne.aff);
        if (!liste || !liste.length) { return ""; }
        var resume = [];
        var html = liste.map(function(item) {
            var etat = Etat_remplissage(item);
            resume.push(item.n + " : " + item.p + (item.c ? " sur " + item.c : "") + " prévus");
            return "<span class='pl-rpl-chip" + (etat ? " " + etat : "") + "'>" + (etat ? "<span class='pl-rpl-point' aria-hidden='true'></span>" : "") +
                "<span class='pl-rpl-ab'>" + Echapper(item.a) + "</span><b>" + item.p + "</b>" + (item.c ? "<span class='pl-rpl-places'>/" + item.c + "</span>" : "") + "</span>";
        }).join("");
        var enc = Encadrement(ligne, liste);
        if (enc) {
            html += "<span class='pl-rpl-sep' aria-hidden='true'></span><span class='pl-rpl-enc" + (enc.depasse ? " depasse" : "") + "'><i class='fa fa-users' aria-hidden='true'></i>1 pour " + Math.round(enc.taux) +
                (enc.depasse ? "<i class='fa fa-exclamation-triangle' aria-hidden='true'></i>" : "") + "</span>";
            resume.push("encadrement 1 pour " + Math.round(enc.taux) + (enc.depasse ? ", au-delà du maximum de 1 pour " + enc.seuil : ""));
        }
        return "<button type='button' class='pl-rpl' data-action='remplissage' data-jour='" + ligne.jour + "' data-aff='" + ligne.aff + "' data-collabs='" + (ligne.collabs || 0) + "'" +
            " aria-label='" + Echapper("Consommations prévues : " + resume.join(", ")) + "' aria-haspopup='dialog'>" + html + "</button>";
    }

    function Html_titre_groupe(ligne) {
        if (V.mode === "date") {
            var html = "<span class='pl-g-titre'>" + Echapper(Texte_jour_long(ligne.jour)) + "</span>";
            var ferie = S.feries.get(ligne.jour), vacances = Vacances_de(ligne.jour);
            if (ferie) { html += "<span class='pl-badge pl-badge-ferie'><i class='fa fa-flag' aria-hidden='true'></i>" + Echapper(ferie) + "</span>"; }
            if (vacances) { html += "<span class='pl-badge pl-badge-vacances'>" + Echapper(vacances.nom) + "</span>"; }
            return html;
        }
        var collab = S.collabs.get(ligne.c);
        return Html_avatar(ligne.c, true) + "<span class='pl-g-titre'>" + Echapper(collab.libelle) + "</span>" + (collab.modifiable ? "" : "<i class='fa fa-lock pl-muted' title='Lecture seule'></i>");
    }

    function Html_droite_groupe(ligne) {
        var html = "";
        if (V.mode === "date") {
            var note = Note_de(ligne.jour, null);
            var autres = Notes_du_jour(ligne.jour).filter(function(n) { return n.aff; });
            html += "<button type='button' class='pl-note-btn" + (note ? " avec" : "") + "' data-action='note' data-jour='" + ligne.jour + "' title='" + Echapper(Texte_notes_du_jour(ligne.jour) || "Ajouter une note pour cette journée") + "'>" +
                "<i class='fa fa-sticky-note-o' aria-hidden='true'></i>" + (note ? Echapper(note.split("\n")[0]) : "Note") +
                (autres.length ? "<span class='pl-note-nbre' aria-label='" + autres.length + " note(s) d'affectation'>+" + autres.length + "</span>" : "") + "</button>";
        } else if (ligne.attendu) {
            var ecart = ligne.total - ligne.attendu;
            html += "<span class='pl-badge pl-badge-contrat' title='Heures prévues au contrat sur les dates affichées'>Contrat " + Duree(ligne.attendu) + "</span>";
            if (Math.abs(ecart) >= 1) { html += "<span class='pl-badge " + (ecart > 0 ? "pl-badge-ecart-plus" : "pl-badge-ecart-moins") + "' title='Écart avec le contrat'>" + (ecart > 0 ? "+" : "") + Duree(ecart) + "</span>"; }
        }
        if (ligne.absents) { html += "<span class='pl-badge pl-badge-abs'>" + ligne.absents + " abs.</span>"; }
        if (V.mode === "collab") {
            html += "<button type='button' class='pl-mini-btn' data-action='masquer' data-c='" + ligne.c + "' aria-label='Masquer ce collaborateur' title='Masquer ce collaborateur'><i class='fa fa-eye-slash'></i></button>";
        }
        return html;
    }

    function Html_groupe(ligne, style) {
        var sous = V.mode === "date" ? "· " + ligne.nbre + " collaborateur" + (ligne.nbre > 1 ? "s" : "") + " · " + Duree(ligne.total) : "· " + Duree(ligne.total) + " sur la sélection";
        return "<div class='pl-l pl-l-groupe' style='" + style + "' data-index='" + ligne.index + "'>" +
            "<button type='button' class='pl-plier' data-action='plier' data-cle='" + ligne.cle + "' aria-expanded='true' aria-label='Replier'><i class='fa fa-chevron-down' aria-hidden='true'></i></button>" +
            Html_titre_groupe(ligne) + "<span class='pl-g-sous'>" + sous + "</span><div class='pl-g-droite'>" + Html_droite_groupe(ligne) + "</div></div>";
    }

    function Html_charge(ligne) {
        if (!R.courbe_charge) { return "<div class='pl-charge'></div>"; }
        var segments = 48, duree = M.plage.fin - M.plage.debut, pas = duree / segments;
        var nbre = Math.max(1, ligne.unites.length), stops = [], pic = {n: 0, m: 0};
        for (var i = 0; i < segments; i++) {
            var milieu = M.plage.debut + pas * (i + 0.5), n = 0;
            ligne.unites.forEach(function(u) {
                var m = u.jour * 1440 + milieu;
                if (Evts_visibles(u.c, u.jour).some(function(evt) { return Signe_categorie(evt.cat) > 0 && evt.s <= m && m < evt.e; })) { n++; }
            });
            if (n > pic.n) { pic = {n: n, m: milieu}; }
            var a = (0.06 + n / nbre * 0.85).toFixed(2);
            stops.push("rgba(var(--pl-primaire-rgb)," + a + ") " + (i / segments * 100).toFixed(2) + "% " + ((i + 1) / segments * 100).toFixed(2) + "%");
        }
        var titre = pic.n ? "Pic : " + pic.n + " présent" + (pic.n > 1 ? "s" : "") + " vers " + Heure(Math.round(pic.m)) : "Aucune présence";
        return "<div class='pl-charge' title='" + titre + "' style='background:linear-gradient(to right," + stops.join(",") + ")'></div>";
    }

    function Html_replie(ligne, style) {
        var g = ligne.groupe;
        var titre = V.mode === "date" ? "<span class='pl-g-titre'>" + Texte_jour_court(g.jour) + "</span>" + (S.feries.has(g.jour) ? "<span class='pl-badge pl-badge-ferie' title='" + Echapper(S.feries.get(g.jour)) + "'>Férié</span>" : "") +
            (!S.feries.has(g.jour) && Vacances_de(g.jour) ? "<span class='pl-badge pl-badge-vacances' title='" + Echapper(Vacances_de(g.jour).nom) + "'>Vac.</span>" : "") +
            (Notes_du_jour(g.jour).length ? "<i class='fa fa-sticky-note pl-icone-note' title='" + Echapper(Texte_notes_du_jour(g.jour)) + "'></i>" : "")
            : Html_avatar(g.c, true) + "<span class='pl-g-titre' style='overflow:hidden;text-overflow:ellipsis'>" + Echapper(S.collabs.get(g.c).libelle) + "</span>";
        var abs = g.absents ? "<span class='pl-badge pl-badge-abs'>" + g.absents + " abs.</span>" : "";
        return "<div class='pl-l pl-l-groupe pl-l-replie' style='" + style + ";padding:0' data-index='" + ligne.index + "'>" +
            "<div class='pl-lbl-ligne' style='padding-left:10px;gap:6px;cursor:default'><button type='button' class='pl-plier' data-action='plier' data-cle='" + g.cle + "' aria-expanded='false' aria-label='Déplier'><i class='fa fa-chevron-right' aria-hidden='true'></i></button>" + titre + abs + "</div>" +
            Html_charge(ligne) + Html_total(g.total, g.attendu) + "</div>";
    }

    function Rendu_frise() {
        // Petits écrans : le libellé passe au-dessus de la frise qui occupe toute la largeur
        M.etroit = $scroll[0].clientWidth < 520;
        $scroll.toggleClass("pl-etroit", M.etroit);
        Construire_lignes();
        M.lignes.forEach(function(ligne, index) { ligne.index = index; });
        var largeur_canvas = $canvas[0].clientWidth || $scroll[0].clientWidth;
        var styles = getComputedStyle(document.getElementById("pl_app"));
        var label = parseFloat(styles.getPropertyValue("--pl-label-w")) || 220, total = parseFloat(styles.getPropertyValue("--pl-total-w")) || 84;
        M.largeur_piste = Math.max(100, largeur_canvas - label - total - 24);
        if (M.etroit) { M.largeur_piste = Math.max(100, largeur_canvas - 16); }
        $canvas.removeClass("pl-densite-confortable pl-densite-compact pl-densite-mini").addClass("pl-densite-" + M.densite);
        $canvas.css("height", M.hauteur + "px");
        Rendu_axe();
        $canvas.empty();
        M.rendues = new Map();
        var vide = !M.collabs.length ? "Aucun collaborateur affiché. Ajoutez des collaborateurs dans le panneau de gauche." : (!V.dates.length ? "Sélectionnez une ou plusieurs dates dans le calendrier." : "");
        $("#pl_vide").prop("hidden", !vide).text(vide);
        Rendu_visible();
        Rendu_minimap();
    }

    function Premier_visible(haut) {
        var a = 0, b = M.lignes.length - 1;
        while (a < b) {
            var m = (a + b) >> 1;
            if (M.lignes[m].top + M.lignes[m].h <= haut) { a = m + 1; } else { b = m; }
        }
        return a;
    }

    function Rendu_visible() {
        if (!M.lignes.length) { $sticky.empty(); return; }
        var haut = $scroll[0].scrollTop - 34, hauteur = $scroll[0].clientHeight, marge = 300;
        var debut = Premier_visible(Math.max(0, haut - marge)), fin = debut;
        var limite = haut + hauteur + marge;
        var visibles = new Set();
        while (fin < M.lignes.length && M.lignes[fin].top < limite) { visibles.add(fin); fin++; }
        M.rendues.forEach(function(element, index) { if (!visibles.has(index)) { element.remove(); M.rendues.delete(index); } });
        var fragment = "";
        var a_ajouter = [];
        visibles.forEach(function(index) { if (!M.rendues.has(index)) { a_ajouter.push(index); fragment += Html_ligne(M.lignes[index]); } });
        if (fragment) {
            var conteneur = document.createElement("div");
            conteneur.innerHTML = fragment;
            var enfants = Array.prototype.slice.call(conteneur.children);
            enfants.forEach(function(element, i) { M.rendues.set(a_ajouter[i], element); $canvas[0].appendChild(element); });
        }
        Rendu_sticky(Math.max(0, haut));
        Maj_minimap_vue();
    }

    function Rendu_sticky(haut) {
        // En-tête de groupe collant lorsque l'en-tête réel est sorti de la vue
        var index = Premier_visible(haut + 1), groupe = null;
        for (var i = Math.min(index, M.lignes.length - 1); i >= 0; i--) {
            if (M.lignes[i].type === "g") { groupe = M.lignes[i]; break; }
            if (M.lignes[i].type === "r") { break; }
        }
        if (!groupe || groupe.top >= haut) { $sticky.empty(); M.sticky = null; return; }
        // Masqué dès que l'en-tête du groupe suivant arrive en haut
        for (var k = groupe.index + 1; k < M.lignes.length; k++) {
            if (M.lignes[k].type === "g" || M.lignes[k].type === "r") {
                if (M.lignes[k].top < haut + HAUTEURS.groupe) { $sticky.empty(); M.sticky = null; return; }
                break;
            }
        }
        if (M.sticky === groupe.cle) { return; }
        M.sticky = groupe.cle;
        $sticky.html("<div>" + Html_groupe(groupe, "top:0;height:" + groupe.h + "px;position:relative") + "</div>");
    }

    function Rendu_minimap() {
        var visible = V.vue === "frise" && M.groupes.length > 1 && M.hauteur > $scroll[0].clientHeight && window.innerWidth >= 768;
        $minimap.prop("hidden", !visible);
        if (!visible) { return; }
        var maxi = Math.max.apply(null, M.groupes.map(function(g) { return Math.abs(g.total); }).concat([1]));
        var html = "<div class='pl-minimap-items'>";
        M.groupes.forEach(function(g) {
            var libelle = V.mode === "date" ? Infos_jour(g.jour).j : Echapper((S.collabs.get(g.c).nom || "").substr(0, 3));
            html += "<div class='pl-minimap-item' data-groupe='" + g.cle + "' title='" + Echapper(V.mode === "date" ? Texte_jour_long(g.jour) : S.collabs.get(g.c).libelle) + "'><span>" + libelle + "</span>" +
                "<i style='opacity:" + (0.2 + 0.8 * Math.abs(g.total) / maxi).toFixed(2) + "'></i></div>";
        });
        html += "</div><div class='pl-minimap-vue' id='pl_minimap_vue'></div>";
        $minimap.html(html);
        Maj_minimap_vue();
    }

    function Maj_minimap_vue() {
        if ($minimap.prop("hidden") || !M.hauteur) { return; }
        var h = $minimap[0].clientHeight - 12, scroll = $scroll[0];
        var haut = scroll.scrollTop / (M.hauteur + 34) * h, hauteur = Math.max(10, scroll.clientHeight / (M.hauteur + 34) * h);
        $("#pl_minimap_vue").css({top: (6 + haut) + "px", height: Math.min(h, hauteur) + "px"});
    }

    function Defiler_vers_groupe(cle) {
        var ligne = M.lignes.find(function(l) { return (l.type === "g" && l.cle === cle) || (l.type === "r" && l.groupe.cle === cle); });
        if (ligne) { $scroll[0].scrollTop = ligne.top; }
    }

    // ------------------------------------------------------------------ Légende
    function Rendu_legende() {
        var collabs = Collabs_visibles();
        var par_cat = new Map(), par_aff = new Map(), nb_cat = new Map(), sans_aff = 0, travail = 0, attendu = 0;
        collabs.forEach(function(c) {
            V.dates.forEach(function(j) {
                Evts_visibles(c, j).forEach(function(evt) {
                    var minutes = Minutes_dans_jour(evt, j);
                    par_cat.set(evt.cat, (par_cat.get(evt.cat) || 0) + minutes);
                    if (Jour_de(evt.s) === j || j === V.dates[0]) { nb_cat.set(evt.cat, (nb_cat.get(evt.cat) || 0) + 1); }
                    var signe = Signe_categorie(evt.cat);
                    travail += signe * minutes;
                    if (!signe) { return; }
                    if (evt.aff && S.affs.has(evt.aff)) {
                        Ancetres_aff(evt.aff).forEach(function(id) { par_aff.set(id, (par_aff.get(id) || 0) + signe * minutes); });
                    } else { sans_aff += signe * minutes; }
                });
            });
            attendu += Minutes_attendues(c, V.dates);
        });
        var html = "";
        if (V.legende === "cat") {
            S.cats.forEach(function(cat) {
                var minutes = par_cat.get(cat.id) || 0, nbre = nb_cat.get(cat.id) || 0;
                var type = cat.type === "ADDITION" ? "comptabilisé" : (cat.type === "SOUSTRACTION" ? "soustrait" : "non comptabilisé");
                html += "<div class='pl-leg-ligne'><span class='pl-pastille' style='background:" + Echapper(cat.couleur) + "'></span><span class='pl-leg-nom'><span>" + Echapper(cat.nom) + "</span>" +
                    "<small>" + nbre + " évènement" + (nbre > 1 ? "s" : "") + " · " + type + "</small></span><span class='pl-leg-val'>" + Duree(minutes) + "</span></div>";
            });
        } else {
            S.affOrdre.forEach(function(id) {
                var minutes = par_aff.get(id);
                if (!minutes) { return; }
                var a = S.affs.get(id);
                html += "<div class='pl-leg-ligne' style='padding-left:" + (a.niveau * 14) + "px'><i class='fa " + (a.niveau ? "fa-angle-right pl-muted" : "fa-sitemap") + "' aria-hidden='true'></i>" +
                    "<span class='pl-leg-nom'><span" + (a.niveau ? "" : " style='font-weight:700'") + ">" + Echapper(a.nom) + "</span></span><span class='pl-leg-val'>" + Duree(minutes) + "</span></div>";
            });
            if (sans_aff) { html += "<div class='pl-leg-ligne'><span class='pl-leg-nom'><span class='pl-muted' style='font-style:italic'>Sans affectation</span></span><span class='pl-leg-val'>" + Duree(sans_aff) + "</span></div>"; }
            if (!html) { html = "<p class='pl-muted pl-petit'>Aucun temps de travail affecté sur la période affichée.</p>"; }
        }
        html += "<div class='pl-leg-total'><span>Temps de travail</span><span class='pl-leg-val'>" + Duree(travail) + "</span></div>";
        $("#pl_acc_resume_legende").text(Duree(travail) + " de travail" + (attendu ? " · écart " + (travail - attendu > 0 ? "+" : "") + Duree(travail - attendu) : ""))
            .attr("title", "Temps de travail : " + Duree(travail) + (attendu ? " · prévu aux contrats : " + Duree(attendu) : ""));
        if (attendu) {
            var ecart = travail - attendu;
            html += "<div class='pl-leg-contrat'><span>Prévu aux contrats</span><span>" + Duree(attendu) + " (écart " + (ecart > 0 ? "+" : "") + Duree(ecart) + ")</span></div>";
        }
        $("#pl_legende").html(html);
        $("[data-legende]").each(function() { $(this).attr("aria-selected", String($(this).data("legende") === V.legende)); });
    }

    // ------------------------------------------------------------------ Calendrier
    var Mois_speciaux_charges = new Set();
    function Charger_dates_speciales_mois() {
        // Jours fériés et vacances de tout le mois affiché dans le calendrier (et des jours voisins visibles)
        var cle = V.mois_cal.a + "-" + V.mois_cal.m;
        if (Mois_speciaux_charges.has(cle)) { return; }
        Mois_speciaux_charges.add(cle);
        var premier = Math.floor(Date.UTC(V.mois_cal.a, V.mois_cal.m, 1) / 86400000) - 7;
        var dernier = Math.floor(Date.UTC(V.mois_cal.a, V.mois_cal.m + 1, 0) / 86400000) + 7;
        Ajax(CFG.urls.evenements, {date_debut: Iso_jour(premier), date_fin: Iso_jour(dernier), collaborateurs: "[]"}).done(function(data) {
            data.feries.forEach(function(f) { S.feries.set(Parse_jour(f.date), f.nom); });
            data.vacances.forEach(function(v) {
                var vac = {d: Parse_jour(v.debut), f: Parse_jour(v.fin), nom: v.nom};
                if (!S.vacances.some(function(x) { return x.d === vac.d && x.f === vac.f; })) { S.vacances.push(vac); }
            });
            Rendu_calendrier();
            if (V.vue === "synthese") { Rendu_synthese(); }
        }).fail(function() { Mois_speciaux_charges.delete(cle); });
    }

    function Rendu_calendrier() {
        if (V.mois_cal === null) { var i = Infos_jour(V.dates.length ? V.dates[0] : Aujourdhui()); V.mois_cal = {a: i.a, m: i.m}; }
        Charger_dates_speciales_mois();
        var premier = Math.floor(Date.UTC(V.mois_cal.a, V.mois_cal.m, 1) / 86400000);
        var nb_jours = new Date(Date.UTC(V.mois_cal.a, V.mois_cal.m + 1, 0)).getUTCDate();
        $("#pl_cal_mois").text(MOIS[V.mois_cal.m] + " " + V.mois_cal.a);
        var selection = new Set(V.dates), aujourdhui = Aujourdhui();
        var html = ["L", "M", "M", "J", "V", "S", "D"].map(function(l) { return "<span class='pl-cal-entete' aria-hidden='true'>" + l + "</span>"; }).join("");
        var decalage = Jour_semaine(premier);
        var debut = premier - decalage, fin = premier + nb_jours - 1;
        fin += 6 - Jour_semaine(fin);
        for (var j = debut; j <= fin; j++) {
            var classes = ["pl-cal-jour"], infos = Infos_jour(j);
            if (Jour_semaine(j) >= 5) { classes.push("we"); }
            if (infos.m !== V.mois_cal.m) { classes.push("autre-mois"); }
            if (j === aujourdhui) { classes.push("aujourdhui"); }
            if (S.feries.has(j)) { classes.push("ferie"); }
            if (Vacances_de(j)) { classes.push("vacances"); }
            if (selection.has(j)) {
                classes.push("sel");
                var avant = selection.has(j - 1) && Jour_semaine(j) !== 0, apres = selection.has(j + 1) && Jour_semaine(j) !== 6;
                if (!avant) { classes.push("debut"); }
                if (!apres) { classes.push("fin"); }
                if (avant && apres) { classes.push("milieu"); }
            }
            var titre = Texte_jour_long(j) + (S.feries.has(j) ? " – " + S.feries.get(j) : "") + (Vacances_de(j) ? " – " + Vacances_de(j).nom : "");
            html += "<button type='button' class='" + classes.join(" ") + "' data-jour='" + j + "' aria-pressed='" + selection.has(j) + "' aria-label='" + Echapper(titre) + "' title='" + Echapper(titre) + "'>" + infos.j + "</button>";
        }
        $("#pl_cal").html(html);
        var n = V.dates.length;
        var resume = "Aucune date sélectionnée";
        if (n === 1) { resume = Texte_jour_long(V.dates[0]); }
        if (n > 1) {
            var d1 = Infos_jour(V.dates[0]), d2 = Infos_jour(V.dates[n - 1]);
            var debut_resume = d1.m === d2.m && d1.a === d2.a ? JOURS_COURTS[Jour_semaine(V.dates[0])] + " " + d1.j : Texte_jour_court(V.dates[0]);
            resume = debut_resume + " → " + Texte_jour_court(V.dates[n - 1]) + " · " + n + " dates";
        }
        $("#pl_acc_resume_dates").text(resume).attr("title", resume);
    }

    // ------------------------------------------------------------------ Collaborateurs et filtres
    function Rendu_collaborateurs() {
        var html = "";
        V.affiches.slice().sort(function(a, b) { return S.collabs.get(a).libelle.localeCompare(S.collabs.get(b).libelle); }).forEach(function(id) {
            var c = S.collabs.get(id), masque = V.masques.has(id);
            html += "<li class='" + (masque ? "masque" : "") + "'>" + Html_avatar(id, true) + "<span class='pl-collab-nom' title='" + Echapper(c.libelle + (c.poste ? " – " + c.poste : "")) + "'>" + Echapper(c.libelle) + "</span>" +
                (c.modifiable ? "" : "<i class='fa fa-lock pl-muted' title='Lecture seule' aria-label='Lecture seule'></i>") +
                "<button type='button' class='pl-mini-btn' data-collab-masquer='" + id + "' aria-label='" + (masque ? "Afficher " : "Masquer ") + Echapper(c.libelle) + "' title='" + (masque ? "Afficher" : "Masquer") + "'><i class='fa " + (masque ? "fa-eye-slash" : "fa-eye") + "'></i></button>" +
                "<button type='button' class='pl-mini-btn' data-collab-retirer='" + id + "' aria-label='Retirer " + Echapper(c.libelle) + "' title='Retirer'><i class='fa fa-times'></i></button></li>";
        });
        $("#pl_collabs_liste").html(html || "<li class='pl-muted pl-petit'>Aucun collaborateur affiché.</li>");
        var visibles = V.affiches.length - V.masques.size;
        $("#pl_collabs_compte").text(visibles + " affiché" + (visibles > 1 ? "s" : "") + (V.masques.size ? " · " + V.masques.size + " masqué" + (V.masques.size > 1 ? "s" : "") : ""));
    }

    function Rendu_filtres() {
        var html = "";
        S.cats.forEach(function(cat) {
            var coche = !V.filtres.cats.size || V.filtres.cats.has(cat.id);
            html += "<label><input type='checkbox' data-filtre-cat='" + cat.id + "'" + (coche ? " checked" : "") + "><span class='pl-pastille' style='background:" + Echapper(cat.couleur) + "'></span>" + Echapper(cat.nom) + "</label>";
        });
        $("#pl_filtre_cats").html(html);
        $("#pl_filtre_aff").html(Options_affectations(V.filtres.aff, false, "Toutes les affectations"));
        var options = "<option value=''>Toutes</option>";
        S.qualifs.forEach(function(q) { options += "<option value='" + q.id + "'" + (q.id === V.filtres.qualif ? " selected" : "") + ">" + Echapper(q.nom) + "</option>"; });
        $("#pl_filtre_qualif").html(options);
    }

    // ------------------------------------------------------------------ Accordéon du panneau latéral
    function Rendu_accordeon() {
        $(".pl-acc-item").each(function() {
            var code = this.getAttribute("data-panneau"), ouvert = V.panneau === code;
            $(this).find(".pl-acc-tete").attr("aria-expanded", String(ouvert));
            $(this).find(".pl-acc-corps").prop("hidden", !ouvert);
        });
    }

    function Maj_resume_filtres() {
        var parties = [], nbre = 0;
        if (V.filtres.cats.size) {
            nbre++;
            var cochees = Array.from(V.filtres.cats).filter(function(id) { return S.cats.has(id); }).length;
            parties.push("Catégories : " + cochees + " sur " + S.cats.size);
        }
        if (V.filtres.aff !== null && S.affs.has(V.filtres.aff)) { nbre++; parties.push("Affectation : " + Chemin_aff(V.filtres.aff, true)); }
        if (V.filtres.qualif !== null) {
            nbre++;
            var q = S.qualifs.find(function(x) { return x.id === V.filtres.qualif; });
            parties.push("Qualification : " + (q ? q.nom : ""));
        }
        $("#pl_acc_resume_filtres").text(parties.length ? parties.join(" · ") : "Aucun filtre");
        $("#pl_acc_badge_filtres").text(nbre).prop("hidden", !nbre);
    }

    // ------------------------------------------------------------------ Barre d'outils, bannière et statut
    function Maj_boutons() {
        $("#pl_annuler").prop("disabled", !Pile.annuler.length).attr("title", Pile.annuler.length ? "Annuler : " + Pile.annuler[Pile.annuler.length - 1].libelle + " (Ctrl+Z)" : "Annuler (Ctrl+Z)");
        $("#pl_retablir").prop("disabled", !Pile.retablir.length).attr("title", Pile.retablir.length ? "Rétablir : " + Pile.retablir[Pile.retablir.length - 1].libelle + " (Ctrl+Y)" : "Rétablir (Ctrl+Y)");
        var selection_modifiable = Array.from(V.selection).some(function(id) { var evt = S.evts.get(id); return evt && Est_modifiable(evt.c); });
        $("#pl_dupliquer, #pl_supprimer").prop("disabled", !selection_modifiable);
        $("[data-mode]").each(function() { $(this).attr("aria-pressed", String($(this).data("mode") === V.mode)); });
        $("[data-vue]").each(function() { $(this).attr("aria-pressed", String($(this).data("vue") === V.vue)); });
        $("[data-densite]").each(function() { $(this).attr("aria-pressed", String($(this).data("densite") === V.densite)); });
        $("#pl_sous").val(V.sous);
        $("#pl_pas").val(String(V.pas));
        $("#pl_opt_titres").prop("checked", V.titres);
        $("#pl_opt_affs").prop("checked", V.affs);
        $("#pl_opt_realise").prop("checked", V.realise);
        $("#pl_plage_auto").text(V.plage.auto ? "AUTO" : "PERSO").toggleClass("perso", !V.plage.auto);
        $("#pl_plage_texte").text(Pad(Math.floor(M.plage.debut / 60)) + "h – " + Pad(Math.floor(M.plage.fin / 60) % 24 || (M.plage.fin === 1440 ? 24 : 0)) + "h");
        var cat = S.cats.get(V.cat_defaut);
        $("#pl_ajouter").attr("title", "Nouvel évènement" + (cat ? " · cliquer-glisser sur une ligne crée : " + cat.nom : ""));
    }

    function Rendu_banniere() {
        var messages = [];
        var n = V.dates.length;
        if (R.synthese_auto && n > R.synthese_jours && V.vue === "frise") {
            messages.push("<i class='fa fa-info-circle' aria-hidden='true'></i><span><strong>Très longue période :</strong> la vue synthèse est plus adaptée au-delà de " + R.synthese_jours + " jours.</span>" +
                "<span class='pl-espace'></span><button type='button' class='pl-lien' data-banniere='synthese'>Passer en synthèse</button>");
        } else if (V.vue === "frise" && R.repli_auto && n > R.repli_jours && M.groupes.some(function(g) { return !g.deplie; })) {
            messages.push("<i class='fa fa-info-circle' aria-hidden='true'></i><span><strong>Longue période :</strong> " + (M.densite !== "confortable" ? "densité réduite et " : "") +
                "groupes repliés automatiquement (au-delà de " + R.repli_jours + " jours, réglable via <i class='fa fa-cog'></i>).</span><span class='pl-espace'></span>" +
                "<button type='button' class='pl-lien' data-banniere='deplier'>Tout déplier</button><button type='button' class='pl-lien' data-banniere='replier'>Tout replier</button>");
        }
        $("#pl_banniere").html(messages.join("")).prop("hidden", !messages.length);
    }

    function Statut() {
        var html;
        if (S.chargement_en_cours) { html = "<i class='fa fa-spinner fa-spin'></i>Chargement des évènements" + (S.progression ? " (" + S.progression + " %)" : "") + "…"; }
        else if (envoi_en_cours || File_envoi.length) { html = "<i class='fa fa-spinner fa-spin'></i>Enregistrement…"; }
        else {
            var nbre = 0;
            (M.collabs || []).forEach(function(c) { V.dates.forEach(function(j) { nbre += Evts_visibles(c, j).filter(function(evt) { return Jour_de(evt.s) === j || j === V.dates[0]; }).length; }); });
            html = "<i class='fa fa-check-circle text-success'></i>" + nbre + " évènement" + (nbre > 1 ? "s" : "") + " affiché" + (nbre > 1 ? "s" : "");
            if (V.vue === "frise" && M.lignes.length) { html += " · " + M.rendues.size + " lignes rendues sur " + M.lignes.length; }
            if (V.selection.size) { html += " · " + V.selection.size + " sélectionné" + (V.selection.size > 1 ? "s" : ""); }
            if (derniere_sauvegarde) { html += " · enregistré à " + Pad(derniere_sauvegarde.getHours()) + ":" + Pad(derniere_sauvegarde.getMinutes()); }
        }
        $("#pl_statut").html(html);
    }

    function Rafraichir_tout() {
        if (V.vue === "frise") {
            $("#pl_corps").prop("hidden", false);
            $synthese.prop("hidden", true).empty();
            Rendu_frise();
        } else {
            $("#pl_corps").prop("hidden", true);
            $synthese.prop("hidden", false);
            Construire_lignes();
            Rendu_synthese();
        }
        Rendu_legende();
        Rendu_banniere();
        Maj_resume_filtres();
        Maj_boutons();
        Statut();
    }

    function Rafraichir_selection() {
        // Mise à jour légère de la sélection sans reconstruire les lignes
        $canvas.find(".pl-barre").each(function() { this.classList.toggle("sel", V.selection.has(+this.getAttribute("data-id"))); });
        Maj_boutons();
        Statut();
    }

    // ------------------------------------------------------------------ Dates
    function Changer_dates(jours) {
        var uniques = Array.from(new Set(jours)).sort(function(a, b) { return a - b; });
        if (uniques.length > 400) { toastr.warning("La sélection est limitée à 400 jours"); uniques = uniques.slice(0, 400); }
        var avant = V.dates.length;
        V.dates = uniques;
        V.bascules.clear();
        if (R.synthese_auto && R.synthese_mode === "basculer" && uniques.length > R.synthese_jours && avant <= R.synthese_jours) { V.vue = "synthese"; }
        Rendu_calendrier();
        Rafraichir_tout();
        Charger_jours(uniques);
        // Préchargement des fériés du mois affiché dans le calendrier
    }

    function Lundi(jour) { return jour - Jour_semaine(jour); }
    function Raccourci_dates(code) {
        var auj = Aujourdhui(), jours = [], i, infos;
        if (code === "semaine" || code === "semaine_suivante") {
            var debut = Lundi(auj) + (code === "semaine_suivante" ? 7 : 0);
            for (i = 0; i < 7; i++) { jours.push(debut + i); }
        } else {
            infos = Infos_jour(auj);
            var mois = infos.m + (code === "mois_suivant" ? 1 : 0);
            var premier = Math.floor(Date.UTC(infos.a, mois, 1) / 86400000), dernier = Math.floor(Date.UTC(infos.a, mois + 1, 0) / 86400000);
            for (i = premier; i <= dernier; i++) { jours.push(i); }
        }
        var info = Infos_jour(jours[0]);
        V.mois_cal = {a: info.a, m: info.m};
        V.ancre_cal = jours[0];
        Changer_dates(jours);
    }

    function Clic_calendrier(jour, e) {
        var jours;
        if (e.shiftKey && V.ancre_cal !== null) {
            var a = Math.min(V.ancre_cal, jour), b = Math.max(V.ancre_cal, jour);
            jours = e.ctrlKey || e.metaKey ? V.dates.slice() : [];
            for (var j = a; j <= b; j++) { jours.push(j); }
        } else if (e.ctrlKey || e.metaKey) {
            jours = V.dates.filter(function(d) { return d !== jour; });
            if (jours.length === V.dates.length) { jours.push(jour); }
            V.ancre_cal = jour;
        } else {
            jours = [jour];
            V.ancre_cal = jour;
        }
        Changer_dates(jours);
    }

    // ------------------------------------------------------------------ Sélection
    function Selectionner(ids, ajouter) {
        if (!ajouter) { V.selection.clear(); }
        ids.forEach(function(id) { V.selection.add(id); });
        Rafraichir_selection();
    }
    function Selection_modifiable() {
        return Array.from(V.selection).map(function(id) { return S.evts.get(id); }).filter(function(evt) { return evt && Est_modifiable(evt.c); });
    }
    function Selectionner_ligne(ligne) {
        Selectionner(Ligne_evts(ligne).map(function(evt) { return evt.id; }), false);
    }

    // ------------------------------------------------------------------ Opérations
    function Nouvel_id() { return S.prochain_tmp--; }

    function Supprimer_selection() {
        var evts = Selection_modifiable();
        if (!evts.length) { return; }
        Valider(evts.length > 1 ? "Supprimer " + evts.length + " évènements" : "Supprimer un évènement",
            evts.map(function(evt) { return {type: "delete", id: evt.id, avant: Copie_evt(evt)}; }));
        V.selection.clear();
        Rafraichir_selection();
    }

    function Emplacement_libre(modele, decalages) {
        // Cherche le premier décalage (en minutes) qui ne crée pas de chevauchement
        for (var i = 0; i < decalages.length; i++) {
            var candidat = $.extend(Copie_evt(modele), {id: 0, s: modele.s + decalages[i], e: modele.e + decalages[i], rs: null, re: null});
            if (!Conflits(candidat).length) { return candidat; }
        }
        return null;
    }

    function Dupliquer_selection() {
        var evts = Selection_modifiable();
        if (!evts.length) { return; }
        var changements = [], echecs = 0, nouveaux = [];
        evts.forEach(function(evt) {
            var duree = evt.e - evt.s;
            var copie = Emplacement_libre(evt, [duree, 1440, 2880, 10080]);
            if (!copie) { echecs++; return; }
            copie.id = Nouvel_id();
            changements.push({type: "create", id: copie.id, apres: copie});
            S.evts.set(copie.id, copie); Reindexer();     // pour que les copies suivantes tiennent compte de celle-ci
            nouveaux.push(copie.id);
        });
        nouveaux.forEach(function(id) { S.evts.delete(id); });
        Reindexer();
        Valider(changements.length > 1 ? "Dupliquer " + changements.length + " évènements" : "Dupliquer un évènement", changements);
        if (nouveaux.length) { Selectionner(nouveaux.map(Id_actuel), false); }
        if (echecs) { toastr.warning(echecs + " évènement" + (echecs > 1 ? "s n'ont" : " n'a") + " pas pu être dupliqué faute de place libre"); }
    }

    function Copier_selection() {
        var evts = Array.from(V.selection).map(function(id) { return S.evts.get(id); }).filter(Boolean);
        if (!evts.length) { return; }
        Presse_papier = evts.map(Copie_evt);
        toastr.info(evts.length + " évènement" + (evts.length > 1 ? "s copiés" : " copié") + " · Ctrl+V pour coller sur la ligne courante");
    }

    function Coller(ligne, minute) {
        if (!Presse_papier.length || !ligne || ligne.type !== "l") { return; }
        if (!Est_modifiable(ligne.c)) { toastr.warning("Vous ne pouvez pas modifier le planning de ce collaborateur"); return; }
        var mini = Math.min.apply(null, Presse_papier.map(function(evt) { return evt.s; }));
        var decalage = minute !== undefined ? ligne.jour * 1440 + minute - mini : (ligne.jour - Jour_de(mini)) * 1440;
        var changements = [], echecs = 0, ajoutes = [];
        Presse_papier.forEach(function(source) {
            var copie = $.extend(Copie_evt(source), {id: Nouvel_id(), c: ligne.c, s: source.s + decalage, e: source.e + decalage, rs: null, re: null, v: 1});
            if (ligne.aff !== undefined) { copie.aff = ligne.aff; }
            if (Conflits(copie).length) { echecs++; return; }
            S.evts.set(copie.id, copie); Reindexer(); ajoutes.push(copie.id);
            changements.push({type: "create", id: copie.id, apres: Copie_evt(copie)});
        });
        ajoutes.forEach(function(id) { S.evts.delete(id); });
        Reindexer();
        Valider("Coller " + changements.length + " évènement" + (changements.length > 1 ? "s" : ""), changements);
        if (ajoutes.length) { Selectionner(ajoutes.map(Id_actuel), false); }
        if (echecs) { toastr.warning(echecs + " évènement" + (echecs > 1 ? "s n'ont" : " n'a") + " pas été collé" + (echecs > 1 ? "s" : "") + " (chevauchement)"); }
    }

    function Couper_en_deux(evt, minute) {
        minute = Math.round(minute / V.pas) * V.pas;
        if (minute <= evt.s || minute >= evt.e) { toastr.warning("Choisissez une heure comprise dans l'évènement"); return; }
        var premiere = $.extend(Copie_evt(evt), {e: minute});
        var seconde = $.extend(Copie_evt(evt), {id: Nouvel_id(), s: minute, rs: null, re: null});
        if (evt.rs !== null) { premiere.rs = null; premiere.re = null; }
        Valider("Couper un évènement", [
            {type: "update", id: evt.id, avant: Copie_evt(evt), apres: premiere},
            {type: "create", id: seconde.id, apres: seconde}
        ]);
    }

    function Modifier_evts(libelle, evts, transformer) {
        // Applique une transformation à plusieurs évènements en ignorant ceux qui créeraient un chevauchement
        var changements = [], ignores = 0, modifies = new Set(evts.map(function(evt) { return evt.id; }));
        var apres_liste = evts.map(function(evt) { var copie = Copie_evt(evt); transformer(copie); return copie; });
        apres_liste.forEach(function(apres, i) {
            var avant = evts[i];
            if (apres.e <= apres.s || !Est_modifiable(apres.c)) { ignores++; return; }
            var conflits = Conflits(apres, modifies).length || apres_liste.some(function(autre, j) {
                return j !== i && autre.c === apres.c && apres.s < autre.e && apres.e > autre.s && !Peut_chevaucher(apres, autre);
            });
            if (conflits) { ignores++; return; }
            if (JSON.stringify(Evt_vers_serveur(avant)) === JSON.stringify(Evt_vers_serveur(apres))) { return; }
            changements.push({type: "update", id: avant.id, avant: Copie_evt(avant), apres: apres});
        });
        Valider(libelle, changements);
        if (ignores) { toastr.warning(ignores + " évènement" + (ignores > 1 ? "s n'ont" : " n'a") + " pas été modifié" + (ignores > 1 ? "s" : "") + " (chevauchement ou horaires incorrects)"); }
        return changements.length;
    }

    function Realise_egal_prevu(evts) {
        Modifier_evts("Saisir le réalisé", evts, function(evt) { evt.rs = evt.s; evt.re = evt.e; });
    }

    // ------------------------------------------------------------------ Glisser-déposer
    var D = null;
    var tooltip = null;

    function Infos_piste(element) {
        var index = +element.getAttribute("data-index");
        return {ligne: M.lignes[index], rect: element.getBoundingClientRect(), element: element};
    }
    function Minute_a_x(piste, x) {
        var ratio = Math.min(1, Math.max(0, (x - piste.rect.left) / piste.rect.width));
        return M.plage.debut + ratio * (M.plage.fin - M.plage.debut);
    }
    function Arrondir(m) { return Math.round(m / V.pas) * V.pas; }

    function Afficher_tooltip(html, x, y) {
        if (!tooltip) { tooltip = document.getElementById("pl_tooltip"); }
        tooltip.innerHTML = html;
        tooltip.hidden = false;
        var largeur = tooltip.offsetWidth, hauteur = tooltip.offsetHeight;
        tooltip.style.left = Math.min(window.innerWidth - largeur - 8, x + 14) + "px";
        tooltip.style.top = (y - hauteur - 14 < 4 ? y + 18 : y - hauteur - 14) + "px";
    }
    function Masquer_tooltip() { if (tooltip) { tooltip.hidden = true; } }

    function Html_info_evt(evt) {
        var cat = S.cats.get(evt.cat) || {nom: "", couleur: "#999"};
        var collab = S.collabs.get(evt.c);
        var html = "<strong><span class='pl-pastille' style='background:" + Echapper(cat.couleur) + "'></span> " + Heure(evt.s) + "–" + Heure(evt.e) + " · " + Duree(evt.e - evt.s) + "</strong><br>" +
            Echapper(collab ? collab.libelle : "") + " · " + Texte_jour_court(Jour_de(evt.s)) + "<br><span class='pl-tt-muted'>" + Echapper(cat.nom) + (evt.t ? " · " + Echapper(evt.t) : "") + "</span>";
        if (evt.aff) { html += "<br><span class='pl-tt-muted'>" + Echapper(Chemin_aff(evt.aff)) + "</span>"; }
        if (evt.rs !== null) { html += "<br>Réalisé : " + Heure(evt.rs) + "–" + Heure(evt.re) + " (" + Duree(evt.re - evt.rs) + ")"; }
        return html;
    }

    function Fantome(piste, evt_ou_debut, fin, classes, jour) {
        var debut = typeof evt_ou_debut === "number" ? evt_ou_debut : evt_ou_debut.s;
        var element = document.createElement("div");
        element.className = "pl-barre fantome " + (classes || "");
        Positionner_fantome(element, debut, fin, jour);
        piste.appendChild(element);
        return element;
    }
    function Positionner_fantome(element, debut, fin, jour) {
        var s = Math.max(debut - jour * 1440, M.plage.debut), e = Math.min(fin - jour * 1440, M.plage.fin);
        element.style.left = Pct(s) + "%";
        element.style.width = "calc(" + Math.max(0.5, Pct(e) - Pct(s)) + "% - 1px)";
    }

    function Pointer_down(e) {
        if (e.button !== 0) { return; }
        var barre = e.target.closest(".pl-barre");
        var piste_el = e.target.closest(".pl-piste");
        Fermer_menu();
        if (barre && !barre.classList.contains("fantome")) {
            var id = +barre.getAttribute("data-id"), evt = S.evts.get(id);
            if (!evt) { return; }
            var deja = V.selection.has(id);
            if (e.ctrlKey || e.metaKey) {
                if (deja) { V.selection.delete(id); } else { V.selection.add(id); }
                Rafraichir_selection();
                return;
            }
            if (e.shiftKey) { V.selection.add(id); Rafraichir_selection(); }
            else if (!deja) { Selectionner([id], false); }
            var piste = Infos_piste(piste_el);
            V.ligne_courante = piste.ligne.cle;
            if (!Est_modifiable(evt.c)) { return; }
            if (e.pointerType === "touch" && !deja) { return; }
            var rect = barre.getBoundingClientRect(), x = e.clientX - rect.left;
            var bord = e.pointerType === "touch" ? 12 : 7;
            D = {type: "barre", id: id, evt: Copie_evt(evt), mode: x < bord ? "l" : (x > rect.width - bord ? "r" : "move"), x0: e.clientX, y0: e.clientY,
                 demarre: false, piste: piste, cible: piste, copie: e.altKey, clic_simple_multi: deja && V.selection.size > 1, pointer: e.pointerId};
            e.preventDefault();
            return;
        }
        if (piste_el) {
            var infos = Infos_piste(piste_el);
            if (!infos.ligne || infos.ligne.type !== "l") { return; }
            V.ligne_courante = infos.ligne.cle;
            if (!e.ctrlKey && !e.metaKey && V.selection.size) { V.selection.clear(); Rafraichir_selection(); }
            if (!Est_modifiable(infos.ligne.c) || e.pointerType === "touch") { return; }
            D = {type: "creation", piste: infos, x0: e.clientX, y0: e.clientY, debut: Arrondir(Minute_a_x(infos, e.clientX)), demarre: false, pointer: e.pointerId};
            e.preventDefault();
        }
    }

    function Pointer_move(e) {
        if (!D) {
            // Infobulle au survol d'une barre
            var barre = e.target.closest && e.target.closest(".pl-barre");
            if (barre && !barre.classList.contains("fantome") && e.pointerType !== "touch") {
                var evt = S.evts.get(+barre.getAttribute("data-id"));
                if (evt) { Afficher_tooltip(Html_info_evt(evt), e.clientX, e.clientY); return; }
            }
            Masquer_tooltip();
            return;
        }
        if (!D.demarre) {
            if (Math.abs(e.clientX - D.x0) < 4 && Math.abs(e.clientY - D.y0) < 4) { return; }
            D.demarre = true;
            try { $scroll[0].setPointerCapture(D.pointer); } catch (err) {}
            Demarrer_glisser();
        }
        if (D.type === "creation") { Glisser_creation(e); } else { Glisser_barre(e); }
    }

    function Demarrer_glisser() {
        Masquer_tooltip();
        if (D.type === "creation") {
            D.fantome = Fantome(D.piste.element, D.piste.ligne.jour * 1440 + D.debut, D.piste.ligne.jour * 1440 + D.debut + V.pas, "creation", D.piste.ligne.jour);
            return;
        }
        // Déplacement multiple : toutes les barres sélectionnées modifiables bougent ensemble (horizontalement)
        D.multi = D.mode === "move" && V.selection.size > 1 && V.selection.has(D.id);
        D.originaux = D.multi ? Selection_modifiable().map(Copie_evt) : [D.evt];
        D.fantomes = [];
        D.originaux.forEach(function(evt) {
            $canvas.find(".pl-barre[data-id='" + evt.id + "']").each(function() {
                if (!D.copie) { this.classList.add("deplace"); }
                var piste = this.parentNode;
                var ligne = M.lignes[+piste.getAttribute("data-index")];
                D.fantomes.push({evt: evt, element: Fantome(piste, evt, evt.e, "", ligne.jour), jour: ligne.jour, piste: piste});
            });
        });
        document.body.style.cursor = D.mode === "move" ? "grabbing" : "ew-resize";
    }

    function Glisser_creation(e) {
        var jour = D.piste.ligne.jour;
        var m = Arrondir(Minute_a_x(D.piste, e.clientX));
        var debut = Math.min(D.debut, m), fin = Math.max(D.debut, m);
        if (fin === debut) { fin = debut + V.pas; }
        D.s = jour * 1440 + debut; D.e = jour * 1440 + fin;
        var candidat = {id: 0, c: D.piste.ligne.c, cat: V.cat_defaut, s: D.s, e: D.e};
        D.valide = !Conflits(candidat).length;
        D.fantome.classList.toggle("invalide", !D.valide);
        Positionner_fantome(D.fantome, D.s, D.e, jour);
        var cat = S.cats.get(V.cat_defaut);
        Afficher_tooltip("<strong>" + Heure(D.s) + " → " + Heure(D.e) + "</strong> (" + Duree(D.e - D.s) + ")<br><span class='pl-tt-muted'>" + (D.valide ? "Nouvel évènement : " + Echapper(cat ? cat.nom : "") : "Chevauchement impossible") + "</span>", e.clientX, e.clientY);
    }

    function Glisser_barre(e) {
        var mpp = (M.plage.fin - M.plage.debut) / D.piste.rect.width;
        var delta = Arrondir((e.clientX - D.x0) * mpp);
        var evt = D.evt;
        if (D.mode === "move" && !D.multi) {
            // Changement de ligne possible
            var element = document.elementFromPoint(e.clientX, e.clientY);
            var piste_el = element && element.closest ? element.closest(".pl-piste") : null;
            if (piste_el && $canvas[0].contains(piste_el)) {
                var cible = Infos_piste(piste_el);
                if (cible.ligne && cible.ligne.type === "l") { D.cible = cible; }
            }
            var ligne_cible = D.cible.ligne, ligne_source = D.piste.ligne;
            var decalage_jour = (ligne_cible.jour - ligne_source.jour) * 1440;
            var nouveau = $.extend(Copie_evt(evt), {s: evt.s + delta + decalage_jour, e: evt.e + delta + decalage_jour, c: ligne_cible.c});
            if (ligne_cible.aff !== undefined) { nouveau.aff = ligne_cible.aff; }
            if (nouveau.rs !== null && (delta || decalage_jour)) { nouveau.rs = null; nouveau.re = null; }
            if (D.copie) { nouveau.id = 0; nouveau.rs = null; nouveau.re = null; }
            var valide = Est_modifiable(nouveau.c) && !Conflits(nouveau, D.copie ? null : new Set([evt.id])).length;
            D.resultats = [{avant: evt, apres: nouveau}];
            D.valide = valide;
            var fantome = D.fantomes[0];
            if (fantome.piste !== D.cible.element) { D.cible.element.appendChild(fantome.element); fantome.piste = D.cible.element; }
            fantome.element.classList.toggle("invalide", !valide);
            fantome.element.style.backgroundColor = (S.cats.get(evt.cat) || {}).couleur || "#999";
            Positionner_fantome(fantome.element, nouveau.s, nouveau.e, ligne_cible.jour);
            var texte = "<strong>" + (D.copie ? "Copie" : "Déplacement") + " : " + Heure(nouveau.s) + " → " + Heure(nouveau.e) + "</strong>";
            if (ligne_cible !== ligne_source) { texte += "<br>" + Echapper(S.collabs.get(nouveau.c).libelle) + " · " + Texte_jour_court(ligne_cible.jour); }
            if (ligne_cible.aff !== undefined && ligne_cible.aff !== evt.aff) { texte += "<br><span class='pl-tt-muted'>Affectation : " + Echapper(ligne_cible.aff ? Chemin_aff(ligne_cible.aff) : "aucune") + "</span>"; }
            if (!valide) { texte += "<br><span class='pl-tt-muted'>" + (Est_modifiable(nouveau.c) ? "Chevauchement impossible" : "Planning non modifiable") + "</span>"; }
            Afficher_tooltip(texte, e.clientX, e.clientY);
            return;
        }
        if (D.mode === "move") {
            var ids = new Set(D.originaux.map(function(o) { return o.id; }));
            D.resultats = D.originaux.map(function(o) { return {avant: o, apres: $.extend(Copie_evt(o), {s: o.s + delta, e: o.e + delta, rs: D.copie ? null : o.rs, re: D.copie ? null : o.re})}; });
            D.valide = D.resultats.every(function(r) { return !Conflits(r.apres, D.copie ? null : ids).length; });
            D.fantomes.forEach(function(f) {
                var r = D.resultats.find(function(x) { return x.avant.id === f.evt.id; });
                f.element.classList.toggle("invalide", !D.valide);
                f.element.style.backgroundColor = (S.cats.get(f.evt.cat) || {}).couleur || "#999";
                Positionner_fantome(f.element, r.apres.s, r.apres.e, f.jour);
            });
            Afficher_tooltip("<strong>" + (D.copie ? "Copie" : "Déplacement") + " de " + D.originaux.length + " évènements : " + (delta >= 0 ? "+" : "") + Duree(delta) + "</strong>" + (D.valide ? "" : "<br><span class='pl-tt-muted'>Chevauchement impossible</span>"), e.clientX, e.clientY);
            return;
        }
        // Redimensionnement : limité par les évènements voisins
        var nouveau_r = Copie_evt(evt);
        var voisins = [];
        for (var j = Jour_de(evt.s) - 1; j <= Jour_de(evt.e) + 1; j++) {
            Evts_de(evt.c, j).forEach(function(autre) { if (autre.id !== evt.id && !Peut_chevaucher(evt, autre) && voisins.indexOf(autre) < 0) { voisins.push(autre); } });
        }
        if (D.mode === "r") {
            nouveau_r.e = Math.max(evt.s + V.pas, evt.e + delta);
            voisins.forEach(function(autre) { if (autre.s >= evt.e && nouveau_r.e > autre.s) { nouveau_r.e = autre.s; } });
        } else {
            nouveau_r.s = Math.min(evt.e - V.pas, evt.s + delta);
            voisins.forEach(function(autre) { if (autre.e <= evt.s && nouveau_r.s < autre.e) { nouveau_r.s = autre.e; } });
        }
        D.resultats = [{avant: evt, apres: nouveau_r}];
        D.valide = nouveau_r.e > nouveau_r.s;
        var f0 = D.fantomes[0];
        f0.element.style.backgroundColor = (S.cats.get(evt.cat) || {}).couleur || "#999";
        Positionner_fantome(f0.element, nouveau_r.s, nouveau_r.e, f0.jour);
        Afficher_tooltip("<strong>" + Heure(nouveau_r.s) + " → " + Heure(nouveau_r.e) + "</strong> (" + Duree(nouveau_r.e - nouveau_r.s) + ")", e.clientX, e.clientY);
    }

    function Pointer_up(e) {
        if (!D) { return; }
        var etat = D;
        D = null;
        document.body.style.cursor = "";
        Masquer_tooltip();
        try { $scroll[0].releasePointerCapture(etat.pointer); } catch (err) {}
        if (!etat.demarre) {
            if (etat.type === "barre" && etat.clic_simple_multi && !e.shiftKey) { Selectionner([etat.id], false); }
            Rafraichir_ligne_courante();
            return;
        }
        if (etat.type === "creation") {
            if (etat.fantome) { etat.fantome.remove(); }
            if (!etat.valide || !etat.s) { if (!etat.valide) { toastr.warning("Impossible de créer un évènement qui en chevauche un autre"); } return; }
            if (!V.cat_defaut) { toastr.warning("Créez d'abord une catégorie d'évènements dans le paramétrage"); return; }
            var ligne = etat.piste.ligne;
            var nouveau = {id: Nouvel_id(), c: ligne.c, cat: V.cat_defaut, aff: ligne.aff !== undefined ? ligne.aff : null, t: "", s: etat.s, e: etat.e, rs: null, re: null, v: 1};
            Valider("Créer un évènement", [{type: "create", id: nouveau.id, apres: nouveau}]);
            Selectionner([Id_actuel(nouveau.id)], false);
            return;
        }
        (etat.fantomes || []).forEach(function(f) { f.element.remove(); });
        $canvas.find(".pl-barre.deplace").removeClass("deplace");
        if (!etat.valide || !etat.resultats) {
            toastr.warning("Déplacement impossible : chevauchement avec un autre évènement");
            Rafraichir_tout();
            return;
        }
        var changements = [], nouveaux_ids = [];
        etat.resultats.forEach(function(r) {
            if (r.apres.s === r.avant.s && r.apres.e === r.avant.e && r.apres.c === r.avant.c && r.apres.aff === r.avant.aff) { return; }
            if (etat.copie) {
                var copie = $.extend(Copie_evt(r.apres), {id: Nouvel_id(), v: 1});
                changements.push({type: "create", id: copie.id, apres: copie});
                nouveaux_ids.push(copie.id);
            } else {
                changements.push({type: "update", id: r.avant.id, avant: Copie_evt(r.avant), apres: $.extend(Copie_evt(r.apres), {id: r.avant.id})});
            }
        });
        if (!changements.length) { Rafraichir_tout(); return; }
        var libelle = etat.copie ? "Copier " + changements.length + " évènement" + (changements.length > 1 ? "s" : "") :
            (etat.mode === "move" ? "Déplacer " + (changements.length > 1 ? changements.length + " évènements" : "un évènement") : "Modifier la durée d'un évènement");
        Valider(libelle, changements);
        if (nouveaux_ids.length) { Selectionner(nouveaux_ids.map(Id_actuel), false); }
    }

    function Rafraichir_ligne_courante() {
        $canvas.find(".pl-l-ligne.courante").removeClass("courante");
        M.rendues.forEach(function(element, index) { if (M.lignes[index].cle === V.ligne_courante) { element.classList.add("courante"); } });
    }

    // ------------------------------------------------------------------ Menu contextuel
    var $menu;
    function Ouvrir_menu(x, y, html) {
        $menu.html(html).prop("hidden", false);
        var largeur = $menu.outerWidth(), hauteur = $menu.outerHeight();
        $menu.css({left: Math.max(4, Math.min(x, window.innerWidth - largeur - 8)) + "px", top: Math.max(4, Math.min(y, window.innerHeight - hauteur - 8)) + "px"});
        $menu.find("button:not(:disabled)").first().focus();
    }
    function Fermer_menu() { if ($menu) { $menu.prop("hidden", true).empty(); } Menu_actions = {}; }
    var Menu_actions = {};
    function Item(code, icone, libelle, raccourci, options) {
        options = options || {};
        if (options.action) { Menu_actions[code] = options.action; }
        return "<button type='button' role='menuitem' data-menu='" + code + "' class='" + (options.danger ? "danger" : "") + "'" + (options.desactive ? " disabled" : "") + ">" +
            "<i class='fa fa-" + icone + "' aria-hidden='true'></i><span>" + libelle + "</span>" + (raccourci ? "<span class='pl-kbd'>" + raccourci + "</span>" : "") + "</button>";
    }
    var SEP = "<div class='pl-menu-sep' role='separator'></div>";

    function Menu_categories(evts, x, y) {
        Menu_actions = {};
        var html = Item("retour", "arrow-left", "Retour", "", {action: function() { Menu_barres(x, y, Minute_menu); }}) + SEP;
        S.cats.forEach(function(cat) {
            html += Item("cat" + cat.id, "square", "<span class='pl-pastille' style='background:" + Echapper(cat.couleur) + "'></span> " + Echapper(cat.nom), "", {action: function() {
                Modifier_evts("Changer de catégorie", evts, function(evt) { evt.cat = cat.id; });
            }});
        });
        Ouvrir_menu(x, y, html);
    }

    var Minute_menu = null;
    function Menu_barres(x, y, minute) {
        Menu_actions = {};
        var evts = Array.from(V.selection).map(function(id) { return S.evts.get(id); }).filter(Boolean);
        if (!evts.length) { return; }
        var modifiables = evts.filter(function(evt) { return Est_modifiable(evt.c); });
        var html = "";
        if (evts.length === 1) {
            var evt = evts[0], cat = S.cats.get(evt.cat) || {nom: ""};
            html += "<div class='pl-menu-titre'>" + Echapper((evt.t || cat.nom) + " · " + Heure(evt.s) + "–" + Heure(evt.e)) + "</div>";
            html += Item("modifier", modifiables.length ? "pencil" : "eye", modifiables.length ? "Modifier…" : "Voir le détail…", "Double-clic", {action: function() { Ouvrir_evt(evt.id); }});
        } else {
            var total = 0;
            evts.forEach(function(e) { total += Signe_categorie(e.cat) * (e.e - e.s); });
            html += "<div class='pl-menu-titre'>" + evts.length + " évènements sélectionnés · " + Duree(total) + "</div>";
            html += Item("lot", "pencil-square-o", "Modifier par lot…", "", {desactive: !modifiables.length, action: function() { Ouvrir_lot(); }});
        }
        if (modifiables.length) {
            html += Item("realise", "check-square-o", "Réalisé = prévu", "", {action: function() { Realise_egal_prevu(modifiables); }});
            html += SEP;
            html += Item("dupliquer", "clone", "Dupliquer", "Ctrl+D", {action: Dupliquer_selection});
            html += Item("dup_dates", "calendar-plus-o", "Dupliquer vers d'autres dates…", "", {action: function() { Ouvrir_dupliquer("dates"); }});
            html += Item("dup_collabs", "users", "Dupliquer vers d'autres collaborateurs…", "", {action: function() { Ouvrir_dupliquer("collabs"); }});
        }
        html += SEP + Item("copier", "copy", "Copier", "Ctrl+C", {action: Copier_selection});
        if (modifiables.length === 1 && evts.length === 1 && minute !== null) {
            var evt1 = evts[0], jour_menu = Minute_menu_jour, coupure = Arrondir(minute) + jour_menu * 1440;
            if (coupure > evt1.s && coupure < evt1.e) {
                html += Item("couper", "scissors", "Couper en deux à " + Heure(coupure), "", {action: function() { Couper_en_deux(evt1, coupure); }});
            }
        }
        if (modifiables.length) {
            html += SEP + Item("categorie", "tags", "Changer de catégorie", "▸", {action: function() { setTimeout(function() { Menu_categories(modifiables, x, y); }, 0); return false; }});
            html += Item("affectation", "sitemap", "Changer d'affectation…", "", {action: function() { Ouvrir_lot("aff"); }});
        }
        html += Item("ligne", "arrows-h", "Sélectionner toute la ligne", "", {action: function() {
            var ligne = M.lignes.find(function(l) { return l.cle === V.ligne_courante; });
            if (ligne) { Selectionner_ligne(ligne); }
        }});
        if (modifiables.length) { html += SEP + Item("supprimer", "trash", "Supprimer", "Suppr", {danger: true, action: Supprimer_selection}); }
        Ouvrir_menu(x, y, html);
    }
    var Minute_menu_jour = 0;

    function Menu_piste(x, y, ligne, minute) {
        Menu_actions = {};
        var modifiable = Est_modifiable(ligne.c);
        var html = "<div class='pl-menu-titre'>" + Echapper(S.collabs.get(ligne.c).libelle) + " · " + Texte_jour_court(ligne.jour) + " · " + Heure(Arrondir(minute)) + "</div>";
        html += Item("nouveau", "plus", "Nouvel évènement ici…", "", {desactive: !modifiable, action: function() {
            var debut = ligne.jour * 1440 + Arrondir(minute);
            Ouvrir_evt(null, {c: ligne.c, s: debut, e: debut + 60, aff: ligne.aff !== undefined ? ligne.aff : null});
        }});
        html += Item("coller", "paste", "Coller ici", "", {desactive: !modifiable || !Presse_papier.length, action: function() { Coller(ligne, Arrondir(minute)); }});
        html += Item("ligne", "arrows-h", "Sélectionner toute la ligne", "", {action: function() { Selectionner_ligne(ligne); }});
        html += SEP + Item("note", "sticky-note-o", ligne.aff ? "Note de l'affectation…" : "Note de la journée…", "", {action: function() { Ouvrir_note(ligne.jour, ligne.aff || null); }});
        Ouvrir_menu(x, y, html);
    }

    function Menu_libelle(x, y, ligne) {
        Menu_actions = {};
        var collab = S.collabs.get(ligne.c);
        var html = "";
        if (V.mode === "date") {
            html += "<div class='pl-menu-titre'>" + Echapper(collab.libelle) + (collab.poste ? " · " + Echapper(collab.poste) : "") + "</div>";
            html += Item("masquer", "eye-slash", "Masquer ce collaborateur", "", {action: function() { V.masques.add(ligne.c); Apres_changement_collabs(); }});
            html += Item("retirer", "times", "Retirer de l'affichage", "", {action: function() { V.affiches = V.affiches.filter(function(id) { return id !== ligne.c; }); Apres_changement_collabs(); }});
        } else {
            html += "<div class='pl-menu-titre'>" + Echapper(Texte_jour_long(ligne.jour)) + "</div>";
            html += Item("note", "sticky-note-o", "Note de la journée…", "", {action: function() { Ouvrir_note(ligne.jour); }});
            html += Item("seule", "calendar-o", "Afficher uniquement cette date", "", {action: function() { Changer_dates([ligne.jour]); }});
        }
        html += Item("ligne", "arrows-h", "Sélectionner toute la ligne", "", {action: function() { Selectionner_ligne(ligne); }});
        html += SEP + Item("ical", "calendar", "Lien d'agenda en ligne (iCal)…", "", {desactive: !collab.modifiable, action: function() { Ouvrir_ical(ligne.c); }});
        html += Item("fiche", "user", "Ouvrir la fiche du collaborateur", "", {action: function() { window.open(CFG.url_fiche.replace(/0$/, String(ligne.c)), "_blank"); }});
        if (CFG.url_planning_individuel) { html += Item("planning_individuel", "calendar-check-o", "Ouvrir le planning individuel", "", {action: function() { window.location.href = CFG.url_planning_individuel + "?idcollaborateur=" + ligne.c; }}); }
        Ouvrir_menu(x, y, html);
    }

    function Context_menu(e) {
        var barre = e.target.closest(".pl-barre");
        var piste_el = e.target.closest(".pl-piste");
        var libelle = e.target.closest(".pl-lbl-ligne");
        if (!barre && !piste_el && !libelle) { return; }
        e.preventDefault();
        Masquer_tooltip();
        var conteneur = (piste_el || libelle.parentNode.querySelector(".pl-piste"));
        if (!conteneur) { return; }
        var infos = Infos_piste(conteneur);
        if (!infos.ligne || infos.ligne.type !== "l") { return; }
        V.ligne_courante = infos.ligne.cle;
        Rafraichir_ligne_courante();
        if (libelle) { Menu_libelle(e.clientX, e.clientY, infos.ligne); return; }
        var minute = Minute_a_x(infos, e.clientX);
        Minute_menu = minute;
        Minute_menu_jour = infos.ligne.jour;
        if (barre && !barre.classList.contains("fantome")) {
            var id = +barre.getAttribute("data-id");
            if (!V.selection.has(id)) { Selectionner([id], false); }
            Menu_barres(e.clientX, e.clientY, minute);
        } else {
            Menu_piste(e.clientX, e.clientY, infos.ligne, minute);
        }
    }

    // ------------------------------------------------------------------ Collaborateurs
    function Apres_changement_collabs() {
        Rendu_collaborateurs();
        Init_ajout_collabs();
        Rafraichir_tout();
        Memoriser_affichage();
    }

    function Init_ajout_collabs() {
        var $select = $("#pl_collabs_ajout");
        var groupes = S.groupes.map(function(g) { return {id: "g" + g.id, text: g.nom + " (groupe)"}; });
        var affiches = new Set(V.affiches);
        var collabs = [];
        S.collabs.forEach(function(c) { if (!affiches.has(c.id)) { collabs.push({id: "c" + c.id, text: c.libelle + (c.poste ? " – " + c.poste : "")}); } });
        var donnees = [{id: "tous", text: "Tous les collaborateurs"}];
        if (groupes.length) { donnees.push({text: "Groupes", children: groupes}); }
        if (collabs.length) { donnees.push({text: "Collaborateurs", children: collabs}); }
        if ($select.data("select2")) { $select.select2("destroy"); }
        $select.empty().append("<option></option>");
        $select.select2({data: donnees, placeholder: "Ajouter un collaborateur ou un groupe…", language: "fr", width: "100%", allowClear: false, theme: "bootstrap4"});
    }

    // ------------------------------------------------------------------ Branchement des évènements
    function Brancher_evenements() {
        $canvas = $("#pl_canvas"); $scroll = $("#pl_scroll"); $axe = $("#pl_axe"); $sticky = $("#pl_sticky"); $minimap = $("#pl_minimap"); $synthese = $("#pl_synthese"); $menu = $("#pl_menu");

        // Défilement virtualisé
        var raf = null;
        $scroll.on("scroll", function() {
            if (raf) { return; }
            raf = requestAnimationFrame(function() { raf = null; Rendu_visible(); });
        });
        $(window).on("resize", Debounce(function() { if (V.vue === "frise") { Rendu_frise(); } Rendu_minimap(); }, 150));

        // Souris / tactile
        $scroll[0].addEventListener("pointerdown", Pointer_down);
        document.addEventListener("pointermove", Pointer_move);
        document.addEventListener("pointerup", Pointer_up);
        document.addEventListener("pointercancel", function() { if (D) { D = null; Masquer_tooltip(); Rafraichir_tout(); } });
        $scroll.on("pointerleave", function() { if (!D) { Masquer_tooltip(); } });
        $scroll[0].addEventListener("contextmenu", Context_menu);
        $scroll.on("dblclick", function(e) {
            var barre = e.target.closest(".pl-barre");
            if (barre) { Ouvrir_evt(+barre.getAttribute("data-id")); return; }
            var piste_el = e.target.closest(".pl-piste");
            if (piste_el) {
                var infos = Infos_piste(piste_el);
                if (infos.ligne && infos.ligne.type === "l" && Est_modifiable(infos.ligne.c)) {
                    var debut = infos.ligne.jour * 1440 + Arrondir(Minute_a_x(infos, e.clientX) - 30);
                    Ouvrir_evt(null, {c: infos.ligne.c, s: debut, e: debut + 60, aff: infos.ligne.aff !== undefined ? infos.ligne.aff : null});
                }
            }
        });
        $scroll.on("click", "[data-action]", function(e) {
            var action = this.getAttribute("data-action");
            if (action === "plier") {
                var cle = this.getAttribute("data-cle");
                var groupe = M.groupes.find(function(g) { return g.cle === cle; });
                V.bascules.set(cle, groupe ? !groupe.deplie : false);
                Rafraichir_tout();
            }
            if (action === "note") { Ouvrir_note(+this.getAttribute("data-jour"), this.getAttribute("data-aff") ? +this.getAttribute("data-aff") : null); }
            if (action === "remplissage") { Ouvrir_detail_remplissage(this); }
            if (action === "masquer") { V.masques.add(+this.getAttribute("data-c")); Apres_changement_collabs(); }
            if (action === "libelle") {
                var piste = this.parentNode.querySelector(".pl-piste");
                if (piste) { var rect = this.getBoundingClientRect(); Context_menu({target: this, clientX: rect.left + 20, clientY: rect.bottom, preventDefault: function() {}}); }
            }
        });
        // Zoom horaire avec Ctrl + molette
        $scroll[0].addEventListener("wheel", function(e) {
            if (!e.ctrlKey) { return; }
            e.preventDefault();
            Zoomer(e.deltaY < 0 ? 1 : -1);
        }, {passive: false});
        $minimap.on("click", function(e) {
            var item = e.target.closest("[data-groupe]");
            if (item) { Defiler_vers_groupe(item.getAttribute("data-groupe")); return; }
            var rect = this.getBoundingClientRect();
            $scroll[0].scrollTop = (e.clientY - rect.top) / rect.height * M.hauteur - $scroll[0].clientHeight / 2;
        });

        // Menu contextuel
        $menu.on("click", "button[data-menu]", function() {
            var action = Menu_actions[this.getAttribute("data-menu")];
            var garder = action ? action() === false : false;
            if (!garder) { Fermer_menu(); }
        });
        $menu.on("keydown", function(e) {
            var boutons = $menu.find("button:not(:disabled)"), index = boutons.index(document.activeElement);
            if (e.key === "ArrowDown") { e.preventDefault(); boutons.eq((index + 1) % boutons.length).focus(); }
            if (e.key === "ArrowUp") { e.preventDefault(); boutons.eq((index - 1 + boutons.length) % boutons.length).focus(); }
            if (e.key === "Escape") { Fermer_menu(); $scroll.focus(); }
        });
        $(document).on("pointerdown", function(e) {
            if (!$menu.prop("hidden") && !$menu[0].contains(e.target)) { Fermer_menu(); }
            $(".pl-pop").each(function() {
                var parent = this.parentNode;
                if (!this.hidden && !parent.contains(e.target)) { this.hidden = true; $(parent).find("[aria-expanded]").attr("aria-expanded", "false"); }
            });
        });

        // Clavier
        $(document).on("keydown", function(e) {
            if ($(".modal.show").length || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable) { return; }
            if (!$menu.prop("hidden")) { return; }
            var ctrl = e.ctrlKey || e.metaKey;
            var touche = e.key.toLowerCase();
            if (ctrl && touche === "z" && !e.shiftKey) { e.preventDefault(); Annuler(); return; }
            if (ctrl && (touche === "y" || (touche === "z" && e.shiftKey))) { e.preventDefault(); Retablir(); return; }
            if (!$("#pl_app")[0].contains(document.activeElement) && document.activeElement !== document.body) { return; }
            if (ctrl && touche === "c" && V.selection.size) { e.preventDefault(); Copier_selection(); return; }
            if (ctrl && touche === "v") {
                e.preventDefault();
                var ligne = M.lignes.find(function(l) { return l.cle === V.ligne_courante; });
                if (ligne) { Coller(ligne); } else { toastr.info("Cliquez d'abord sur une ligne pour indiquer où coller"); }
                return;
            }
            if (ctrl && touche === "d") { e.preventDefault(); Dupliquer_selection(); return; }
            if (ctrl && touche === "a") {
                e.preventDefault();
                var ids = [];
                M.lignes.forEach(function(l) { if (l.type === "l") { Ligne_evts(l).forEach(function(evt) { if (ids.indexOf(evt.id) < 0) { ids.push(evt.id); } }); } });
                Selectionner(ids, false);
                return;
            }
            if (e.key === "Delete" || e.key === "Backspace") { if (V.selection.size) { e.preventDefault(); Supprimer_selection(); } return; }
            if (e.key === "Escape") { if (V.selection.size) { Selectionner([], false); } return; }
            if (e.key === "Enter" && V.selection.size === 1) { e.preventDefault(); Ouvrir_evt(V.selection.values().next().value); return; }
            if (e.key === "Enter" && V.selection.size > 1) { e.preventDefault(); Ouvrir_lot(); return; }
            if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && V.selection.size) {
                e.preventDefault();
                var delta = (e.key === "ArrowLeft" ? -1 : 1) * V.pas;
                var evts = Selection_modifiable();
                if (e.shiftKey) { Modifier_evts("Modifier la durée", evts, function(evt) { evt.e += delta; }); }
                else { Modifier_evts("Déplacer", evts, function(evt) { evt.s += delta; evt.e += delta; if (evt.rs !== null) { evt.rs = null; evt.re = null; } }); }
                return;
            }
            if (e.key === "ContextMenu" || (e.shiftKey && e.key === "F10")) {
                if (V.selection.size) {
                    e.preventDefault();
                    var barre = $canvas.find(".pl-barre.sel")[0];
                    var rect = barre ? barre.getBoundingClientRect() : {left: 200, bottom: 200};
                    Minute_menu = null;
                    Menu_barres(rect.left + 10, rect.bottom + 4, null);
                }
            }
        });

        // Calendrier
        $("#pl_cal").on("click", ".pl-cal-jour", function(e) { Clic_calendrier(+this.getAttribute("data-jour"), e); });
        $("#pl_cal_prec, #pl_cal_suiv").on("click", function() {
            var sens = this.id === "pl_cal_prec" ? -1 : 1;
            var d = new Date(Date.UTC(V.mois_cal.a, V.mois_cal.m + sens, 1));
            V.mois_cal = {a: d.getUTCFullYear(), m: d.getUTCMonth()};
            Rendu_calendrier();
        });
        $("#pl_cal_effacer").on("click", function() { var j = Aujourdhui(); var i = Infos_jour(j); V.mois_cal = {a: i.a, m: i.m}; V.ancre_cal = j; Changer_dates([j]); });
        $("[data-raccourci]").on("click", function() { Raccourci_dates(this.getAttribute("data-raccourci")); });

        // Collaborateurs
        Init_ajout_collabs();
        $("#pl_collabs_ajout").on("select2:select", function(e) {
            var valeur = e.params.data.id, ajouts = [];
            if (valeur === "tous") { S.collabs.forEach(function(c) { ajouts.push(c.id); }); }
            else if (valeur.charAt(0) === "g") { var idg = +valeur.substr(1); S.collabs.forEach(function(c) { if (c.groupes.indexOf(idg) >= 0) { ajouts.push(c.id); } }); }
            else { ajouts.push(+valeur.substr(1)); }
            ajouts.forEach(function(id) { if (V.affiches.indexOf(id) < 0) { V.affiches.push(id); } V.masques.delete(id); });
            Apres_changement_collabs();
        });
        $("#pl_collabs_liste").on("click", "[data-collab-masquer]", function() {
            var id = +this.getAttribute("data-collab-masquer");
            if (V.masques.has(id)) { V.masques.delete(id); } else { V.masques.add(id); }
            Apres_changement_collabs();
        });
        $("#pl_collabs_liste").on("click", "[data-collab-retirer]", function() {
            var id = +this.getAttribute("data-collab-retirer");
            V.affiches = V.affiches.filter(function(x) { return x !== id; });
            V.masques.delete(id);
            Apres_changement_collabs();
        });
        $("#pl_collabs_tout_afficher").on("click", function() { V.masques.clear(); Apres_changement_collabs(); });
        $("#pl_collabs_vider").on("click", function() { V.affiches = []; V.masques.clear(); Apres_changement_collabs(); });

        // Filtres
        $("#pl_filtre_cats").on("change", "input", function() {
            var cochees = $("#pl_filtre_cats input:checked").map(function() { return +this.getAttribute("data-filtre-cat"); }).get();
            V.filtres.cats = cochees.length === S.cats.size ? new Set() : new Set(cochees.length ? cochees : [-1]);
            Rafraichir_tout(); Memoriser_affichage();
        });
        $("#pl_filtre_aff").on("change", function() { V.filtres.aff = this.value ? +this.value : null; Rafraichir_tout(); Memoriser_affichage(); });
        $("#pl_filtre_qualif").on("change", function() { V.filtres.qualif = this.value ? +this.value : null; Rafraichir_tout(); Memoriser_affichage(); });
        $("#pl_filtres_reinit").on("click", function() { V.filtres = {cats: new Set(), aff: null, qualif: null}; Rendu_filtres(); Rafraichir_tout(); Memoriser_affichage(); });
        $(".pl-acc-tete").on("click", function() {
            var code = this.getAttribute("data-panneau");
            V.panneau = V.panneau === code ? null : code;
            Rendu_accordeon();
            if (V.panneau === "collabs") { Init_ajout_collabs(); }
            Memoriser_affichage();
        });
        Rendu_accordeon();
        $("[data-legende]").on("click", function() { V.legende = this.getAttribute("data-legende"); Rendu_legende(); Memoriser_affichage(); });
        $("#pl_side_bascule").on("click", function() {
            var replie = !$("#pl_side").hasClass("replie");
            $("#pl_side").toggleClass("replie", replie);
            $(this).attr("aria-expanded", String(!replie));
        });
        if (window.innerWidth < 992) { $("#pl_side").addClass("replie"); $("#pl_side_bascule").attr("aria-expanded", "false"); }

        // Barre d'outils
        $("#pl_annuler").on("click", Annuler);
        $("#pl_retablir").on("click", Retablir);
        $("[data-mode]").on("click", function() { V.mode = this.getAttribute("data-mode"); V.bascules.clear(); $scroll[0].scrollTop = 0; Rafraichir_tout(); Memoriser_affichage(); });
        $("#pl_sous").on("change", function() { V.sous = this.value; Rafraichir_tout(); Memoriser_affichage(); });
        $("[data-vue]").on("click", function() { V.vue = this.getAttribute("data-vue"); Rafraichir_tout(); Memoriser_affichage(); });
        $("[data-densite]").on("click", function() { V.densite = this.getAttribute("data-densite"); Rafraichir_tout(); Memoriser_affichage(); });
        $("#pl_pas").on("change", function() { V.pas = +this.value; Memoriser_affichage(); });
        $("#pl_opt_titres").on("change", function() { V.titres = this.checked; Rafraichir_tout(); Memoriser_affichage(); });
        $("#pl_opt_affs").on("change", function() { V.affs = this.checked; Rafraichir_tout(); Memoriser_affichage(); });
        $("#pl_opt_realise").on("change", function() { V.realise = this.checked; Rafraichir_tout(); Memoriser_affichage(); });
        $("#pl_ajouter").on("click", function() {
            var ligne = M.lignes.find(function(l) { return l.cle === V.ligne_courante; }) || M.lignes.find(function(l) { return l.type === "l" && Est_modifiable(l.c); });
            var jour = ligne ? ligne.jour : (V.dates[0] || Aujourdhui());
            Ouvrir_evt(null, {c: ligne ? ligne.c : null, s: jour * 1440 + 540, e: jour * 1440 + 600, aff: ligne && ligne.aff !== undefined ? ligne.aff : null});
        });
        $("#pl_cat_defaut_btn").on("click", function(e) {
            e.stopPropagation();
            var $pop = $("#pl_cat_defaut_menu");
            var html = "<div class='pl-menu-titre'>Catégorie créée par cliquer-glisser</div>";
            S.cats.forEach(function(cat) {
                html += "<button type='button' data-cat-defaut='" + cat.id + "'><span class='pl-pastille' style='background:" + Echapper(cat.couleur) + "'></span>" + Echapper(cat.nom) +
                    (cat.id === V.cat_defaut ? "<i class='fa fa-check' style='margin-left:auto;color:inherit'></i>" : "") + "</button>";
            });
            $pop.html(html).prop("hidden", !$pop.prop("hidden"));
            if (!$pop.prop("hidden")) { Positionner_pop($pop); }
            $(this).attr("aria-expanded", String(!$pop.prop("hidden")));
        });
        $("#pl_cat_defaut_menu").on("click", "[data-cat-defaut]", function() {
            V.cat_defaut = +this.getAttribute("data-cat-defaut");
            $("#pl_cat_defaut_menu").prop("hidden", true);
            Maj_boutons(); Memoriser_affichage();
            toastr.info("Le cliquer-glisser crée maintenant : " + S.cats.get(V.cat_defaut).nom);
        });
        $("#pl_dupliquer").on("click", Dupliquer_selection);
        $("#pl_supprimer").on("click", Supprimer_selection);
        $("#pl_modele").on("click", function() { Ouvrir_lot_serveur("modele"); });
        $("#pl_copie").on("click", function() { Ouvrir_lot_serveur("copie"); });
        $("#pl_zoom_moins").on("click", function() { Zoomer(-1); });
        $("#pl_zoom_plus").on("click", function() { Zoomer(1); });
        $("#pl_plage_btn").on("click", function(e) { e.stopPropagation(); Ouvrir_plage(); });
        $("#pl_plage_appliquer").on("click", function() { Appliquer_plage(false); });
        $("#pl_plage_memoriser").on("click", function() { Appliquer_plage(true); });
        $("#pl_diffusion_btn").on("click", function(e) {
            e.stopPropagation();
            var $pop = $("#pl_diffusion_menu");
            $pop.prop("hidden", !$pop.prop("hidden"));
            $(this).attr("aria-expanded", String(!$pop.prop("hidden")));
        });
        $("#pl_diffusion_menu").on("click", "[data-diffusion]", function() { $("#pl_diffusion_menu").prop("hidden", true); Ouvrir_diffusion(this.getAttribute("data-diffusion")); });
        $("#pl_actualiser").on("click", Actualiser);
        $("#pl_plein_ecran").on("click", function() {
            var app = document.getElementById("pl_app");
            if (document.fullscreenElement) { document.exitFullscreen(); } else if (app.requestFullscreen) { app.requestFullscreen(); }
        });
        document.addEventListener("fullscreenchange", function() {
            $("#pl_plein_ecran i").toggleClass("fa-expand", !document.fullscreenElement).toggleClass("fa-compress", !!document.fullscreenElement);
            // Les menus et infobulles doivent être dans l'élément en plein écran pour rester visibles
            setTimeout(function() { Rafraichir_tout(); }, 100);
        });
        $("#pl_reglages_btn").on("click", Ouvrir_reglages);
        $("#pl_banniere").on("click", "[data-banniere]", function() {
            var action = this.getAttribute("data-banniere");
            if (action === "synthese") { V.vue = "synthese"; Memoriser_affichage(); }
            if (action === "deplier" || action === "replier") { M.groupes.forEach(function(g) { V.bascules.set(g.cle, action === "deplier"); }); }
            Rafraichir_tout();
        });

        // Avertissement si des modifications sont en cours d'enregistrement
        window.addEventListener("beforeunload", function(e) {
            if (envoi_en_cours || File_envoi.length) { e.preventDefault(); e.returnValue = ""; }
        });
    }

    // ------------------------------------------------------------------ Plage horaire
    function Positionner_pop($pop) {
        // Garde le panneau déroulant dans la fenêtre (il est aligné à gauche de son bouton par défaut)
        $pop.css({left: "0px", right: "auto"});
        var rect = $pop[0].getBoundingClientRect(), marge = 8;
        var decalage = 0;
        if (rect.right > window.innerWidth - marge) { decalage = window.innerWidth - marge - rect.right; }
        if (rect.left + decalage < marge) { decalage = marge - rect.left; }
        $pop.css("left", decalage + "px");
    }

    // Détail du remplissage d'une affectation
    function Fermer_detail_remplissage() {
        $("#pl_rpl_pop").remove();
        $(document).off(".plrpl");
        document.removeEventListener("scroll", Fermer_detail_remplissage, true);
    }
    function Ouvrir_detail_remplissage(bouton) {
        var deja = $("#pl_rpl_pop").data("bouton") === bouton;
        Fermer_detail_remplissage();
        if (deja) { return; }
        var jour = +bouton.getAttribute("data-jour"), aff = +bouton.getAttribute("data-aff");
        var ligne = {jour: jour, aff: aff, collabs: +bouton.getAttribute("data-collabs")};
        var liste = Remplissage_de(jour, aff) || [];
        var a = S.affs.get(aff) || {};
        var lignes = liste.map(function(item) {
            return "<tr class='" + Etat_remplissage(item) + "'><td><b>" + Echapper(item.a) + "</b> " + Echapper(item.n) + "</td><td><b>" + item.p + "</b></td><td>" + (item.c || "–") + "</td><td>" + (item.c ? item.c - item.p : "–") + "</td></tr>";
        }).join("");
        var enc = Encadrement(ligne, liste);
        var html = "<div id='pl_rpl_pop' class='pl-rpl-pop' role='dialog' aria-label='Consommations prévues'>" +
            "<div class='pl-rpl-pop-titre'>" + Echapper(a.nom || "") + " · " + Echapper(Texte_jour_long(jour)) + "</div>" +
            "<div class='pl-rpl-pop-sous'>" + (a.lien ? Echapper(a.lien) : "Cumul des sous-affectations liées") + "</div>" +
            "<table><thead><tr><th>Unité</th><th>Prévus</th><th>Places</th><th>Restantes</th></tr></thead><tbody>" + lignes + "</tbody></table>" +
            (enc ? "<div class='pl-rpl-pop-enc" + (enc.depasse ? " depasse" : "") + "'><i class='fa fa-users' aria-hidden='true'></i>Encadrement : " + enc.collabs + " collaborateur" + (enc.collabs > 1 ? "s" : "") +
                " pour " + enc.pic + " au pic, soit 1 pour " + (Math.round(enc.taux * 10) / 10).toString().replace(".", ",") +
                (enc.seuil ? " (maximum 1 pour " + enc.seuil + ")" : "") + "</div>" : "") +
            (CFG.urls.suivi_consommations ? "<a href='" + CFG.urls.suivi_consommations + "'>Ouvrir le suivi des consommations <i class='fa fa-angle-right' aria-hidden='true'></i></a>" : "") +
            "</div>";
        var $pop = $(html).appendTo("body").data("bouton", bouton);
        var r = bouton.getBoundingClientRect(), largeur = $pop.outerWidth(), hauteur = $pop.outerHeight();
        var gauche = Math.max(8, Math.min(r.left, window.innerWidth - largeur - 8));
        var haut = r.bottom + 6 + hauteur > window.innerHeight - 8 ? Math.max(8, r.top - hauteur - 6) : r.bottom + 6;
        $pop.css({left: gauche + "px", top: haut + "px"});
        setTimeout(function() {
            $(document).on("mousedown.plrpl", function(e) { if (!$(e.target).closest("#pl_rpl_pop, .pl-rpl").length) { Fermer_detail_remplissage(); } })
                       .on("keydown.plrpl", function(e) { if (e.key === "Escape") { Fermer_detail_remplissage(); bouton.focus(); } });
            $(window).one("resize.plrpl", Fermer_detail_remplissage);
            document.addEventListener("scroll", Fermer_detail_remplissage, true);
        }, 0);
    }

    function Zoomer(sens) {
        var debut = M.plage.debut, fin = M.plage.fin;
        if (sens > 0 && fin - debut > 180) { debut += 60; fin -= 60; }
        if (sens < 0) { debut = Math.max(0, debut - 60); fin = Math.min(1440, fin + 60); }
        V.plage = {auto: false, debut: debut, fin: fin};
        Rafraichir_tout();
        Memoriser_affichage();
    }

    function Ouvrir_plage() {
        var $pop = $("#pl_plage_pop");
        if (!$pop.prop("hidden")) { $pop.prop("hidden", true); return; }
        $("input[name='pl_plage_mode'][value='" + (V.plage.auto ? "auto" : "perso") + "']").prop("checked", true);
        $("#pl_plage_marge").val(R.plage_marge);
        $("#pl_plage_min").val(Math.round(R.plage_min / 60));
        $("#pl_plage_debut").val(Heure(M.plage.debut));
        $("#pl_plage_fin").val(M.plage.fin >= 1440 ? "23:59" : Heure(M.plage.fin));
        $pop.prop("hidden", false);
        Positionner_pop($pop);
        $("#pl_plage_btn").attr("aria-expanded", "true");
        $pop.find("input:checked").focus();
    }

    function Lire_heure(valeur) {
        if (!valeur) { return null; }
        var p = valeur.split(":");
        return +p[0] * 60 + +p[1];
    }

    function Appliquer_plage(memoriser) {
        var auto = $("input[name='pl_plage_mode']:checked").val() === "auto";
        var marge = Math.max(0, Math.min(240, +$("#pl_plage_marge").val() || 0));
        var plage_min = Math.max(1, Math.min(24, +$("#pl_plage_min").val() || 8)) * 60;
        var debut = Lire_heure($("#pl_plage_debut").val()), fin = Lire_heure($("#pl_plage_fin").val());
        if (fin === 1439) { fin = 1440; }
        if (!auto && (debut === null || fin === null || fin - debut < 60)) { toastr.warning("La plage horaire doit durer au moins une heure"); return; }
        S.reglages_user.plage_marge = marge;
        S.reglages_user.plage_min = plage_min;
        V.plage = auto ? {auto: true, debut: R.plage_debut, fin: R.plage_fin} : {auto: false, debut: debut, fin: fin};
        if (memoriser) {
            S.reglages_user.plage_auto = auto;
            if (!auto) { S.reglages_user.plage_debut = debut; S.reglages_user.plage_fin = fin; }
            Enregistrer_reglages("utilisateur", $.extend({}, R, S.reglages_user), true);
        }
        Reglages_effectifs();
        $("#pl_plage_pop").prop("hidden", true);
        $("#pl_plage_btn").attr("aria-expanded", "false");
        Rafraichir_tout();
        Memoriser_affichage();
    }

    // ------------------------------------------------------------------ Modale évènement
    var Evt_edite = null;      // {id: id ou null, base: évènement de départ}

    function Options_collabs(valeur, modifiables_seulement) {
        var html = "";
        var ids = V.affiches.slice();
        if (valeur && ids.indexOf(valeur) < 0) { ids.push(valeur); }
        S.collabs.forEach(function(c) { if (ids.indexOf(c.id) < 0) { ids.push(c.id); } });
        ids.forEach(function(id) {
            var c = S.collabs.get(id);
            if (!c || (modifiables_seulement && !c.modifiable && id !== valeur)) { return; }
            html += "<option value='" + id + "'" + (id === valeur ? " selected" : "") + ">" + Echapper(c.libelle) + "</option>";
        });
        return html;
    }
    function Options_categories(valeur, libelle_vide) {
        var html = libelle_vide ? "<option value=''>" + Echapper(libelle_vide) + "</option>" : "";
        S.cats.forEach(function(cat) {
            var type = cat.type === "ADDITION" ? "" : (cat.type === "SOUSTRACTION" ? " (temps soustrait)" : " (non comptabilisé)");
            html += "<option value='" + cat.id + "'" + (cat.id === valeur ? " selected" : "") + ">" + Echapper(cat.nom + type) + "</option>";
        });
        return html;
    }

    function Ouvrir_evt(id, valeurs) {
        Fermer_menu();
        var evt = id !== null ? S.evts.get(id) : null;
        if (id !== null && !evt) { return; }
        var base = evt ? Copie_evt(evt) : $.extend({id: null, c: null, cat: V.cat_defaut, aff: null, t: "", s: null, e: null, rs: null, re: null}, valeurs || {});
        if (!base.c) { var premier = Collabs_visibles().find(Est_modifiable); base.c = premier || null; }
        Evt_edite = {id: evt ? evt.id : null, base: base};
        var modifiable = evt ? Est_modifiable(evt.c) : true;
        $("#pl_modal_evt_titre strong").text(evt ? (modifiable ? "Modifier l'évènement" : "Détail de l'évènement") : "Nouvel évènement");
        $("#pl_evt_lecture").prop("hidden", modifiable);
        $("#pl_evt_collab").html(Options_collabs(base.c, true));
        $("#pl_evt_cat").html(Options_categories(base.cat));
        $("#pl_evt_aff").html(Options_affectations(base.aff, true));
        $("#pl_evt_collab, #pl_evt_cat, #pl_evt_aff").trigger("change.select2");
        $("#pl_evt_titre").val(base.t);
        var jour = Jour_de(base.s);
        $("#pl_evt_date").val(Iso_jour(jour));
        $("#pl_evt_debut").val(Heure(base.s));
        $("#pl_evt_fin").val(Heure(base.e));
        var multi_jours = Jour_de(base.e - 1) > jour + 1 || (Jour_de(base.e - 1) > jour && (base.e - base.s) > 1440);
        $("#pl_evt_date_fin_div").prop("hidden", !multi_jours);
        $("#pl_evt_date_fin").val(Iso_jour(Jour_de(base.e - 1)));
        $("#pl_evt_rdebut").val(base.rs !== null ? Heure(base.rs) : "");
        $("#pl_evt_rfin").val(base.re !== null ? Heure(base.re) : "");
        $("#pl_modal_evt").find("input, select").not(".select2-search__field").prop("disabled", !modifiable);
        $("#pl_evt_supprimer, #pl_evt_dupliquer").prop("hidden", !evt || !modifiable);
        $("#pl_evt_enregistrer, #pl_evt_realise_copier").prop("hidden", !modifiable);
        Maj_info_evt();
        $("#pl_modal_evt").modal("show");
    }

    function Lire_evt_modale() {
        var jour_txt = $("#pl_evt_date").val();
        var debut = Lire_heure($("#pl_evt_debut").val()), fin = Lire_heure($("#pl_evt_fin").val());
        if (!jour_txt || debut === null || fin === null) { return {erreur: "Renseignez la date et les heures de début et de fin"}; }
        var jour = Parse_jour(jour_txt);
        var s = jour * 1440 + debut, e;
        if (!$("#pl_evt_date_fin_div").prop("hidden") && $("#pl_evt_date_fin").val()) { e = Parse_jour($("#pl_evt_date_fin").val()) * 1440 + fin; }
        else { e = jour * 1440 + fin; if (e <= s) { e += 1440; } }
        if (e <= s) { return {erreur: "L'heure de fin doit être postérieure à l'heure de début"}; }
        var rd = Lire_heure($("#pl_evt_rdebut").val()), rf = Lire_heure($("#pl_evt_rfin").val());
        var rs = null, re = null;
        if (rd !== null || rf !== null) {
            if (rd === null || rf === null) { return {erreur: "Saisissez à la fois le début et la fin du réalisé"}; }
            rs = jour * 1440 + rd; re = jour * 1440 + rf;
            if (re <= rs) { re += 1440; }
        }
        var cat = +$("#pl_evt_cat").val(), c = +$("#pl_evt_collab").val();
        if (!cat) { return {erreur: "Sélectionnez une catégorie"}; }
        if (!c) { return {erreur: "Sélectionnez un collaborateur"}; }
        return {evt: {id: Evt_edite.id || 0, c: c, cat: cat, aff: $("#pl_evt_aff").val() ? +$("#pl_evt_aff").val() : null, t: $.trim($("#pl_evt_titre").val()), s: s, e: e, rs: rs, re: re}};
    }

    function Maj_info_evt() {
        var lu = Lire_evt_modale(), $info = $("#pl_evt_info");
        if (lu.erreur) { $info.attr("class", "pl-alerte attention").text(lu.erreur); return lu; }
        var evt = lu.evt, cat = S.cats.get(evt.cat);
        var conflits = Conflits(evt);
        var texte = "<strong>Durée : " + Duree(evt.e - evt.s) + "</strong>, " + (cat && cat.type === "ADDITION" ? "temps comptabilisé" : (cat && cat.type === "SOUSTRACTION" ? "temps soustrait" : "temps non comptabilisé")) + ".";
        if (evt.rs !== null) { texte += " Réalisé : " + Duree(evt.re - evt.rs) + " (écart " + ((evt.re - evt.rs) - (evt.e - evt.s) >= 0 ? "+" : "") + Duree((evt.re - evt.rs) - (evt.e - evt.s)) + ")."; }
        var contrat = Contrat_actif(evt.c, Jour_de(evt.s));
        if (contrat === false) { texte += " <br><i class='fa fa-exclamation-triangle'></i> Cette date est en dehors des contrats du collaborateur."; }
        if (conflits.length) {
            texte += "<br><i class='fa fa-exclamation-triangle'></i> Chevauchement avec " + conflits.map(function(c) { return Heure(c.s) + "–" + Heure(c.e); }).join(", ") + ".";
            $info.attr("class", "pl-alerte erreur").html(texte);
            lu.conflit = true;
        } else {
            $info.attr("class", "pl-alerte" + (contrat === false ? " attention" : "")).html(texte);
        }
        return lu;
    }

    function Enregistrer_evt(dupliquer) {
        var lu = Maj_info_evt();
        if (lu.erreur) { toastr.warning(lu.erreur); return; }
        if (!Est_modifiable(lu.evt.c)) { toastr.warning("Vous ne pouvez pas modifier le planning de ce collaborateur"); return; }
        if (dupliquer) {
            var copie = Emplacement_libre($.extend({}, lu.evt, {id: 0}), [0, lu.evt.e - lu.evt.s, 1440, 2880, 10080]);
            if (!copie) { toastr.warning("Aucun emplacement libre pour la copie"); return; }
            copie.id = Nouvel_id(); copie.v = 1;
            Valider("Dupliquer un évènement", [{type: "create", id: copie.id, apres: copie}]);
            $("#pl_modal_evt").modal("hide");
            Selectionner([Id_actuel(copie.id)], false);
            return;
        }
        if (lu.conflit) { toastr.warning("Cet évènement chevauche un autre évènement du collaborateur"); return; }
        V.cat_defaut = lu.evt.cat;
        if (Evt_edite.id === null) {
            var nouveau = $.extend(lu.evt, {id: Nouvel_id(), v: 1});
            Valider("Créer un évènement", [{type: "create", id: nouveau.id, apres: nouveau}]);
            Selectionner([Id_actuel(nouveau.id)], false);
        } else {
            var avant = S.evts.get(Evt_edite.id);
            if (!avant) { $("#pl_modal_evt").modal("hide"); return; }
            Valider("Modifier un évènement", [{type: "update", id: avant.id, avant: Copie_evt(avant), apres: $.extend(lu.evt, {id: avant.id})}]);
        }
        $("#pl_modal_evt").modal("hide");
        Memoriser_affichage();
    }

    // ------------------------------------------------------------------ Modification par lot
    function Ouvrir_lot(focus) {
        Fermer_menu();
        var evts = Selection_modifiable();
        if (!evts.length) { return; }
        $("#pl_lot_intro").text(evts.length + " évènement" + (evts.length > 1 ? "s" : "") + " sélectionné" + (evts.length > 1 ? "s" : "") + ". Seuls les champs renseignés seront modifiés.");
        $("#pl_lot_cat").html(Options_categories(null, "— Inchangée —"));
        $("#pl_lot_aff").html("<option value='inchange'>— Inchangée —</option>" + Options_affectations(null, true));
        $("#pl_lot_titre_coche").prop("checked", false);
        $("#pl_lot_titre").val("").prop("disabled", true);
        $("#pl_lot_decalage, #pl_lot_duree").val(0);
        $("#pl_modal_lot").modal("show");
        if (focus === "aff") { $("#pl_modal_lot").one("shown.bs.modal", function() { $("#pl_lot_aff").focus(); }); }
    }

    function Valider_lot() {
        var cat = $("#pl_lot_cat").val() ? +$("#pl_lot_cat").val() : null;
        var aff = $("#pl_lot_aff").val();
        var titre = $("#pl_lot_titre_coche").is(":checked") ? $.trim($("#pl_lot_titre").val()) : null;
        var decalage = Math.round(+$("#pl_lot_decalage").val() || 0), duree = Math.round(+$("#pl_lot_duree").val() || 0);
        var nbre = Modifier_evts("Modifier par lot", Selection_modifiable(), function(evt) {
            if (cat) { evt.cat = cat; }
            if (aff !== "inchange") { evt.aff = aff ? +aff : null; }
            if (titre !== null) { evt.t = titre; }
            if (decalage) { evt.s += decalage; evt.e += decalage; evt.rs = null; evt.re = null; }
            if (duree) { evt.e += duree; }
        });
        $("#pl_modal_lot").modal("hide");
        if (nbre) { toastr.success(nbre + " évènement" + (nbre > 1 ? "s modifiés" : " modifié")); }
    }

    // ------------------------------------------------------------------ Dupliquer vers d'autres dates ou collaborateurs
    var Dup_mode = "dates", Dup_dates_extra = [];
    function Ouvrir_dupliquer(mode) {
        Fermer_menu();
        var evts = Selection_modifiable();
        if (!evts.length) { return; }
        Dup_mode = mode; Dup_dates_extra = [];
        $("#pl_modal_dupliquer_titre strong").text(mode === "dates" ? "Dupliquer vers d'autres dates" : "Dupliquer vers d'autres collaborateurs");
        $("#pl_dup_intro").text(evts.length + " évènement" + (evts.length > 1 ? "s" : "") + " à dupliquer" + (mode === "dates" ? " en conservant les horaires." : " sur les mêmes dates et horaires."));
        $("#pl_dup_dates_div").prop("hidden", mode !== "dates");
        $("#pl_dup_collabs_div").prop("hidden", mode !== "collabs");
        var jours_sources = new Set(evts.map(function(evt) { return Jour_de(evt.s); }));
        $("#pl_dup_dates").html(V.dates.filter(function(j) { return !jours_sources.has(j); }).map(function(j) {
            return "<label><input type='checkbox' value='" + j + "'>" + Texte_jour_court(j) + "</label>";
        }).join("") || "<span class='pl-muted pl-petit'>Ajoutez des dates ci-dessous.</span>");
        var sources = new Set(evts.map(function(evt) { return evt.c; }));
        $("#pl_dup_collabs").html(Collabs_visibles().filter(function(c) { return !sources.has(c) && Est_modifiable(c); }).map(function(c) {
            return "<label><input type='checkbox' value='" + c + "'>" + Echapper(S.collabs.get(c).libelle) + "</label>";
        }).join("") || "<span class='pl-muted pl-petit'>Aucun autre collaborateur modifiable n'est affiché.</span>");
        $("#pl_modal_dupliquer").modal("show");
    }

    function Valider_dupliquer() {
        var evts = Selection_modifiable();
        var changements = [], echecs = 0, ajoutes = [];
        function Essayer(source, modifications) {
            var copie = $.extend(Copie_evt(source), modifications, {id: Nouvel_id(), rs: null, re: null, v: 1});
            if (Conflits(copie).length) { echecs++; return; }
            S.evts.set(copie.id, copie); Reindexer(); ajoutes.push(copie.id);
            changements.push({type: "create", id: copie.id, apres: Copie_evt(copie)});
        }
        var jours = [];
        if (Dup_mode === "dates") {
            jours = $("#pl_dup_dates input:checked").map(function() { return +this.value; }).get();
            if (!jours.length) { toastr.warning("Cochez au moins une date"); return; }
            evts.forEach(function(evt) {
                jours.forEach(function(j) { var decalage = (j - Jour_de(evt.s)) * 1440; if (decalage) { Essayer(evt, {s: evt.s + decalage, e: evt.e + decalage}); } });
            });
        } else {
            var collabs = $("#pl_dup_collabs input:checked").map(function() { return +this.value; }).get();
            if (!collabs.length) { toastr.warning("Cochez au moins un collaborateur"); return; }
            evts.forEach(function(evt) { collabs.forEach(function(c) { Essayer(evt, {c: c}); }); });
        }
        ajoutes.forEach(function(id) { S.evts.delete(id); });
        Reindexer();
        Valider("Dupliquer " + changements.length + " évènement" + (changements.length > 1 ? "s" : ""), changements);
        $("#pl_modal_dupliquer").modal("hide");
        toastr.success(changements.length + " copie" + (changements.length > 1 ? "s créées" : " créée") + (echecs ? " · " + echecs + " ignorée" + (echecs > 1 ? "s" : "") + " (chevauchement)" : ""));
        // Les dates ajoutées sont intégrées à l'affichage
        var nouvelles = jours.filter(function(j) { return V.dates.indexOf(j) < 0; });
        if (nouvelles.length) { Changer_dates(V.dates.concat(nouvelles)); }
    }

    // ------------------------------------------------------------------ Appliquer un modèle / copier une période (côté serveur)
    var LS_mode = "modele";
    function Ouvrir_lot_serveur(mode) {
        LS_mode = mode;
        var collabs = Collabs_visibles().filter(Est_modifiable);
        if (mode === "modele" && !S.modeles.length) {
            bootbox.alert("Aucun modèle de planning n'a été créé. Vous pouvez en créer dans le menu Paramétrage > Collaborateurs > Modèles de plannings.");
            return;
        }
        $("#pl_ls_titre").text(mode === "modele" ? "Appliquer un modèle de planning" : "Copier une période");
        $("#pl_ls_modele_div").prop("hidden", mode !== "modele");
        $("#pl_ls_copie_div").prop("hidden", mode !== "copie");
        $("#pl_ls_dates_div").prop("hidden", mode !== "modele");
        Frise_ls().reinitialiser();
        $("#pl_ls_dates_info").text(V.dates.length + " date" + (V.dates.length > 1 ? "s" : "") + (V.dates.length ? " (du " + Texte_jour_fr(V.dates[0]) + " au " + Texte_jour_fr(V.dates[V.dates.length - 1]) + ")" : ""));
        $("#pl_ls_periode_debut").val(V.dates.length ? Iso_jour(V.dates[0]) : "");
        $("#pl_ls_periode_fin").val(V.dates.length ? Iso_jour(V.dates[V.dates.length - 1]) : "");
        if (mode === "copie" && V.dates.length) {
            var debut = V.dates[0], fin = V.dates[V.dates.length - 1];
            $("#pl_ls_source_debut").val(Iso_jour(debut));
            $("#pl_ls_source_fin").val(Iso_jour(fin));
            var duree = fin - debut + 1;
            $("#pl_ls_destination").val(Iso_jour(debut + Math.ceil(duree / 7) * 7));
        }
        $("#pl_ls_collabs_info").text(collabs.length + " collaborateur" + (collabs.length > 1 ? "s" : "") + " modifiable" + (collabs.length > 1 ? "s" : ""));
        $("#pl_ls_collabs_choix").html(collabs.map(function(c) { return "<label><input type='checkbox' value='" + c + "' checked>" + Echapper(S.collabs.get(c).libelle) + "</label>"; }).join("")).prop("hidden", true);
        $("input[name='pl_ls_collabs'][value='affiches']").prop("checked", true);
        $("input[name='pl_ls_dates'][value='selection']").prop("checked", true);
        $("input[name='pl_ls_conflit'][value='ignorer']").prop("checked", true);
        $("#pl_ls_apercu").prop("hidden", true).empty();
        $("#pl_ls_valider").html("<i class='fa fa-check margin-r-5'></i>" + (mode === "modele" ? "Appliquer" : "Copier"));
        if (mode === "modele") { Selecteur_ls().reinitialiser(); }
        $("#pl_modal_lot_serveur").modal("show");
    }

    var selecteur_ls = null;
    function Collabs_lot_serveur() {
        return $("input[name='pl_ls_collabs']:checked").val() === "choix"
            ? $("#pl_ls_collabs_choix input:checked").map(function() { return +this.value; }).get()
            : Collabs_visibles().filter(Est_modifiable);
    }
    function Selecteur_ls() {
        if (!selecteur_ls) {
            selecteur_ls = SelecteurModelesPlanning({conteneur: "#pl_ls_modeles", url: CFG.urls.liste_modeles, csrf: CFG.csrf, parametres: function() {
                var jours = Jours_lot_serveur();
                return {collaborateurs: Collabs_lot_serveur(), date: jours.erreur ? "" : Iso_jour(jours[0])};
            }, change: function() { $("#pl_ls_apercu").prop("hidden", true); Frise_ls().maj(); }});
        }
        return selecteur_ls;
    }

    var frise_ls = null;
    function Frise_ls() {
        if (!frise_ls) {
            frise_ls = FriseModelesPlanning({conteneur: "#pl_ls_frise", url: CFG.urls.frise, csrf: CFG.csrf, parametres: function() {
                if (LS_mode !== "modele") { return null; }
                var jours = Jours_lot_serveur();
                if (jours.erreur) { return null; }
                return {modeles: Selecteur_ls().selection(), dates: jours.map(Iso_jour)};
            }, change: function() { $("#pl_ls_apercu").prop("hidden", true); }});
        }
        return frise_ls;
    }

    function Jours_lot_serveur() {
        var jours = V.dates.slice();
        if ($("input[name='pl_ls_dates']:checked").val() === "periode") {
            var d = $("#pl_ls_periode_debut").val(), f = $("#pl_ls_periode_fin").val();
            if (!d || !f || f < d) { return {erreur: "Période incorrecte"}; }
            jours = [];
            for (var j = Parse_jour(d); j <= Parse_jour(f); j++) { jours.push(j); }
        }
        if (!jours.length) { return {erreur: "Aucune date sélectionnée"}; }
        if (jours.length > 400) { return {erreur: "La période ne peut pas dépasser 400 jours"}; }
        return jours;
    }

    function Parametres_lot_serveur() {
        var collabs = $("input[name='pl_ls_collabs']:checked").val() === "choix"
            ? $("#pl_ls_collabs_choix input:checked").map(function() { return +this.value; }).get()
            : Collabs_visibles().filter(Est_modifiable);
        if (!collabs.length) { return {erreur: "Aucun collaborateur modifiable sélectionné"}; }
        var p = {collaborateurs: JSON.stringify(collabs), conflit: $("input[name='pl_ls_conflit']:checked").val()};
        if (LS_mode === "modele") {
            var modeles = Selecteur_ls().selection();
            if (!modeles.length) { return {erreur: "Cochez au moins un modèle"}; }
            var jours = Jours_lot_serveur();
            if (jours.erreur) { return jours; }
            p.modeles = JSON.stringify(modeles);
            p.departs = JSON.stringify(Frise_ls().departs());
            p.forcer = Selecteur_ls().forcer() ? "true" : "false";
            p.dates = JSON.stringify(jours.map(Iso_jour));
            p.jours = jours;
        } else {
            p.source_debut = $("#pl_ls_source_debut").val();
            p.source_fin = $("#pl_ls_source_fin").val();
            p.destination_debut = $("#pl_ls_destination").val();
            if (!p.source_debut || !p.source_fin || !p.destination_debut || p.source_fin < p.source_debut) { return {erreur: "Renseignez la période à copier et la date de destination"}; }
            var debut_dest = Parse_jour(p.destination_debut), duree = Parse_jour(p.source_fin) - Parse_jour(p.source_debut);
            p.jours = [];
            for (var k = 0; k <= duree; k++) { p.jours.push(debut_dest + k); }
        }
        return p;
    }

    function Executer_lot_serveur(apercu) {
        var p = Parametres_lot_serveur();
        if (p.erreur) { toastr.warning(p.erreur); return; }
        var jours = p.jours;
        delete p.jours;
        p.apercu = apercu ? "true" : "false";
        var $bouton = apercu ? $("#pl_ls_btn_apercu") : $("#pl_ls_valider");
        $bouton.prop("disabled", true);
        Ajax(LS_mode === "modele" ? CFG.urls.modele : CFG.urls.copie, p).done(function(data) {
            var texte = "<strong>" + data.nbre_crees + " évènement" + (data.nbre_crees > 1 ? "s" : "") + (apercu ? " seront créés" : " créé" + (data.nbre_crees > 1 ? "s" : "")) + "</strong>";
            if (data.nbre_supprimes) { texte += ", " + data.nbre_supprimes + " évènement" + (data.nbre_supprimes > 1 ? "s" : "") + " existant" + (data.nbre_supprimes > 1 ? "s" : "") + (apercu ? " seront supprimés" : " supprimé" + (data.nbre_supprimes > 1 ? "s" : "")); }
            if (data.nbre_ignores) { texte += ", " + data.nbre_ignores + " ignoré" + (data.nbre_ignores > 1 ? "s" : "") + " (chevauchement)"; }
            if (data.nbre_hors_contrat) { texte += ", " + data.nbre_hors_contrat + " hors contrat"; }
            texte += ".";
            (data.messages_restriction || []).forEach(function(message) { texte += "<br><i class='fa fa-exclamation-triangle margin-r-5'></i>" + Echapper(message) + "."; });
            if (apercu) {
                $("#pl_ls_apercu").html(texte + " L'opération pourra être annulée (Ctrl+Z).").attr("class", "pl-alerte mt-3" + (data.nbre_supprimes ? " attention" : "")).prop("hidden", false);
                return;
            }
            // Mise à jour locale et ajout dans l'historique d'annulation (déjà enregistré côté serveur)
            var changements = [];
            data.supprimes.forEach(function(e) {
                var evt = Evt_depuis_serveur(e);
                changements.push({type: "delete", id: evt.id, avant: evt});
                S.evts.delete(evt.id);
            });
            data.crees.forEach(function(e) {
                var evt = Evt_depuis_serveur(e);
                changements.push({type: "create", id: evt.id, apres: evt});
                S.evts.set(evt.id, evt);
                Versions.set(evt.id, evt.v);
            });
            Reindexer();
            Valider(LS_mode === "modele" ? "Appliquer un modèle de planning" : "Copier une période", changements, true);
            $("#pl_modal_lot_serveur").modal("hide");
            toastr.success(texte.replace(/<[^>]+>/g, ""));
            if (LS_mode === "copie") {
                var nouvelles = jours.filter(function(j) { return V.dates.indexOf(j) < 0; });
                if (nouvelles.length && V.dates.length + nouvelles.length <= 62) {
                    bootbox.confirm({message: "Afficher aussi les dates de destination de la copie ?", buttons: {confirm: {label: "Afficher"}, cancel: {label: "Non"}},
                        callback: function(ok) { if (ok) { Changer_dates(V.dates.concat(nouvelles)); } }});
                }
            }
        }).fail(function(xhr) {
            toastr.error(Message_erreur(xhr));
        }).always(function() { $bouton.prop("disabled", false); });
    }

    // ------------------------------------------------------------------ Notes
    var Note_jour = null;
    function Ouvrir_note(jour, aff) {
        Fermer_menu();
        Note_jour = jour;
        $("#pl_note_date").text(Texte_jour_long(jour));
        $("#pl_note_aff").html(Options_affectations(aff || null, true, "Toute la journée (note générale)")).val(aff ? String(aff) : "");
        Maj_modale_note();
        $("#pl_modal_note").modal("show");
        $("#pl_modal_note").one("shown.bs.modal", function() { $("#pl_note_texte").focus(); });
    }
    function Maj_modale_note() {
        var aff = $("#pl_note_aff").val() ? +$("#pl_note_aff").val() : null;
        var texte = Note_de(Note_jour, aff);
        $("#pl_note_texte").val(texte);
        $("#pl_note_supprimer").prop("hidden", !texte);
        var autres = Notes_du_jour(Note_jour).filter(function(n) { return n.aff !== aff; });
        $("#pl_note_autres").html(autres.length ? "<strong>Autres notes de la journée :</strong><br>" + autres.map(function(n) {
            return Echapper((n.aff ? Chemin_aff(n.aff, true) : "Générale") + " : " + n.texte.split("\n")[0]);
        }).join("<br>") : "").prop("hidden", !autres.length);
    }

    function Enregistrer_note(texte) {
        var aff = $("#pl_note_aff").val() ? +$("#pl_note_aff").val() : null;
        Ajax(CFG.urls.note, {date: Iso_jour(Note_jour), affectation: aff || "", texte: texte}).done(function(data) {
            if (data.texte) { S.notes.set(Cle_note(Note_jour, aff), data.texte); } else { S.notes.delete(Cle_note(Note_jour, aff)); }
            $("#pl_modal_note").modal("hide");
            Rafraichir_tout();
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Diffusion (PDF, emails, Excel)
    var Diff_action = "imprimer";
    // Options proposées pour chaque type de document
    var DIFF_OPTIONS = {
        individuel: ["affs", "realise"], calendrier: [], equipe: ["affs", "notes"], frise: ["grouper", "notes"],
        affectation: ["realise", "notes"], emargement: ["affs", "notes"], recapitulatif: []
    };
    var DIFF_TYPES_EMAIL = ["individuel", "calendrier"];
    var DIFF_INTROS = {
        imprimer: "Choisissez le document à générer pour les dates sélectionnées.",
        email: "Chaque collaborateur recevra son document en PDF. Le message pourra être relu dans l'éditeur d'emails avant l'envoi.",
        excel: "Le fichier contient le récapitulatif des heures par collaborateur (planifié, réalisé, contrat, dimanches, fériés, nuit) et le détail des évènements."
    };
    function Ouvrir_diffusion(action) {
        if (!V.dates.length) { toastr.warning("Sélectionnez d'abord des dates"); return; }
        Diff_action = action;
        var titres = {imprimer: "Imprimer le planning", email: "Envoyer le planning par email", excel: "Récapitulatif des heures (Excel)"};
        $("#pl_diff_titre").text(titres[action]);
        $("#pl_diff_intro").text(DIFF_INTROS[action] + " Période : " + (V.dates.length > 1 ? "du " + Texte_jour_fr(V.dates[0]) + " au " + Texte_jour_fr(V.dates[V.dates.length - 1]) : Texte_jour_long(V.dates[0])) + ".");
        $("#pl_diff_types_bloc").prop("hidden", action === "excel");
        $("#pl_modal_diffusion .pl-type-doc").each(function() {
            this.hidden = action === "email" && DIFF_TYPES_EMAIL.indexOf(this.getAttribute("data-type")) < 0;
        });
        var $coche = $("input[name='pl_diff_type']:checked");
        if (!$coche.length || $coche.closest(".pl-type-doc").prop("hidden")) { $("input[name='pl_diff_type'][value='individuel']").prop("checked", true); }
        var visibles = Collabs_visibles();
        $("#pl_diff_collabs_info").text(visibles.length + " collaborateur" + (visibles.length > 1 ? "s" : ""));
        var sel = Collabs_selection();
        $("#pl_diff_sel_info").text(sel.length ? sel.length + " collaborateur" + (sel.length > 1 ? "s" : "") : "Aucun évènement sélectionné");
        $("input[name='pl_diff_collabs'][value='selection']").prop("disabled", !sel.length);
        $("input[name='pl_diff_collabs'][value='affiches']").prop("checked", true);
        $("#pl_diff_realise").prop("checked", V.realise);
        $("#pl_diff_grouper").prop("checked", V.sous === "aff");
        Maj_options_diffusion();
        $("#pl_modal_diffusion").modal("show");
    }
    function Type_diffusion() {
        return Diff_action === "excel" ? null : ($("input[name='pl_diff_type']:checked").val() || "individuel");
    }
    function Maj_options_diffusion() {
        var type = Type_diffusion();
        var options = type ? DIFF_OPTIONS[type] : [];
        $("#pl_diff_options [data-option]").each(function() { this.hidden = options.indexOf(this.getAttribute("data-option")) < 0; });
        $("#pl_diff_options").prop("hidden", Diff_action === "excel");
        $("#pl_diff_sans_option").prop("hidden", options.length > 0);
        // Avertissement sur le volume de pages
        var avert = "";
        if ((type === "frise" || type === "emargement") && V.dates.length > 7) {
            avert = "Ce document comporte une page par jour : " + V.dates.length + " pages seront générées.";
        }
        $("#pl_diff_avert").text(avert).prop("hidden", !avert);
    }
    function Collabs_selection() {
        var ids = [];
        V.selection.forEach(function(id) { var evt = S.evts.get(id); if (evt && ids.indexOf(evt.c) < 0) { ids.push(evt.c); } });
        return ids;
    }
    function Valider_diffusion() {
        var collabs = $("input[name='pl_diff_collabs']:checked").val() === "selection" ? Collabs_selection() : Collabs_visibles();
        if (!collabs.length) { toastr.warning("Aucun collaborateur"); return; }
        var coche = function(id) { return $(id).is(":checked") ? "true" : "false"; };
        var donnees = {dates: JSON.stringify(V.dates.map(Iso_jour)), collaborateurs: JSON.stringify(collabs), type: Type_diffusion() || "individuel",
                       afficher_realise: coche("#pl_diff_realise"), afficher_affectations: coche("#pl_diff_affs"),
                       afficher_notes: coche("#pl_diff_notes"), grouper_affectations: coche("#pl_diff_grouper")};
        var url = {imprimer: CFG.urls.imprimer, email: CFG.urls.emails, excel: CFG.urls.excel}[Diff_action];
        var $bouton = $("#pl_diff_valider").prop("disabled", true).html("<i class='fa fa-spinner fa-spin margin-r-5'></i>Génération…");
        Ajax(url, donnees).done(function(data) {
            $("#pl_modal_diffusion").modal("hide");
            if (Diff_action === "imprimer") { charge_pdf(data); }
            if (Diff_action === "excel") { window.location = data.url; }
            if (Diff_action === "email") {
                if (data.sans_adresse && data.sans_adresse.length) { toastr.warning("Sans adresse email : " + data.sans_adresse.join(", ")); }
                window.location = data.url;
            }
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); })
          .always(function() { $bouton.prop("disabled", false).html("<i class='fa fa-check margin-r-5'></i>Valider"); });
    }

    // ------------------------------------------------------------------ Lien iCal
    var Ical_collab = null;
    function Ouvrir_ical(c) {
        Ical_collab = c;
        $("#pl_ical_intro").text("Abonnez l'agenda de " + S.collabs.get(c).libelle + " (Google Agenda, Outlook, téléphone…) avec ce lien. Les évènements s'y mettent à jour automatiquement.");
        Action_ical("obtenir", true);
    }
    function Action_ical(action, ouvrir) {
        Ajax(CFG.urls.ical, {idcollaborateur: Ical_collab, action: action}).done(function(data) {
            if (!data.url) { $("#pl_modal_ical").modal("hide"); toastr.success("Le lien d'agenda a été désactivé"); return; }
            $("#pl_ical_url").val(data.url);
            if (ouvrir) { $("#pl_modal_ical").modal("show"); }
            if (action === "regenerer") { toastr.success("Nouveau lien généré : l'ancien ne fonctionne plus"); }
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Réglages
    var Reglages_portee = "utilisateur";
    function Ouvrir_reglages() {
        $("#pl_modal_reglages [data-reglage]").each(function() {
            var nom = this.getAttribute("data-reglage");
            if (this.type === "checkbox") { this.checked = !!R[nom]; } else { $(this).val(R[nom]); }
        });
        Reglages_portee = "utilisateur";
        $("#pl_reglages_portee").prop("hidden", !S.peut_regler_tous);
        $("[data-portee]").each(function() { $(this).attr("aria-checked", String(this.getAttribute("data-portee") === Reglages_portee)); });
        $("#pl_modal_reglages").modal("show");
    }
    function Lire_reglages() {
        var reglages = {};
        $("#pl_modal_reglages [data-reglage]").each(function() {
            var nom = this.getAttribute("data-reglage");
            if (this.type === "checkbox") { reglages[nom] = this.checked; }
            else if (this.type === "number") { reglages[nom] = +this.value; }
            else { reglages[nom] = this.value; }
        });
        return reglages;
    }
    function Enregistrer_reglages(portee, reglages, silencieux) {
        return Ajax(CFG.urls.reglages, {portee: portee, reglages: JSON.stringify(reglages)}).done(function(data) {
            S.reglages_defaut = data.reglages.defaut;
            S.reglages_user = data.reglages.utilisateur;
            Reglages_effectifs();
            if (!silencieux) { toastr.success(portee === "tous" ? "Réglages enregistrés pour tous les utilisateurs" : (portee === "reinitialiser" ? "Réglages par défaut rétablis" : "Réglages enregistrés")); }
            Rafraichir_tout();
        }).fail(function(xhr) { toastr.error(Message_erreur(xhr)); });
    }

    // ------------------------------------------------------------------ Vue synthèse
    function Rendu_synthese() {
        var collabs = Collabs_visibles(), dates = V.dates;
        if (!collabs.length || !dates.length) {
            $synthese.html("<div class='pl-vide'>" + (!collabs.length ? "Aucun collaborateur affiché." : "Sélectionnez des dates dans le calendrier.") + "</div>");
            return;
        }
        var html = "<table role='grid' aria-label='Synthèse des heures'><thead><tr><th scope='col' class='pl-sy-nom'>Collaborateur</th>";
        dates.forEach(function(j, i) {
            var classes = [];
            if (Jour_semaine(j) === 0 && i) { classes.push("lundi"); }
            if (Jour_semaine(j) >= 5) { classes.push("we"); }
            if (S.feries.has(j)) { classes.push("ferie"); }
            else if (Vacances_de(j)) { classes.push("vacances"); }
            html += "<th scope='col' class='" + classes.join(" ") + "' title='" + Echapper(Texte_jour_long(j) + (S.feries.has(j) ? " – " + S.feries.get(j) : (Vacances_de(j) ? " – " + Vacances_de(j).nom : ""))) + "'><small>" + "LMMJVSD".charAt(Jour_semaine(j)) + "</small>" + Infos_jour(j).j + "</th>";
        });
        html += "<th scope='col' class='pl-sy-total'>Total</th></tr></thead><tbody>";
        var totaux_jours = dates.map(function() { return 0; }), total_general = 0, attendu_general = 0;
        collabs.forEach(function(c) {
            var collab = S.collabs.get(c), total = 0;
            html += "<tr><th scope='row' class='pl-sy-nom'><span style='display:flex;align-items:center;gap:8px'>" + Html_avatar(c, true) + Echapper(collab.libelle) + "</span></th>";
            dates.forEach(function(j, i) {
                var evts = Evts_visibles(c, j);
                var minutes = Total_minutes(evts, j);
                total += minutes; totaux_jours[i] += minutes;
                var classes = ["pl-sy-cell"];
                if (Jour_semaine(j) === 0 && i) { classes.push("lundi"); }
                if (Jour_semaine(j) >= 5) { classes.push("we"); }
                if (Contrat_actif(c, j) === false) { classes.push("hors-contrat"); }
                var contenu = "", style = "";
                if (minutes) {
                    var par_cat = new Map();
                    evts.forEach(function(evt) { if (Signe_categorie(evt.cat) > 0) { par_cat.set(evt.cat, (par_cat.get(evt.cat) || 0) + Minutes_dans_jour(evt, j)); } });
                    var pile = "";
                    par_cat.forEach(function(m, cat) { pile += "<span style='flex:" + m + " 1 0;background:" + Echapper(S.cats.get(cat).couleur) + "'></span>"; });
                    contenu = Duree_decimale(minutes) + "<span class='pl-sy-pile'>" + pile + "</span>";
                    style = "background-color:rgba(var(--pl-primaire-rgb)," + (Math.min(600, Math.max(0, minutes)) / 600 * 0.16).toFixed(3) + ")";
                } else if (evts.length) {
                    // Journée sans temps comptabilisé (congés...) : initiales de la catégorie principale
                    var dominante = evts.reduce(function(a, b) { return Minutes_dans_jour(b, j) > Minutes_dans_jour(a, j) ? b : a; });
                    var cat = S.cats.get(dominante.cat);
                    contenu = "<span style='color:" + Echapper(cat.couleur) + "'>" + Echapper(cat.nom.substr(0, 2).toUpperCase()) + "</span>";
                }
                html += "<td class='" + classes.join(" ") + "' style='" + style + "' data-c='" + c + "' data-jour='" + j + "' tabindex='-1'>" + contenu + "</td>";
            });
            var attendu = Minutes_attendues(c, dates);
            total_general += total; attendu_general += attendu;
            var ecart = attendu ? total - attendu : 0;
            html += "<td class='pl-sy-total'>" + Duree(total) + (attendu ? "<small>contrat " + Duree(attendu) + " · " + (ecart > 0 ? "+" : "") + Duree(ecart) + "</small>" : "") + "</td></tr>";
        });
        html += "</tbody><tfoot><tr><th scope='row' class='pl-sy-nom'>Total jour</th>";
        dates.forEach(function(j, i) {
            html += "<td class='" + (Jour_semaine(j) === 0 && i ? "lundi" : "") + "'>" + (totaux_jours[i] ? Duree_decimale(totaux_jours[i]) : "") + "</td>";
        });
        html += "<td class='pl-sy-total'>" + Duree(total_general) + (attendu_general ? "<small>contrats " + Duree(attendu_general) + "</small>" : "") + "</td></tr></tfoot></table>";
        $synthese.html(html);
    }

    var $sy_pop = null;
    function Ouvrir_cellule_synthese(cellule) {
        if ($sy_pop) { $sy_pop.remove(); }
        var c = +cellule.getAttribute("data-c"), j = +cellule.getAttribute("data-jour");
        $synthese.find(".pl-sy-cell.sel").removeClass("sel");
        cellule.classList.add("sel");
        var evts = Evts_visibles(c, j);
        var html = "<h3>" + Echapper(S.collabs.get(c).libelle) + " · " + Texte_jour_court(j) + "</h3>";
        if (!evts.length) { html += "<p class='pl-muted pl-petit' style='margin:0'>Aucun évènement.</p>"; }
        evts.forEach(function(evt) {
            var cat = S.cats.get(evt.cat) || {nom: "", couleur: "#999"};
            html += "<div class='pl-sy-evt'><span class='pl-pastille' style='background:" + Echapper(cat.couleur) + "'></span><span>" + Heure(evt.s) + "–" + Heure(evt.e) + "</span>" +
                "<span>" + Echapper(cat.nom + (evt.t ? " · " + evt.t : "") + (evt.aff ? " · " + Chemin_aff(evt.aff, true) : "")) + "</span></div>";
        });
        html += "<div class='pl-sy-pop-actions'><button type='button' class='pl-btn pl-btn-sm' data-sy='frise'><i class='fa fa-align-left'></i>Ouvrir en frise</button>" +
            (Est_modifiable(c) ? "<button type='button' class='pl-btn pl-btn-sm' data-sy='ajouter'><i class='fa fa-plus'></i>Ajouter</button>" : "") + "</div>";
        $sy_pop = $("<div class='pl-sy-pop' role='dialog'></div>").html(html).appendTo("#pl_app");
        var rect = cellule.getBoundingClientRect();
        $sy_pop.css({left: Math.min(window.innerWidth - 300, rect.left) + "px", top: Math.min(window.innerHeight - $sy_pop.outerHeight() - 8, rect.bottom + 6) + "px"});
        $sy_pop.on("click", "[data-sy]", function() {
            var action = this.getAttribute("data-sy");
            $sy_pop.remove(); $sy_pop = null;
            if (action === "frise") { V.vue = "frise"; Changer_dates([j]); Memoriser_affichage(); }
            if (action === "ajouter") { Ouvrir_evt(null, {c: c, s: j * 1440 + 540, e: j * 1440 + 600}); }
        });
    }

    // ------------------------------------------------------------------ Select2 de la modale évènement
    function Html_pastille(couleur) {
        return "<span class='pl-s2-pastille' style='background:" + Echapper(couleur || "#94a3b8") + "' aria-hidden='true'></span>";
    }
    function Init_select2_evt() {
        var $modal = $("#pl_modal_evt");
        var options = {language: "fr", width: "100%", theme: "bootstrap4", dropdownParent: $modal, escapeMarkup: function(m) { return m; }};
        function Texte(d) { return Echapper($.trim(d.text)); }

        // Collaborateur : avatar + nom
        function Rendu_collab(d) {
            if (!d.id) { return Texte(d); }
            return "<span class='pl-s2-ligne'>" + Html_avatar(+d.id, true) + "<span>" + Texte(d) + "</span></span>";
        }
        $("#pl_evt_collab").select2($.extend({}, options, {templateResult: Rendu_collab, templateSelection: Rendu_collab}));

        // Catégorie : pastille de couleur
        function Rendu_cat(d) {
            if (!d.id) { return Texte(d); }
            var cat = S.cats.get(+d.id);
            return "<span class='pl-s2-ligne'>" + Html_pastille(cat && cat.couleur) + "<span>" + Texte(d) + "</span></span>";
        }
        $("#pl_evt_cat").select2($.extend({}, options, {templateResult: Rendu_cat, templateSelection: Rendu_cat}));

        // Affectation : arborescence indentée dans la liste + pastille, effaçable
        function Rendu_aff(d, dans_liste) {
            if (!d.id) { return Texte(d); }
            var aff = S.affs.get(+d.id);
            var niveau = dans_liste && d.element ? (+$(d.element).data("niveau") || 0) : 0;
            return "<span class='pl-s2-ligne' style='padding-left:" + (niveau * 1.1) + "em'>" + Html_pastille(aff && aff.couleur) + "<span>" + Texte(d) + "</span></span>";
        }
        $("#pl_evt_aff").select2($.extend({}, options, {
            placeholder: "Aucune affectation", allowClear: true,
            templateResult: function(d) { return Rendu_aff(d, true); },
            templateSelection: function(d) { return Rendu_aff(d, false); }
        }));

        // Échap dans la liste déroulante : fermer la liste sans fermer la modale
        $("#pl_evt_collab, #pl_evt_cat, #pl_evt_aff").each(function() {
            $(this).data("select2").$dropdown.on("keydown", function(e) { if (e.key === "Escape") { e.stopPropagation(); } });
        });
    }

    function Brancher_modales() {
        Init_select2_evt();
        $("#pl_modal_evt").on("change input", "input, select", Debounce(Maj_info_evt, 120));
        $("#pl_evt_enregistrer").on("click", function() { Enregistrer_evt(false); });
        $("#pl_evt_dupliquer").on("click", function() { Enregistrer_evt(true); });
        $("#pl_evt_supprimer").on("click", function() {
            var evt = S.evts.get(Evt_edite.id);
            if (evt) { Valider("Supprimer un évènement", [{type: "delete", id: evt.id, avant: Copie_evt(evt)}]); }
            $("#pl_modal_evt").modal("hide");
        });
        $("#pl_evt_realise_copier").on("click", function() { $("#pl_evt_rdebut").val($("#pl_evt_debut").val()); $("#pl_evt_rfin").val($("#pl_evt_fin").val()); Maj_info_evt(); });
        $("#pl_modal_evt").on("keydown", function(e) { if (e.key === "Enter" && !$(e.target).closest(".select2-container").length && e.target.tagName !== "TEXTAREA" && e.target.tagName !== "BUTTON") { e.preventDefault(); Enregistrer_evt(false); } });

        $("#pl_lot_titre_coche").on("change", function() { $("#pl_lot_titre").prop("disabled", !this.checked); if (this.checked) { $("#pl_lot_titre").focus(); } });
        $("#pl_lot_valider").on("click", Valider_lot);

        $("#pl_dup_date_ajouter").on("click", function() {
            var valeur = $("#pl_dup_date_autre").val();
            if (!valeur) { return; }
            var j = Parse_jour(valeur);
            if (Dup_dates_extra.indexOf(j) < 0 && V.dates.indexOf(j) < 0) {
                Dup_dates_extra.push(j);
                $("#pl_dup_dates .pl-muted").remove();
                $("#pl_dup_dates").append("<label><input type='checkbox' value='" + j + "' checked>" + Texte_jour_court(j) + "</label>");
            }
            $("#pl_dup_date_autre").val("");
        });
        $("#pl_dup_valider").on("click", Valider_dupliquer);

        $("input[name='pl_ls_collabs']").on("change", function() { $("#pl_ls_collabs_choix").prop("hidden", this.value !== "choix"); });
        $("#pl_modal_lot_serveur").on("change", "input", function() { $("#pl_ls_apercu").prop("hidden", true); });
        $("#pl_modal_lot_serveur").on("change", "input[name='pl_ls_dates'], #pl_ls_periode_debut, #pl_ls_periode_fin", function() { if (LS_mode === "modele") { Frise_ls().maj(); Selecteur_ls().maj(); } });
        $("#pl_modal_lot_serveur").on("change", "input[name='pl_ls_collabs'], #pl_ls_collabs_choix input", function() { if (LS_mode === "modele") { Selecteur_ls().maj(); } });
        $("#pl_ls_btn_apercu").on("click", function() { Executer_lot_serveur(true); });
        $("#pl_ls_valider").on("click", function() { Executer_lot_serveur(false); });

        $("#pl_note_valider").on("click", function() { Enregistrer_note($.trim($("#pl_note_texte").val())); });
        $("#pl_note_supprimer").on("click", function() { Enregistrer_note(""); });
        $("#pl_note_aff").on("change", Maj_modale_note);

        $("#pl_diff_valider").on("click", Valider_diffusion);
        $("#pl_modal_diffusion").on("change", "input[name='pl_diff_type']", Maj_options_diffusion);
        $("#pl_modal_diffusion").on("dblclick", ".pl-type-doc", Valider_diffusion);

        $("#pl_ical_copier").on("click", function() {
            var champ = document.getElementById("pl_ical_url");
            champ.select();
            (navigator.clipboard ? navigator.clipboard.writeText(champ.value) : $.Deferred().resolve(document.execCommand("copy"))).then(function() { toastr.success("Lien copié"); });
        });
        $("#pl_ical_regenerer").on("click", function() { Action_ical("regenerer", false); });
        $("#pl_ical_revoquer").on("click", function() { Action_ical("revoquer", false); });

        $("[data-portee]").on("click", function() {
            Reglages_portee = this.getAttribute("data-portee");
            $("[data-portee]").each(function() { $(this).attr("aria-checked", String(this.getAttribute("data-portee") === Reglages_portee)); });
        });
        $("#pl_reglages_valider").on("click", function() {
            Enregistrer_reglages(Reglages_portee, Lire_reglages()).done(function() { $("#pl_modal_reglages").modal("hide"); });
        });
        $("#pl_reglages_reinit").on("click", function() {
            Enregistrer_reglages("reinitialiser", {}).done(function() { $("#pl_modal_reglages").modal("hide"); });
        });

        // Synthèse
        $synthese.on("click", ".pl-sy-cell", function(e) { e.stopPropagation(); Ouvrir_cellule_synthese(this); });
        $synthese.on("dblclick", ".pl-sy-cell", function() {
            if ($sy_pop) { $sy_pop.remove(); $sy_pop = null; }
            V.vue = "frise"; Changer_dates([+this.getAttribute("data-jour")]); Memoriser_affichage();
        });
        $(document).on("pointerdown", function(e) { if ($sy_pop && !$sy_pop[0].contains(e.target) && !e.target.closest(".pl-sy-cell")) { $sy_pop.remove(); $sy_pop = null; } });

        // Les modales et menus sont déplacés dans l'application pour rester visibles en plein écran
        $(".modal[id^='pl_modal_'], #modal_pdf").each(function() { document.getElementById("pl_app").appendChild(this); });
    }

    // ------------------------------------------------------------------ Initialisation
    function Initialiser() {
        $("#pl_statut").html("<i class='fa fa-spinner fa-spin'></i>Chargement…");
        Ajax(CFG.urls.donnees).done(function(data) {
            Charger_donnees_reference(data);
            Restaurer_affichage(data.affichage);
            Brancher_evenements();
            Brancher_modales();
            Rendu_collaborateurs();
            Rendu_filtres();
            // Dates initiales : semaine en cours (du lundi au vendredi)
            var lundi = Lundi(Aujourdhui());
            var jours = [lundi, lundi + 1, lundi + 2, lundi + 3, lundi + 4];
            var infos = Infos_jour(lundi);
            V.mois_cal = {a: infos.a, m: infos.m};
            V.ancre_cal = lundi;
            Changer_dates(jours);
        }).fail(function(xhr) {
            $("#pl_statut").html("<span class='text-danger'>" + Echapper(Message_erreur(xhr, "Impossible de charger le planning")) + "</span>");
        });
    }

    // Exposé pour les tests et le débogage
    window.PlanningEquipe = {S: S, V: V, M: M, R: function() { return R; }, Pile: Pile, Rafraichir: function() { Rafraichir_tout(); }};

    $(Initialiser);

})(jQuery);
