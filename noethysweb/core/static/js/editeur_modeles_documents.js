/*
 *  Noethysweb - Éditeur de modèles de documents (fabric.js 3.6)
 *  Distribué sous licence GNU GPL.
 *
 *  Unités : 1 unité du canvas = 1 mm (converti en points par reportlab).
 *  Configuration attendue dans window.EDITEUR_CONFIG (voir modeles_documents.html).
 */

(function ($) {
    "use strict";

    // ========================================================================
    // CONSTANTES ET PRÉFÉRENCES
    // ========================================================================

    const CFG = window.EDITEUR_CONFIG || {};
    const PX_PAR_MM = 96 / 25.4;
    const ZOOM_MIN = 0.3;
    const ZOOM_MAX = 40;
    const COULEUR_SELECTION = "#1a73e8";
    const COULEUR_GUIDE = "#e83e8c";
    const COULEUR_CHAMP = "rgba(206,203,246,0.8)";
    const COULEUR_CHAMP_INCONNU = "rgba(247,193,193,0.95)";
    const COULEUR_EXEMPLE = "rgba(192,221,151,0.9)";
    const REGEX_CODE_CHAMP = /^\{[A-Za-z0-9_-]+\}$/;
    const REGEX_CHAMPS_DYNAMIQUES = /^\{(CODEBARRES_)?QUESTION_\d+\}$/;
    const REGEX_CHAMP = /\{[^{}\n]+\}/g;
    const PROPRIETES_PERSO = ["nom", "categorie", "champ", "type_image", "cb_norme", "cb_affiche_numero", "verrouille", "qr_contenu", "qr_correction"];
    const HISTORIQUE_MAX = 100;
    // Rendu commun avec la liste des modèles (modeles_documents_rendu.js)
    const RENDU = window.RenduModelesDocuments;
    const ECHELLE_TEXTE = RENDU.ECHELLE_TEXTE;
    const INTERLIGNE_TEXTE = RENDU.interligne_texte();
    const CLE_PREFS = "noethysweb.editeur_modeles";
    const ICONES = {
        texte: "fa-font", rectangle: "fa-square-o", cercle: "fa-circle-thin", ligne: "fa-minus",
        image: "fa-picture-o", logo: "fa-star-o", photo: "fa-user-o", barcode: "fa-barcode", special: "fa-table", qrcode: "fa-qrcode",
    };
    const LIBELLES_GROUPES = {
        FAMILLE: "Famille", INDIVIDU: "Individu", ORGANISATEUR: "Organisateur", ACTIVITE: "Activité",
        INSCRIPTION: "Inscription", COTISATION: "Cotisation", FACTURE: "Facture", REGLEMENT: "Règlement",
        LOCATION: "Location", PRODUIT: "Produit", DEVIS: "Devis", RAPPEL: "Rappel", DATE: "Dates",
        DESTINATAIRE: "Destinataire", PAYEUR: "Payeur", QUESTION: "Questionnaire",
    };

    const prefs = Object.assign({
        grille: false, magnetisme: true, marges: true, regles: true,
        pas_grille: 5, marge: 10, couleurs_recentes: [],
    }, lire_prefs());

    function lire_prefs() {
        try { return JSON.parse(window.localStorage.getItem(CLE_PREFS)) || {}; } catch (e) { return {}; }
    }
    function ecrire_prefs() {
        try { window.localStorage.setItem(CLE_PREFS, JSON.stringify(prefs)); } catch (e) { /* stockage indisponible */ }
    }

    // ========================================================================
    // OUTILS
    // ========================================================================

    function limiter(valeur, min, max) { return Math.min(Math.max(valeur, min), max); }
    function arrondi(valeur, decimales = 1) { const f = Math.pow(10, decimales); return Math.round(valeur * f) / f; }
    function arrondi_demi(valeur) { return Math.round(valeur * 2) / 2; }
    function fmt(valeur) { return String(arrondi(valeur)).replace(".", ","); }
    function lire_nombre(valeur) { const n = parseFloat(String(valeur).replace(",", ".")); return isNaN(n) ? null : n; }
    function sans_accents(texte) { return String(texte || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
    function largeur_page() { return lire_nombre($("#id_largeur").val()) || 210; }
    function hauteur_page() { return lire_nombre($("#id_hauteur").val()) || 297; }
    function est_saisie(el) {
        if (!el) { return false; }
        const tag = el.tagName;
        return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
    }

    // ========================================================================
    // FABRIC : SÉRIALISATION ET STYLE DE SÉLECTION
    // ========================================================================

    // Ajout des propriétés spécifiques à Noethys dans l'export JSON
    fabric.Object.prototype.toObject = (function (toObject) {
        return function (propertiesToInclude) {
            return toObject.call(this, (propertiesToInclude || []).concat(PROPRIETES_PERSO));
        };
    })(fabric.Object.prototype.toObject);

    // Précision de l'export JSON : 6 décimales au lieu de 2, sinon l'échelle des textes (0,352778)
    // serait arrondie à 0,35 et la largeur imprimée des cadres de texte changerait
    fabric.Object.NUM_FRACTION_DIGITS = 6;

    fabric.Object.prototype.set({
        transparentCorners: false,
        cornerColor: "#ffffff",
        cornerStrokeColor: COULEUR_SELECTION,
        borderColor: COULEUR_SELECTION,
        borderScaleFactor: 1.5,
        cornerSize: 8,
        cornerStyle: "circle",
        padding: 0,
        lockScalingFlip: true,
        hasRotatingPoint: true,
        snapAngle: 15,
    });

    // ========================================================================
    // CANVAS
    // ========================================================================

    const canvas = new fabric.Canvas("canvas", {
        preserveObjectStacking: true,
        stopContextMenu: true,
        fireRightClick: true,
        fireMiddleClick: true,
        backgroundColor: "#ced4da",
        selectionColor: "rgba(26,115,232,0.08)",
        selectionBorderColor: COULEUR_SELECTION,
        selectionLineWidth: 1,
    });
    canvas.lockScalingFlip = true;
    window.editeur_canvas = canvas;

    let feuille = null;
    let objets_fond_actuels = [];
    let nb_objets_fond = 0;
    let vue_automatique = true;
    let canvas_dimensionne = false;
    let survol = null;
    let guides = [];
    let etiquette = null;
    let curseur = null;
    let espace_presse = false;
    let glissement_vue = null;
    let clic_droit = null;
    let maj_panneau_en_cours = false;
    let proportions_actives = false;

    // ------------------------------------------------------------------------
    // Fond de page (feuille blanche + calque de fond éventuel)
    // ------------------------------------------------------------------------

    function dessiner_fond(objets_modele_fond) {
        if (objets_modele_fond !== undefined) {
            objets_fond_actuels = objets_modele_fond || [];
        }
        feuille = new fabric.Rect({
            left: 0, top: 0, width: largeur_page(), height: hauteur_page(), fill: "white",
            selectable: false, evented: false, excludeFromExport: true,
            shadow: new fabric.Shadow({color: "rgba(0,0,0,0.25)", blur: 3, offsetX: 0.6, offsetY: 0.6}),
        });
        const groupe = new fabric.Group([feuille], {selectable: false, evented: false, objectCaching: false});
        canvas.setBackgroundImage(groupe, canvas.requestRenderAll.bind(canvas));
        nb_objets_fond = objets_fond_actuels.length;
        fabric.util.enlivenObjects(objets_fond_actuels, function (objets) {
            objets.forEach(function (objet) {
                if (objet.categorie === "logo") {
                    charger_logo(objet);
                }
                objet.__fond = true;
                normaliser_texte(objet);
                surligner_champs(objet);
                if (apercu_exemples) { appliquer_apercu(objet); }
                groupe.addWithUpdate(objet);
            });
            canvas.requestRenderAll();
            maj_calques();
        });
        canvas.requestRenderAll();
    }

    function charger_fond() {
        const id_fond = $("#id_fond").val();
        if (!id_fond) {
            dessiner_fond([]);
            return;
        }
        $.ajax({
            type: "POST",
            url: CFG.url_fond,
            data: {id_fond: id_fond},
            datatype: "json",
            success: function (data) {
                let objets = [];
                try { objets = JSON.parse(data.objets) || []; } catch (e) { objets = []; }
                dessiner_fond(objets);
            },
        });
    }

    // Grille et marges dessinées juste après le fond, sous les objets
    const rendu_fond_origine = canvas._renderBackground;
    canvas._renderBackground = function (ctx) {
        rendu_fond_origine.call(this, ctx);
        dessiner_grille_et_marges(ctx);
    };

    function dessiner_grille_et_marges(ctx) {
        const v = canvas.viewportTransform;
        const zoom = v[0];
        const W = largeur_page();
        const H = hauteur_page();
        ctx.save();
        ctx.transform(v[0], v[1], v[2], v[3], v[4], v[5]);
        if (prefs.grille) {
            const pas = prefs.pas_grille;
            if (pas * zoom >= 5) {
                ctx.beginPath();
                for (let x = pas; x < W; x += pas) { ctx.moveTo(x, 0); ctx.lineTo(x, H); }
                for (let y = pas; y < H; y += pas) { ctx.moveTo(0, y); ctx.lineTo(W, y); }
                ctx.strokeStyle = "rgba(0,0,0,0.08)";
                ctx.lineWidth = 1 / zoom;
                ctx.stroke();
            }
        }
        const m = prefs.marge;
        if (prefs.marges && m > 0 && m * 2 < W && m * 2 < H) {
            ctx.setLineDash([5 / zoom, 4 / zoom]);
            ctx.strokeStyle = "rgba(220,53,69,0.55)";
            ctx.lineWidth = 1 / zoom;
            ctx.strokeRect(m, m, W - 2 * m, H - 2 * m);
        }
        ctx.restore();
    }

    // Surcouche : survol, repères magnétiques, étiquette de dimensions
    canvas.on("after:render", function (opt) {
        dessiner_surcouche((opt && opt.ctx) || canvas.contextContainer);
        planifier_regles();
    });

    function dessiner_surcouche(ctx) {
        const v = canvas.viewportTransform;
        const zoom = v[0];
        ctx.save();
        ctx.transform(v[0], v[1], v[2], v[3], v[4], v[5]);
        if (survol && survol.canvas && canvas.getActiveObjects().indexOf(survol) < 0 && !canvas._currentTransform) {
            const r = survol.getBoundingRect(true, true);
            ctx.strokeStyle = COULEUR_SELECTION;
            ctx.lineWidth = 1 / zoom;
            ctx.strokeRect(r.left, r.top, r.width, r.height);
        }
        if (guides.length) {
            ctx.strokeStyle = COULEUR_GUIDE;
            ctx.lineWidth = 1 / zoom;
            ctx.setLineDash([4 / zoom, 3 / zoom]);
            guides.forEach(function (g) {
                ctx.beginPath();
                if (g.sens === "v") { ctx.moveTo(g.pos, -10000); ctx.lineTo(g.pos, 10000); }
                else { ctx.moveTo(-10000, g.pos); ctx.lineTo(10000, g.pos); }
                ctx.stroke();
            });
        }
        ctx.restore();

        if (etiquette && etiquette.objet && etiquette.objet.canvas) {
            const o = etiquette.objet;
            const r = o.getBoundingRect(false, true);
            let texte;
            if (etiquette.mode === "taille") {
                texte = fmt(o.width * o.scaleX) + " × " + fmt(o.height * o.scaleY) + " mm";
            } else if (etiquette.mode === "angle") {
                texte = Math.round(o.angle || 0) + "°";
            } else {
                texte = "X " + fmt(o.left) + " · Y " + fmt(o.top);
            }
            ctx.save();
            ctx.font = "11px sans-serif";
            const largeur = ctx.measureText(texte).width + 12;
            const x = r.left + r.width / 2 - largeur / 2;
            const y = r.top + r.height + 8;
            ctx.fillStyle = COULEUR_SELECTION;
            ctx.beginPath();
            if (ctx.roundRect) { ctx.roundRect(x, y, largeur, 18, 4); } else { ctx.rect(x, y, largeur, 18); }
            ctx.fill();
            ctx.fillStyle = "#ffffff";
            ctx.textBaseline = "middle";
            ctx.fillText(texte, x + 6, y + 9.5);
            ctx.restore();
        }
    }

    // ========================================================================
    // RÈGLES
    // ========================================================================

    const regle_h = document.getElementById("regle_h");
    const regle_v = document.getElementById("regle_v");
    let regles_planifiees = false;

    function planifier_regles() {
        if (regles_planifiees) { return; }
        regles_planifiees = true;
        window.requestAnimationFrame(function () {
            regles_planifiees = false;
            if (prefs.regles) {
                dessiner_regle(regle_h, true);
                dessiner_regle(regle_v, false);
            }
        });
    }

    function dessiner_regle(cv, horizontal) {
        const dpr = window.devicePixelRatio || 1;
        const w = cv.clientWidth;
        const h = cv.clientHeight;
        if (!w || !h) { return; }
        if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) {
            cv.width = Math.round(w * dpr);
            cv.height = Math.round(h * dpr);
        }
        const ctx = cv.getContext("2d");
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.fillStyle = "#f1f3f5";
        ctx.fillRect(0, 0, w, h);

        const v = canvas.viewportTransform;
        const zoom = v[0];
        const decalage = horizontal ? v[4] : v[5];
        const longueur = horizontal ? w : h;
        const epaisseur = horizontal ? h : w;
        const taille_page = horizontal ? largeur_page() : hauteur_page();

        function segment(debut, fin, couleur) {
            ctx.fillStyle = couleur;
            if (horizontal) { ctx.fillRect(debut, 0, fin - debut, epaisseur); }
            else { ctx.fillRect(0, debut, epaisseur, fin - debut); }
        }

        // Étendue de la page et de la sélection
        segment(decalage, decalage + taille_page * zoom, "#ffffff");
        const actif = canvas.getActiveObject();
        if (actif) {
            const r = actif.getBoundingRect(true, true);
            const debut = horizontal ? r.left : r.top;
            const taille = horizontal ? r.width : r.height;
            segment(decalage + debut * zoom, decalage + (debut + taille) * zoom, "rgba(26,115,232,0.2)");
        }

        // Graduations
        const majeur = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000].find(function (p) { return p * zoom >= 40; }) || 1000;
        let division = 10;
        while (division > 1 && (majeur / division) * zoom < 4) {
            division = division === 10 ? 5 : (division === 5 ? 2 : 1);
        }
        const mineur = majeur / division;
        const premier = Math.floor((-decalage / zoom) / mineur);
        const dernier = Math.ceil(((longueur - decalage) / zoom) / mineur);

        ctx.strokeStyle = "#adb5bd";
        ctx.fillStyle = "#6c757d";
        ctx.font = "9px sans-serif";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i = premier; i <= dernier; i++) {
            const mm = i * mineur;
            const pos = Math.round(decalage + mm * zoom) + 0.5;
            const est_majeur = i % division === 0;
            const est_demi = division % 2 === 0 && i % (division / 2) === 0;
            const l = est_majeur ? epaisseur * 0.6 : (est_demi ? epaisseur * 0.4 : epaisseur * 0.22);
            if (horizontal) { ctx.moveTo(pos, epaisseur); ctx.lineTo(pos, epaisseur - l); }
            else { ctx.moveTo(epaisseur, pos); ctx.lineTo(epaisseur - l, pos); }
            if (est_majeur) {
                const libelle = String(Math.round(mm));
                if (horizontal) {
                    ctx.fillText(libelle, pos + 2, 9);
                } else {
                    ctx.save();
                    ctx.translate(9, pos - 2);
                    ctx.rotate(-Math.PI / 2);
                    ctx.fillText(libelle, 0, 0);
                    ctx.restore();
                }
            }
        }
        ctx.stroke();

        // Bordure
        ctx.strokeStyle = "#dee2e6";
        ctx.beginPath();
        if (horizontal) { ctx.moveTo(0, h - 0.5); ctx.lineTo(w, h - 0.5); }
        else { ctx.moveTo(w - 0.5, 0); ctx.lineTo(w - 0.5, h); }
        ctx.stroke();

        // Position du curseur
        if (curseur) {
            const pos = Math.round(decalage + (horizontal ? curseur.x : curseur.y) * zoom) + 0.5;
            ctx.strokeStyle = "#e03131";
            ctx.beginPath();
            if (horizontal) { ctx.moveTo(pos, 0); ctx.lineTo(pos, h); }
            else { ctx.moveTo(0, pos); ctx.lineTo(w, pos); }
            ctx.stroke();
        }
    }

    // ========================================================================
    // DIMENSIONNEMENT ET ZOOM
    // ========================================================================

    function dimensionner_zone() {
        const $zone = $("#zone_editeur");
        const hauteur = window.innerHeight - $zone.offset().top - 20;
        $zone.css("height", Math.max(420, hauteur) + "px");
        ajuster_panneau();
    }

    // Le panneau à onglets s'arrête au bas de la zone de dessin : les listes défilent à l'intérieur
    function ajuster_panneau() {
        const $zone = $("#zone_editeur");
        const $contenu = $(".editeur-panneau .tab-content");
        if (!$contenu.length) { return; }
        const bas_zone = $zone.offset().top + $zone.outerHeight();
        const haut_contenu = $contenu.offset().top;
        // Colonnes empilées (petit écran) : hauteur raisonnable par défaut
        if (haut_contenu >= bas_zone - 100) {
            $contenu.css("max-height", "60vh");
            return;
        }
        $contenu.css("max-height", Math.max(220, bas_zone - haut_contenu - 1) + "px");
    }

    function redimensionner_canvas() {
        const div = document.getElementById("div_canvas");
        const w = div.clientWidth;
        const h = div.clientHeight;
        if (!w || !h || (w === canvas.width && h === canvas.height)) { return; }
        const premier = !canvas_dimensionne;
        canvas.setDimensions({width: w, height: h});
        canvas_dimensionne = true;
        if (premier || vue_automatique) {
            ajuster_page();
        } else {
            canvas.calcOffset();
            canvas.requestRenderAll();
        }
    }

    function apres_changement_vue() {
        canvas.getObjects().forEach(function (o) { o.setCoords(); });
        const actif = canvas.getActiveObject();
        if (actif) { actif.setCoords(); }
        const pourcentage = Math.round(canvas.getZoom() / PX_PAR_MM * 100);
        $("#zoom_valeur").text(pourcentage + " %");
        $(".menu-zoom [data-zoom]").each(function () {
            $(this).toggleClass("zoom-actuel", String($(this).data("zoom")) === String(pourcentage));
        });
        canvas.requestRenderAll();
    }

    function zoomer(zoom, point) {
        zoom = limiter(zoom, ZOOM_MIN, ZOOM_MAX);
        point = point || new fabric.Point(canvas.width / 2, canvas.height / 2);
        canvas.zoomToPoint(point, zoom);
        vue_automatique = false;
        apres_changement_vue();
    }

    function ajuster_page() {
        if (!canvas.width || !canvas.height) { return; }
        const W = largeur_page();
        const H = hauteur_page();
        const marge = 24;
        const zoom = limiter(Math.min((canvas.width - 2 * marge) / W, (canvas.height - 2 * marge) / H), ZOOM_MIN, ZOOM_MAX);
        canvas.setViewportTransform([zoom, 0, 0, zoom, (canvas.width - W * zoom) / 2, (canvas.height - H * zoom) / 2]);
        vue_automatique = true;
        apres_changement_vue();
    }

    function ajuster_largeur() {
        const W = largeur_page();
        const marge = 24;
        const zoom = limiter((canvas.width - 2 * marge) / W, ZOOM_MIN, ZOOM_MAX);
        canvas.setViewportTransform([zoom, 0, 0, zoom, (canvas.width - W * zoom) / 2, marge]);
        vue_automatique = false;
        apres_changement_vue();
    }

    canvas.on("mouse:wheel", function (opt) {
        const e = opt.e;
        fermer_menu();
        const delta = e.deltaMode === 1 ? e.deltaY * 33 : e.deltaY;
        zoomer(canvas.getZoom() * Math.pow(0.999, delta), new fabric.Point(e.offsetX, e.offsetY));
        e.preventDefault();
        e.stopPropagation();
    });

    // ------------------------------------------------------------------------
    // Déplacement de la vue (Espace + glisser, clic droit, clic molette, Alt + glisser)
    // ------------------------------------------------------------------------

    function activer_mode_main(etat) {
        espace_presse = etat;
        canvas.skipTargetFind = etat;
        canvas.selection = !etat;
        canvas.defaultCursor = etat ? "grab" : "default";
        canvas.setCursor(canvas.defaultCursor);
    }

    canvas.on("mouse:down", function (opt) {
        const e = opt.e;
        if (opt.button === 3) {
            clic_droit = {x: e.clientX, y: e.clientY, cible: canvas.findTarget(e, false), point: canvas.getPointer(e)};
        }
        if (espace_presse || e.altKey || opt.button === 2 || opt.button === 3) {
            glissement_vue = {x: e.clientX, y: e.clientY};
            canvas.selection = false;
            canvas.setCursor("grabbing");
        }
    });

    canvas.on("mouse:move", function (opt) {
        const e = opt.e;
        if (glissement_vue) {
            const v = canvas.viewportTransform;
            v[4] += e.clientX - glissement_vue.x;
            v[5] += e.clientY - glissement_vue.y;
            glissement_vue = {x: e.clientX, y: e.clientY};
            vue_automatique = false;
            canvas.requestRenderAll();
        }
        curseur = canvas.getPointer(e);
        $("#statut_curseur").html('<i class="fa fa-mouse-pointer margin-r-5"></i>x ' + fmt(curseur.x) + " · y " + fmt(curseur.y) + " mm");
        planifier_regles();
    });

    canvas.on("mouse:out", function (opt) {
        if (!opt.target) {
            curseur = null;
            planifier_regles();
        }
    });

    function terminer_glissement_vue() {
        if (!glissement_vue) { return; }
        glissement_vue = null;
        canvas.selection = !espace_presse;
        canvas.setCursor(canvas.defaultCursor);
        apres_changement_vue();
    }

    canvas.on("mouse:up", function () {
        terminer_glissement_vue();
        if (guides.length || etiquette) {
            guides = [];
            etiquette = null;
            canvas.requestRenderAll();
        }
    });
    // Clic droit court = menu contextuel ; clic droit glissé = déplacement de la vue
    $(document).on("mouseup", function (e) {
        const clic = clic_droit;
        clic_droit = null;
        terminer_glissement_vue();
        if (clic && e.button === 2 && Math.hypot(e.clientX - clic.x, e.clientY - clic.y) < 4) {
            ouvrir_menu_canvas(clic.cible, clic.point, e.clientX, e.clientY);
        }
    });

    canvas.on("mouse:over", function (opt) {
        if (opt.target !== survol) {
            survol = opt.target || null;
            canvas.requestRenderAll();
        }
    });
    canvas.on("mouse:out", function (opt) {
        if (opt.target && opt.target === survol) {
            survol = null;
            canvas.requestRenderAll();
        }
    });

    // ========================================================================
    // HISTORIQUE (annuler / rétablir) ET ÉTAT DE MODIFICATION
    // ========================================================================

    let pile = [];
    let position = -1;
    let historique_suspendu = true;
    let minuteur_historique = null;
    let jeton_restauration = 0;
    let etat_enregistre = null;
    let formulaire_modifie = false;
    let soumission = false;

    function serialiser() {
        const objets = canvas.toJSON().objects;
        const sources = canvas.getObjects().filter(function (o) { return !o.excludeFromExport; });
        objets.forEach(function (o, i) {
            // Les styles des textes ne servent qu'au surlignage des champs : inutile de les stocker
            if (o.styles) { o.styles = {}; }
            // En mode aperçu, on enregistre le texte du modèle et non les données d'exemple
            if (sources[i] && sources[i].__texte_modele !== undefined) { o.text = sources[i].__texte_modele; }
            if (o.textAlign === "justify-left") { o.textAlign = "justify"; }
        });
        return objets;
    }

    function etat_courant() {
        return JSON.stringify(serialiser());
    }

    function initialiser_historique() {
        pile = [etat_courant()];
        position = 0;
        etat_enregistre = pile[0];
        historique_suspendu = false;
        maj_historique_ui();
    }

    function enregistrer_historique() {
        clearTimeout(minuteur_historique);
        minuteur_historique = null;
        if (historique_suspendu || position < 0) { return; }
        const etat = etat_courant();
        if (etat !== pile[position]) {
            pile = pile.slice(0, position + 1);
            pile.push(etat);
            if (pile.length > HISTORIQUE_MAX) { pile.shift(); }
            position = pile.length - 1;
        }
        maj_historique_ui();
    }

    function enregistrer_historique_differe(delai) {
        clearTimeout(minuteur_historique);
        minuteur_historique = setTimeout(enregistrer_historique, delai === undefined ? 400 : delai);
    }

    function annuler() {
        if (minuteur_historique) { enregistrer_historique(); }
        if (position > 0) {
            position -= 1;
            restaurer(pile[position]);
        }
    }

    function retablir() {
        if (position < pile.length - 1) {
            position += 1;
            restaurer(pile[position]);
        }
    }

    function restaurer(etat) {
        const jeton = ++jeton_restauration;
        historique_suspendu = true;
        canvas.discardActiveObject();
        canvas.remove.apply(canvas, canvas.getObjects());
        fabric.util.enlivenObjects(JSON.parse(etat), function (objets) {
            if (jeton !== jeton_restauration) { return; }
            objets.forEach(function (objet) { ajouter_objet_charge(objet); });
            historique_suspendu = false;
            canvas.requestRenderAll();
            maj_panneau();
            maj_calques();
            maj_historique_ui();
        });
        maj_historique_ui();
    }

    function est_modifie() {
        return formulaire_modifie || (position >= 0 && pile[position] !== etat_enregistre);
    }

    function maj_historique_ui() {
        maj_controle_champs();
        $("#bouton_annuler").prop("disabled", position <= 0);
        $("#bouton_retablir").prop("disabled", position < 0 || position >= pile.length - 1);
        $("#statut_modifie").toggle(est_modifie());
        $("#bouton_enregistrer").toggleClass("modifie", est_modifie())
            .attr("title", est_modifie() ? "Enregistrer les modifications (Ctrl+S)" : "Enregistrer (Ctrl+S)");
    }

    window.addEventListener("beforeunload", function (e) {
        if (minuteur_historique) { enregistrer_historique(); }
        if (!soumission && est_modifie()) {
            e.preventDefault();
            e.returnValue = "";
        }
    });

    // ========================================================================
    // CHARGEMENT ET PRÉPARATION DES OBJETS
    // ========================================================================

    // Remplace l'image d'un objet logo par le logo de l'organisateur en conservant la hauteur définie dans le modèle
    function charger_logo(objet) {
        return new Promise(function (resolve) {
            if (!CFG.url_logo) { resolve(); return; }
            const hauteur = objet.height * objet.scaleY;
            objet.setSrc(CFG.url_logo, function (img) {
                if (img && img.height) {
                    img.scaleX = img.scaleY = hauteur / img.height;
                    img.setCoords();
                }
                canvas.requestRenderAll();
                resolve();
            });
        });
    }

    function appliquer_verrou(objet) {
        const v = !!objet.verrouille;
        objet.set({
            lockMovementX: v, lockMovementY: v, lockScalingX: v, lockScalingY: v, lockRotation: v,
            hasControls: !v,
        });
    }

    // Surligne les champs {XXX} dans les textes (affichage uniquement, non exporté)
    function surligner_champs(objet) {
        if (!objet || typeof objet.text !== "string" || objet.__texte_modele !== undefined) { return; }
        const styles = {};
        objet.text.split("\n").forEach(function (ligne, num_ligne) {
            REGEX_CHAMP.lastIndex = 0;
            let resultat;
            while ((resultat = REGEX_CHAMP.exec(ligne)) !== null) {
                for (let c = resultat.index; c < resultat.index + resultat[0].length; c++) {
                    styles[num_ligne] = styles[num_ligne] || {};
                    styles[num_ligne][c] = {textBackgroundColor: (objet.__fond || champ_reconnu(resultat[0])) ? COULEUR_CHAMP : COULEUR_CHAMP_INCONNU};
                }
            }
        });
        objet.styles = styles;
        objet.dirty = true;
    }

    // Aligne l'affichage d'un texte sur le rendu PDF, sans rien changer à ce qui est imprimé :
    // - échelle d'un point (le PDF ignore l'échelle et imprime fontSize en points) ;
    // - largeur du cadre conservée en mm (c'est elle qui sert au retour à la ligne dans le PDF) ;
    // - interligne identique à celui du PDF.
    // Les poignées d'angle sont retirées : on élargit le cadre par les côtés, la taille se règle dans le panneau.
    function normaliser_texte(objet) {
        if (objet.categorie !== "texte" || typeof objet.text !== "string") { return; }
        RENDU.aligner_texte_sur_pdf(objet);
        objet.setControlsVisibility({tl: false, tr: false, bl: false, br: false, mt: false, mb: false});
        objet.setCoords();
    }

    function preparer_objet(objet) {
        normaliser_texte(objet);
        RENDU.preparer_cadre_special(objet);
        // Anciennes normes de codes-barres non gérées par le générateur PDF
        if (objet.categorie === "barcode") {
            if (objet.cb_norme === "Ean13BarcodeWidget") { objet.cb_norme = "EAN13"; }
            if (objet.cb_norme === "Ean8BarcodeWidget") { objet.cb_norme = "EAN8"; }
        }
        if (objet.categorie === "qrcode") {
            objet.lockUniScaling = true;
            objet.setControlsVisibility({mt: false, mb: false, ml: false, mr: false});
        }
        appliquer_verrou(objet);
        surligner_champs(objet);
        if (apercu_exemples) { appliquer_apercu(objet); }
    }

    function ajouter_objet_charge(objet) {
        preparer_objet(objet);
        canvas.add(objet);
        if (objet.categorie === "logo") { return charger_logo(objet); }
        return actualiser_image_code(objet);
    }

    // Image d'aperçu des codes : datamatrix ou code-barres linéaire selon la norme (taille conservée)
    function actualiser_image_code(objet) {
        return new Promise(function (resolve) {
            if (objet.categorie !== "barcode" || !objet.setSrc) { resolve(); return; }
            const url = RENDU.est_datamatrix(objet) ? CFG.url_datamatrix : CFG.url_codebarres;
            const src = objet.getSrc ? objet.getSrc() : "";
            if (!url || src.indexOf(url) >= 0) { resolve(); return; }
            RENDU.remplacer_image(objet, url, function () {
                canvas.requestRenderAll();
                resolve();
            });
        });
    }

    function chargement_initial() {
        let objets_json = [];
        try { objets_json = JSON.parse($("#id_objets").val() || "[]") || []; } catch (e) { objets_json = []; }
        historique_suspendu = true;
        fabric.util.enlivenObjects(objets_json, function (objets) {
            const promesses = objets.map(ajouter_objet_charge);
            canvas.requestRenderAll();
            maj_calques();
            Promise.all(promesses).then(initialiser_historique);
        });
    }

    // ========================================================================
    // AJOUT D'OBJETS
    // ========================================================================

    function centre_visible() {
        const v = canvas.viewportTransform;
        return {
            x: limiter((canvas.width / 2 - v[4]) / v[0], 0, largeur_page()),
            y: limiter((canvas.height / 2 - v[5]) / v[3], 0, hauteur_page()),
        };
    }

    function placer(objet, point, depuis_coin) {
        const p = point || centre_visible();
        if (depuis_coin) {
            objet.set({left: p.x, top: p.y});
        } else {
            objet.setPositionByOrigin(new fabric.Point(p.x, p.y), "center", "center");
        }
        objet.setCoords();
        // Recadre l'objet dans la page si possible
        const W = largeur_page();
        const H = hauteur_page();
        const r = objet.getBoundingRect(true, true);
        let dx = 0;
        let dy = 0;
        if (r.left + r.width > W) { dx = W - (r.left + r.width); }
        if (r.left + dx < 0) { dx = -r.left; }
        if (r.top + r.height > H) { dy = H - (r.top + r.height); }
        if (r.top + dy < 0) { dy = -r.top; }
        objet.set({left: Math.round(objet.left + dx), top: Math.round(objet.top + dy)});
        objet.setCoords();
    }

    function inserer_objet(objet, options) {
        options = options || {};
        if (apercu_exemples && objet.categorie === "texte") { basculer_apercu(false); }
        historique_suspendu = true;
        preparer_objet(objet);
        canvas.add(objet);
        historique_suspendu = false;
        placer(objet, options.point, options.depuis_coin);
        canvas.setActiveObject(objet);
        canvas.requestRenderAll();
        enregistrer_historique();
        maj_calques();
        $("#onglet_proprietes").tab("show");
    }

    function nouveau_texte(texte) {
        return new fabric.Textbox(texte, {
            nom: "Texte", categorie: "texte", fontFamily: "Arial", fontSize: 10,
            width: 35 / ECHELLE_TEXTE, scaleX: ECHELLE_TEXTE, scaleY: ECHELLE_TEXTE, lineHeight: INTERLIGNE_TEXTE,
        });
    }

    const ajouts = {
        texte: function (data, point) {
            inserer_objet(nouveau_texte("Tapez votre texte ici"), {point: point});
        },
        rectangle: function (data, point) {
            inserer_objet(new fabric.Rect({
                width: 50, height: 30, fill: "rgba(122,156,255,1)", strokeWidth: 0, stroke: "rgba(0,0,0,1)",
                nom: "Rectangle", categorie: "rectangle",
            }), {point: point});
        },
        cercle: function (data, point) {
            inserer_objet(new fabric.Circle({
                radius: 20, fill: "rgba(122,156,255,1)", strokeWidth: 0, stroke: "rgba(0,0,0,1)",
                nom: "Cercle", categorie: "cercle",
            }), {point: point});
        },
        ligne: function (data, point) {
            inserer_objet(new fabric.Line([0, 0, 100, 0], {
                stroke: "rgba(0,0,0,1)", strokeWidth: 0.5, nom: "Ligne", categorie: "ligne",
            }), {point: point});
        },
        image: function () {
            $("#erreurs_image").empty();
            $("#image_loader").val("");
            $("#modal_selection_image").modal("show");
        },
        logo: function () {
            if (!CFG.url_logo) {
                toastr.warning("Aucun logo n'est défini pour l'organisateur. Vous pouvez l'ajouter dans Paramétrage > Organisateur.");
                return;
            }
            fabric.Image.fromURL(CFG.url_logo, function (objet) {
                objet.set({nom: "Logo organisateur", stroke: "rgba(0,0,0,0)", categorie: "logo"});
                ajuster_taille_image(objet);
                inserer_objet(objet);
            });
        },
        photo: function () {
            fabric.Image.fromURL(CFG.url_photo, function (objet) {
                objet.set({nom: "Photo individuelle", stroke: "rgba(0,0,0,0)", categorie: "photo"});
                inserer_objet(objet);
            });
        },
        codebarres: function (data) {
            fabric.Image.fromURL(CFG.url_codebarres, function (objet) {
                objet.set({
                    nom: "Code-barres " + data.nom, champ: data.champ, categorie: "barcode",
                    cb_norme: "Extended39", cb_affiche_numero: false, scaleX: 0.09, scaleY: 0.05,
                    stroke: "rgba(0,0,0,0)",
                });
                if (String(data.champ).indexOf("DATAMATRIX") >= 0) {
                    objet.set({cb_norme: "datamatrix", scaleX: 1, scaleY: 1, width: 22, height: 22});
                    actualiser_image_code(objet).then(function () { inserer_objet(objet); });
                    return;
                }
                inserer_objet(objet);
            });
        },
        qrcode: function (data, point) {
            fabric.Image.fromURL(CFG.url_qrcode, function (objet) {
                objet.set({nom: "QR code", categorie: "qrcode", qr_contenu: "", qr_correction: "M", stroke: "rgba(0,0,0,0)"});
                objet.scaleX = objet.scaleY = 25 / objet.width;
                inserer_objet(objet, {point: point});
                setTimeout(function () { $("#objet_qr_contenu").trigger("focus"); }, 150);
            });
        },
        special: function (data) {
            inserer_objet(new fabric.Rect({
                nom: data.nom, champ: data.champ, categorie: "special",
                width: parseFloat(data.largeur) || 50, height: parseFloat(data.hauteur) || 50,
                fill: "rgba(244,255,153,1)", stroke: "rgba(0,0,0,0)", strokeWidth: 0,
            }));
        },
    };

    function ajuster_taille_image(objet) {
        const largeur_max = largeur_page() * 0.5;
        if (objet.width > largeur_max) {
            objet.scaleX = objet.scaleY = largeur_max / objet.width;
        }
    }

    $("[data-ajouter]").on("click", function (e) {
        e.preventDefault();
        const type = $(this).data("ajouter");
        if (ajouts[type]) {
            ajouts[type]({
                nom: $(this).attr("data-nom"), champ: $(this).attr("data-champ"),
                largeur: $(this).attr("data-largeur"), hauteur: $(this).attr("data-hauteur"),
            });
        }
    });

    document.getElementById("image_loader").addEventListener("change", function (e) {
        const fichier = e.target.files[0];
        if (!fichier) { return; }
        if (!/^image\/(png|jpeg)$/.test(fichier.type)) {
            $("#erreurs_image").text("Seules les images PNG et JPEG sont acceptées.");
            return;
        }
        const reader = new FileReader();
        reader.onload = function (event) {
            const img = new Image();
            img.onload = function () {
                const objet = new fabric.Image(img, {nom: "Image", stroke: "rgba(0,0,0,0)", categorie: "image"});
                ajuster_taille_image(objet);
                inserer_objet(objet);
            };
            img.src = event.target.result;
        };
        reader.readAsDataURL(fichier);
        $("#modal_selection_image").modal("hide");
    });

    // ========================================================================
    // ACTIONS SUR LA SÉLECTION
    // ========================================================================

    let presse_papier = null;

    function ordonner_par_pile(objets) {
        const tous = canvas.getObjects();
        return objets.slice().sort(function (a, b) { return tous.indexOf(a) - tous.indexOf(b); });
    }

    function selectionner(objets) {
        objets = ordonner_par_pile(objets.filter(function (o) { return o.visible !== false; }));
        canvas.discardActiveObject();
        if (objets.length === 1) {
            canvas.setActiveObject(objets[0]);
        } else if (objets.length > 1) {
            canvas.setActiveObject(new fabric.ActiveSelection(objets, {canvas: canvas}));
        }
        canvas.requestRenderAll();
        maj_panneau();
        maj_calques();
    }

    function tout_selectionner() {
        selectionner(canvas.getObjects());
    }

    function supprimer() {
        const objets = canvas.getActiveObjects();
        if (!objets.length) { return; }
        const supprimables = objets.filter(function (o) { return !o.verrouille; });
        if (supprimables.length < objets.length) {
            toastr.info("Les objets verrouillés n'ont pas été supprimés.");
        }
        if (!supprimables.length) { return; }
        canvas.discardActiveObject();
        historique_suspendu = true;
        supprimables.forEach(function (o) { canvas.remove(o); });
        historique_suspendu = false;
        survol = null;
        canvas.requestRenderAll();
        enregistrer_historique();
    }

    function copier() {
        const actif = canvas.getActiveObject();
        if (!actif) { return false; }
        actif.clone(function (clone) { corriger_clone(actif, clone); presse_papier = clone; }, PROPRIETES_PERSO);
        return true;
    }

    function coller(point) {
        if (!presse_papier) { return false; }
        presse_papier.clone(function (clone) {
            canvas.discardActiveObject();
            if (point) {
                clone.set({left: Math.round(point.x), top: Math.round(point.y), evented: true});
            } else {
                clone.set({left: clone.left + 5, top: clone.top + 5, evented: true});
            }
            historique_suspendu = true;
            if (clone.type === "activeSelection") {
                clone.canvas = canvas;
                clone.forEachObject(function (o) { preparer_objet(o); canvas.add(o); });
                clone.setCoords();
            } else {
                preparer_objet(clone);
                canvas.add(clone);
            }
            historique_suspendu = false;
            presse_papier.left += 5;
            presse_papier.top += 5;
            canvas.setActiveObject(clone);
            canvas.requestRenderAll();
            enregistrer_historique();
        }, PROPRIETES_PERSO);
        return true;
    }

    // Un clone d'un texte en mode aperçu doit reprendre le texte du modèle
    function corriger_clone(source, clone) {
        const paires = source.type === "activeSelection"
            ? source.getObjects().map(function (s, i) { return [s, clone.getObjects()[i]]; })
            : [[source, clone]];
        paires.forEach(function (p) {
            if (p[1] && p[0].__texte_modele !== undefined) {
                p[1].set({text: p[0].__texte_modele, editable: true});
                p[1].styles = {};
            }
        });
    }

    function couper() {
        const objets = canvas.getActiveObjects();
        if (!objets.length || objets.some(function (o) { return o.verrouille; })) { return false; }
        copier();
        supprimer();
        return true;
    }

    function masquer_selection() {
        const objets = canvas.getActiveObjects().filter(function (o) { return o.categorie !== "special"; });
        if (!objets.length) { return; }
        canvas.discardActiveObject();
        objets.forEach(function (o) { o.visible = false; });
        survol = null;
        canvas.requestRenderAll();
        enregistrer_historique();
        maj_calques();
    }

    function editer_texte(objet) {
        if (apercu_exemples) { basculer_apercu(false); }
        canvas.setActiveObject(objet);
        objet.enterEditing();
        objet.setSelectionStart(objet.text.length);
        objet.setSelectionEnd(objet.text.length);
        if (objet.hiddenTextarea) { objet.hiddenTextarea.focus(); }
        canvas.requestRenderAll();
    }

    function renommer() {
        $("#onglet_proprietes").tab("show");
        setTimeout(function () { $("#objet_nom").trigger("focus").trigger("select"); }, 150);
    }

    function dupliquer() {
        const actif = canvas.getActiveObject();
        if (!actif) { return false; }
        actif.clone(function (clone) {
            corriger_clone(actif, clone);
            presse_papier = clone;
            coller();
        }, PROPRIETES_PERSO);
        return true;
    }

    function changer_ordre(action) {
        const actif = canvas.getActiveObject();
        if (!actif) { return; }
        if (action === "devant") { canvas.bringToFront(actif); }
        if (action === "avancer") { canvas.bringForward(actif); }
        if (action === "reculer") { canvas.sendBackwards(actif); }
        if (action === "derriere") { canvas.sendToBack(actif); }
        canvas.requestRenderAll();
        enregistrer_historique();
        maj_calques();
    }

    function deplacer(dx, dy) {
        const actif = canvas.getActiveObject();
        if (!actif || canvas.getActiveObjects().some(function (o) { return o.verrouille; })) { return; }
        actif.set({left: actif.left + dx, top: actif.top + dy});
        actif.setCoords();
        canvas.requestRenderAll();
        maj_geometrie();
        enregistrer_historique_differe();
    }

    function basculer_verrou() {
        const objets = canvas.getActiveObjects();
        if (!objets.length) { return; }
        const verrouiller = !objets.every(function (o) { return o.verrouille; });
        objets.forEach(function (o) { o.verrouille = verrouiller; appliquer_verrou(o); });
        const actif = canvas.getActiveObject();
        if (actif.type === "activeSelection") {
            actif.set({lockMovementX: verrouiller, lockMovementY: verrouiller, lockScalingX: verrouiller, lockScalingY: verrouiller, lockRotation: verrouiller, hasControls: !verrouiller});
        }
        canvas.requestRenderAll();
        enregistrer_historique();
        maj_panneau();
        maj_calques();
    }

    // ------------------------------------------------------------------------
    // Alignement et répartition
    // ------------------------------------------------------------------------

    function aligner(mode) {
        const selection = canvas.getActiveObjects();
        const objets = selection.filter(function (o) { return !o.verrouille; });
        if (!objets.length) { return; }
        const reference = $("#alignement_reference").val() || "page";
        if ((mode === "repartir_h" || mode === "repartir_v") && objets.length < 3) {
            toastr.info("Sélectionnez au moins 3 objets pour les répartir.");
            return;
        }

        canvas.discardActiveObject();
        const rects = objets.map(function (o) { o.setCoords(); return o.getBoundingRect(true, true); });
        const W = largeur_page();
        const H = hauteur_page();
        const m = prefs.marge;
        let zone;
        if (reference === "selection") {
            const tous_rects = selection.map(function (o) { o.setCoords(); return o.getBoundingRect(true, true); });
            const gauche = Math.min.apply(null, tous_rects.map(function (r) { return r.left; }));
            const haut = Math.min.apply(null, tous_rects.map(function (r) { return r.top; }));
            const droite = Math.max.apply(null, tous_rects.map(function (r) { return r.left + r.width; }));
            const bas = Math.max.apply(null, tous_rects.map(function (r) { return r.top + r.height; }));
            zone = {left: gauche, top: haut, width: droite - gauche, height: bas - haut};
        } else if (reference === "marges") {
            zone = {left: m, top: m, width: W - 2 * m, height: H - 2 * m};
        } else {
            zone = {left: 0, top: 0, width: W, height: H};
        }

        if (mode === "repartir_h" || mode === "repartir_v") {
            const horizontal = mode === "repartir_h";
            const ordre = objets.map(function (o, i) { return {o: o, r: rects[i]}; }).sort(function (a, b) {
                return horizontal ? a.r.left - b.r.left : a.r.top - b.r.top;
            });
            const debut = horizontal ? ordre[0].r.left : ordre[0].r.top;
            const dernier = ordre[ordre.length - 1].r;
            const fin = horizontal ? dernier.left + dernier.width : dernier.top + dernier.height;
            const total = ordre.reduce(function (s, x) { return s + (horizontal ? x.r.width : x.r.height); }, 0);
            const ecart = (fin - debut - total) / (ordre.length - 1);
            let curseur_pos = debut;
            ordre.forEach(function (x) {
                if (horizontal) { x.o.left += curseur_pos - x.r.left; curseur_pos += x.r.width + ecart; }
                else { x.o.top += curseur_pos - x.r.top; curseur_pos += x.r.height + ecart; }
                x.o.setCoords();
            });
        } else {
            objets.forEach(function (o, i) {
                const r = rects[i];
                if (mode === "gauche") { o.left += zone.left - r.left; }
                if (mode === "centre_h") { o.left += zone.left + zone.width / 2 - (r.left + r.width / 2); }
                if (mode === "droite") { o.left += zone.left + zone.width - (r.left + r.width); }
                if (mode === "haut") { o.top += zone.top - r.top; }
                if (mode === "centre_v") { o.top += zone.top + zone.height / 2 - (r.top + r.height / 2); }
                if (mode === "bas") { o.top += zone.top + zone.height - (r.top + r.height); }
                o.setCoords();
            });
        }

        selectionner(selection);
        enregistrer_historique();
    }

    // ========================================================================
    // MAGNÉTISME ET ÉTIQUETTES PENDANT LES TRANSFORMATIONS
    // ========================================================================

    function cibles_alignement(exclus) {
        const W = largeur_page();
        const H = hauteur_page();
        const m = prefs.marge;
        const verticales = [0, W / 2, W];
        const horizontales = [0, H / 2, H];
        if (prefs.marges && m > 0) {
            verticales.push(m, W - m);
            horizontales.push(m, H - m);
        }
        canvas.getObjects().forEach(function (o) {
            if (o.visible === false || exclus.indexOf(o) >= 0) { return; }
            const r = o.getBoundingRect(true, true);
            verticales.push(r.left, r.left + r.width / 2, r.left + r.width);
            horizontales.push(r.top, r.top + r.height / 2, r.top + r.height);
        });
        return {v: verticales, h: horizontales};
    }

    function meilleur_ecart(valeurs, cibles, seuil) {
        let meilleur = null;
        valeurs.forEach(function (valeur) {
            cibles.forEach(function (cible) {
                const ecart = cible - valeur;
                if (Math.abs(ecart) <= seuil && (meilleur === null || Math.abs(ecart) < Math.abs(meilleur.ecart))) {
                    meilleur = {ecart: ecart, pos: cible};
                }
            });
        });
        return meilleur;
    }

    canvas.on("object:moving", function (opt) {
        const objet = opt.target;
        const sans_magnetisme = opt.e && (opt.e.ctrlKey || opt.e.metaKey);
        guides = [];
        if (prefs.magnetisme && !sans_magnetisme) {
            objet.setCoords();
            const r = objet.getBoundingRect(true, true);
            const exclus = objet.type === "activeSelection" ? objet.getObjects() : [objet];
            const cibles = cibles_alignement(exclus);
            const seuil = 6 / canvas.getZoom();
            const pas = prefs.pas_grille;
            const ex = meilleur_ecart([r.left, r.left + r.width / 2, r.left + r.width], cibles.v, seuil);
            const ey = meilleur_ecart([r.top, r.top + r.height / 2, r.top + r.height], cibles.h, seuil);
            if (ex) { objet.left += ex.ecart; guides.push({sens: "v", pos: ex.pos}); }
            else if (prefs.grille) { objet.left = Math.round(objet.left / pas) * pas; }
            else { objet.left = Math.round(objet.left); }
            if (ey) { objet.top += ey.ecart; guides.push({sens: "h", pos: ey.pos}); }
            else if (prefs.grille) { objet.top = Math.round(objet.top / pas) * pas; }
            else { objet.top = Math.round(objet.top); }
        } else {
            objet.left = Math.round(objet.left);
            objet.top = Math.round(objet.top);
        }
        objet.setCoords();
        etiquette = {objet: objet, mode: "position"};
        maj_geometrie();
    });

    canvas.on("object:scaling", function (opt) {
        etiquette = {objet: opt.target, mode: "taille"};
        maj_geometrie();
    });

    canvas.on("object:rotating", function (opt) {
        etiquette = {objet: opt.target, mode: "angle"};
        maj_geometrie();
    });

    // Les rectangles conservent une échelle de 1 (largeur/hauteur réelles en mm)
    canvas.on("object:scaled", function (opt) {
        const objet = opt.target;
        if (!objet || objet.type !== "rect") { return; }
        objet.set({
            left: arrondi_demi(objet.left), top: arrondi_demi(objet.top),
            width: arrondi_demi(objet.width * objet.scaleX), height: arrondi_demi(objet.height * objet.scaleY),
            scaleX: 1, scaleY: 1,
        });
        objet.setCoords();
    });

    // ========================================================================
    // ÉVÉNEMENTS DU CANVAS
    // ========================================================================

    canvas.on({
        "selection:created": sur_selection,
        "selection:updated": sur_selection,
        "selection:cleared": sur_selection,
        "object:modified": function () {
            guides = [];
            etiquette = null;
            enregistrer_historique();
            maj_panneau();
            maj_calques();
        },
        "object:added": function () {
            if (!historique_suspendu) { enregistrer_historique(); }
            maj_calques();
        },
        "object:removed": function () {
            if (!historique_suspendu) { enregistrer_historique(); }
            maj_calques();
        },
    });

    function sur_selection() {
        maj_panneau();
        maj_calques();
        planifier_regles();
    }

    // ------------------------------------------------------------------------
    // Édition des textes et insertion de champs
    // ------------------------------------------------------------------------

    let dernier_texte = null;
    let derniere_selection = null;

    function memoriser_selection_texte(objet) {
        dernier_texte = objet;
        derniere_selection = {debut: objet.selectionStart, fin: objet.selectionEnd};
    }

    canvas.on("text:editing:entered", function (opt) {
        memoriser_selection_texte(opt.target);
        $("#bouton_inserer_champ").show();
    });
    canvas.on("text:editing:exited", function (opt) {
        memoriser_selection_texte(opt.target);
        surligner_champs(opt.target);
        $("#bouton_inserer_champ").hide();
    });
    canvas.on("text:selection:changed", function (opt) { memoriser_selection_texte(opt.target); });
    canvas.on("text:changed", function (opt) {
        memoriser_selection_texte(opt.target);
        surligner_champs(opt.target);
        maj_controle_champs();
        maj_alerte_champs();
    });

    function inserer_champ(code, cible) {
        const objet = cible || canvas.getActiveObject();
        if (objet && objet.categorie === "qrcode") {
            inserer_champ_qrcode(objet, code);
            return;
        }
        if (apercu_exemples) { basculer_apercu(false); }
        if (!objet || objet.categorie !== "texte" || objet.type === "activeSelection") {
            inserer_objet(nouveau_texte(code));
            return;
        }
        const etait_en_edition = objet.isEditing;
        let debut;
        let fin;
        let insertion = code;
        if (etait_en_edition) {
            debut = objet.selectionStart;
            fin = objet.selectionEnd;
            objet.exitEditing();
        } else if (objet === dernier_texte && derniere_selection) {
            debut = derniere_selection.debut;
            fin = derniere_selection.fin;
        } else {
            debut = fin = objet.text.length;
            if (objet.text && !/\s$/.test(objet.text)) { insertion = " " + code; }
        }
        objet.set("text", objet.text.slice(0, debut) + insertion + objet.text.slice(fin));
        surligner_champs(objet);
        const position_curseur = debut + insertion.length;
        derniere_selection = {debut: position_curseur, fin: position_curseur};
        dernier_texte = objet;
        if (canvas.getActiveObject() !== objet) { canvas.setActiveObject(objet); }
        if (etait_en_edition) {
            objet.enterEditing();
            objet.setSelectionStart(position_curseur);
            objet.setSelectionEnd(position_curseur);
            if (objet.hiddenTextarea) { objet.hiddenTextarea.focus(); }
        }
        canvas.requestRenderAll();
        enregistrer_historique();
    }

    $("#bouton_inserer_champ").on("click", function () {
        $("#onglet_champs").tab("show");
        setTimeout(function () { $("#champs_recherche").trigger("focus"); }, 150);
    });

    // ========================================================================
    // PANNEAU DES PROPRIÉTÉS
    // ========================================================================

    const SECTIONS = ["#prop_vide", "#prop_entete", "#prop_alerte_champs", "#prop_position", "#prop_texte", "#prop_couleurs", "#prop_codebarres", "#prop_qrcode", "#prop_alignement"];

    function dimensions(o) {
        return {l: o.width * o.scaleX, h: o.height * o.scaleY};
    }

    function maj_geometrie() {
        const actif = canvas.getActiveObject();
        if (!actif) {
            $("#statut_selection").text("");
            return;
        }
        const objets = canvas.getActiveObjects();
        const unique = objets.length === 1 ? objets[0] : null;
        const focus = document.activeElement;
        function definir(selecteur, valeur) {
            const el = $(selecteur)[0];
            if (el !== focus) { el.value = valeur; }
        }
        definir("#objet_x", arrondi(actif.left));
        definir("#objet_y", arrondi(actif.top));
        if (unique) {
            const d = dimensions(unique);
            definir("#objet_largeur", arrondi(d.l));
            definir("#objet_hauteur", arrondi(d.h));
            definir("#objet_angle", Math.round(unique.angle || 0));
            $("#statut_selection").text((unique.nom || "Objet") + " · " + fmt(d.l) + " × " + fmt(d.h) + " mm");
        } else {
            $("#statut_selection").text(objets.length + " objets sélectionnés");
        }
    }

    function definir_couleur(selecteur, valeur) {
        const $input = $(selecteur);
        $input.colorpicker("setValue", valeur || "rgba(0,0,0,0)");
    }

    function maj_panneau() {
        maj_panneau_en_cours = true;
        try {
            remplir_panneau();
        } finally {
            maj_panneau_en_cours = false;
        }
    }

    function remplir_panneau() {
        const actif = canvas.getActiveObject();
        const objets = canvas.getActiveObjects();
        $(".fonctions_objet").prop("disabled", !actif);
        $(SECTIONS.join(",")).hide();
        if (!actif) {
            $("#prop_vide").show();
            $("#statut_selection").text("");
            return;
        }

        const unique = objets.length === 1 ? objets[0] : null;
        const categories = objets.map(function (o) { return o.categorie; });
        function tous(liste) { return categories.length > 0 && categories.every(function (c) { return liste.indexOf(c) >= 0; }); }
        const verrouille = objets.every(function (o) { return o.verrouille; });

        // En-tête
        $("#prop_entete").show();
        $("#prop_icone").attr("class", "fa fa-fw text-muted " + (unique ? (ICONES[unique.categorie] || "fa-square-o") : "fa-object-group"));
        $("#objet_nom").toggle(!!unique).val(unique ? (unique.nom || "") : "");
        $("#prop_multi").toggle(!unique).text(objets.length + " objets sélectionnés");
        $("#objet_verrouiller").toggleClass("active", verrouille)
            .attr("title", verrouille ? "Déverrouiller" : "Verrouiller la position et la taille")
            .find("i").attr("class", verrouille ? "fa fa-lock" : "fa fa-unlock");

        // Position et taille
        $("#prop_position").show();
        $("#objet_x, #objet_y").prop("disabled", verrouille);
        const categorie = unique ? unique.categorie : null;
        $("#champ_largeur, #champ_angle").toggle(!!unique);
        $("#champ_hauteur").toggle(!!unique && categorie !== "ligne");
        $("#objet_largeur, #objet_angle").prop("disabled", verrouille);
        $("#objet_hauteur").prop("disabled", verrouille || categorie === "texte")
            .attr("title", categorie === "texte" ? "La hauteur d'un texte dépend de son contenu" : "");
        const proportions_forcees = categorie === "logo" || categorie === "qrcode";
        $("#objet_proportions").toggle(!!unique && ["ligne", "texte"].indexOf(categorie) < 0)
            .toggleClass("active", proportions_actives || proportions_forcees)
            .prop("disabled", proportions_forcees || verrouille);
        maj_geometrie();

        // Texte
        if (tous(["texte"])) {
            const ref = objets[0];
            $("#prop_texte").show();
            $("#objet_texte_taille").val(ref.fontSize);
            $("#objet_texte_gras").toggleClass("active", objets.every(function (o) { return o.fontWeight === "bold"; }));
            $("#objet_texte_italique").toggleClass("active", objets.every(function (o) { return o.fontStyle === "italic"; }));
            $("#objet_texte_alignement .btn").each(function () {
                $(this).toggleClass("active", $(this).data("valeur") === (ref.textAlign === "justify-left" ? "justify" : ref.textAlign));
            });
        }

        // Couleurs
        const avec_texte = tous(["texte"]);
        const avec_fond = tous(["rectangle", "cercle"]);
        const avec_trait = tous(["rectangle", "cercle", "ligne"]);
        if (avec_texte || avec_fond || avec_trait) {
            $("#prop_couleurs").show();
            $("#bloc_couleur_texte").toggle(avec_texte);
            $("#bloc_couleur_remplissage").toggle(avec_fond);
            $("#bloc_trait").toggle(avec_trait);
            if (avec_texte) { definir_couleur("#objet_texte_couleur", objets[0].fill); }
            if (avec_fond) { definir_couleur("#objet_remplissage_couleur", objets[0].fill); }
            if (avec_trait) {
                definir_couleur("#objet_trait_couleur", objets[0].stroke);
                $("#objet_trait_epaisseur").val(objets[0].strokeWidth);
                $("#objet_trait_style").val(JSON.stringify(objets[0].strokeDashArray || null));
            }
            maj_couleurs_recentes();
        }

        // Code-barres
        if (unique && categorie === "barcode") {
            $("#prop_codebarres").show();
            $("#objet_cb_norme").val(unique.cb_norme);
            $("#codes_barres_numero").prop("checked", !!unique.cb_affiche_numero);
        }

        // QR code
        if (unique && categorie === "qrcode") {
            $("#prop_qrcode").show();
            if (document.activeElement !== $("#objet_qr_contenu")[0]) { $("#objet_qr_contenu").val(unique.qr_contenu || ""); }
            $("#objet_qr_correction").val(unique.qr_correction || "M");
            $("#qr_vide").toggle(!(unique.qr_contenu || "").trim());
        }

        // Champs non reconnus
        maj_alerte_champs();

        // Alignement
        $("#prop_alignement").show();
        const $reference = $("#alignement_reference");
        $reference.find("option[value=selection]").prop("disabled", objets.length < 2);
        if (objets.length > 1) { $reference.val(reference_alignement); }
        else { $reference.val(reference_alignement === "marges" ? "marges" : "page"); }
        $("[data-aligner^=repartir]").prop("disabled", objets.length < 3);
    }

    // Applique une modification à tous les objets sélectionnés compatibles
    function appliquer(categories, fonction, differe) {
        canvas.getActiveObjects().forEach(function (o) {
            if (!categories || categories.indexOf(o.categorie) >= 0) {
                fonction(o);
                o.dirty = true;
                o.setCoords();
            }
        });
        canvas.requestRenderAll();
        if (differe) { enregistrer_historique_differe(); } else { enregistrer_historique(); }
    }

    // Nom
    $("#objet_nom").on("input", function () {
        const objet = canvas.getActiveObject();
        if (objet && objet.type !== "activeSelection") {
            objet.nom = this.value;
            maj_calques();
            enregistrer_historique_differe(600);
        }
    });

    // Position
    $("#objet_x, #objet_y").on("input change", function (e) {
        const actif = canvas.getActiveObject();
        const valeur = lire_nombre(this.value);
        if (!actif || valeur === null) { return; }
        actif.set(this.id === "objet_x" ? "left" : "top", valeur);
        actif.setCoords();
        canvas.requestRenderAll();
        if (e.type === "change") { enregistrer_historique(); }
    });

    // Dimensions
    function definir_dimension(objet, axe, valeur) {
        if (!(valeur > 0)) { return; }
        const d = dimensions(objet);
        const garder_ratio = (proportions_actives || objet.categorie === "logo" || objet.categorie === "qrcode") && ["ligne", "texte"].indexOf(objet.categorie) < 0;
        const ratio = axe === "l" ? d.h / d.l : d.l / d.h;
        if (objet.categorie === "texte") {
            if (axe === "l") { objet.set("width", valeur / objet.scaleX); }
            return;
        }
        if (objet.type === "rect") {
            if (axe === "l") {
                objet.set({width: valeur, scaleX: 1});
                if (garder_ratio) { objet.set({height: valeur * ratio, scaleY: 1}); }
            } else {
                objet.set({height: valeur, scaleY: 1});
                if (garder_ratio) { objet.set({width: valeur * ratio, scaleX: 1}); }
            }
            return;
        }
        if (axe === "l") {
            objet.set("scaleX", valeur / objet.width);
            if (garder_ratio) { objet.set("scaleY", (valeur * ratio) / objet.height); }
        } else {
            objet.set("scaleY", valeur / objet.height);
            if (garder_ratio) { objet.set("scaleX", (valeur * ratio) / objet.width); }
        }
    }

    $("#objet_largeur, #objet_hauteur").on("input change", function (e) {
        const objet = canvas.getActiveObject();
        const valeur = lire_nombre(this.value);
        if (!objet || objet.type === "activeSelection" || valeur === null) { return; }
        definir_dimension(objet, this.id === "objet_largeur" ? "l" : "h", valeur);
        objet.setCoords();
        canvas.requestRenderAll();
        maj_geometrie();
        if (e.type === "change") { enregistrer_historique(); }
    });

    $("#objet_angle").on("input change", function (e) {
        const objet = canvas.getActiveObject();
        const valeur = lire_nombre(this.value);
        if (!objet || objet.type === "activeSelection" || valeur === null) { return; }
        objet.set("angle", valeur);
        objet.setCoords();
        canvas.requestRenderAll();
        if (e.type === "change") { enregistrer_historique(); }
    });

    $("#objet_proportions").on("click", function () {
        proportions_actives = !proportions_actives;
        $(this).toggleClass("active", proportions_actives);
    });

    $("#objet_verrouiller").on("click", basculer_verrou);

    // Texte
    $("#objet_texte_taille").on("input change", function (e) {
        const valeur = lire_nombre(this.value);
        if (!(valeur > 0)) { return; }
        appliquer(["texte"], function (o) { o.set("fontSize", valeur); }, e.type === "input");
    });
    $("#objet_texte_gras").on("click", function () {
        const actif = !$(this).hasClass("active");
        $(this).toggleClass("active", actif);
        appliquer(["texte"], function (o) { o.set("fontWeight", actif ? "bold" : "normal"); });
    });
    $("#objet_texte_italique").on("click", function () {
        const actif = !$(this).hasClass("active");
        $(this).toggleClass("active", actif);
        appliquer(["texte"], function (o) { o.set("fontStyle", actif ? "italic" : "normal"); });
    });
    $("#objet_texte_alignement .btn").on("click", function () {
        const valeur = $(this).data("valeur");
        $("#objet_texte_alignement .btn").removeClass("active");
        $(this).addClass("active");
        appliquer(["texte"], function (o) { o.set("textAlign", valeur === "justify" ? "justify-left" : valeur); });
    });

    // Couleurs
    let cible_couleur = "#objet_remplissage_couleur";

    function initialiser_couleur(selecteur, pastille, categories, propriete) {
        const $input = $(selecteur);
        $input.colorpicker({format: "rgba"}).on("changeColor", function (e) {
            const couleur = e.color.toString("rgba");
            $(pastille)[0].style.setProperty("--couleur", couleur);
            if (maj_panneau_en_cours) { return; }
            appliquer(categories, function (o) { o.set(propriete, couleur); }, true);
        }).on("hidePicker", function () {
            ajouter_couleur_recente($input.val());
        }).on("focus", function () {
            cible_couleur = selecteur;
        });
        $(pastille).on("click", function () {
            cible_couleur = selecteur;
            $input.colorpicker("show");
        });
    }

    initialiser_couleur("#objet_texte_couleur", "#pastille_texte", ["texte"], "fill");
    initialiser_couleur("#objet_remplissage_couleur", "#pastille_remplissage", ["rectangle", "cercle", "special"], "fill");
    initialiser_couleur("#objet_trait_couleur", "#pastille_trait", ["rectangle", "cercle", "ligne"], "stroke");

    function ajouter_couleur_recente(couleur) {
        if (!couleur) { return; }
        prefs.couleurs_recentes = [couleur].concat(prefs.couleurs_recentes.filter(function (c) { return c !== couleur; })).slice(0, 8);
        ecrire_prefs();
        maj_couleurs_recentes();
    }

    function maj_couleurs_recentes() {
        const $zone = $("#couleurs_recentes").empty();
        prefs.couleurs_recentes.forEach(function (couleur) {
            $("<span class='couleur-recente'>").css("background", couleur).attr("title", couleur).attr("data-couleur", couleur).appendTo($zone);
        });
        $(".prop-recentes").toggle(prefs.couleurs_recentes.length > 0);
    }

    $("#couleurs_recentes").on("click", ".couleur-recente", function () {
        let cible = cible_couleur;
        if (!$(cible).is(":visible")) {
            cible = ["#objet_remplissage_couleur", "#objet_texte_couleur", "#objet_trait_couleur"].find(function (s) { return $(s).is(":visible"); });
        }
        if (cible) { $(cible).colorpicker("setValue", $(this).attr("data-couleur")); }
    });

    $("#objet_trait_epaisseur").on("input change", function (e) {
        const valeur = lire_nombre(this.value);
        if (valeur === null || valeur < 0) { return; }
        appliquer(["rectangle", "cercle", "ligne"], function (o) { o.set("strokeWidth", valeur); }, e.type === "input");
    });
    $("#objet_trait_style").on("change", function () {
        const valeur = JSON.parse(this.value);
        appliquer(["rectangle", "cercle", "ligne"], function (o) { o.set("strokeDashArray", valeur); });
    });

    // Codes-barres
    $("#objet_cb_norme").on("change", function () {
        const valeur = this.value;
        appliquer(["barcode"], function (o) { o.set("cb_norme", valeur); });
        canvas.getActiveObjects().forEach(function (o) {
            actualiser_image_code(o).then(function () { enregistrer_historique(); });
        });
    });
    $("#codes_barres_numero").on("change", function () {
        const valeur = this.checked;
        appliquer(["barcode"], function (o) { o.set("cb_affiche_numero", valeur); });
    });

    // Alignement (la référence choisie est mémorisée pour les sélections suivantes)
    let reference_alignement = "selection";
    $("#alignement_reference").on("change", function () { reference_alignement = this.value; });
    $("[data-aligner]").on("click", function () { aligner($(this).data("aligner")); });

    // ========================================================================
    // CALQUES
    // ========================================================================

    let maj_calques_planifiee = false;
    let index_glisse = null;

    function maj_calques() {
        if (maj_calques_planifiee) { return; }
        maj_calques_planifiee = true;
        window.requestAnimationFrame(function () {
            maj_calques_planifiee = false;
            rendre_calques();
        });
    }

    function rendre_calques() {
        const objets = canvas.getObjects();
        const actifs = canvas.getActiveObjects();
        const $liste = $("#liste_calques").empty();
        if (!objets.length) {
            $liste.append("<li class='calques-vide'>Aucun objet sur ce modèle.</li>");
        }
        for (let i = objets.length - 1; i >= 0; i--) {
            const o = objets[i];
            const masque = o.visible === false;
            const $li = $("<li class='calque' draggable='true'>").attr("data-index", i)
                .toggleClass("selectionne", actifs.indexOf(o) >= 0)
                .toggleClass("masque", masque);
            $li.append("<span class='calque-poignee'><i class='fa fa-bars'></i></span>");
            $li.append($("<i class='calque-icone fa'>").addClass(ICONES[o.categorie] || "fa-square-o"));
            $li.append($("<span class='calque-nom'>").text(o.nom || o.categorie || "Objet").attr("title", o.nom || ""));
            $li.append($("<button type='button' class='btn btn-outil calque-visible'>")
                .attr("title", o.categorie === "special" ? "Un objet spécial ne peut pas être masqué" : (masque ? "Afficher (et imprimer)" : "Masquer (ne sera pas imprimé)"))
                .prop("disabled", o.categorie === "special")
                .toggleClass("actif", masque)
                .append($("<i class='fa'>").addClass(masque ? "fa-eye-slash" : "fa-eye")));
            $li.append($("<button type='button' class='btn btn-outil calque-verrou'>")
                .attr("title", o.verrouille ? "Déverrouiller" : "Verrouiller")
                .toggleClass("actif", !!o.verrouille)
                .append($("<i class='fa'>").addClass(o.verrouille ? "fa-lock" : "fa-unlock")));
            $liste.append($li);
        }
        $("#calques_fond").text(nb_objets_fond ? "Calque de fond : " + nb_objets_fond + " objet(s), modifiable(s) uniquement dans le modèle de fond." : "");
        $("#calques_nombre").text(objets.length + (objets.length > 1 ? " objets" : " objet"));
    }

    function objet_de_ligne(ligne) {
        return canvas.item(parseInt($(ligne).closest(".calque").attr("data-index"), 10));
    }

    $("#liste_calques")
        .on("click", ".calque", function (e) {
            if ($(e.target).closest("button, input").length) { return; }
            const objet = objet_de_ligne(this);
            if (!objet || objet.visible === false) { return; }
            let selection = [objet];
            if (e.shiftKey || e.ctrlKey || e.metaKey) {
                const actuels = canvas.getActiveObjects();
                selection = actuels.indexOf(objet) >= 0
                    ? actuels.filter(function (o) { return o !== objet; })
                    : actuels.concat([objet]);
            }
            selectionner(selection);
        })
        .on("click", ".calque-visible", function () {
            const objet = objet_de_ligne(this);
            objet.visible = objet.visible === false;
            if (!objet.visible && canvas.getActiveObjects().indexOf(objet) >= 0) {
                canvas.discardActiveObject();
            }
            canvas.requestRenderAll();
            enregistrer_historique();
            maj_calques();
        })
        .on("click", ".calque-verrou", function () {
            const objet = objet_de_ligne(this);
            objet.verrouille = !objet.verrouille;
            appliquer_verrou(objet);
            canvas.requestRenderAll();
            enregistrer_historique();
            maj_panneau();
            maj_calques();
        })
        .on("dblclick", ".calque-nom", function () {
            const objet = objet_de_ligne(this);
            const $nom = $(this);
            const $input = $("<input type='text' class='form-control form-control-sm'>").val(objet.nom || "");
            $nom.empty().append($input);
            $input.trigger("focus").trigger("select");
            let termine = false;
            function valider(enregistrer) {
                if (termine) { return; }
                termine = true;
                if (enregistrer) {
                    objet.nom = $input.val();
                    enregistrer_historique();
                    maj_panneau();
                }
                maj_calques();
            }
            $input.on("keydown", function (e) {
                if (e.key === "Enter") { valider(true); }
                if (e.key === "Escape") { valider(false); }
            }).on("blur", function () { valider(true); });
        })
        .on("mouseenter", ".calque", function () {
            survol = objet_de_ligne(this) || null;
            canvas.requestRenderAll();
        })
        .on("mouseleave", ".calque", function () {
            survol = null;
            canvas.requestRenderAll();
        })
        .on("dragstart", ".calque", function (e) {
            index_glisse = parseInt(this.dataset.index, 10);
            e.originalEvent.dataTransfer.effectAllowed = "move";
            e.originalEvent.dataTransfer.setData("text/plain", "calque");
        })
        .on("dragover", ".calque", function (e) {
            if (index_glisse === null) { return; }
            e.preventDefault();
            const rect = this.getBoundingClientRect();
            const haut = e.originalEvent.clientY < rect.top + rect.height / 2;
            $(".calque").removeClass("survol-depot-haut survol-depot-bas");
            $(this).addClass(haut ? "survol-depot-haut" : "survol-depot-bas");
        })
        .on("drop", ".calque", function (e) {
            if (index_glisse === null) { return; }
            e.preventDefault();
            const source = index_glisse;
            const cible = parseInt(this.dataset.index, 10);
            const haut = $(this).hasClass("survol-depot-haut");
            let destination;
            if (haut) { destination = source < cible ? cible : cible + 1; }
            else { destination = source < cible ? cible - 1 : cible; }
            const objet = canvas.item(source);
            canvas.discardActiveObject();
            canvas.moveTo(objet, limiter(destination, 0, canvas.getObjects().length - 1));
            canvas.setActiveObject(objet);
            canvas.requestRenderAll();
            enregistrer_historique();
            maj_calques();
        })
        .on("dragend", ".calque", function () {
            index_glisse = null;
            $(".calque").removeClass("survol-depot-haut survol-depot-bas");
        });

    // ========================================================================
    // CHAMPS DE FUSION
    // ========================================================================

    let glisse_champ = false;

    function liste_champs() {
        return (CFG.champs || []).map(function (c) {
            return Array.isArray(c) ? {label: c[0], exemple: c[1], code: c[2]} : c;
        });
    }

    function rendre_champs() {
        const recherche = sans_accents($("#champs_recherche").val()).trim();
        const champs = liste_champs();
        const prefixe = function (code) { return String(code).replace(/[{}]/g, "").split("_")[0]; };
        const compteurs = {};
        champs.forEach(function (c) { const p = prefixe(c.code); compteurs[p] = (compteurs[p] || 0) + 1; });

        const groupes = [];
        const index_groupes = {};
        champs.forEach(function (c) {
            if (recherche && sans_accents(c.label + " " + c.code + " " + c.exemple).indexOf(recherche) < 0) { return; }
            const p = prefixe(c.code);
            const nom = compteurs[p] >= 2 ? (LIBELLES_GROUPES[p] || (p.charAt(0) + p.slice(1).toLowerCase())) : "Divers";
            if (!(nom in index_groupes)) {
                index_groupes[nom] = groupes.length;
                groupes.push({nom: nom, champs: []});
            }
            groupes[index_groupes[nom]].champs.push(c);
        });
        // "Divers" toujours en dernier
        groupes.sort(function (a, b) { return (a.nom === "Divers") - (b.nom === "Divers"); });

        const $liste = $("#liste_champs").empty();
        if (!groupes.length) {
            $liste.append($("<div class='champs-vide'>").text(champs.length ? "Aucun champ ne correspond à cette recherche." : "Aucun champ disponible pour ce type de document."));
            return;
        }
        groupes.forEach(function (g) {
            $liste.append($("<div class='champ-groupe'>").text(g.nom));
            g.champs.forEach(function (c) {
                $("<div class='champ' draggable='true'>")
                    .attr("data-code", c.code)
                    .append($("<span class='champ-label'>").text(c.label).attr("title", c.label + (c.exemple ? " (exemple : " + c.exemple + ")" : "")))
                    .append($("<span class='champ-code'>").text(c.code))
                    .appendTo($liste);
            });
        });
    }

    $("#champs_recherche").on("input", rendre_champs);

    $("#liste_champs")
        .on("click", ".champ", function () {
            inserer_champ($(this).attr("data-code"));
        })
        .on("dragstart", ".champ", function (e) {
            glisse_champ = true;
            e.originalEvent.dataTransfer.effectAllowed = "copy";
            e.originalEvent.dataTransfer.setData("text/plain", $(this).attr("data-code"));
        })
        .on("dragend", ".champ", function () {
            glisse_champ = false;
            $("#div_canvas").removeClass("depot-actif");
        });

    $("#div_canvas")
        .on("dragover", function (e) {
            if (!glisse_champ) { return; }
            e.preventDefault();
            e.originalEvent.dataTransfer.dropEffect = "copy";
            $(this).addClass("depot-actif");
        })
        .on("dragleave", function () {
            $(this).removeClass("depot-actif");
        })
        .on("drop", function (e) {
            $(this).removeClass("depot-actif");
            if (!glisse_champ) { return; }
            e.preventDefault();
            glisse_champ = false;
            const evt = e.originalEvent;
            const code = evt.dataTransfer.getData("text/plain");
            const cible = canvas.findTarget(evt, false);
            if (cible && (cible.categorie === "texte" || cible.categorie === "qrcode") && !cible.verrouille) {
                canvas.setActiveObject(cible);
                inserer_champ(code, cible);
            } else {
                inserer_objet(nouveau_texte(code), {point: canvas.getPointer(evt), depuis_coin: true});
            }
        });

    // ========================================================================
    // CONTRÔLE DES CHAMPS, APERÇU AVEC EXEMPLES ET QR CODE
    // ========================================================================

    const CODES_CONNUS = new Set();
    const EXEMPLES = {};
    let apercu_exemples = false;
    let objets_champs_inconnus = [];
    let curseur_qr = null;

    (function initialiser_codes() {
        liste_champs().forEach(function (c) {
            CODES_CONNUS.add(c.code);
            if (c.exemple !== undefined && c.exemple !== null && String(c.exemple) !== "") {
                EXEMPLES[c.code] = String(c.exemple).replace(/\s*\n\s*/g, " ");
            }
        });
        $("[data-ajouter=codebarres], [data-ajouter=special]").each(function () {
            if ($(this).attr("data-champ")) { CODES_CONNUS.add($(this).attr("data-champ")); }
        });
    })();

    function champ_reconnu(code) {
        if (!CODES_CONNUS.size || !REGEX_CODE_CHAMP.test(code)) { return true; }
        return CODES_CONNUS.has(code) || REGEX_CHAMPS_DYNAMIQUES.test(code);
    }

    function contenu_avec_champs(objet) {
        if (objet.categorie === "texte") { return objet.__texte_modele !== undefined ? objet.__texte_modele : (objet.text || ""); }
        if (objet.categorie === "qrcode") { return objet.qr_contenu || ""; }
        return "";
    }

    function champs_inconnus(objet) {
        const resultat = [];
        const texte = contenu_avec_champs(objet);
        REGEX_CHAMP.lastIndex = 0;
        let m;
        while ((m = REGEX_CHAMP.exec(texte)) !== null) {
            if (!champ_reconnu(m[0]) && resultat.indexOf(m[0]) < 0) { resultat.push(m[0]); }
        }
        return resultat;
    }

    function tous_les_champs_inconnus() {
        const liste = [];
        canvas.getObjects().forEach(function (o) {
            champs_inconnus(o).forEach(function (c) { if (liste.indexOf(c) < 0) { liste.push(c); } });
        });
        return liste;
    }

    function distance_edition(a, b) {
        const d = [];
        for (let i = 0; i <= a.length; i++) { d[i] = [i]; }
        for (let j = 1; j <= b.length; j++) { d[0][j] = j; }
        for (let i = 1; i <= a.length; i++) {
            for (let j = 1; j <= b.length; j++) {
                d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
            }
        }
        return d[a.length][b.length];
    }

    function suggestion_champ(code) {
        const cible = code.toUpperCase();
        let meilleur = null;
        let meilleure_distance = Infinity;
        CODES_CONNUS.forEach(function (c) {
            const d = distance_edition(cible, c);
            if (d < meilleure_distance) { meilleure_distance = d; meilleur = c; }
        });
        return meilleure_distance <= Math.max(2, Math.floor(code.length * 0.25)) ? meilleur : null;
    }

    function maj_controle_champs() {
        objets_champs_inconnus = canvas.getObjects().filter(function (o) { return champs_inconnus(o).length > 0; });
        const total = tous_les_champs_inconnus().length;
        $("#statut_champs").toggle(total > 0)
            .html('<i class="fa fa-exclamation-triangle margin-r-5"></i>' + total + (total > 1 ? " champs non reconnus" : " champ non reconnu"));
    }

    function maj_alerte_champs() {
        const objets = canvas.getActiveObjects();
        const $zone = $("#prop_alerte_champs").empty().hide();
        if (objets.length !== 1) { return; }
        const objet = objets[0];
        champs_inconnus(objet).forEach(function (code) {
            const $alerte = $("<div class='alerte-champ'>")
                .append($("<code>").text(code))
                .append(document.createTextNode(" n'est pas reconnu et sera imprimé vide."));
            const proposition = suggestion_champ(code);
            if (proposition) {
                $alerte.append("<br>").append($("<a href='#'>").text("Remplacer par " + proposition)
                    .attr("data-remplacer", code).attr("data-par", proposition));
            }
            $zone.append($alerte).show();
        });
    }

    function definir_contenu(objet, contenu) {
        if (objet.categorie === "qrcode") {
            objet.qr_contenu = contenu;
            if (canvas.getActiveObject() === objet) { $("#objet_qr_contenu").val(contenu); }
            return;
        }
        if (objet.__texte_modele !== undefined) {
            retirer_apercu(objet);
            objet.set("text", contenu);
            appliquer_apercu(objet);
        } else {
            objet.set("text", contenu);
            surligner_champs(objet);
        }
    }

    $("#prop_alerte_champs").on("click", "a[data-remplacer]", function (e) {
        e.preventDefault();
        const objet = canvas.getActiveObject();
        if (!objet) { return; }
        definir_contenu(objet, contenu_avec_champs(objet).split($(this).attr("data-remplacer")).join($(this).attr("data-par")));
        canvas.requestRenderAll();
        enregistrer_historique();
        maj_panneau();
    });

    $("#statut_champs").on("click", function (e) {
        e.preventDefault();
        if (!objets_champs_inconnus.length) { return; }
        const objet = objets_champs_inconnus[0];
        if (objet.visible === false) { objet.visible = true; maj_calques(); }
        selectionner([objet]);
        $("#onglet_proprietes").tab("show");
    });

    // ------------------------------------------------------------------------
    // Aperçu avec données d'exemple (affichage seulement)
    // ------------------------------------------------------------------------

    function appliquer_apercu(objet) {
        if (objet.categorie !== "texte" || typeof objet.text !== "string" || objet.__texte_modele !== undefined) { return; }
        const modele = objet.text;
        const styles = {};
        const lignes = modele.split("\n").map(function (ligne, num_ligne) {
            let resultat = "";
            let dernier = 0;
            let m;
            REGEX_CHAMP.lastIndex = 0;
            while ((m = REGEX_CHAMP.exec(ligne)) !== null) {
                resultat += ligne.slice(dernier, m.index);
                const code = m[0];
                const exemple = EXEMPLES[code];
                const remplacement = exemple !== undefined ? exemple : code;
                const couleur = exemple !== undefined ? COULEUR_EXEMPLE : ((objet.__fond || champ_reconnu(code)) ? COULEUR_CHAMP : COULEUR_CHAMP_INCONNU);
                for (let c = resultat.length; c < resultat.length + remplacement.length; c++) {
                    styles[num_ligne] = styles[num_ligne] || {};
                    styles[num_ligne][c] = {textBackgroundColor: couleur};
                }
                resultat += remplacement;
                dernier = m.index + code.length;
            }
            return resultat + ligne.slice(dernier);
        });
        objet.__texte_modele = modele;
        objet.set({text: lignes.join("\n"), editable: false});
        objet.styles = styles;
        objet.dirty = true;
        objet.setCoords();
    }

    function retirer_apercu(objet) {
        if (objet.__texte_modele === undefined) { return; }
        const modele = objet.__texte_modele;
        delete objet.__texte_modele;
        objet.set({text: modele, editable: true});
        surligner_champs(objet);
        objet.setCoords();
    }

    function basculer_apercu(etat) {
        if (etat === apercu_exemples) { return; }
        quitter_edition_texte();
        apercu_exemples = etat;
        const fond = canvas.backgroundImage && canvas.backgroundImage._objects ? canvas.backgroundImage._objects : [];
        canvas.getObjects().concat(fond).forEach(function (o) {
            if (etat) { appliquer_apercu(o); } else { retirer_apercu(o); }
        });
        $("#bascule_apercu .btn").each(function () {
            $(this).toggleClass("active", ($(this).data("apercu") === 1) === etat);
        });
        $("#bascule_apercu_unique").toggleClass("active", etat)
            .attr("title", etat ? "Revenir à l'affichage des champs" : "Afficher des données d'exemple à la place des champs");
        canvas.requestRenderAll();
        maj_panneau();
    }

    $("#bascule_apercu .btn").on("click", function () { basculer_apercu($(this).data("apercu") === 1); });
    $("#bascule_apercu_unique").on("click", function () { basculer_apercu(!apercu_exemples); });

    // Double-clic sur un texte en mode aperçu : retour aux champs et édition
    canvas.on("mouse:dblclick", function (opt) {
        if (apercu_exemples && opt.target && opt.target.categorie === "texte") {
            editer_texte(opt.target);
            toastr.info("L'aperçu des exemples a été désactivé pour modifier le texte.");
        }
    });

    // ------------------------------------------------------------------------
    // QR code
    // ------------------------------------------------------------------------

    function memoriser_curseur_qr() {
        const zone = $("#objet_qr_contenu")[0];
        curseur_qr = {objet: canvas.getActiveObject(), debut: zone.selectionStart, fin: zone.selectionEnd};
    }

    function inserer_champ_qrcode(objet, code) {
        const contenu = objet.qr_contenu || "";
        let debut = contenu.length;
        let fin = contenu.length;
        if (curseur_qr && curseur_qr.objet === objet && curseur_qr.debut <= contenu.length) {
            debut = curseur_qr.debut;
            fin = curseur_qr.fin;
        }
        const nouveau = contenu.slice(0, debut) + code + contenu.slice(fin);
        if (canvas.getActiveObject() !== objet) { canvas.setActiveObject(objet); }
        objet.qr_contenu = nouveau;
        curseur_qr = {objet: objet, debut: debut + code.length, fin: debut + code.length};
        const zone = $("#objet_qr_contenu").val(nouveau)[0];
        if ($(zone).is(":visible")) {
            zone.focus();
            zone.setSelectionRange(curseur_qr.debut, curseur_qr.fin);
        } else {
            toastr.success(code + " ajouté au contenu du QR code.");
        }
        enregistrer_historique();
        maj_panneau();
    }

    $("#objet_qr_contenu")
        .on("input", function () {
            const objet = canvas.getActiveObject();
            if (!objet || objet.categorie !== "qrcode") { return; }
            objet.qr_contenu = this.value;
            $("#qr_vide").toggle(!this.value.trim());
            memoriser_curseur_qr();
            maj_controle_champs();
            maj_alerte_champs();
            enregistrer_historique_differe(600);
        })
        .on("keyup click select blur", memoriser_curseur_qr);

    $("#objet_qr_correction").on("change", function () {
        const valeur = this.value;
        appliquer(["qrcode"], function (o) { o.qr_correction = valeur; });
    });

    // ========================================================================
    // BARRE D'OUTILS ET OPTIONS D'AFFICHAGE
    // ========================================================================

    $("#bouton_annuler").on("click", annuler);
    $("#bouton_retablir").on("click", retablir);
    $("#bouton_dupliquer").on("click", dupliquer);
    $("#bouton_supprimer").on("click", supprimer);
    $("[data-ordre]").on("click", function () { changer_ordre($(this).data("ordre")); });
    $("[data-ordre-menu]").on("click", function (e) {
        e.preventDefault();
        changer_ordre($(this).data("ordre-menu"));
    }).each(function () {
        $(this).prepend(icone_ordre($(this).data("ordre-menu")));
    });
    $("#menu_ordre_bouton").append(icone_ordre("avancer"));

    // ------------------------------------------------------------------------
    // Barre d'outils sur une seule ligne : on active les paliers de compactage
    // dans l'ordre (p1 à p6) jusqu'à ce que tout tienne sur une ligne
    // ------------------------------------------------------------------------

    const NB_PALIERS = 6;
    const barre = document.querySelector(".editeur-barre");

    function barre_sur_une_ligne() {
        const elements = Array.prototype.filter.call(barre.children, function (e) { return e.offsetParent !== null; });
        if (!elements.length) { return true; }
        const haut = elements[0].offsetTop;
        return elements.every(function (e) { return Math.abs(e.offsetTop - haut) < 10; });
    }

    function adapter_barre() {
        for (let palier = 0; palier <= NB_PALIERS; palier++) {
            for (let n = 1; n <= NB_PALIERS; n++) { barre.classList.toggle("p" + n, n <= palier); }
            if (barre_sur_une_ligne()) { break; }
        }
    }

    let largeur_barre = 0;
    if (window.ResizeObserver) {
        // Relance si la largeur change, ou si un contenu (libellé du zoom, etc.) fait passer la barre sur deux lignes
        new ResizeObserver(function (entrees) {
            const largeur = Math.round(entrees[0].contentRect.width);
            if (largeur !== largeur_barre || !barre_sur_une_ligne()) {
                largeur_barre = largeur;
                adapter_barre();
                dimensionner_zone();
            }
        }).observe(barre);
    } else {
        $(window).on("resize", adapter_barre);
    }
    adapter_barre();
    $("#zoom_plus").on("click", function () { zoomer(canvas.getZoom() * 1.2); });
    $("#zoom_moins").on("click", function () { zoomer(canvas.getZoom() / 1.2); });
    $("[data-zoom]").on("click", function (e) {
        e.preventDefault();
        const valeur = $(this).data("zoom");
        if (valeur === "ajuster") { ajuster_page(); }
        else if (valeur === "largeur") { ajuster_largeur(); }
        else { zoomer(parseFloat(valeur) / 100 * PX_PAR_MM); }
    });
    $("#bouton_pdf").on("click", apercu_pdf);
    $("#bouton_raccourcis, [data-action=raccourcis]").on("click", function (e) {
        e.preventDefault();
        $(".editeur-menu-affichage").prev("[data-toggle=dropdown]").dropdown("hide");
        $("#modal_raccourcis").modal("show");
    });

    function appliquer_prefs_affichage() {
        $("#bascule_grille").toggleClass("active", prefs.grille);
        $("#bascule_magnetisme").toggleClass("active", prefs.magnetisme);
        $("#option_grille").prop("checked", prefs.grille);
        $("#option_magnetisme").prop("checked", prefs.magnetisme);
        $("#option_regles").prop("checked", prefs.regles);
        $("#option_marges").prop("checked", prefs.marges);
        $("#option_pas_grille").val(prefs.pas_grille);
        $("#option_marge").val(prefs.marge);
        $("#zone_editeur").toggleClass("sans-regles", !prefs.regles);
        canvas.requestRenderAll();
    }

    $("#bascule_grille").on("click", function () { prefs.grille = !prefs.grille; ecrire_prefs(); appliquer_prefs_affichage(); });
    $("#bascule_magnetisme").on("click", function () { prefs.magnetisme = !prefs.magnetisme; ecrire_prefs(); appliquer_prefs_affichage(); });
    $("#option_grille").on("change", function () { prefs.grille = this.checked; ecrire_prefs(); appliquer_prefs_affichage(); });
    $("#option_magnetisme").on("change", function () { prefs.magnetisme = this.checked; ecrire_prefs(); appliquer_prefs_affichage(); });
    $("#option_regles").on("change", function () { prefs.regles = this.checked; ecrire_prefs(); appliquer_prefs_affichage(); });
    $("#option_marges").on("change", function () { prefs.marges = this.checked; ecrire_prefs(); appliquer_prefs_affichage(); });
    $("#option_pas_grille").on("change", function () {
        prefs.pas_grille = limiter(lire_nombre(this.value) || 5, 1, 50);
        ecrire_prefs();
        appliquer_prefs_affichage();
    });
    $("#option_marge").on("change", function () {
        prefs.marge = limiter(lire_nombre(this.value) || 0, 0, 50);
        ecrire_prefs();
        appliquer_prefs_affichage();
    });
    $(".editeur-menu-affichage").on("click", function (e) { e.stopPropagation(); });

    // ========================================================================
    // MENU CONTEXTUEL
    // ========================================================================

    const LIBELLES_ALIGNEMENT = {selection: "Aligner", page: "Aligner sur la page", marges: "Aligner sur les marges"};

    function construire_menu(items) {
        const $menu = $("<div class='ctx-menu' role='menu'>");
        items.forEach(function (item) {
            if (item === "-") {
                $menu.append("<div class='ctx-separateur' role='separator'></div>");
                return;
            }
            const $bouton = $("<button type='button' class='ctx-item' role='menuitem' tabindex='-1'>")
                .toggleClass("ctx-danger", !!item.danger)
                .prop("disabled", !!item.desactive)
                .append(item.icone_svg
                    ? $(item.icone_svg).addClass("ctx-icone")
                    : $("<i class='fa fa-fw ctx-icone'>").addClass(item.coche === false ? "" : (item.coche ? "fa-check" : (item.icone || ""))))
                .append($("<span class='ctx-libelle'>").text(item.libelle));
            if (item.sous_menu) {
                $bouton.addClass("ctx-parent").attr("aria-haspopup", "true").append("<i class='fa fa-angle-right ctx-fleche'></i>");
                $("<div class='ctx-groupe'>").append($bouton).append(construire_menu(item.sous_menu)).appendTo($menu);
            } else {
                if (item.raccourci) { $bouton.append($("<span class='ctx-raccourci'>").text(item.raccourci)); }
                $bouton.on("click", function () {
                    fermer_menu();
                    item.action();
                });
                $menu.append($bouton);
            }
        });
        return $menu;
    }

    function fermer_menu() {
        $(".editeur-menu-contextuel").remove();
        $(document).off(".menu_contextuel");
        $(window).off(".menu_contextuel");
    }

    function ouvrir_menu(items, x, y) {
        fermer_menu();
        const $menu = construire_menu(items).addClass("editeur-menu-contextuel").attr("tabindex", "-1").appendTo("body");
        const largeur = $menu.outerWidth();
        const hauteur = $menu.outerHeight();
        if (x + largeur > window.innerWidth - 4) { x = Math.max(4, x - largeur); }
        if (y + hauteur > window.innerHeight - 4) { y = Math.max(4, window.innerHeight - hauteur - 4); }
        // Sous-menus ouverts à gauche s'il n'y a pas la place à droite
        $menu.toggleClass("ctx-vers-gauche", x + largeur * 2 > window.innerWidth);
        $menu.css({left: x, top: y}).trigger("focus");

        $menu.on("contextmenu", function (e) { e.preventDefault(); });
        $menu.on("keydown", navigation_menu);
        setTimeout(function () {
            $(document).on("mousedown.menu_contextuel", function (e) {
                if (!$(e.target).closest(".editeur-menu-contextuel").length) { fermer_menu(); }
            });
            $(window).on("blur.menu_contextuel resize.menu_contextuel wheel.menu_contextuel", fermer_menu);
        }, 0);
    }

    function navigation_menu(e) {
        const $courant = $(document.activeElement).closest(".ctx-item");
        const $menu = $courant.length ? $courant.closest(".ctx-menu") : $(".editeur-menu-contextuel");
        const $items = $menu.children(".ctx-item, .ctx-groupe").map(function () {
            return $(this).is(".ctx-groupe") ? $(this).children(".ctx-item")[0] : this;
        }).filter(":not(:disabled)");
        const index = $items.index($courant);
        let traite = true;
        if (e.key === "Escape") { fermer_menu(); }
        else if (e.key === "ArrowDown") { $items.eq((index + 1) % $items.length).trigger("focus"); }
        else if (e.key === "ArrowUp") { $items.eq(index <= 0 ? $items.length - 1 : index - 1).trigger("focus"); }
        else if (e.key === "ArrowRight" && $courant.hasClass("ctx-parent")) { $courant.next(".ctx-menu").find(".ctx-item:not(:disabled)").first().trigger("focus"); }
        else if (e.key === "ArrowLeft" && $menu.parent().hasClass("ctx-groupe")) { $menu.prev(".ctx-item").trigger("focus"); }
        else if ((e.key === "Enter" || e.key === " ") && $courant.length && !$courant.hasClass("ctx-parent")) { $courant.trigger("click"); }
        else { traite = false; }
        if (traite) { e.preventDefault(); e.stopPropagation(); }
    }

    // Les icônes d'ordre sont définies une seule fois, dans les boutons de la barre d'outils
    function icone_ordre(action) {
        return $("[data-ordre=" + action + "] svg").first().clone();
    }

    function items_objet() {
        const objets = canvas.getActiveObjects();
        const unique = objets.length === 1 ? objets[0] : null;
        const verrouille = objets.some(function (o) { return o.verrouille; });
        const items = [];
        if (unique && unique.categorie === "texte") {
            items.push({libelle: "Modifier le texte", icone: "fa-pencil", action: function () { editer_texte(unique); }});
            items.push({libelle: "Insérer un champ", icone: "fa-code", action: function () {
                $("#onglet_champs").tab("show");
                setTimeout(function () { $("#champs_recherche").trigger("focus"); }, 150);
            }});
        }
        if (unique && unique.categorie === "qrcode") {
            items.push({libelle: "Modifier le contenu", icone: "fa-pencil", action: function () {
                $("#onglet_proprietes").tab("show");
                setTimeout(function () { $("#objet_qr_contenu").trigger("focus"); }, 150);
            }});
        }
        if (unique) {
            items.push({libelle: "Renommer", icone: "fa-i-cursor", action: renommer});
        }
        if (items.length) { items.push("-"); }

        const alignements = [
            {libelle: "À gauche", icone: "fa-align-left", action: function () { aligner("gauche"); }},
            {libelle: "Centrer horizontalement", icone: "fa-align-center", action: function () { aligner("centre_h"); }},
            {libelle: "À droite", icone: "fa-align-right", action: function () { aligner("droite"); }},
            "-",
            {libelle: "En haut", icone: "fa-long-arrow-up", action: function () { aligner("haut"); }},
            {libelle: "Centrer verticalement", icone: "fa-arrows-v", action: function () { aligner("centre_v"); }},
            {libelle: "En bas", icone: "fa-long-arrow-down", action: function () { aligner("bas"); }},
        ];
        if (objets.length >= 3) {
            alignements.push("-",
                {libelle: "Répartir horizontalement", icone: "fa-arrows-h", action: function () { aligner("repartir_h"); }},
                {libelle: "Répartir verticalement", icone: "fa-arrows-v", action: function () { aligner("repartir_v"); }});
        }

        items.push(
            {libelle: "Couper", icone: "fa-scissors", raccourci: "Ctrl+X", desactive: verrouille, action: couper},
            {libelle: "Copier", icone: "fa-files-o", raccourci: "Ctrl+C", action: copier},
            {libelle: "Coller", icone: "fa-clipboard", raccourci: "Ctrl+V", desactive: !presse_papier, action: function () { coller(); }},
            {libelle: "Dupliquer", icone: "fa-clone", raccourci: "Ctrl+D", action: dupliquer},
            "-",
            {libelle: "Ordre", icone_svg: icone_ordre("avancer"), sous_menu: [
                {libelle: "Premier plan", icone_svg: icone_ordre("devant"), action: function () { changer_ordre("devant"); }},
                {libelle: "Avancer", icone_svg: icone_ordre("avancer"), action: function () { changer_ordre("avancer"); }},
                {libelle: "Reculer", icone_svg: icone_ordre("reculer"), action: function () { changer_ordre("reculer"); }},
                {libelle: "Arrière-plan", icone_svg: icone_ordre("derriere"), action: function () { changer_ordre("derriere"); }},
            ]},
            {libelle: LIBELLES_ALIGNEMENT[$("#alignement_reference").val()] || "Aligner", icone: "fa-align-left", desactive: objets.every(function (o) { return o.verrouille; }), sous_menu: alignements},
            "-",
            {libelle: objets.every(function (o) { return o.verrouille; }) ? "Déverrouiller" : "Verrouiller", icone: objets.every(function (o) { return o.verrouille; }) ? "fa-unlock" : "fa-lock", action: basculer_verrou},
            {libelle: "Masquer (non imprimé)", icone: "fa-eye-slash", desactive: objets.every(function (o) { return o.categorie === "special"; }), action: masquer_selection},
            "-",
            {libelle: "Supprimer", icone: "fa-trash-o", raccourci: "Suppr", danger: true, desactive: verrouille, action: supprimer}
        );
        return items;
    }

    function items_page(point) {
        return [
            {libelle: "Coller ici", icone: "fa-clipboard", raccourci: "Ctrl+V", desactive: !presse_papier, action: function () { coller(point); }},
            {libelle: "Ajouter ici", icone: "fa-plus", sous_menu: [
                {libelle: "Texte", icone: "fa-font", action: function () { ajouts.texte(null, point); }},
                {libelle: "Rectangle", icone: "fa-square-o", action: function () { ajouts.rectangle(null, point); }},
                {libelle: "Cercle", icone: "fa-circle-thin", action: function () { ajouts.cercle(null, point); }},
                {libelle: "Ligne", icone: "fa-minus", action: function () { ajouts.ligne(null, point); }},
                "-",
                {libelle: "QR code", icone: "fa-qrcode", action: function () { ajouts.qrcode(null, point); }},
            ]},
            {libelle: "Tout sélectionner", icone: "fa-object-group", raccourci: "Ctrl+A", desactive: !canvas.getObjects().length, action: tout_selectionner},
            "-",
            {libelle: "Aperçu avec exemples", coche: apercu_exemples, desactive: !liste_champs().length, action: function () { basculer_apercu(!apercu_exemples); }},
            {libelle: "Grille", coche: prefs.grille, action: function () { $("#bascule_grille").trigger("click"); }},
            {libelle: "Magnétisme", coche: prefs.magnetisme, action: function () { $("#bascule_magnetisme").trigger("click"); }},
            {libelle: "Règles", coche: prefs.regles, action: function () { $("#option_regles").prop("checked", !prefs.regles).trigger("change"); }},
            {libelle: "Ajuster à la page", icone: "fa-arrows-alt", raccourci: "Ctrl+0", action: ajuster_page},
            "-",
            {libelle: "Aperçu PDF", icone: "fa-file-pdf-o", action: apercu_pdf},
        ];
    }

    function ouvrir_menu_canvas(cible, point, x, y) {
        const actif = canvas.getActiveObject();
        if (actif && actif.isEditing && cible !== actif) { actif.exitEditing(); }
        if (cible) {
            if (cible !== actif && canvas.getActiveObjects().indexOf(cible) < 0) {
                canvas.setActiveObject(cible);
                canvas.requestRenderAll();
            }
            ouvrir_menu(items_objet(), x, y);
        } else {
            if (actif) {
                canvas.discardActiveObject();
                canvas.requestRenderAll();
            }
            ouvrir_menu(items_page(point), x, y);
        }
    }

    // Ouverture au clavier (touche Menu ou Maj+F10) sur la sélection, sinon au centre de la vue
    function ouvrir_menu_clavier() {
        const rect = canvas.upperCanvasEl.getBoundingClientRect();
        const actif = canvas.getActiveObject();
        if (actif) {
            const r = actif.getBoundingRect(false, true);
            ouvrir_menu(items_objet(), rect.left + r.left + r.width / 2, rect.top + r.top + r.height / 2);
        } else {
            ouvrir_menu(items_page(centre_visible()), rect.left + rect.width / 2, rect.top + rect.height / 2);
        }
        $(".editeur-menu-contextuel .ctx-item:not(:disabled)").first().trigger("focus");
    }

    // ========================================================================
    // CLAVIER
    // ========================================================================

    $(document).on("keydown", function (e) {
        // Espace maintenu : déplacement de la vue
        if ($(e.target).closest(".editeur-menu-contextuel").length) { return; }
        if (e.key === " " && !est_saisie(e.target)) {
            if (!espace_presse) { activer_mode_main(true); }
            e.preventDefault();
            return;
        }
        // Aucun raccourci pendant une saisie (dont l'édition d'un texte du canvas) ou avec une fenêtre ouverte
        if (est_saisie(e.target) || $(".modal.show").length) { return; }

        const ctrl = e.ctrlKey || e.metaKey;
        const touche = (e.key || "").toLowerCase();
        let traite = true;

        if (ctrl && !e.altKey) {
            if (touche === "z") { if (e.shiftKey) { retablir(); } else { annuler(); } }
            else if (touche === "y") { retablir(); }
            else if (touche === "c") { traite = copier(); }
            else if (touche === "x") { traite = couper(); }
            else if (touche === "v") { traite = coller(); }
            else if (touche === "d") { traite = dupliquer(); }
            else if (touche === "a") { tout_selectionner(); }
            else if (touche === "s") { enregistrer_modele(); }
            else if (touche === "0") { ajuster_page(); }
            else if (touche === "+" || touche === "=") { zoomer(canvas.getZoom() * 1.2); }
            else if (touche === "-") { zoomer(canvas.getZoom() / 1.2); }
            else { traite = false; }
        } else {
            const pas = e.shiftKey ? 10 : 1;
            if (e.key === "Delete" || e.key === "Backspace") { traite = canvas.getActiveObjects().length > 0; supprimer(); }
            else if (e.key === "Escape") { canvas.discardActiveObject(); canvas.requestRenderAll(); }
            else if (e.key === "ArrowLeft") { traite = !!canvas.getActiveObject(); deplacer(-pas, 0); }
            else if (e.key === "ArrowRight") { traite = !!canvas.getActiveObject(); deplacer(pas, 0); }
            else if (e.key === "ArrowUp") { traite = !!canvas.getActiveObject(); deplacer(0, -pas); }
            else if (e.key === "ArrowDown") { traite = !!canvas.getActiveObject(); deplacer(0, pas); }
            else if (e.key === "?") { $("#modal_raccourcis").modal("show"); }
            else if (e.key === "ContextMenu" || (e.key === "F10" && e.shiftKey)) { ouvrir_menu_clavier(); }
            else { traite = false; }
        }
        if (traite) { e.preventDefault(); }
    });

    $(document).on("keyup", function (e) {
        if (e.key === " " && espace_presse) { activer_mode_main(false); }
    });
    $(window).on("blur", function () {
        if (espace_presse) { activer_mode_main(false); }
    });

    // ========================================================================
    // FORMULAIRE, APERÇU PDF ET ENREGISTREMENT
    // ========================================================================

    function quitter_edition_texte() {
        const actif = canvas.getActiveObject();
        if (actif && actif.isEditing) { actif.exitEditing(); }
    }

    function enregistrer_modele() {
        $("#bouton_enregistrer").trigger("click");
    }

    $("#modeles_documents_form").on("submit", function () {
        quitter_edition_texte();
        const inconnus = tous_les_champs_inconnus();
        if (inconnus.length) {
            const message = (inconnus.length > 1 ? "Ces champs ne sont pas reconnus" : "Ce champ n'est pas reconnu") +
                " et sera" + (inconnus.length > 1 ? "nt" : "") + " imprimé" + (inconnus.length > 1 ? "s" : "") + " vide" + (inconnus.length > 1 ? "s" : "") +
                " :\n\n" + inconnus.join("\n") + "\n\nEnregistrer quand même ?";
            if (!window.confirm(message)) { return false; }
        }
        canvas.discardActiveObject();
        $("#id_objets").val(JSON.stringify(serialiser()));
        soumission = true;
        return true;
    });

    $("#modeles_documents_form").on("input change", ":input", function () {
        if (this.id === "id_objets") { return; }
        formulaire_modifie = true;
        maj_historique_ui();
    });

    function apercu_pdf() {
        quitter_edition_texte();
        $.ajax({
            type: "POST",
            url: CFG.url_export_pdf,
            data: {
                objets_json: JSON.stringify(serialiser()),
                id_fond: $("#id_fond").val(),
                largeur: $("#id_largeur").val(),
                hauteur: $("#id_hauteur").val(),
                nom: $("#id_nom").val(),
            },
            datatype: "json",
            success: function (data) { charge_pdf(data); },
            error: function (data) {
                toastr.error((data.responseJSON && data.responseJSON.erreur) || "Impossible de générer l'aperçu PDF.");
            },
        });
    }

    const FORMATS_PAGE = {A3: [297, 420], A4: [210, 297], A5: [148, 210], A6: [105, 148]};

    // Format standard correspondant aux dimensions actuelles : {nom, orientation} ou null
    function format_page() {
        const W = largeur_page();
        const H = hauteur_page();
        let resultat = null;
        Object.keys(FORMATS_PAGE).forEach(function (f) {
            if (W === FORMATS_PAGE[f][0] && H === FORMATS_PAGE[f][1]) { resultat = {nom: f, orientation: "portrait"}; }
            if (W === FORMATS_PAGE[f][1] && H === FORMATS_PAGE[f][0]) { resultat = {nom: f, orientation: "paysage"}; }
        });
        return resultat;
    }

    function maj_statut_page() {
        const format = format_page();
        $("#statut_page").text((format ? format.nom + " " + format.orientation : "Format personnalisé") + " · " + fmt(largeur_page()) + " × " + fmt(hauteur_page()) + " mm");
        $("#modele_format").val(format ? format.nom : "");
    }

    function definir_dimensions_page(largeur, hauteur) {
        $("#id_largeur").val(largeur);
        $("#id_hauteur").val(hauteur).trigger("change");
        if (vue_automatique) { ajuster_page(); }
    }

    $("#id_largeur, #id_hauteur").on("input change", function () {
        dessiner_fond();
        maj_statut_page();
        planifier_regles();
    });

    // Liste des formats : remplit largeur et hauteur en conservant l'orientation
    $("#modele_format").on("change", function () {
        const dims = FORMATS_PAGE[this.value];
        if (!dims) { $("#id_largeur").trigger("focus"); return; }
        const paysage = largeur_page() > hauteur_page();
        definir_dimensions_page(paysage ? dims[1] : dims[0], paysage ? dims[0] : dims[1]);
    });

    $("#modele_pivoter").on("click", function () {
        definir_dimensions_page(hauteur_page(), largeur_page());
    });

    // Mode consultation : les aides de format suivent l'état des champs
    if ($("#id_largeur").prop("disabled")) {
        $("#modele_format, #modele_pivoter").prop("disabled", true);
    }
    $("#id_fond").on("change", charger_fond);

    // ========================================================================
    // INITIALISATION
    // ========================================================================

    appliquer_prefs_affichage();
    maj_couleurs_recentes();
    maj_statut_page();
    dessiner_fond([]);
    charger_fond();
    rendre_champs();
    maj_panneau();
    maj_historique_ui();
    chargement_initial();

    dimensionner_zone();
    redimensionner_canvas();
    new ResizeSensor(document.getElementById("div_canvas"), redimensionner_canvas);
    $(window).on("resize", dimensionner_zone);
    // La carte "Modèle" repliable peut décaler la zone : on recalcule après les animations
    $(document).on("expanded.lte.cardwidget collapsed.lte.cardwidget", function () { setTimeout(dimensionner_zone, 50); });
    // Le cadre "Modèle" peut changer de hauteur (erreurs de saisie, listes repliées sur deux lignes)
    if (window.ResizeObserver) {
        new ResizeObserver(ajuster_panneau).observe(document.getElementById("caracteristiques_modele"));
    }

})(jQuery);
